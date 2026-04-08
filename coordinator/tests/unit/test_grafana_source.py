from unittest.mock import patch

import nginx_config
import ops
from ops.testing import State
from pytest_bdd import given, scenarios, then, when

scenarios("grafana_source.feature")


@given("the coordinator is deployed without ingress", target_fixture="initial_state")
def coordinator_no_ingress(
    s3, all_worker, nginx_container, nginx_prometheus_exporter_container, grafana_source, peers
):
    return State(
        relations=[peers, s3, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )


@given('the unit FQDN resolves to "foo.com"', target_fixture="fqdn")
def fqdn_foo():
    return "foo.com"


@given(
    "the unit FQDN resolves to a Kubernetes cluster-internal address",
    target_fixture="fqdn",
)
def fqdn_k8s():
    return "something-something.something-else.svc.cluster.local"


@given("the coordinator is deployed with an ingress relation", target_fixture="initial_state")
def coordinator_with_ingress(
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    grafana_source,
    ingress,
    peers,
):
    return State(
        relations=[peers, s3, ingress, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )


@when("an update-status event is processed", target_fixture="state_out")
def run_update_status(context, initial_state, fqdn):
    with patch("socket.getfqdn", new=lambda: fqdn):
        return context.run(context.on.update_status(), initial_state)


@then('the Grafana datasource host is "http://foo.com:8080"')
def check_url_no_ingress(state_out, grafana_source):
    rel = state_out.get_relation(grafana_source.id)
    assert rel.local_unit_data["grafana_source_host"] == "http://foo.com:8080"


@then("the Grafana datasource host uses the Kubernetes service FQDN")
def check_url_k8s(state_out, grafana_source):
    rel = state_out.get_relation(grafana_source.id)
    expected = (
        f"http://pyroscope-coordinator-k8s.{state_out.model.name}.svc.cluster.local"
        f":{nginx_config.http_server_port}"
    )
    assert rel.local_unit_data["grafana_source_host"] == expected


@then("the Grafana datasource host uses the ingress external URL")
def check_url_with_ingress(state_out, grafana_source, external_host):
    rel = state_out.get_relation(grafana_source.id)
    expected = f"http://{external_host}/{state_out.model.name}-pyroscope-coordinator-k8s"
    assert rel.local_unit_data["grafana_source_host"] == expected
