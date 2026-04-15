import ops
from conftest import k8s_patch
from ops.testing import PeerRelation, State


def _peers_with_units():
    return PeerRelation("peers", peers_data={1: {}, 2: {}})


def test_blocked_without_any_dependencies(context, nginx_container, nginx_prometheus_exporter_container):
    # GIVEN the coordinator has no peer units or other relations
    state_in = State(
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN the charm starts
    state_out = context.run(context.on.start(), state_in)

    # THEN the charm reports blocked status
    assert state_out.unit_status.name == "blocked"


def test_blocked_without_required_relations(context, nginx_container, nginx_prometheus_exporter_container):
    # GIVEN the coordinator has peer units but no S3 or worker relations
    state_in = State(
        relations=[_peers_with_units()],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN the charm starts
    state_out = context.run(context.on.start(), state_in)

    # THEN the charm reports blocked status
    assert state_out.unit_status.name == "blocked"


def test_active_when_all_dependencies_present(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN the coordinator has peer units, S3, and worker relations
    state_in = State(
        relations=[_peers_with_units(), s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN the charm starts
    state_out = context.run(context.on.start(), state_in)

    # THEN the charm reports active status with "UI ready" in the message
    assert state_out.unit_status.name == "active"
    assert "UI ready" in state_out.unit_status.message


def test_blocked_when_k8s_patch_fails(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN the coordinator has all required relations
    state_in = State(
        relations=[_peers_with_units(), s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN an update-status event is processed and the Kubernetes resource patch reports blocked
    with k8s_patch(status=ops.BlockedStatus("`juju trust` this application")):
        state_out = context.run(context.on.update_status(), state_in)

    # THEN the charm forwards the blocked status with the trust message
    assert state_out.unit_status.name == "blocked"
    assert state_out.unit_status.message == "`juju trust` this application"


def test_blocked_when_retention_period_invalid(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN the coordinator has all required relations but an invalid retention_period config
    state_in = State(
        relations=[_peers_with_units(), s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        config={"retention_period": "invalid"},
    )

    # WHEN a config-changed event is processed
    state_out = context.run(context.on.config_changed(), state_in)

    # THEN the charm reports blocked status listing the invalid config key
    assert state_out.unit_status.name == "blocked"
    assert state_out.unit_status.message == "The following configurations are not valid: ['retention_period']"


def test_waiting_when_k8s_patch_waiting(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container
):
    # GIVEN the coordinator has all required relations
    state_in = State(
        relations=[_peers_with_units(), s3, all_worker],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN an update-status event is processed and the Kubernetes resource patch is waiting
    with k8s_patch(status=ops.WaitingStatus("waiting")):
        state_out = context.run(context.on.update_status(), state_in)

    # THEN the charm forwards the waiting status
    assert state_out.unit_status.name == "waiting"
    assert state_out.unit_status.message == "waiting"
