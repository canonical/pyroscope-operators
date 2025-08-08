import dataclasses
import json
from unittest.mock import patch

import ops
import pytest

import nginx_config
from ops.testing import State, Context

from charms.pyroscope_coordinator_k8s.v0.profiling import (
    ProfilingEndpointRequirer,
    _Endpoint,
)


def test_provide_profiling(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    profiling,
    peers,
):
    with patch("socket.getfqdn", new=lambda: "foo.com"):
        state_out = context.run(
            context.on.update_status(),
            State(
                relations=[peers, s3, all_worker, profiling],
                containers=[nginx_container, nginx_prometheus_exporter_container],
                unit_status=ops.ActiveStatus(),
                leader=True,
            ),
        )
    profiling_out = state_out.get_relation(profiling.id)

    assert profiling_out.local_app_data["otlp_grpc_endpoint_url"] == json.dumps(
        f"foo.com:{nginx_config.grpc_server_port}"
    )


def test_provide_profiling_ingress(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    profiling,
    ingress,
    external_host,
    peers,
):
    with patch("socket.getfqdn", new=lambda: "foo.com"):
        state_out = context.run(
            context.on.update_status(),
            State(
                relations=[peers, s3, ingress, all_worker, profiling],
                containers=[nginx_container, nginx_prometheus_exporter_container],
                unit_status=ops.ActiveStatus(),
                leader=True,
            ),
        )
    profiling_out = state_out.get_relation(profiling.id)

    assert profiling_out.local_app_data["otlp_grpc_endpoint_url"] == json.dumps(
        f"{external_host}:{nginx_config.grpc_server_port}"
    )


@pytest.mark.parametrize(
    "databag, expected",
    (
        ({}, []),
        (
            {"otlp_grpc_endpoint_url": '"foo.com:1234"'},
            [_Endpoint(otlp_grpc="foo.com:1234")],
        ),
    ),
)
def test_require_profiling(profiling, databag, expected):
    ctx = Context(
        ops.CharmBase,
        meta={"name": "mateusz", "requires": {"profiling": {"interface": "profiling"}}},
    )
    with ctx(
        state=State(
            relations={dataclasses.replace(profiling, remote_app_data=databag)},
            leader=True,
        ),
        event=ctx.on.update_status(),
    ) as mgr:
        ep = ProfilingEndpointRequirer(mgr.charm.model.relations["profiling"])
        assert ep.get_endpoints() == expected
