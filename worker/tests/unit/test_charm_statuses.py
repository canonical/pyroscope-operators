import json
import ops
from ops.testing import State, Relation
from tests.unit.conftest import config_on_disk, endpoint_ready, k8s_patch


@k8s_patch(status=ops.BlockedStatus("`juju trust` this application"))
@config_on_disk()
@endpoint_ready()
def test_patch_k8s_failed(ctx, pyroscope_container):
    state_out = ctx.run(
        ctx.on.config_changed(),
        state=State(
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
    )

    assert state_out.unit_status == ops.BlockedStatus("`juju trust` this application")


@k8s_patch(status=ops.WaitingStatus(""))
@config_on_disk()
@endpoint_ready()
def test_patch_k8s_waiting(ctx, pyroscope_container):
    state_out = ctx.run(
        ctx.on.config_changed(),
        state=State(
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
    )

    assert state_out.unit_status == ops.WaitingStatus("")
