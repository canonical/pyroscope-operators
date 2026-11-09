# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about where Pyroscope's endpoints answer: on the coordinator, or through the ingress.

The coordinator's nginx serves the HTTP and gRPC endpoints. The ingress is whatever sits in
front of it over the "ingress" relation, here Traefik.
"""

import subprocess

import jubilant
import requests
import tenacity
from pytest_bdd import then
from tenacity import stop_after_attempt as satt
from tenacity import wait_exponential as wexp

from tests.integration.helpers import (
    PYROSCOPE_APP,
    get_ingress_proxied_hostname,
    get_unit_ip_address,
)

# hardcoded here instead of imported from coordinator.src.nginx_config to avoid dependency and PYTHONPATH conflicts
NGINX_CONFIG_HTTP_SERVER_PORT = 8080
NGINX_CONFIG_GRPC_SERVER_PORT = 42424

# The endpoints trail the relations that expose them, so the steps retry until they answer.
_until_answered = tenacity.retry(wait=wexp(multiplier=2, max=30), stop=satt(10))


@_until_answered
def check_http_endpoint(juju: jubilant.Juju, use_ingress: bool):
    if use_ingress:
        ingress_hostname = get_ingress_proxied_hostname(juju)
        url = f"http://{ingress_hostname}/{juju.model}-{PYROSCOPE_APP}"
    else:
        nginx_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
        url = f"http://{nginx_ip}:{NGINX_CONFIG_HTTP_SERVER_PORT}"

    ui = requests.get(url)
    assert b"<title>Pyroscope</title>" in ui.content


@_until_answered
def check_grpc_endpoint(juju: jubilant.Juju, use_ingress: bool):
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


@then("Pyroscope's HTTP endpoint answers on the coordinator")
def http_endpoint_on_coordinator(juju: jubilant.Juju):
    check_http_endpoint(juju, use_ingress=False)


@then("Pyroscope's gRPC endpoint answers on the coordinator")
def grpc_endpoint_on_coordinator(juju: jubilant.Juju):
    check_grpc_endpoint(juju, use_ingress=False)


@then("Pyroscope's HTTP endpoint answers through the ingress")
def http_endpoint_through_ingress(juju: jubilant.Juju):
    check_http_endpoint(juju, use_ingress=True)


@then("Pyroscope's gRPC endpoint answers through the ingress")
def grpc_endpoint_through_ingress(juju: jubilant.Juju):
    check_grpc_endpoint(juju, use_ingress=True)
