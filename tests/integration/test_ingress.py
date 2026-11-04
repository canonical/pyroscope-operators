#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess

import requests
import tenacity
from tenacity import wait_exponential as wexp, stop_after_attempt as satt
import pytest
from jubilant import Juju, all_active, any_error
from pytest_bdd import given, when, then

from tests.integration.helpers import (
    PYROSCOPE_APP,
    WORKER_APP,
    deploy_monolithic_cluster,
    TRAEFIK_APP,
    get_ingress_proxied_hostname,
    get_unit_ip_address,
)

pytestmark = pytest.mark.usefixtures("teardown_ingress_stack")

# hardcoded here instead of imported from coordinator.src.nginx_config to avoid dependency and PYTHONPATH conflicts
NGINX_CONFIG_HTTP_SERVER_PORT = 8080
NGINX_CONFIG_GRPC_SERVER_PORT = 42424

logger = logging.getLogger(__name__)


@tenacity.retry(wait=wexp(multiplier=2, max=30), stop=satt(10))
def check_http_endpoint(juju: Juju, use_ingress: bool):
    if use_ingress:
        ingress_hostname = get_ingress_proxied_hostname(juju)
        url = f"http://{ingress_hostname}/{juju.model}-{PYROSCOPE_APP}"
    else:
        nginx_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
        url = f"http://{nginx_ip}:{NGINX_CONFIG_HTTP_SERVER_PORT}"

    ui = requests.get(url)
    assert b"<title>Pyroscope</title>" in ui.content


@tenacity.retry(wait=wexp(multiplier=2, max=30), stop=satt(10))
def check_grpc_endpoint(juju: Juju, use_ingress: bool):
    if use_ingress:
        hostname = get_ingress_proxied_hostname(juju)
    else:
        hostname = "http://" + get_unit_ip_address(juju, PYROSCOPE_APP, 0)

    url = f"{hostname}:{NGINX_CONFIG_GRPC_SERVER_PORT}"
    proc = subprocess.run(["curl", url], capture_output=True, text=True, check=False)

    # With ingress, Traefik connects to nginx over h2c (HTTP/2),
    # so nginx accepts the request and serves the default homepage on the gRPC port, since no `location /` is defined.
    # Without ingress, https://github.com/canonical/nginx-rock 1.27.5 also accepts plain HTTP/1.1 connections on the gRPC port,
    # so direct curl requests to the gRPC port are handled and return the default homepage as well.

    # NOTE: `ubuntu/nginx:1.24-24.04_beta` didn't accept plain HTTP/1.1 connections on a gRPC port.
    assert "Welcome to nginx!" in proc.stdout


@pytest.mark.setup
@given("a Pyroscope cluster and Traefik are deployed")
def test_setup(juju: Juju):
    juju.deploy(
        "traefik-k8s",
        app=TRAEFIK_APP,
        channel="latest/stable",
        base="ubuntu@26.04",
        trust=True,
    )
    deploy_monolithic_cluster(juju)


@then("we can hit the HTTP endpoint through nginx")
def test_nginx_ui_route_before_ingress(juju: Juju):
    """Verify that before we integrate ingress, we can hit the http endpoint through nginx."""
    check_http_endpoint(juju, use_ingress=False)


@then("we can hit the gRPC endpoint through nginx")
def test_nginx_grpc_server_route_before_ingress(juju: Juju):
    """Verify that before we integrate ingress, we can hit the grpc endpoint through nginx."""
    check_grpc_endpoint(juju, use_ingress=False)


@pytest.mark.setup
@when("we integrate the Pyroscope cluster with Traefik over ingress")
def test_add_ingress(juju: Juju):
    juju.integrate(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)


@then("the coordinator, worker, and Traefik are all in active/idle state")
def test_ingress_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP),
        error=any_error,
        timeout=2000,
    )


@then("we can hit the HTTP endpoint through nginx")
def test_nginx_ui_route_with_ingress(juju: Juju):
    """Verify that once we integrate ingress, we can hit the http endpoint through nginx."""
    check_http_endpoint(juju, use_ingress=True)


@then("we can hit the gRPC endpoint through nginx")
def test_nginx_grpc_server_route_with_ingress(juju: Juju):
    """Verify that once we integrate ingress, we can hit the grpc endpoint through nginx."""
    check_grpc_endpoint(juju, use_ingress=True)


@given("a model with traefik and the Pyroscope cluster integrated")
def test_ingress_integrated_and_active(juju: Juju):
    status = juju.status()
    assert all_active(status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP)


@pytest.mark.teardown
@when("we remove the ingress relation")
def test_remove_ingress(juju: Juju):
    juju.remove_relation(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)


@then("the coordinator and worker are in active/idle state")
def test_ingress_removed_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP),
        error=any_error,
        timeout=2000,
    )


@then("we can once again hit the HTTP endpoint through nginx")
def test_nginx_ui_route_after_ingress(juju: Juju):
    """Verify that after we remove ingress, we can once again hit the http endpoint through nginx."""
    check_http_endpoint(juju, use_ingress=False)


@then("we can once again hit the gRPC endpoint through nginx")
def test_nginx_grpc_server_route_after_ingress(juju: Juju):
    """Verify that after we remove ingress, we can once again hit the grpc endpoint through nginx."""
    check_grpc_endpoint(juju, use_ingress=False)
