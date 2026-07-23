import json
from dataclasses import replace

import pytest
import yaml
from ops.testing import State

from charm import PyroscopeCoordinatorCharm


DEFAULT_RETENTION_PERIOD_CONFIG = "1d"
DISABLED_RETENTION_PERIOD_CONFIG = 0
VALID_RETENTION_PERIOD_CONFIG = "7d"
INVALID_RETENTION_PERIOD_CONFIG = "invalid"


def get_worker_unit_data(unit_no):
    return {
        "address": json.dumps(f"worker-{unit_no}.test.svc.cluster.local"),
        "juju_topology": json.dumps(
            {
                "model": "test",
                "unit": f"worker/{unit_no}",
                "model_uuid": "1",
                "application": "worker",
                "charm_name": "PyroscopeWorker",
            }
        ),
    }


@pytest.fixture
def state(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def state_with_s3_and_workers(
    all_worker, s3, nginx_container, nginx_prometheus_exporter_container, peers
):
    state = State(
        leader=True,
        relations=[all_worker, s3, peers],
        containers=[nginx_container, nginx_prometheus_exporter_container],
    )
    return state


@pytest.fixture
def state_with_ingress(
    all_worker, s3, nginx_container, nginx_prometheus_exporter_container, ingress, peers
):
    state = State(
        leader=True,
        relations=[all_worker, s3, ingress, peers],
        containers=[nginx_container, nginx_prometheus_exporter_container],
    )
    return state


@pytest.mark.parametrize("workers_no", (1, 3))
def test_memberlist_config(
    workers_no, context, state_with_s3_and_workers, all_worker, s3
):
    # GIVEN an s3 relation and a worker relation that has n units
    workers = replace(
        all_worker,
        remote_units_data={
            worker_idx: get_worker_unit_data(worker_idx)
            for worker_idx in range(workers_no)
        },
    )
    state = replace(state_with_s3_and_workers, relations={workers, s3})

    # WHEN an event is fired
    with context(context.on.relation_changed(workers), state) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_memberlist_config = {
            "bind_port": 7946,
            "join_members": [
                f"worker-{worker_idx}.test.svc.cluster.local:7946"
                for worker_idx in range(workers_no)
            ],
        }
        # THEN memberlist config portion is generated
        assert "memberlist" in actual_config_dict
        # AND this config contains all worker units as members
        assert actual_config_dict["memberlist"] == expected_memberlist_config


def test_server_config(context, state_with_s3_and_workers):
    # GIVEN an s3 relation and a worker relation
    # WHEN an event is fired
    with context(context.on.config_changed(), state_with_s3_and_workers) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {
            "http_listen_port": 4040,
        }
        # THEN server config portion is generated
        assert "server" in actual_config_dict
        # AND this config contains both http and grpc server ports
        assert actual_config_dict["server"] == expected_config


@pytest.mark.parametrize("workers_no", (1, 3))
def test_segment_writer_config(
    workers_no, context, state_with_s3_and_workers, all_worker, s3
):
    # GIVEN an s3 relation and a segment-writer worker relation that has n units
    segment_writer_workers = replace(
        all_worker,
        remote_app_data={"role": '"segment-writer"'},
        remote_units_data={
            worker_idx: get_worker_unit_data(worker_idx)
            for worker_idx in range(workers_no)
        },
    )
    state = replace(state_with_s3_and_workers, relations={segment_writer_workers, s3})
    # WHEN an event is fired
    with context(context.on.relation_changed(segment_writer_workers), state) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {
            "lifecycler": {
                "ring": {
                    "replication_factor": 3 if workers_no >= 3 else 1,
                    "kvstore": {"store": "memberlist"},
                }
            }
        }
        # THEN segment_writer config portion is generated
        assert "segment_writer" in actual_config_dict
        # AND this config has memberlist store and a replication factor dependant on the no of segment-writer workers
        assert actual_config_dict["segment_writer"] == expected_config


@pytest.mark.parametrize("workers_no", (1, 3))
def test_metastore_config(
    workers_no, context, state_with_s3_and_workers, all_worker, s3
):
    # GIVEN an s3 relation and a metastore worker relation that has n units
    metastore_workers = replace(
        all_worker,
        remote_app_data={"role": '"metastore"'},
        remote_units_data={
            worker_idx: get_worker_unit_data(worker_idx)
            for worker_idx in range(workers_no)
        },
    )
    state = replace(state_with_s3_and_workers, relations={metastore_workers, s3})
    # WHEN an event is fired
    with context(context.on.relation_changed(metastore_workers), state) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {
            "raft": {
                "dir": "/pyroscope-data/metastore/raft",
                "snapshots_dir": "/pyroscope-data/metastore/snapshots",
                "bootstrap_expect_peers": workers_no,
            },
            "data_dir": "/pyroscope-data/metastore/data",
        }
        # THEN metastore config portion is generated
        assert "metastore" in actual_config_dict
        # AND its Raft cluster expects as many peers as there are metastore workers
        assert actual_config_dict["metastore"] == expected_config


def test_s3_storage_config(context, state_with_s3_and_workers):
    # GIVEN an s3 relation and a worker relation
    # WHEN an event is fired
    with context(context.on.config_changed(), state_with_s3_and_workers) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {
            "backend": "s3",
            "s3": {
                "access_key_id": "key",
                "bucket_name": "pyroscope",
                "endpoint": "1.2.3.4:9000",
                "secret_access_key": "soverysecret",
                "insecure": True,
            },
        }
        # THEN storage config portion is generated
        assert "storage" in actual_config_dict
        # AND this config contains the s3 config as upstream defines it
        assert actual_config_dict["storage"] == expected_config


def test_base_url_config_without_ingress(context, state_with_s3_and_workers):
    with context(context.on.config_changed(), state_with_s3_and_workers) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {}
        # THEN api config portion is generated
        assert "api" in actual_config_dict
        # AND this config doesn't contain the base-url
        assert actual_config_dict["api"] == expected_config


def test_base_url_config_with_no_ingress(context, state_with_s3_and_workers):
    with context(context.on.config_changed(), state_with_s3_and_workers) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {}
        # THEN api config portion is generated
        assert "api" in actual_config_dict
        # AND this config doesn't contain the base-url
        assert actual_config_dict["api"] == expected_config


def test_base_url_config_with_ingress(context, state_with_ingress, external_host):
    with context(context.on.config_changed(), state_with_ingress) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        expected_prefix = f"/{state_with_ingress.model.name}-pyroscope-coordinator-k8s"
        assert (
            charm.ingress.is_ready()
            and charm.ingress.external_host
            and charm.ingress.scheme
        )
        assert charm._external_http_url == f"http://{external_host}{expected_prefix}"

        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        expected_config = {"base-url": expected_prefix}
        # THEN api config portion is generated
        assert "api" in actual_config_dict
        # AND this config contains the base-url used by pyroscope-UI to point at the right endpoints
        assert actual_config_dict["api"] == expected_config


@pytest.mark.parametrize(
    "charm_config, expected_retention_period",
    [
        pytest.param({}, DEFAULT_RETENTION_PERIOD_CONFIG, id="default charm config"),
        pytest.param(
            {"retention_period": VALID_RETENTION_PERIOD_CONFIG},
            VALID_RETENTION_PERIOD_CONFIG,
            id="valid retention_period",
        ),
        pytest.param(
            {"retention_period": INVALID_RETENTION_PERIOD_CONFIG},
            DISABLED_RETENTION_PERIOD_CONFIG,
            id="invalid retention_period",
        ),
    ],
)
def test_retention_period_config(
    context,
    all_worker,
    s3,
    nginx_container,
    nginx_prometheus_exporter_container,
    peers,
    charm_config,
    expected_retention_period,
):
    state = State(
        leader=True,
        config=charm_config,
        relations=[all_worker, s3, peers],
        containers=[nginx_container, nginx_prometheus_exporter_container],
    )
    with context(context.on.config_changed(), state) as mgr:
        charm: PyroscopeCoordinatorCharm = mgr.charm
        actual_config = charm.pyroscope.config(charm.coordinator)
        actual_config_dict = yaml.safe_load(actual_config)
        actual_limits_config = actual_config_dict["limits"]
        expected_limits_config = {
            "compactor_blocks_retention_period": expected_retention_period,
        }
        # THEN retention is reflected in the limits section
        # (v2 has no separate compactor block; compaction is driven by the metastore)
        assert actual_limits_config == expected_limits_config
