#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed Operator for Pyroscope; a lightweight object storage based profiling backend."""

import logging
from pathlib import Path

import ops_tracing
from ops.charm import CharmBase

from pyroscope import PyroscopeWorker

logger = logging.getLogger(__name__)


class PyroscopeWorkerCharm(CharmBase):
    """Charmed Operator for Pyroscope; a distributed profiling backend."""

    def __init__(self, *args):
        super().__init__(*args)
        self.worker = PyroscopeWorker(self)
        self._setup_charm_tracing()

    def _setup_charm_tracing(self):
        # we can't use ops.tracing.Tracing as this charm doesn't integrate with certs/tracing directly,
        # but the data goes through the coordinator.
        if self.worker.is_ready():
            charm_tracing_endpoint, charm_tracing_ca_path = self.worker.charm_tracing_config()
            if charm_tracing_endpoint:
                ca_text = Path(charm_tracing_ca_path).read_text() if charm_tracing_ca_path else None
                ops_tracing.set_destination(charm_tracing_endpoint+"/v1/traces", ca_text)


if __name__ == "__main__":  # pragma: nocover
    from ops import main
    main(PyroscopeWorkerCharm)  # noqa
