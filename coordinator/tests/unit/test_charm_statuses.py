import ops
import pytest
from conftest import k8s_patch
from ops.testing import PeerRelation, State
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("charm_statuses.feature")


# --- shared mutable state fixture ---


@pytest.fixture
def state_params():
    """Accumulates state inputs set by Given steps, consumed by When steps."""
    return {"relations": [], "config": {}}


@pytest.fixture
def k8s_override_status():
    """Default: no k8s patch override; overridden by specific Given steps."""
    return None


# --- Given steps ---


@given("the coordinator has no peer units")
def no_peers(state_params):
    pass  # absence step: documents that no peer relation is added


@given("the coordinator has peer units")
def has_peers(state_params):
    state_params["relations"].append(PeerRelation("peers", peers_data={1: {}, 2: {}}))


@given("the coordinator has an S3 relation")
def has_s3(state_params, s3):
    state_params["relations"].append(s3)


@given("the coordinator has a worker relation")
def has_worker(state_params, all_worker):
    state_params["relations"].append(all_worker)


@given("the Kubernetes resource patch reports blocked status", target_fixture="k8s_override_status")
def k8s_blocked():
    return ops.BlockedStatus("`juju trust` this application")


@given("the Kubernetes resource patch reports waiting status", target_fixture="k8s_override_status")
def k8s_waiting():
    return ops.WaitingStatus("waiting")


@given(parsers.parse('the retention_period config is "{value}"'))
def config_retention(state_params, value):
    state_params["config"]["retention_period"] = value


# --- When steps ---


@when("the charm starts", target_fixture="state_out")
def charm_starts(context, state_params, nginx_container, nginx_prometheus_exporter_container):
    state = State(
        relations=state_params["relations"],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        config=state_params["config"],
    )
    return context.run(context.on.start(), state)


@when("an update-status event is processed", target_fixture="state_out")
def update_status(
    context,
    state_params,
    nginx_container,
    nginx_prometheus_exporter_container,
    k8s_override_status,
):
    state = State(
        relations=state_params["relations"],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        config=state_params["config"],
    )
    if k8s_override_status is not None:
        with k8s_patch(status=k8s_override_status):
            return context.run(context.on.update_status(), state)
    return context.run(context.on.update_status(), state)


@when("a config-changed event is processed", target_fixture="state_out")
def config_changed(
    context, state_params, nginx_container, nginx_prometheus_exporter_container
):
    state = State(
        relations=state_params["relations"],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        config=state_params["config"],
    )
    return context.run(context.on.config_changed(), state)


# --- Then steps ---


@then(parsers.parse('the charm unit status is "{status}"'))
def check_status(state_out, status):
    assert state_out.unit_status.name == status


@then(parsers.parse('the status message contains "{text}"'))
def check_message_contains(state_out, text):
    assert text in state_out.unit_status.message


@then(parsers.parse('the status message is "{message}"'))
def check_message_exact(state_out, message):
    assert state_out.unit_status.message == message
