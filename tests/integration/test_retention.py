#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import time
from jubilant import Juju, all_active
from pytest_bdd import parsers, scenarios, when, then
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.integration.helpers import (
    emit_profile,
    PYROSCOPE_APP,
    WORKER_APP,
    get_unit_ip_address,
)
from tests.integration.assertions import assert_no_profiles, assert_profile_is_ingested

scenarios("retention.feature")


@when(
    parsers.parse(
        'we set retention time to "{minutes:d}m" and emit a profile to Pyroscope using OTLP gRPC'
    )
)
def configure_retention_and_ingest_profile(juju: Juju, minutes: int):
    juju.config(
        PYROSCOPE_APP,
        {"retention_period": f"{minutes}m"},
    )
    # juju.config returns before services restart, so an immediate push may
    # hit a closed gRPC port.

    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP),
        timeout=1000,
        delay=5,
        successes=3,
    )
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(endpoint=f"{pyroscope_ip}:42424")
    assert_profile_is_ingested(hostname=pyroscope_ip)


@then(parsers.parse('the profile should be removed after "{minutes:d}m"'))
@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
def profile_is_removed(juju: Juju, minutes: int):
    time.sleep(minutes * 60)
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_no_profiles(hostname=pyroscope_ip)
