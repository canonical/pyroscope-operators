#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess

import requests
import tenacity
from tenacity import wait_exponential as wexp, stop_after_attempt as satt
from jubilant import Juju, all_active, any_error
from pytest_bdd import given, scenarios, when, then

from tests.integration.helpers import (
    PYROSCOPE_APP,
    WORKER_APP,
    TRAEFIK_APP,
    ensure_monolithic_cluster,
    get_ingress_proxied_hostname,
    get_unit_ip_address,
    related_apps,
)

scenarios("ingress.feature")

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


def wait_for_active(juju: Juju, *apps: str):
    juju.wait(
        lambda status: all_active(status, *apps),
        error=any_error,
        timeout=2000,
    )


def integrate_ingress(juju: Juju):
    if TRAEFIK_APP not in related_apps(juju, PYROSCOPE_APP, "ingress"):
        juju.integrate(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)


def remove_ingress(juju: Juju):
    if TRAEFIK_APP in related_apps(juju, PYROSCOPE_APP, "ingress"):
        juju.remove_relation(PYROSCOPE_APP + ":ingress", TRAEFIK_APP)


@given("a Pyroscope cluster and Traefik are deployed")
def pyroscope_cluster_and_traefik_are_deployed(juju: Juju):
    if TRAEFIK_APP not in juju.status().apps:
        juju.deploy(
            "traefik-k8s",
            app=TRAEFIK_APP,
            channel="latest/stable",
            base="ubuntu@26.04",
            trust=True,
        )
    ensure_monolithic_cluster(juju)
    wait_for_active(juju, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP)


@given("the Pyroscope cluster is not integrated with Traefik over ingress")
def pyroscope_is_not_integrated_with_traefik(juju: Juju):
    remove_ingress(juju)
    juju.wait(
        lambda status: (
            not status.apps[PYROSCOPE_APP].relations.get("ingress")
            and all_active(status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP)
        ),
        error=any_error,
        timeout=2000,
    )


@given("the Pyroscope cluster is integrated with Traefik over ingress")
def pyroscope_is_integrated_with_traefik(juju: Juju):
    integrate_ingress(juju)
    wait_for_active(juju, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP)


@when("we integrate the Pyroscope cluster with Traefik over ingress")
def integrate_pyroscope_with_traefik(juju: Juju):
    integrate_ingress(juju)


@when("we remove the ingress relation")
def remove_ingress_relation(juju: Juju):
    remove_ingress(juju)


@then("the coordinator, worker, and Traefik are all in active/idle state")
def coordinator_worker_and_traefik_are_active(juju: Juju):
    wait_for_active(juju, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP)


@then("the coordinator and worker are in active/idle state")
def coordinator_and_worker_are_active(juju: Juju):
    wait_for_active(juju, PYROSCOPE_APP, WORKER_APP)


@then("we can hit the HTTP endpoint through nginx")
def http_endpoint_through_nginx(juju: Juju):
    check_http_endpoint(juju, use_ingress=False)


@then("we can hit the gRPC endpoint through nginx")
def grpc_endpoint_through_nginx(juju: Juju):
    check_grpc_endpoint(juju, use_ingress=False)


@then("we can hit the HTTP endpoint through the ingress")
def http_endpoint_through_ingress(juju: Juju):
    check_http_endpoint(juju, use_ingress=True)


@then("we can hit the gRPC endpoint through the ingress")
def grpc_endpoint_through_ingress(juju: Juju):
    check_grpc_endpoint(juju, use_ingress=True)
