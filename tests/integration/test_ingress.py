#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess

import requests
import tenacity
from tenacity import wait_exponential as wexp, stop_after_attempt as satt
import jubilant
import pytest
from jubilant import Juju
from pytest_bdd import scenarios, given, when, then

from tests.integration.helpers import (
    PYROSCOPE_APP,
    WORKER_APP,
    deploy_monolithic_cluster,
    TRAEFIK_APP,
    get_ingress_proxied_hostname,
    get_unit_ip_address,
)

# hardcoded here instead of imported from coordinator.src.nginx_config to avoid dependency and PYTHONPATH conflicts
NGINX_CONFIG_HTTP_SERVER_PORT = 8080
NGINX_CONFIG_GRPC_SERVER_PORT = 42424

logger = logging.getLogger(__name__)

scenarios("common/ingress.feature")


@tenacity.retry(wait=wexp(multiplier=2, max=30), stop=satt(10))
def check_http_endpoint(juju: Juju, use_ingress: bool):
    if use_ingress:
        ingress_hostname = get_ingress_proxied_hostname(juju)
        url = f"http://{ingress_hostname}/{juju.model}-{PYROSCOPE_APP}"
    else:
        nginx_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
        url = f"http://{nginx_ip}:{NGINX_CONFIG_HTTP_SERVER_PORT}"

    ui = requests.get(url)
    assert b"Grafana Pyroscope" in ui.content


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


@given("a cluster is deployed alongside Traefik")
def deploy_cluster_with_traefik(juju: Juju):
    juju.deploy("traefik-k8s", app=TRAEFIK_APP, channel="latest/stable", trust=True)
    deploy_monolithic_cluster(juju)


@then("the HTTP endpoint is accessible directly through nginx")
def http_accessible_via_nginx(juju: Juju):
    check_http_endpoint(juju, use_ingress=False)


@then("the gRPC endpoint is accessible directly through nginx")
def grpc_accessible_via_nginx(juju: Juju):
    check_grpc_endpoint(juju, use_ingress=False)


@when("Traefik is integrated with the cluster over ingress")
def add_ingress_integration(juju: Juju):
    juju.integrate(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)
    juju.wait(
        lambda status: jubilant.all_active(
            status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP
        ),
        error=jubilant.any_error,
        timeout=2000,
    )


@then("the HTTP endpoint is accessible via the ingress hostname")
def http_accessible_via_ingress(juju: Juju):
    check_http_endpoint(juju, use_ingress=True)


@then("the gRPC endpoint is accessible via the ingress hostname")
def grpc_accessible_via_ingress(juju: Juju):
    check_grpc_endpoint(juju, use_ingress=True)


@when("the ingress integration is removed")
def remove_ingress_integration(juju: Juju):
    juju.remove_relation(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, WORKER_APP),
        error=jubilant.any_error,
        timeout=2000,
    )


@pytest.mark.teardown
def test_teardown(juju: Juju):
    juju.remove_application(PYROSCOPE_APP)
    juju.remove_application(WORKER_APP)
    juju.remove_application(TRAEFIK_APP)

    # THEN nothing throws an exception
