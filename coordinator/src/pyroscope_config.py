# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper module for interacting with the Pyroscope configuration."""

from enum import StrEnum, unique
from typing import List, Optional

from coordinated_workers.coordinator import ClusterRolesConfig
from pydantic import BaseModel, Field


@unique
class PyroscopeRole(StrEnum):
    """Pyroscope v2 component role names.

    v2 replaces the v1 ingester/store-gateway/compactor write+read path with an
    object-storage-native one: segment-writer (write), metastore (Raft metadata
    index), query-backend (read execution) and compaction-worker.

    References:
     arch:
      -> https://grafana.com/docs/pyroscope/latest/reference-pyroscope-v2-architecture/about-pyroscope-v2-architecture/
     config:
      -> https://grafana.com/docs/pyroscope/latest/configure-server/
    """

    all = "all"  # default, meta-role.
    # query path
    querier = "querier"
    query_frontend = "query-frontend"
    query_scheduler = "query-scheduler"
    query_backend = "query-backend"
    # write / ingest path
    distributor = "distributor"
    segment_writer = "segment-writer"
    # storage / metadata
    metastore = "metastore"
    compaction_worker = "compaction-worker"
    # misc
    tenant_settings = "tenant-settings"
    ad_hoc_profiles = "ad-hoc-profiles"

    @staticmethod
    def all_nonmeta():
        return {
            PyroscopeRole.querier,
            PyroscopeRole.query_frontend,
            PyroscopeRole.query_scheduler,
            PyroscopeRole.query_backend,
            PyroscopeRole.distributor,
            PyroscopeRole.segment_writer,
            PyroscopeRole.metastore,
            PyroscopeRole.compaction_worker,
            PyroscopeRole.tenant_settings,
            PyroscopeRole.ad_hoc_profiles,
        }


META_ROLES = {
    "all": set(PyroscopeRole.all_nonmeta()),
}
# Pyroscope component meta-role names.

MINIMAL_DEPLOYMENT = {
    PyroscopeRole.querier: 1,
    PyroscopeRole.query_frontend: 1,
    PyroscopeRole.query_scheduler: 1,
    PyroscopeRole.query_backend: 1,
    PyroscopeRole.distributor: 1,
    PyroscopeRole.segment_writer: 1,
    PyroscopeRole.metastore: 1,
    PyroscopeRole.compaction_worker: 1,
    PyroscopeRole.tenant_settings: 1,
    PyroscopeRole.ad_hoc_profiles: 1,
}
# The minimal set of roles that need to be allocated for the
# deployment to be considered consistent (otherwise we set blocked).

PYROSCOPE_ROLES_CONFIG = ClusterRolesConfig(
    roles={role for role in PyroscopeRole},
    meta_roles=META_ROLES,
    minimal_deployment=MINIMAL_DEPLOYMENT,
)
# Define the configuration for Pyroscope roles.


class Kvstore(BaseModel):
    """Kvstore schema."""

    store: str = "memberlist"


class Ring(BaseModel):
    """Ring schema."""

    kvstore: Kvstore
    replication_factor: Optional[int] = None


class Lifecycler(BaseModel):
    """Lifecycler schema."""

    ring: Ring


class SegmentWriter(BaseModel):
    """Segment-writer schema (v2 write path; replaces the v1 ingester).

    Note: upstream defaults this ring's kvstore to ``consul``, so we must set it
    to ``memberlist`` explicitly for our gossip-based cluster.
    """

    lifecycler: Lifecycler


class Raft(BaseModel):
    """Metastore Raft schema."""

    dir: str
    snapshots_dir: str
    # Number of peers to expect before bootstrapping the Raft cluster. Equals the
    # number of workers running the metastore role (1 for a single-node deploy).
    bootstrap_expect_peers: Optional[int] = None


class Metastore(BaseModel):
    """Metastore schema (v2 metadata index, Raft-based)."""

    raft: Raft
    data_dir: str


class Api(BaseModel):
    """Api schema."""

    base_url: Optional[str] = Field(
        alias="base-url", default=None
    )  # this is the only field with dash in the entire config

    model_config = {"populate_by_name": True}


class Server(BaseModel):
    """Server schema."""

    http_listen_port: int


class Memberlist(BaseModel):
    """Memberlist schema."""

    bind_port: int
    join_members: List[str]


class S3Storage(BaseModel):
    """S3 Storage schema"""

    bucket_name: str
    endpoint: str
    access_key_id: str
    secret_access_key: str
    region: Optional[str] = None
    insecure: bool = False


class Storage(BaseModel):
    """Storage schema"""

    backend: str
    s3: S3Storage


class Distributor(BaseModel):
    """Distributor schema."""

    ring: Ring


class Limits(BaseModel):
    """Limits schema."""

    compactor_blocks_retention_period: str | int = "1d"


class PyroscopeConfig(BaseModel):
    """PyroscopeConfig config schema (v2-only, minimal)."""

    api: Api
    server: Server
    distributor: Distributor
    segment_writer: SegmentWriter
    metastore: Metastore
    memberlist: Memberlist
    limits: Limits
    storage: Storage
