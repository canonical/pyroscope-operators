#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
from jubilant import Juju, all_blocked
from pytest_bdd import scenarios, given, when, then

from tests.integration.helpers import deploy_monolithic_cluster, PYROSCOPE_APP, S3_APP, WORKER_APP

scenarios("common/scaling.feature")


@given("a coordinator is deployed without S3 or workers")
def deploy_coordinator_only(juju: Juju, coordinator_charm):
    url, channel, resources = coordinator_charm
    juju.deploy(url, PYROSCOPE_APP, channel=channel, resources=resources, trust=True)


@then("the coordinator reports blocked status")
def coordinator_is_blocked(juju: Juju):
    juju.wait(lambda status: all_blocked(status, PYROSCOPE_APP), timeout=1000)


@when("the coordinator is scaled up to 2 units")
def scale_up_coordinator(juju: Juju):
    juju.cli("add-unit", PYROSCOPE_APP, "-n", "1")


@when("S3 and workers are deployed and integrated with the coordinator")
def deploy_s3_and_workers(juju: Juju):
    deploy_monolithic_cluster(
        juju, coordinator_deployed_as=PYROSCOPE_APP, wait_for_idle=True
    )


@then("the coordinator reports active status")
def coordinator_is_active(juju: Juju):
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, WORKER_APP, S3_APP),
        timeout=2000,
    )


@when("the S3 relation is removed")
def remove_s3_relation(juju: Juju):
    juju.remove_relation(S3_APP, PYROSCOPE_APP)
    # FIXME: s3 stubbornly refuses to die
    # juju.remove_application(S3_APP, force=True)
