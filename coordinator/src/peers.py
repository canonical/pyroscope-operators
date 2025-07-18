#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Peer relation for pyroscope coordinators to exchange fqdns."""

from typing import List

import ops
from cosl.interfaces.utils import DatabagModel

PEERS_RELATION_ENDPOINT_NAME = "peers"


class PeerData(DatabagModel):
    """Databag model for the "peers" relation between coordinator units."""

    fqdn: str
    """FQDN hostname of this coordinator unit."""


class Peers:
    def __init__(self, relation: ops.Relation, hostname: str, unit: ops.Unit):
        self._relation = relation
        self._hostname = hostname
        self._unit = unit

    def reconcile(self) -> None:
        """Update peer unit data bucket with this unit's hostname."""
        if self._relation and self._relation.data:
            PeerData(fqdn=self._hostname).dump(self._relation.data[self._unit])

    def _get_peer_data(self, unit: ops.Unit) -> PeerData:
        """Get peer data from a given unit data bucket."""
        return PeerData.load(self._relation.data.get(unit, {}))

    def get_fqdns(self) -> List[str]:
        """Obtain from peer data all peer unit fqdns (including this unit)."""
        if not self._relation or not self._relation.data:
            return [self._hostname]

        return [self._get_peer_data(peer).fqdn for peer in self._relation.units] + [
            self._hostname
        ]
