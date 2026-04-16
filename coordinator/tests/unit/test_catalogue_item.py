from unittest.mock import patch

import ops
import pytest
from conftest import tls_patch
from ops.testing import Model, State
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("catalogue.feature")


@pytest.fixture
def tls_enabled():
    """Default: TLS disabled. Overridden by the 'TLS is with' Given step."""
    return False


@pytest.fixture
def fqdn_override():
    """Default: use the 'foo.com' patch already active via pyroscope_charm fixture."""
    return None


@given("the coordinator is deployed without ingress for catalogue", target_fixture="initial_state")
def coordinator_no_ingress(
    s3, all_worker, nginx_container, nginx_prometheus_exporter_container, catalogue, peers
):
    return State(
        relations=[peers, s3, all_worker, catalogue],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        model=Model(name="test"),
    )


@given(parsers.parse("TLS is {tls_label}"), target_fixture="tls_enabled")
def tls_state(tls_label):
    return tls_label == "with"


@given("the FQDN resolves to a Kubernetes cluster-internal address", target_fixture="fqdn_override")
def fqdn_k8s():
    return "something-something.something-else.svc.cluster.local"


@given(
    parsers.parse("the coordinator is deployed with ingress for catalogue using {tls_label} TLS"),
    target_fixture="initial_state",
)
def coordinator_with_ingress(
    tls_label,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    catalogue,
    ingress,
    ingress_with_tls,
    peers,
):
    selected_ingress = ingress_with_tls if tls_label == "with" else ingress
    return State(
        relations=[peers, s3, selected_ingress, all_worker, catalogue],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
        model=Model(name="test"),
    )


@when("a catalogue update-status event is processed", target_fixture="state_out")
def run_update_status(context, initial_state, tls_enabled, fqdn_override):
    fqdn = fqdn_override or "foo.com"
    with tls_patch(tls_enabled):
        with patch("socket.getfqdn", new=lambda: fqdn):
            return context.run(context.on.update_status(), initial_state)


@then(parsers.parse('the catalogue URL is "{expected_url}"'))
def check_catalogue_url(state_out, catalogue, expected_url):
    catalogue_out = state_out.get_relation(catalogue.id)
    assert catalogue_out.local_app_data["url"] == expected_url
