# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about the profiles sent to Pyroscope, directly or through an OTel Collector."""

import time

import jubilant
from pytest import FixtureRequest
from pytest_bdd import parsers, then, when
from tenacity import retry, stop_after_attempt, wait_fixed

from tests.integration.assertions import assert_no_profiles, assert_profile_is_ingested
from tests.integration.helpers import (
    OTEL_COLLECTOR_APP,
    PYROSCOPE_APP,
    emit_profile,
    get_unit_ip_address,
    related_apps,
)

COLLECTOR_SERVICE_NAME = "profilegen-otel-collector"

# Profiles trail the request that sends them, so the steps retry until they arrive.
_retried = retry(stop=stop_after_attempt(6), wait=wait_fixed(10))


def tls_options(juju: jubilant.Juju, request: FixtureRequest) -> dict:
    """The options to reach Pyroscope over TLS, when it is related to a CA."""
    if not related_apps(juju, PYROSCOPE_APP, "certificates"):
        return {}
    return {
        "tls": True,
        "ca_path": str(request.getfixturevalue("ca_cert_path")),
        # pass server_name to avoid hostname mismatch
        "server_name": f"{PYROSCOPE_APP}.{juju.model}.svc.cluster.local",
    }


@when("a profile is emitted to Pyroscope")
def emit_profile_to_pyroscope(juju: jubilant.Juju, request: FixtureRequest):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(endpoint=f"{pyroscope_ip}:42424", **tls_options(juju, request))


@when("a profile is emitted to the OTel Collector")
def emit_profile_to_collector(juju: jubilant.Juju):
    collector_ip = get_unit_ip_address(juju, OTEL_COLLECTOR_APP, 0)
    emit_profile(endpoint=f"{collector_ip}:4317", service_name=COLLECTOR_SERVICE_NAME)


@then("Pyroscope has ingested the profile")
@_retried
def profile_is_ingested(juju: jubilant.Juju, request: FixtureRequest):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_profile_is_ingested(hostname=pyroscope_ip, **tls_options(juju, request))


@then("Pyroscope has ingested the profile from the OTel Collector")
@_retried
def profile_from_collector_is_ingested(juju: jubilant.Juju, request: FixtureRequest):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_profile_is_ingested(
        hostname=pyroscope_ip,
        service_name=COLLECTOR_SERVICE_NAME,
        **tls_options(juju, request),
    )


@then(parsers.parse('Pyroscope removes the profile after "{minutes:d}m"'))
@_retried
def profile_is_removed(juju: jubilant.Juju, minutes: int):
    time.sleep(minutes * 60)
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_no_profiles(hostname=pyroscope_ip)
