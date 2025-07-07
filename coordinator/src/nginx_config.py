# Copyright 2023 Canonical
# See LICENSE file for licensing details.
"""Coordinator Nginx workload configuration utils."""

import logging
from typing import Dict, List

from coordinated_workers.nginx import (
    NginxLocationConfig,
    NginxUpstream,
)

from pyroscope_config import PyroscopeRole

logger = logging.getLogger(__name__)


nginx_port = 8080
nginx_tls_port = 443

_locations_write: List[NginxLocationConfig] = [
    NginxLocationConfig(path="/ingest", backend="distributor", modifier="="),
]

_locations_query_frontend: List[NginxLocationConfig] = [
    NginxLocationConfig(
        path="/pyroscope/render", backend="query-frontend", modifier="="
    ),  # API queries
    NginxLocationConfig(
        path="/pyroscope/render-diff", backend="query-frontend", modifier="="
    ),  # API queries
    NginxLocationConfig(
        path="/querier.v1.QuerierService", backend="query-frontend"
    ),  # called by the frontend
]

_locations_tenant_settings: List[NginxLocationConfig] = [
    NginxLocationConfig(path="/settings.v1.SettingsService", backend="tenant-settings"),
]

_locations_ad_hoc_profiles: List[NginxLocationConfig] = [
    NginxLocationConfig(path="/adhocprofiles.v1.AdHocProfileService", backend="ad-hoc-profiles")
]

_locations_worker: List[NginxLocationConfig] = [
    NginxLocationConfig(
        path="/", backend="worker", modifier="="
    ),  # pyroscope UI - not bound to a specific role
    NginxLocationConfig(path="/assets", backend="worker"),
]


def upstreams(pyroscope_port: int) -> List[NginxUpstream]:
    """Generate the list of Nginx upstream metadata configurations."""
    upstreams = [NginxUpstream(role, pyroscope_port, role) for role in PyroscopeRole]
    # add a generic `worker` upstream that routes to all workers
    upstreams.append(
        NginxUpstream("worker", pyroscope_port, "worker", ignore_worker_role=True)
    )
    return upstreams


def server_ports_to_locations(
    tls_available: bool,
) -> Dict[int, List[NginxLocationConfig]]:
    """Generate a mapping from server ports to a list of Nginx location configurations."""
    return {
        nginx_tls_port if tls_available else nginx_port: _locations_write
        + _locations_query_frontend
        + _locations_tenant_settings
        + _locations_ad_hoc_profiles
        + _locations_worker
    }
