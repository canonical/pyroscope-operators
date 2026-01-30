#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed Operator for Pyroscope; a lightweight object storage based profiling backend."""

import logging
import socket
from typing import Optional

from charms.catalogue_k8s.v1.catalogue import CatalogueItem
from charms.grafana_k8s.v0.grafana_source import GrafanaSourceProvider
from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointProvider
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
from coordinated_workers.coordinator import Coordinator
from coordinated_workers.nginx import NginxConfig, CA_CERT_PATH, CERT_PATH, KEY_PATH
from ops import BlockedStatus, CollectStatusEvent
from ops.charm import CharmBase

import nginx_config
import traefik_config
from charm_config import (
    CharmConfig,
    CharmConfigInvalidError,
    PyroscopeCoordinatorConfigModel,
)
from peers import Peers, PEERS_RELATION_ENDPOINT_NAME
from pyroscope import Pyroscope
from pyroscope_config import PYROSCOPE_ROLES_CONFIG
from cosl.reconciler import all_events, observe_events

logger = logging.getLogger(__name__)

DISABLED_DATA_CLEANUP_CHARM_CONFIG = CharmConfig(
    pyroscope_charm_config_model=PyroscopeCoordinatorConfigModel(
        **{"retention_period": "0", "deletion_delay": "0", "cleanup_interval": "15m"}
    )
)
PYROSCOPE_GRAFANA_DATASOURCE_TYPE = "grafana-pyroscope-datasource"


class PyroscopeCoordinator(Coordinator):
    def __init__(self, *args, active_status_msg: str = "ready", **kwargs):
        super().__init__(*args, **kwargs)
        self._active_status_msg = active_status_msg

    @property
    def _default_active_message(self) -> str:
        return self._active_status_msg

    @property
    def _default_degraded_message(self) -> str:
        return "[degraded] " + self._active_status_msg


class PyroscopeCoordinatorCharm(CharmBase):
    """Charmed Operator for Pyroscope; a distributed profiling backend."""

    def __init__(self, *args):
        super().__init__(*args)
        self._ingress_prefix = f"/{self.model.name}-{self.app.name}"
        self._peers = Peers(
            self.model.get_relation(PEERS_RELATION_ENDPOINT_NAME),
            self.hostname,
            self.unit,
        )

        self._nginx_container = self.unit.get_container("nginx")
        self._nginx_prometheus_exporter_container = self.unit.get_container(
            "nginx-prometheus-exporter"
        )
        self.ingress = TraefikRouteRequirer(
            self,
            self.model.get_relation("ingress"),  # type: ignore
            "ingress",
        )
        self.grafana_source = GrafanaSourceProvider(
            self,
            source_type=PYROSCOPE_GRAFANA_DATASOURCE_TYPE,
            is_ingress_per_app=self._is_ingressed,
        )
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError as e:
            logger.warning(f"{e.msg}\nDisabling profiles cleanup to prevent data loss.")
            self._charm_config = DISABLED_DATA_CLEANUP_CHARM_CONFIG
        self.pyroscope = Pyroscope(
            external_url=self._most_external_http_url,
            charm_config=self._charm_config,
        )
        self.profiling_provider = ProfilingEndpointProvider(
            self.model.relations["profiling"], self.app
        )
        self.coordinator = PyroscopeCoordinator(
            charm=self,
            roles_config=PYROSCOPE_ROLES_CONFIG,
            external_url=self._most_external_http_url,
            worker_metrics_port=Pyroscope.http_server_port,
            endpoints={
                "certificates": "certificates",
                "cluster": "pyroscope-cluster",
                "grafana-dashboards": "grafana-dashboard",
                "logging": "logging",
                "metrics": "metrics-endpoint",
                "s3": "s3",
                "charm-tracing": "charm-tracing",
                "workload-tracing": "workload-tracing",
                "send-datasource": "send-datasource",
                "receive-datasource": None,
                "catalogue": "catalogue",
            },
            nginx_config=NginxConfig(
                server_name=self.hostname,
                upstream_configs=nginx_config.upstreams(Pyroscope.http_server_port),
                server_ports_to_locations=nginx_config.server_ports_to_locations(),
                enable_status_page=True,
            ),
            workers_config=self.pyroscope.config,
            worker_ports=lambda role: (
                Pyroscope.memberlist_port,
                # we need http_server_port because the metrics server runs on it.
                Pyroscope.http_server_port,
            ),
            workload_tracing_protocols=["jaeger_thrift_http"],
            container_name="nginx",
            resources_requests=lambda _: {"cpu": "50m", "memory": "100Mi"},
            catalogue_item=self._catalogue_item,
            active_status_msg=self._active_status_msg,
        )

        # do this regardless of what event we are processing
        observe_events(self, all_events, self._reconcile)
        self.framework.observe(
            self.on.collect_unit_status, self._on_collect_unit_status
        )

    ######################
    # UTILITY PROPERTIES #
    ######################
    @property
    def hostname(self) -> str:
        """Unit's hostname."""
        return socket.getfqdn()

    @property
    def app_hostname(self) -> str:
        """Application-level fqdn."""
        return Coordinator.app_hostname(
            hostname=self.hostname, app_name=self.app.name, model_name=self.model.name
        )

    @property
    def _is_ingressed(self) -> bool:
        """Return True if an ingress is configured and ready, otherwise False."""
        return bool(
            self.ingress.is_ready()
            and self.ingress.scheme
            and self.ingress.external_host
        )

    @property
    def _is_external_url_tls(self) -> bool:
        """Return True if an ingress is configured and is configured with TLS, otherwise False."""
        external_http_url = self._external_http_url
        if external_http_url and external_http_url.startswith("https://"):
            return True
        return False

    @property
    def _external_http_url(self) -> Optional[str]:
        """Return the external URL if the ingress is configured and ready, otherwise None."""
        if self._is_ingressed:
            ingress_url = f"{self.ingress.scheme}://{self.ingress.external_host}{self._ingress_prefix}"
            logger.debug("This unit's ingress URL: %s", ingress_url)
            return ingress_url
        return None

    @property
    def _external_grpc_url(self) -> Optional[str]:
        """Return the external grpc server URL if the ingress is configured and ready, otherwise None."""
        if self._is_ingressed:
            ingress_url = (
                f"{self.ingress.external_host}:{nginx_config.grpc_server_port}"
            )
            logger.debug("This unit's grpc server ingress URL: %s", ingress_url)
            return ingress_url

        return None

    @property
    def _scheme(self) -> str:
        """Return the URI scheme that should be used when communicating with this unit."""
        return "https" if self._are_certificates_on_disk else "http"

    @property
    def _internal_http_url(self) -> str:
        """Return the locally addressable, FQDN based service address for the http server."""
        return f"{self._scheme}://{self.app_hostname}:{self._http_server_port}"

    @property
    def _internal_grpc_url(self) -> str:
        """Return the locally addressable, FQDN based service address for the grpc server."""
        return f"{self.app_hostname}:{nginx_config.grpc_server_port}"

    @property
    def _most_external_http_url(self) -> str:
        """Return the most external HTTP url known about by this charm.

        This will return the first of:
        - the external URL, if the ingress is configured and ready
        - the internal k8s service URL
        """
        return self._external_http_url or self._internal_http_url

    @property
    def _active_status_msg(self) -> str:
        return f"UI ready at {self._most_external_http_url}"

    @property
    def _most_external_grpc_url(self) -> str:
        """Return the most external grpc server url known about by this charm.

        This will return the first of:
        - the external URL, if the ingress is configured and ready
        - the internal k8s service URL
        """
        # If we do not have an ingress, then use the K8s service.
        return self._external_grpc_url or self._internal_grpc_url

    @property
    def _http_server_port(self) -> int:
        """The http port that we should open on this pod."""
        return nginx_config.http_server_port

    @property
    def _catalogue_item(self) -> CatalogueItem:
        """A catalogue application entry for this Pyroscope instance."""
        return CatalogueItem(
            # use app name in case there are multiple Pyroscope apps deployed.
            name=f"Pyroscope ({self.app.name})",
            icon="flame",
            url=self._most_external_http_url,
            description=(
                "Grafana Pyroscope is a distributed continuous profiling backend. "
                "Allows you to collect, store, query, and visualize profiles from your distributed deployment."
            ),
        )

    def _on_collect_unit_status(self, event: CollectStatusEvent):
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError as exc:
            self._charm_config = DISABLED_DATA_CLEANUP_CHARM_CONFIG
            event.add_status(BlockedStatus(exc.msg))
            return

    # TODO: use the coordinated_workers method
    # cfr https://github.com/canonical/cos-coordinated-workers/issues/54
    @property
    def _are_certificates_on_disk(self) -> bool:
        """Return True if the certificates files are on the nginx container's disk."""
        return (
            self._nginx_container.can_connect()
            and self._nginx_container.exists(CERT_PATH)
            and self._nginx_container.exists(KEY_PATH)
            and self._nginx_container.exists(CA_CERT_PATH)
        )

    def _reconcile(self):
        # This method contains unconditional update logic, i.e. logic that should be executed
        # regardless of the event we are processing.
        # reason is, if we miss these events because our coordinator cannot process events (inconsistent status),
        # we need to 'remember' to run this logic as soon as we become ready, which is hard and error-prone
        # open the necessary ports on this unit
        self.unit.set_ports(self._http_server_port, nginx_config.grpc_server_port)
        self._peers.reconcile()
        self._reconcile_ingress()
        self.profiling_provider.publish_endpoint(
            otlp_grpc_endpoint=self._most_external_grpc_url,
            # if ingress is configured, rely on its TLS config
            # otherwise check if internal TLS (certificates on disk) is configured.
            insecure=not (
                self._is_external_url_tls
                if self._is_ingressed
                else self._are_certificates_on_disk
            ),
        )
        self.grafana_source.update_source(self._most_external_http_url)

    def _reconcile_ingress(self):
        if not self.ingress.is_ready() or not self.unit.is_leader():
            return

        config = traefik_config.traefik_config(
            http_port=self._http_server_port,
            grpc_port=nginx_config.grpc_server_port,
            coordinator_fqdns=self._peers.get_fqdns(),
            model_name=self.model.name,
            app_name=self.app.name,
            tls=self._are_certificates_on_disk,
            prefix=self._ingress_prefix,
        )
        self.ingress.submit_to_traefik(config=config.dynamic, static=config.static)


if __name__ == "__main__":  # pragma: nocover
    from ops import main

    main(PyroscopeCoordinatorCharm)  # noqa
