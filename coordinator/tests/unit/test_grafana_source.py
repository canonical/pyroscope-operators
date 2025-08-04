from unittest.mock import patch

import ops

import nginx_config
from ops.testing import State


def assert_unit_source_url_equals(
    grafana_source_out: ops.testing.Relation, expected_value: str
):
    assert grafana_source_out.local_unit_data["grafana_source_host"] == expected_value


def test_grafana_source_no_ingress(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    grafana_source,
    peers,
):
    with patch("socket.getfqdn", new=lambda: "foo.com"):
        state_out = context.run(
            context.on.update_status(),
            State(
                relations=[peers, s3, all_worker, grafana_source],
                containers=[nginx_container, nginx_prometheus_exporter_container],
                unit_status=ops.ActiveStatus(),
                leader=True,
            ),
        )
    assert_unit_source_url_equals(
        state_out.get_relation(grafana_source.id), "http://foo.com:8080"
    )


def test_grafana_source_with_k8s_fqdn(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    grafana_source,
    external_host,
    peers,
):
    with patch(
        "socket.getfqdn",
        new=lambda: "something-something.something-else.svc.cluster.local",
    ):
        state_out = context.run(
            context.on.update_status(),
            State(
                relations=[peers, s3, all_worker, grafana_source],
                containers=[nginx_container, nginx_prometheus_exporter_container],
                unit_status=ops.ActiveStatus(),
                leader=True,
            ),
        )
    assert_unit_source_url_equals(
        state_out.get_relation(grafana_source.id),
        f"http://pyroscope-coordinator-k8s.{state_out.model.name}.svc.cluster.local:{nginx_config.http_server_port}",
    )


def test_grafana_source_ingress(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    grafana_source,
    ingress,
    external_host,
    peers,
):
    with patch("socket.getfqdn", new=lambda: "foo.com"):
        state_out = context.run(
            context.on.update_status(),
            State(
                relations=[peers, s3, ingress, all_worker, grafana_source],
                containers=[nginx_container, nginx_prometheus_exporter_container],
                unit_status=ops.ActiveStatus(),
                leader=True,
            ),
        )
    assert_unit_source_url_equals(
        state_out.get_relation(grafana_source.id),
        f"http://{external_host}/{state_out.model.name}-pyroscope-coordinator-k8s",
    )
