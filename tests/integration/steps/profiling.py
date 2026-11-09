# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about the profiles sent to Pyroscope, directly or through an OTel Collector."""

import time

import jubilant
from pytest import FixtureRequest
from pytest_bdd import parsers, then, when
from tenacity import retry, stop_after_attempt, wait_fixed

from tests.integration.helpers import (
    NGINX_GRPC_PORT,
    OTEL_COLLECTOR_APP,
    PYROSCOPE_APP,
    coordinator_client,
    emit_profile,
    get_unit_ip_address,
    related_apps,
)

PROFILEGEN_SERVICE_NAME = "profilegen"
COLLECTOR_SERVICE_NAME = "profilegen-otel-collector"

# Pyroscope only names a profile "process_cpu" when the OTLP sample type is exactly
# "samples:count:cpu:nanoseconds"; otherwise it takes the third field of the type
# (pkg/ingester/otlp/convert.go). profilegen emits cpu/nanoseconds, so it lands as "cpu".
PROFILEGEN_PROFILE_TYPE = "cpu:cpu:nanoseconds:cpu:nanoseconds"

# Profiles trail the request that sends them, so the steps retry until they arrive.
_retried = retry(stop=stop_after_attempt(6), wait=wait_fixed(10), reraise=True)


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


def profile_query(service_name: str) -> str:
    return f'{PROFILEGEN_PROFILE_TYPE}{{service_name="{service_name}"}}'


def pyroscope_client(juju: jubilant.Juju):
    return coordinator_client(juju, get_unit_ip_address(juju, PYROSCOPE_APP, 0))


@when("a profile is emitted to Pyroscope")
def emit_profile_to_pyroscope(juju: jubilant.Juju, request: FixtureRequest):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(
        endpoint=f"{pyroscope_ip}:{NGINX_GRPC_PORT}", **tls_options(juju, request)
    )


@when("a profile is emitted to the OTel Collector")
def emit_profile_to_collector(juju: jubilant.Juju):
    collector_ip = get_unit_ip_address(juju, OTEL_COLLECTOR_APP, 0)
    emit_profile(endpoint=f"{collector_ip}:4317", service_name=COLLECTOR_SERVICE_NAME)


def has_profile(juju: jubilant.Juju, service_name: str) -> bool:
    flamebearer = pyroscope_client(juju).render(
        profile_query(service_name), start="now-1h"
    )["flamebearer"]
    return flamebearer["numTicks"] > 0


@then("Pyroscope has ingested the profile")
@_retried
def profile_is_ingested(juju: jubilant.Juju):
    assert has_profile(juju, PROFILEGEN_SERVICE_NAME), "No profile ingested"


@then("Pyroscope has ingested the profile from the OTel Collector")
@_retried
def profile_from_collector_is_ingested(juju: jubilant.Juju):
    assert has_profile(juju, COLLECTOR_SERVICE_NAME), "No profile ingested"


@then(parsers.parse('Pyroscope removes the profile after "{minutes:d}m"'))
@_retried
def profile_is_removed(juju: jubilant.Juju, minutes: int):
    time.sleep(minutes * 60)
    flamebearer = pyroscope_client(juju).render(
        profile_query(PROFILEGEN_SERVICE_NAME), start="now-1m"
    )["flamebearer"]
    # the profile is removed if numTicks (the number of samples) is 0
    assert flamebearer["numTicks"] == 0
