import pytest
from charmlibs.nginx_k8s import NginxConfig

import nginx_config


@pytest.mark.parametrize(
    "port",
    [
        4040,
        4209,
    ],
)
def test_upstreams_contain_correct_port(port):
    # GIVEN a port number

    # WHEN upstreams configuration is generated
    upstream_config = nginx_config.upstreams(port)

    # THEN it contains the correct port
    for upstream in upstream_config:
        assert upstream.port == port


def test_servers_config():
    # GIVEN information if tls is enabled

    # WHEN a mapping of server ports is generated
    server_ports_to_locations = nginx_config.server_ports_to_locations()

    # THEN the locations are mapped to the right port
    assert server_ports_to_locations[nginx_config.http_server_port]


@pytest.mark.parametrize(
    "path, backend",
    [
        # unrouted, these 404 from nginx's static root and pushes are silently lost
        ("/push.v1.PusherService", "distributor"),
        ("/ingest", "distributor"),
    ],
)
def test_ingest_paths_are_routed_to_the_distributor(path, backend):
    # GIVEN the http locations the coordinator serves
    locations = nginx_config.server_ports_to_locations()[nginx_config.http_server_port]

    # WHEN we look up an ingest path
    matching = [location for location in locations if location.path == path]

    # THEN it is routed, and to the distributor
    assert matching, f"{path} is not routed on the http server port"
    assert all(location.backend == backend for location in matching)


@pytest.mark.parametrize("path", ["/", "/assets"])
def test_ui_paths_are_routed_to_a_role_that_serves_the_ui(path):
    # GIVEN the http locations the coordinator serves
    locations = nginx_config.server_ports_to_locations()[nginx_config.http_server_port]

    # WHEN we look up a UI path
    matching = [location for location in locations if location.path == path]

    # THEN it is routed at the query-frontend, not at the generic worker upstream.
    # Every other role answers `/` with a redirect, so the generic upstream makes the
    # UI load only on the fraction of requests that happen to land on a query-frontend.
    assert matching, f"{path} is not routed on the http server port"
    assert all(location.backend == "query-frontend" for location in matching)


def test_rendered_config_proxies_the_push_api():
    # GIVEN a rendered config with a distributor in the cluster
    rendered = NginxConfig(
        server_name="pyroscope-0.pyroscope-endpoints.test.svc.cluster.local",
        upstream_configs=nginx_config.upstreams(4040),
        server_ports_to_locations=nginx_config.server_ports_to_locations(),
        enable_status_page=True,
    ).get_config(
        upstreams_to_addresses={
            "distributor": {"distributor-0.test.svc.cluster.local"}
        },
        listen_tls=False,
    )

    # THEN it reaches the config nginx actually runs
    assert "location /push.v1.PusherService" in rendered
