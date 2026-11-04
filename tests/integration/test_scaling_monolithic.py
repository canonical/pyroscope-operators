#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from jubilant import Juju, all_active, all_blocked
from pytest_bdd import given, when, then

from tests.integration.helpers import (
    PYROSCOPE_APP,
    SWFS_APP,
    WORKER_APP,
    deploy_monolithic_cluster,
)


@pytest.mark.setup
@given("a Pyroscope coordinator is deployed with no other relations")
def test_deploy_pyroscope_alone(juju: Juju, coordinator_charm):
    url, channel, resources = coordinator_charm
    juju.deploy(url, PYROSCOPE_APP, channel=channel, resources=resources, trust=True)


@then("the coordinator is blocked")
def test_coordinator_blocked_alone(juju: Juju):
    # coordinator is blocked because of missing s3 and workers integration
    juju.wait(lambda status: all_blocked(status, PYROSCOPE_APP), timeout=1000)


@when("we add a coordinator unit")
def test_add_coordinator_unit(juju: Juju):
    juju.cli("add-unit", PYROSCOPE_APP, "-n", "1")


@then("the coordinator is blocked")
def test_coordinator_stays_blocked_after_scale_up(juju: Juju):
    juju.wait(lambda status: all_blocked(status, PYROSCOPE_APP), timeout=1000)


@pytest.mark.setup
@when("we deploy an s3 backend and a full monolithic set of workers, and integrate them")
@then("the coordinator and workers are active")
def test_deploy_swfs_and_workers(juju: Juju):
    deploy_monolithic_cluster(
        juju, coordinator_deployed_as=PYROSCOPE_APP, wait_for_idle=True
    )


@given("the coordinator, s3 backend and workers are all integrated and active")
def test_coordinator_swfs_workers_integrated(juju: Juju):
    status = juju.status()
    assert all_active(status, PYROSCOPE_APP, WORKER_APP, SWFS_APP)


@pytest.mark.teardown
@when("we remove the s3 relation")
def test_remove_s3_relation(juju: Juju):
    juju.remove_relation(SWFS_APP, PYROSCOPE_APP)
    # FIXME: s3 stubbornly refuses to die
    # juju.remove_application(SWFS_APP, force=True)


@then("the coordinator is blocked")
def test_coordinator_blocked_after_s3_removed(juju: Juju):
    juju.wait(lambda status: all_blocked(status, PYROSCOPE_APP), timeout=1000)