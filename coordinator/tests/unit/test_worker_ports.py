import pytest

from charm import PyroscopeCoordinatorCharm
from pyroscope import Pyroscope
from pyroscope_config import PyroscopeRole


@pytest.mark.parametrize(
    "role, expected_ports",
    [
        pytest.param(
            PyroscopeRole.all,
            (
                Pyroscope.memberlist_port,
                Pyroscope.http_server_port,
                Pyroscope.grpc_port,
                Pyroscope.metastore_raft_port,
            ),
            id="all",
        ),
        pytest.param(
            PyroscopeRole.metastore,
            (
                Pyroscope.memberlist_port,
                Pyroscope.http_server_port,
                Pyroscope.grpc_port,
                Pyroscope.metastore_raft_port,
            ),
            id="metastore",
        ),
        pytest.param(
            f"{PyroscopeRole.metastore},{PyroscopeRole.segment_writer}",
            (
                Pyroscope.memberlist_port,
                Pyroscope.http_server_port,
                Pyroscope.grpc_port,
                Pyroscope.metastore_raft_port,
            ),
            id="multi-role with metastore",
        ),
        pytest.param(
            PyroscopeRole.query_backend,
            (
                Pyroscope.memberlist_port,
                Pyroscope.http_server_port,
                Pyroscope.grpc_port,
            ),
            id="query-backend",
        ),
        pytest.param(
            PyroscopeRole.distributor,
            (
                Pyroscope.memberlist_port,
                Pyroscope.http_server_port,
                Pyroscope.grpc_port,
            ),
            id="distributor",
        ),
    ],
)
def test_worker_ports(role, expected_ports):
    assert PyroscopeCoordinatorCharm._worker_ports(role) == expected_ports
