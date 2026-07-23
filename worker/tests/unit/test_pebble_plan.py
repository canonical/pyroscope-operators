# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import os
import socket
from unittest.mock import MagicMock, patch
import pytest
from ops.model import ActiveStatus
from scenario import Relation, State
from cosl import JujuTopology

from helpers import set_roles
from conftest import config_on_disk, endpoint_ready


@config_on_disk()
@endpoint_ready()
@pytest.mark.parametrize("https_proxy", (True, False))
@pytest.mark.parametrize(
    "roles",
    (
        ["all"],
        ["querier"],
        ["query-frontend"],
        ["query-scheduler"],
        ["query-backend"],
        ["distributor"],
        ["segment-writer"],
        ["metastore"],
        ["compaction-worker"],
        # multiple roles on one worker
        ["query-scheduler", "query-frontend", "querier"],
        ["segment-writer", "metastore"],
    ),
)
def test_pebble_ready_plan(ctx, pyroscope_container, roles, https_proxy):
    roles = sorted(roles)
    host = socket.getfqdn()
    if https_proxy:
        os.environ["JUJU_CHARM_HTTPS_PROXY"] = "0.0.0.1"
    # GIVEN a pyroscope-cluster with a placeholder worker config
    state = set_roles(
        State(
            containers=[pyroscope_container],
            relations=[
                Relation(
                    "pyroscope-cluster",
                    remote_app_data={
                        "worker_config": json.dumps("beef"),
                    },
                )
            ],
        ),
        roles,
    )
    # WHEN a workload pebble ready event is fired
    state_out = ctx.run(ctx.on.pebble_ready(pyroscope_container), state=state)

    # THEN pyroscope pebble plan is generated
    pyroscope_container_out = state_out.get_container(pyroscope_container.name)
    plan_out = pyroscope_container_out.plan.to_dict()

    assert plan_out["checks"]["ready"]["http"]["url"] == f"http://{host}:4040/ready"
    assert (
        plan_out["services"]["pyroscope"]["command"]
        == f"/usr/bin/pyroscope -config.file=/etc/worker/config.yaml -target={','.join(roles)} -architecture.storage=v2"
    )
    assert plan_out["services"]["pyroscope"]["environment"]["https_proxy"] == "0.0.0.1"
    # AND the pebble service is running
    assert pyroscope_container_out.services.get("pyroscope").is_running() is True

    # AND the charm status is active
    if roles == ["all"]:
        assert state_out.unit_status == ActiveStatus("(all roles) ready.")
    else:
        # the worker lib builds the status message from its role set, so the
        # order of roles in the message is not guaranteed; compare as a set.
        assert state_out.unit_status.name == "active"
        status_roles = state_out.unit_status.message.removesuffix(" ready.").split(",")
        assert set(status_roles) == set(roles)


@config_on_disk()
@endpoint_ready()
@patch.object(
    JujuTopology,
    "from_charm",
    MagicMock(
        return_value=JujuTopology(
            model="test",
            model_uuid="00000000-0000-4000-8000-000000000000",
            application="worker",
            unit="worker/0",
            charm_name="pyroscope",
        )
    ),
)
def test_tracing_config_in_pebble_plan(ctx, pyroscope_container):
    host = socket.getfqdn()
    tempo_endpoint = "http://127.0.0.1"
    # GIVEN a workload tracing endpoint in the pyroscope-cluster config
    state = State(
        containers=[pyroscope_container],
        relations=[
            Relation(
                "pyroscope-cluster",
                remote_app_data={
                    "worker_config": json.dumps("beef"),
                    "workload_tracing_receivers": json.dumps(
                        {"jaeger_thrift_http": tempo_endpoint}
                    ),
                },
            ),
        ],
        config={
            "role-all": True,
        },
    )
    # WHEN a workload pebble ready event is fired
    state_out = ctx.run(ctx.on.pebble_ready(pyroscope_container), state=state)

    # THEN the pebble plan contains the workload tracing-related environment variables
    pyroscope_container_out = state_out.get_container(pyroscope_container.name)
    plan_out = pyroscope_container_out.plan.to_dict()

    assert plan_out["checks"]["ready"]["http"]["url"] == f"http://{host}:4040/ready"
    assert (
        plan_out["services"]["pyroscope"]["command"]
        == "/usr/bin/pyroscope -config.file=/etc/worker/config.yaml -target=all -architecture.storage=v2"
    )
    assert (
        plan_out["services"]["pyroscope"]["environment"]["JAEGER_ENDPOINT"]
        == f"{tempo_endpoint}/api/traces?format=jaeger.thrift"
    )
    assert plan_out["services"]["pyroscope"]["environment"]["JAEGER_SAMPLER_PARAM"]
    assert plan_out["services"]["pyroscope"]["environment"]["JAEGER_SAMPLER_TYPE"]
    assert (
        plan_out["services"]["pyroscope"]["environment"]["JAEGER_TAGS"]
        == "juju_application=worker,juju_model=test,juju_model_uuid=00000000-0000-4000-8000-000000000000,juju_unit=worker/0,juju_charm=pyroscope"
    )
