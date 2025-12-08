#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import time
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed
from helpers import (
    deploy_monolithic_cluster,
    emit_profile,
    PYROSCOPE_APP,
    get_unit_ip_address,
)
from assertions import assert_no_profiles, assert_profile_is_ingested
from pytest_bdd import given, when, then


@pytest.mark.setup
@given("a pyroscope cluster is deployed")
def test_deploy_pyroscope(juju: Juju):
    deploy_monolithic_cluster(juju, wait_for_idle=True)


@when("we set retention time to `1m` and emit a profile to pyroscope using otlp grpc")
def test_configure_retention_and_ingest_profile(juju: Juju):
    juju.config(
        PYROSCOPE_APP,
        {"retention_period": "1m", "deletion_delay": "0", "cleanup_interval": "30s"},
    )
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(endpoint=f"{pyroscope_ip}:42424")
    assert_profile_is_ingested(hostname=pyroscope_ip)


@retry(stop=stop_after_attempt(6), wait=wait_fixed(10))
@then("the profile should be removed after `1m`")
def test_profile_removed(juju: Juju):
    time.sleep(1 * 60)
    pyroscope_ip = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    assert_no_profiles(hostname=pyroscope_ip)
