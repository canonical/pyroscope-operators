#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pyroscope workload management objects."""

import logging
import socket

from ops.charm import CharmBase
from coordinated_workers.worker import Worker, CONFIG_FILE
from ops.pebble import Layer

API_PORT = 4040
METASTORE_RAFT_PORT = 9099


logger = logging.getLogger(__name__)


class PyroscopeWorker:
    _name = "pyroscope"

    def __init__(self, charm: CharmBase):
        self._worker = Worker(
            charm=charm,
            name=self._name,
            pebble_layer=self.layer,
            endpoints={"cluster": "pyroscope-cluster"},
            readiness_check_endpoint=self.readiness_check_endpoint,
            container_name=self._name,
            # each worker needs different resources.
            # we set minimal requests just to ensure scheduling — won’t affect actual performance since limits handle that.
            # cfr. https://github.com/grafana/pyroscope/blob/v2.2.0/operations/pyroscope/helm/pyroscope/values-micro-services.yaml
            resources_requests=lambda _: {"cpu": "100m", "memory": "256Mi"},
        )

    @staticmethod
    def layer(worker: Worker) -> Layer:
        """Return the Pebble layer for the Worker.

        This method assumes that worker.roles is valid.
        """
        # Configure Pyroscope workload traces
        env = {}
        if tempo_endpoint := worker.cluster.get_workload_tracing_receivers().get(
            "jaeger_thrift_http", None
        ):
            topology = worker.cluster.juju_topology
            # TODO once https://github.com/grafana/pyroscope/issues/4127 is implemented, switch to otel envvars
            env.update(
                {
                    "JAEGER_ENDPOINT": (
                        f"{tempo_endpoint}/api/traces?format=jaeger.thrift"
                    ),
                    "JAEGER_SAMPLER_PARAM": "1",
                    "JAEGER_SAMPLER_TYPE": "const",
                    "JAEGER_TAGS": f"juju_application={topology.application},juju_model={topology.model}"
                    + f",juju_model_uuid={topology.model_uuid},juju_unit={topology.unit},juju_charm={topology.charm_name}",
                }
            )

        roles = worker.roles
        # sort the roles to avoid unnecessary replans
        roles = sorted(roles)

        # -architecture.storage=v2 selects the v2 object-storage path (default is dual)
        command = (
            f"/usr/bin/pyroscope -config.file={CONFIG_FILE} "
            f"-target={','.join(roles)} -architecture.storage=v2"
        )
        # Per-unit Raft identity, which the shared coordinator config can't carry.
        # server-id is the bare host, matching how bootstrap_peers resolves each peer.
        if "all" in roles or "metastore" in roles:
            fqdn = socket.getfqdn()
            command += (
                f" -metastore.raft.server-id={fqdn}"
                f" -metastore.raft.advertise-address={fqdn}:{METASTORE_RAFT_PORT}"
                f" -metastore.raft.bind-address=:{METASTORE_RAFT_PORT}"
            )

        return Layer(
            {
                "summary": "pyroscope worker layer",
                "description": "pebble config layer for pyroscope worker",
                "services": {
                    "pyroscope": {
                        "override": "replace",
                        "summary": "pyroscope worker process",
                        "command": command,
                        "startup": "enabled",
                        "environment": env,
                    }
                },
            }
        )

    @staticmethod
    def readiness_check_endpoint(worker: Worker) -> str:
        """Endpoint for worker readiness checks."""
        # e2e TLS in upstream is not supported yet
        # https://github.com/grafana/pyroscope/issues/3598
        return f"http://{socket.getfqdn()}:{API_PORT}/ready"
