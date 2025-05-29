#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed Operator for Pyroscope; a lightweight object storage based profiling backend."""

import logging

import ops


logger = logging.getLogger(__name__)
PEERS_RELATION_ENDPOINT_NAME = "peers"

class PyroscopeWorkerCharm(CharmBase):
    """Charmed Operator for Pyroscope; a distributed profiling backend."""

    def __init__(self, *args):
        super().__init__(*args)

        # do this regardless of what event we are processing
        self._reconcile()


    ######################
    # UTILITY PROPERTIES #
    ######################

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
        pass


if __name__ == "__main__":  # pragma: nocover
    from ops import main

    main(PyroscopeWorkerCharm)  # noqa
