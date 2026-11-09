#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from jubilant import Juju, all_active, all_blocked
from pytest_bdd import given, parsers, scenarios, when, then

from tests.integration.helpers import (
    PYROSCOPE_APP,
    SWFS_APP,
    WORKER_APP,
    deploy_monolithic_cluster,
    related_apps,
)

scenarios("scaling-monolithic.feature")


def integrate_s3_and_worker(juju: Juju):
    """Make sure the coordinator has an s3 backend and a worker, deploying what is missing."""
    if WORKER_APP not in juju.status().apps:
        deploy_monolithic_cluster(
            juju, coordinator_deployed_as=PYROSCOPE_APP, wait_for_idle=False
        )
    elif SWFS_APP not in related_apps(juju, PYROSCOPE_APP, "s3"):
        juju.integrate(PYROSCOPE_APP + ":s3", SWFS_APP)


def wait_for_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP, SWFS_APP),
        timeout=2000,
        delay=5,
        successes=3,
    )


@given("a Pyroscope coordinator is deployed with no other relations")
def pyroscope_coordinator_is_deployed_alone(juju: Juju, coordinator_charm):
    # the scenarios that need the coordinator to be blocked come before the ones that integrate it
    if PYROSCOPE_APP not in juju.status().apps:
        url, channel, resources = coordinator_charm
        juju.deploy(
            url, PYROSCOPE_APP, channel=channel, resources=resources, trust=True
        )


@given("the coordinator, s3 backend and worker are all integrated and active")
def coordinator_s3_and_worker_are_integrated(juju: Juju):
    integrate_s3_and_worker(juju)
    wait_for_active(juju)


@when(parsers.parse("we scale the coordinator to {units:d} units"))
def scale_coordinator(juju: Juju, units: int):
    current = len(juju.status().apps[PYROSCOPE_APP].units)
    if units > current:
        juju.add_unit(PYROSCOPE_APP, num_units=units - current)


@when(
    "we integrate the coordinator with an s3 backend and a worker that runs every role"
)
def integrate_coordinator_with_s3_and_worker(juju: Juju):
    integrate_s3_and_worker(juju)


@when("we remove the s3 relation")
def remove_s3_relation(juju: Juju):
    if SWFS_APP in related_apps(juju, PYROSCOPE_APP, "s3"):
        juju.remove_relation(SWFS_APP, PYROSCOPE_APP)
    # FIXME: s3 stubbornly refuses to die
    # juju.remove_application(SWFS_APP, force=True)


@then("the coordinator is blocked")
def coordinator_is_blocked(juju: Juju):
    # the coordinator is blocked because of the missing s3 and workers integration
    juju.wait(lambda status: all_blocked(status, PYROSCOPE_APP), timeout=1000)


@then("the coordinator and the worker are active")
def coordinator_and_worker_are_active(juju: Juju):
    wait_for_active(juju)
