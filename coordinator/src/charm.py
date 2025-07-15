#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed Operator for Pyroscope; a lightweight object storage based profiling backend."""

import logging
import socket
from typing import List, Optional, Set, Tuple

import ops
from charms.catalogue_k8s.v1.catalogue import CatalogueItem
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
from coordinated_workers.coordinator import Coordinator
from coordinated_workers.nginx import CA_CERT_PATH, CERT_PATH, KEY_PATH, NginxConfig
from cosl.interfaces.utils import DatabagModel
from ops.charm import CharmBase

import nginx_config
import traefik_config
from pyroscope import Pyroscope
from pyroscope_config import PYROSCOPE_ROLES_CONFIG

logger = logging.getLogger(__name__)

PEERS_RELATION_ENDPOINT_NAME = "peers"


class PeerData(DatabagModel):
    """Databag model for the "peers" relation between coordinator units."""

    fqdn: str
    """FQDN hostname of this coordinator unit."""


class PyroscopeCoordinatorCharm(CharmBase):
    """Charmed Operator for Pyroscope; a distributed profiling backend."""

    def __init__(self, *args):
        super().__init__(*args)

        self._nginx_container = self.unit.get_container("nginx")
        self._nginx_prometheus_exporter_container = self.unit.get_container(
            "nginx-prometheus-exporter"
        )
        self.ingress = TraefikRouteRequirer(
            self, self.model.get_relation("ingress"), "ingress"
        )  # type: ignore
        self.pyroscope = Pyroscope()
        self.coordinator = Coordinator(
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
                server_ports_to_locations=nginx_config.server_ports_to_locations(
                    tls_available=self._are_certificates_on_disk
                ),
                enable_status_page=True,
            ),
            workers_config=self.pyroscope.config,
            worker_ports=self._get_worker_ports,
            workload_tracing_protocols=["jaeger_thrift_http"],
            container_name="charm",
            resources_requests=lambda _: {"cpu": "50m", "memory": "100Mi"},
            catalogue_item=self._catalogue_item,
        )

        # do this regardless of what event we are processing
        self._reconcile()

        ######################################
        # === EVENT HANDLER REGISTRATION === #
        ######################################

    ######################
    # UTILITY PROPERTIES #
    ######################
    @property
    def hostname(self) -> str:
        """Unit's hostname."""
        return socket.getfqdn()

    @property
    def _external_http_url(self) -> Optional[str]:
        """Return the external URL if the ingress is configured and ready, otherwise None."""
        if (
            self.ingress.is_ready()
            and self.ingress.scheme
            and self.ingress.external_host
        ):
            ingress_url = f"{self.ingress.scheme}://{self.ingress.external_host}"
            logger.debug("This unit's ingress URL: %s", ingress_url)
            return ingress_url

        return None

    @property
    def service_hostname(self) -> str:
        """The FQDN of the k8s service associated with this application.

        This service load balances traffic across all application units.
        Falls back to this unit's DNS name if the hostname does not resolve to a Kubernetes-style fqdn.
        """
        # example: 'pyroscope-0.pyroscope-headless.default.svc.cluster.local'
        hostname = self.hostname
        hostname_parts = hostname.split(".")
        # 'svc' is always there in a K8s service fqdn
        # ref: https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/#services
        if "svc" not in hostname_parts:
            logger.debug(f"expected K8s-style fqdn, but got {hostname} instead")
            return hostname

        dns_name_parts = hostname_parts[hostname_parts.index("svc") :]
        dns_name = ".".join(dns_name_parts)  # 'svc.cluster.local'
        return f"{self.app.name}.{self.model.name}.{dns_name}"  # 'pyroscope.model.svc.cluster.local'

    @property
    def _scheme(self) -> str:
        """Return the URI scheme that should be used when communicating with this unit."""
        scheme = "http"
        # FIXME: add a check for are_certificates_on_disk
        return scheme

    @property
    def _internal_http_url(self) -> str:
        """Return the locally addressable, FQDN based service address."""
        return f"{self._scheme}://{self.service_hostname}:{self._http_server_port}"

    @property
    def _most_external_http_url(self) -> str:
        """Return the most external url known about by this charm.

        This will return the first of:
        - the external URL, if the ingress is configured and ready
        - the internal URL
        """
        external_url = self._external_http_url
        if external_url:
            return external_url
        # If we do not have an ingress, then use the K8s service.
        return self._internal_http_url

    @property
    def _are_certificates_on_disk(self) -> bool:
        return (
            self._nginx_container.can_connect()
            and self._nginx_container.exists(CERT_PATH)
            and self._nginx_container.exists(KEY_PATH)
            and self._nginx_container.exists(CA_CERT_PATH)
        )

    @property
    def _http_server_port(self) -> int:
        """The http port that we should open on this pod."""
        return (
            nginx_config.https_server_port
            if self._are_certificates_on_disk
            else nginx_config.http_server_port
        )

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

    ##################
    # EVENT HANDLERS #
    ##################

    ###################
    # UTILITY METHODS #
    ###################

    def _reconcile(self):
        # This method contains unconditional update logic, i.e. logic that should be executed
        # regardless of the event we are processing.
        # reason is, if we miss these events because our coordinator cannot process events (inconsistent status),
        # we need to 'remember' to run this logic as soon as we become ready, which is hard and error-prone
        # open the necessary ports on this unit
        self.unit.set_ports(self._http_server_port, nginx_config.grpc_server_port)
        self._reconcile_ingress()

    def _reconcile_ingress(self):
        if self.ingress.is_ready():
            endpoints = [
                traefik_config.Endpoint(
                    name="http_server", protocol="http", port=self._http_server_port
                ),
                traefik_config.Endpoint(
                    name="grpc_server",
                    protocol="grpc",
                    port=nginx_config.grpc_server_port,
                ),
            ]
            self.ingress.submit_to_traefik(
                traefik_config.ingress_config(
                    endpoints,
                    coordinator_fqdns=self._get_peer_fqdns(),
                    model_name=self.model.name,
                    app_name=self.app.name,
                    ingressed=self.ingress.is_ready,
                    tls=self._are_certificates_on_disk,
                ),
                static=traefik_config.static_ingress_config(endpoints),
            )

    def _get_worker_ports(self, role: str) -> Tuple[int, ...]:
        """Determine, from the role of a worker, which ports it should open."""
        ports: Set[int] = {
            Pyroscope.memberlist_port,
            # we need http_server_port because the metrics server runs on it.
            Pyroscope.http_server_port,
        }
        return tuple(ports)

    # peer relation: scaled-up coordinator units fqdn collection
    @property
    def peers(self):
        """Fetch the "peers" peer relation."""
        return self.model.get_relation(PEERS_RELATION_ENDPOINT_NAME)

    def _update_peer_data(self) -> None:
        """Update peer unit data bucket with this unit's hostname."""
        if self.peers and self.peers.data:
            PeerData(fqdn=self.hostname).dump(self.peers.data[self.unit])

    def _get_peer_data(self, unit: ops.Unit) -> Optional[PeerData]:
        """Get peer data from a given unit data bucket."""
        if not (self.peers and self.peers.data):
            return None

        return PeerData.load(self.peers.data.get(unit, {}))

    def _get_peer_fqdns(self) -> List[str]:
        """Obtain from peer data all peer unit fqdns."""
        return [self._get_peer_data(peer).fqdn for peer in self.peers.units] + [
            self.hostname
        ]


if __name__ == "__main__":  # pragma: nocover
    from ops import main

    main(PyroscopeCoordinatorCharm)  # noqa
