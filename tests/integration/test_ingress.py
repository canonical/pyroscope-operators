#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging

import jubilant
import pytest
from jubilant import Juju

from conftest import (
    PYROSCOPE_APP,
)
from helpers import (
    emit_profile,
    get_profiles_patiently,
)

TRAEFIK_APP = "trfk"


logger = logging.getLogger(__name__)

# @pytest.fixture(autouse=True, scope="module")
# def deployment(juju: Juju):
#     with pyroscope_deployment(juju, True, False):
#         yield

def _get_ingress_proxied_endpoint(juju: Juju):
    result = juju.run(f"{TRAEFIK_APP}/0", "show-proxied-endpoints")
    endpoints = json.loads(result.results["proxied-endpoints"])
    assert PYROSCOPE_APP in endpoints
    return endpoints[PYROSCOPE_APP]["url"]

@pytest.mark.setup
def test_deploy_and_relate_ingress(juju: Juju, workers):
    # GIVEN a Pyroscope cluster
    # WHEN deploying traefik
    juju.deploy("traefik-k8s", app=TRAEFIK_APP, channel="edge", trust=True)
    # AND we integrate the pyroscope cluster with traefik over ingress
    juju.integrate(PYROSCOPE_APP + ":ingress", TRAEFIK_APP + ":ingress")

    # THEN the coordinator, worker, and traefik are all in active/idle state
    juju.wait(
        lambda status: jubilant.all_active(status, TRAEFIK_APP, PYROSCOPE_APP, *workers),
        error=jubilant.any_error,
        timeout=2000,
    )

def test_ingest_profiles(juju: Juju):
    # GIVEN a pyroscope cluster
    # WHEN we emit a profile through Pyroscope's ingressed URL
    ingress_url = _get_ingress_proxied_endpoint(juju)
    # THEN we get a successful 2xx response
    assert emit_profile(ingress_url)

def test_query_profiles(juju: Juju):
    # GIVEN a pyroscope cluster
    # WHEN we query profiles through Pyroscope's ingressed URL
    ingress_url = _get_ingress_proxied_endpoint(juju)
    # THEN we get a successful 2xx response
    # AND we a non-empty list of samples
    assert get_profiles_patiently(ingress_url)

@pytest.mark.teardown
def test_remove_ingress(juju: Juju, workers):
    # GIVEN a model with traefik and the tempo cluster integrated
    # WHEN we remove the ingress relation
    juju.remove_relation(PYROSCOPE_APP + ":ingress", TRAEFIK_APP + ":ingress")
    # AND the traefik app
    juju.remove_application(TRAEFIK_APP)

    # THEN the coordinator and worker are in active/idle state
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, *workers),
        error=jubilant.any_error,
        timeout=2000,
    )

