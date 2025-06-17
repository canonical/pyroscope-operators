#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

import jubilant
import pytest
from jubilant import Juju

from helpers import (
    PYROSCOPE_APP,
    WORKER_APP,
    deploy_monolithic_cluster,
    TRAEFIK_APP,
    get_ingress_proxied_hostname,
    emit_profile,
    get_profiles_patiently,
)

logger = logging.getLogger(__name__)


@pytest.mark.setup
def test_build_and_deploy(juju: Juju):
    # GIVEN an empty model
    # WHEN deploying the tempo cluster and traefik
    juju.deploy("traefik-k8s", app=TRAEFIK_APP, channel="edge", trust=True)
    deploy_monolithic_cluster(juju)

    # THEN the s3-integrator, coordinator, worker, and traefik are all in active/idle state
    juju.wait(
        lambda status: jubilant.all_active(status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP),
        error=jubilant.any_error,
        timeout=2000,
    )


def test_relate_ingress(juju: Juju):
    # GIVEN a model with a tempo cluster and traefik
    # WHEN we integrate the tempo cluster with traefik over ingress
    juju.integrate(PYROSCOPE_APP + ":ingress", TRAEFIK_APP + ":ingress")

    # THEN the coordinator, worker, and traefik are all in active/idle state
    juju.wait(
        lambda status: jubilant.all_active(status, TRAEFIK_APP, PYROSCOPE_APP, WORKER_APP),
        error=jubilant.any_error,
        timeout=2000,
        delay=5,
        successes=3,
    )

def test_ingest_profiles(juju: Juju):
    # GIVEN a pyroscope cluster
    # WHEN we emit a profile through Pyroscope's ingressed URL
    address = get_ingress_proxied_hostname(juju)
    # THEN we get a successful 2xx response
    assert emit_profile(address)

def test_query_profiles(juju: Juju):
    # GIVEN a pyroscope cluster
    # WHEN we query profiles through Pyroscope's ingressed URL
    address = get_ingress_proxied_hostname(juju)
    # THEN we get a successful 2xx response
    # AND we a non-empty list of samples
    assert get_profiles_patiently(address)


@pytest.mark.teardown
def test_remove_ingress(juju: Juju):
    # GIVEN a model with traefik and the tempo cluster integrated
    # WHEN we remove the ingress relation
    juju.remove_relation(PYROSCOPE_APP + ":ingress", TRAEFIK_APP + ":ingress")

    # THEN the coordinator and worker are in active/idle state
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, WORKER_APP),
        error=jubilant.any_error,
        timeout=2000,
    )


@pytest.mark.teardown
def test_teardown(juju: Juju):
    # GIVEN a model with traefik and the tempo cluster
    # WHEN we remove traefik, the coordinator, and the worker
    juju.remove_application(PYROSCOPE_APP)
    juju.remove_application(WORKER_APP)
    juju.remove_application(TRAEFIK_APP)

    # THEN nothing throws an exception
