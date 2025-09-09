#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from jubilant import Juju, all_active, any_error
from tenacity import retry, stop_after_attempt, wait_fixed
from helpers import (
    deploy_monolithic_cluster,
    emit_profile,
    PYROSCOPE_APP,
    get_unit_ip_address,
    OTEL_COLLECTOR_APP,
    INTEGRATION_TESTERS_CHANNEL,
    WORKER_APP,
)
from assertions import assert_profile_is_ingested
from pytest_bdd import given, when, then


@pytest.mark.setup
@given("a pyroscope cluster is deployed")
def test_deploy_pyroscope(juju: Juju):
    deploy_monolithic_cluster(juju, wait_for_idle=False)


@pytest.mark.setup
@given(
    "an otel collector charm is deployed and integrated with pyroscope over profiling"
)
def test_deploy_and_integrate_collector(juju: Juju):
    juju.deploy(
        "opentelemetry-collector-k8s",
        OTEL_COLLECTOR_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
        trust=True,
    )
    juju.integrate(f"{PYROSCOPE_APP}:profiling", OTEL_COLLECTOR_APP)
    juju.wait(
        lambda status: all_active(
            status, PYROSCOPE_APP, WORKER_APP, OTEL_COLLECTOR_APP
        ),
        timeout=10 * 60,
        error=lambda status: any_error(status, PYROSCOPE_APP, WORKER_APP),
        delay=10,
        successes=6,
    )


@when("we emit a profile to the otel collector using otlp grpc")
def test_emit_profile_to_collector(juju: Juju):
    collector_ip = get_unit_ip_address(juju, OTEL_COLLECTOR_APP, 0)
    emit_profile(
        endpoint=f"{collector_ip}:4317", service_name="profilegen-otel-collector"
    )


@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
@then("the profile should be ingested by pyroscope")
def test_ingest_profile_from_collector(juju: Juju):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_profile_is_ingested(
        hostname=pyroscope_ip, service_name="profilegen-otel-collector"
    )


@pytest.mark.teardown
def test_teardown(juju: Juju):
    juju.remove_relation(f"{PYROSCOPE_APP}:profiling", OTEL_COLLECTOR_APP)
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP),
        timeout=10 * 60,
        error=lambda status: any_error(status, PYROSCOPE_APP, WORKER_APP),
        delay=10,
        successes=6,
    )
