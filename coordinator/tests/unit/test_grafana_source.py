from unittest.mock import patch

import nginx_config
import ops
from ops.testing import State


def test_grafana_source_url_no_ingress_external_fqdn(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container, grafana_source, peers
):
    # GIVEN the coordinator is deployed without ingress and the FQDN resolves externally (default: "foo.com")
    state_in = State(
        relations=[peers, s3, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN an update-status event is processed
    state_out = context.run(context.on.update_status(), state_in)

    # THEN the Grafana datasource host is the external FQDN with the http port
    rel = state_out.get_relation(grafana_source.id)
    assert rel.local_unit_data["grafana_source_host"] == "http://foo.com:8080"


def test_grafana_source_url_no_ingress_k8s_fqdn(
    context, s3, all_worker, nginx_container, nginx_prometheus_exporter_container, grafana_source, peers
):
    # GIVEN the coordinator is deployed without ingress and the FQDN resolves to a cluster-internal address
    state_in = State(
        relations=[peers, s3, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN an update-status event is processed
    with patch("socket.getfqdn", new=lambda: "something-something.something-else.svc.cluster.local"):
        state_out = context.run(context.on.update_status(), state_in)

    # THEN the Grafana datasource host uses the Kubernetes service FQDN
    rel = state_out.get_relation(grafana_source.id)
    expected = (
        f"http://pyroscope-coordinator-k8s.{state_out.model.name}.svc.cluster.local"
        f":{nginx_config.http_server_port}"
    )
    assert rel.local_unit_data["grafana_source_host"] == expected


def test_grafana_source_url_with_ingress(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    grafana_source,
    ingress,
    peers,
    external_host,
):
    # GIVEN the coordinator is deployed with an ingress relation
    state_in = State(
        relations=[peers, s3, ingress, all_worker, grafana_source],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=True,
    )

    # WHEN an update-status event is processed
    state_out = context.run(context.on.update_status(), state_in)

    # THEN the Grafana datasource host uses the ingress external URL
    rel = state_out.get_relation(grafana_source.id)
    expected = f"http://{external_host}/{state_out.model.name}-pyroscope-coordinator-k8s"
    assert rel.local_unit_data["grafana_source_host"] == expected
