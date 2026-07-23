#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pyroscope workload configuration and client."""

from typing import Dict, Optional, Set, Tuple
from urllib.parse import urlparse

import yaml
from coordinated_workers.coordinator import Coordinator

import pyroscope_config
from charm_config import CharmConfig


class Pyroscope:
    """Class representing the Pyroscope client workload configuration."""

    _data_path = "/pyroscope-data"
    # this is the single source of truth for which ports are opened and configured
    # in the distributed Pyroscope deployment (on the worker nodes)
    memberlist_port = 7946
    # this is an http server, but it can also somehow accept grpc traffic using some dark trick
    http_server_port = 4040

    def __init__(
        self,
        external_url: str,
        charm_config: CharmConfig,
    ):
        self._external_url = external_url
        self._charm_config = charm_config

    def config(
        self,
        coordinator: Coordinator,
    ) -> str:
        """Generate the Pyroscope (v2) configuration."""
        addrs = coordinator.cluster.gather_addresses()
        addrs_by_role = coordinator.cluster.gather_addresses_by_role()
        config = pyroscope_config.PyroscopeConfig(
            api=self._build_api_config(self._external_url),
            server=self._build_server_config(),
            distributor=self._build_distributor_config(),
            segment_writer=self._build_segment_writer_config(addrs_by_role),
            metastore=self._build_metastore_config(addrs_by_role),
            memberlist=self._build_memberlist_config(addrs),
            limits=self._build_limits_config(),
            storage=self._build_storage_config(coordinator._s3_config),
        )
        return yaml.dump(
            config.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    def _build_server_config(self):
        return pyroscope_config.Server(
            http_listen_port=self.http_server_port,
        )

    @staticmethod
    def _build_segment_writer_config(roles_addresses: Dict[str, Set[str]]):
        # v2 write path (replaces the v1 ingester). Its ring kvstore defaults to
        # consul upstream, so we pin it to memberlist for our gossip cluster.
        sw_addresses = roles_addresses.get(
            pyroscope_config.PyroscopeRole.segment_writer
        )
        return pyroscope_config.SegmentWriter(
            lifecycler=pyroscope_config.Lifecycler(
                ring=pyroscope_config.Ring(
                    replication_factor=3
                    if sw_addresses and len(sw_addresses) >= 3
                    else 1,
                    kvstore=pyroscope_config.Kvstore(
                        store="memberlist",
                    ),
                )
            )
        )

    @staticmethod
    def _build_metastore_config(roles_addresses: Dict[str, Set[str]]):
        # The metastore forms a Raft cluster across all workers running the
        # metastore role. For a single (monolithic 'all') worker this is 1.
        # TODO(v2-ha): a multi-node metastore needs persistent, stable peer
        # addresses + odd quorum; out of scope for the minimal single-node build.
        ms_addresses = roles_addresses.get(pyroscope_config.PyroscopeRole.metastore)
        peers = len(ms_addresses) if ms_addresses else 1
        return pyroscope_config.Metastore(
            raft=pyroscope_config.Raft(
                dir=f"{Pyroscope._data_path}/metastore/raft",
                snapshots_dir=f"{Pyroscope._data_path}/metastore/snapshots",
                bootstrap_expect_peers=peers,
            ),
            data_dir=f"{Pyroscope._data_path}/metastore/data",
        )

    def _build_memberlist_config(self, worker_peers: Optional[Tuple[str, ...]]):
        return pyroscope_config.Memberlist(
            bind_port=self.memberlist_port,
            join_members=(
                [f"{peer}:{self.memberlist_port}" for peer in worker_peers]
                if worker_peers
                else []
            ),
        )

    def _build_limits_config(self):
        return pyroscope_config.Limits(
            compactor_blocks_retention_period=0
            if self._charm_config.retention_period == "0"
            else self._charm_config.retention_period
        )

    @staticmethod
    def _build_storage_config(s3_config: dict):
        return pyroscope_config.Storage(
            backend="s3", s3=pyroscope_config.S3Storage(**s3_config)
        )

    @staticmethod
    def _build_distributor_config():
        return pyroscope_config.Distributor(
            ring=pyroscope_config.Ring(
                kvstore=pyroscope_config.Kvstore(
                    store="memberlist",
                )
            )
        )

    def _build_api_config(self, external_url):
        if external_url:
            base_url = self._base_url(external_url)
            if base_url == "" or base_url == "/":
                # we're behind ingress, but on a root path
                return pyroscope_config.Api()
            return pyroscope_config.Api(base_url=base_url)  # pyright: ignore[reportCallIssue]
        return pyroscope_config.Api()

    @staticmethod
    def _base_url(external_url):
        return urlparse(external_url).path
