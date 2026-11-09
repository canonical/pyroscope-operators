#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from jubilant import Juju
from pytest_bdd import scenarios, when, then
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.integration.helpers import (
    emit_profile,
    PYROSCOPE_APP,
    get_unit_ip_address,
    OTEL_COLLECTOR_APP,
)
from tests.integration.assertions import assert_profile_is_ingested

scenarios("profiling-with-collector.feature")


@when("we emit a profile to the OTel Collector using OTLP gRPC")
def emit_profile_to_collector(juju: Juju):
    collector_ip = get_unit_ip_address(juju, OTEL_COLLECTOR_APP, 0)
    emit_profile(
        endpoint=f"{collector_ip}:4317", service_name="profilegen-otel-collector"
    )


@then("the profile should be ingested by Pyroscope")
@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
def profile_from_collector_is_ingested(juju: Juju):
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_profile_is_ingested(
        hostname=pyroscope_ip, service_name="profilegen-otel-collector"
    )
