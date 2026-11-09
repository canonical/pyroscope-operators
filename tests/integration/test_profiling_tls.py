#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from jubilant import Juju, all_active, any_error
from pytest_bdd import given, scenarios, when, then
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.integration.helpers import (
    emit_profile,
    PYROSCOPE_APP,
    get_unit_ip_address,
    related_apps,
    SSC_APP,
    WORKER_APP,
)
from tests.integration.assertions import assert_profile_is_ingested

scenarios("profiling-tls.feature")


@given("a certificates provider charm is deployed and integrated with Pyroscope")
def ssc_is_integrated_with_pyroscope(juju: Juju):
    if SSC_APP not in juju.status().apps:
        juju.deploy("self-signed-certificates", SSC_APP)
    if SSC_APP not in related_apps(juju, PYROSCOPE_APP, "certificates"):
        juju.integrate(f"{PYROSCOPE_APP}:certificates", SSC_APP)
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP, SSC_APP),
        timeout=10 * 60,
        error=lambda status: any_error(status, PYROSCOPE_APP, WORKER_APP),
        delay=10,
        successes=6,
    )


@when("we emit a profile to Pyroscope using OTLP gRPC over TLS")
def emit_profile_to_pyroscope_over_tls(juju: Juju, ca_cert_path):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(
        endpoint=f"{pyroscope_ip}:42424",
        tls=True,
        ca_path=str(ca_cert_path),
        # pass server_name to avoid hostname mismatch
        server_name=f"{PYROSCOPE_APP}.{juju.model}.svc.cluster.local",
    )


@then("the profile should be ingested by Pyroscope")
@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
def profile_is_ingested_over_tls(juju: Juju, ca_cert_path):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_profile_is_ingested(
        hostname=pyroscope_ip,
        tls=True,
        ca_path=str(ca_cert_path),
        # pass server_name to avoid hostname mismatch
        server_name=f"{PYROSCOPE_APP}.{juju.model}.svc.cluster.local",
    )
