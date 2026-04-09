#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest

pytestmark = [
    pytest.mark.skip(
        reason="Skipped due to https://github.com/canonical/pyroscope-operators/issues/315"
    ),
]

import time
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.integration.helpers import (
    deploy_monolithic_cluster,
    emit_profile,
    PYROSCOPE_APP,
    get_unit_ip_address,
)
from tests.integration.assertions import assert_no_profiles, assert_profile_is_ingested
from pytest_bdd import scenarios, given, when, then

scenarios("retention.feature")


@given("a pyroscope cluster is deployed")
def deploy_pyroscope(juju: Juju):
    deploy_monolithic_cluster(juju, wait_for_idle=True)


@when('we configure retention policy to "1m" and emit a profile')
def configure_retention_and_ingest_profile(juju: Juju):
    juju.config(
        PYROSCOPE_APP,
        {"retention_period": "1m", "deletion_delay": "0", "cleanup_interval": "30s"},
    )
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(endpoint=f"{pyroscope_ip}:42424")
    assert_profile_is_ingested(hostname=pyroscope_ip)


@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
@then('the profile should be removed after "1m"')
def profile_removed(juju: Juju):
    time.sleep(1 * 60)
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_no_profiles(hostname=pyroscope_ip)
