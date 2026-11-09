# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import sh
from jubilant import Juju, all_active, all_blocked
from pytest_bdd import given, scenarios, when, then

from tests.integration.helpers import (
    ALL_ROLES,
    PYROSCOPE_APP,
    SWFS_APP,
    deploy_swfs,
)

scenarios("juju-doctor.feature")


def _deploy_worker(juju: Juju, worker_charm, role: str, scale: int):
    """Deploy a worker for a specific role."""
    charm_url, channel, resources = worker_charm
    juju.deploy(
        charm_url,
        role,
        channel=channel,
        resources=resources,
        trust=True,
        config={
            "role-all": False,
            f"role-{role}": True,
        },
        num_units=scale,
    )


@given("the workers are deployed with the recommended scale")
def workers_are_deployed(juju: Juju, worker_charm):
    for role in ALL_ROLES:
        if role not in juju.status().apps:
            _deploy_worker(juju, worker_charm, role, 1)


@then("the workers are blocked because of the missing coordinator integration")
def workers_are_blocked(juju: Juju):
    juju.wait(
        lambda status: all_blocked(status, *ALL_ROLES),
        timeout=1000,
    )


@when("the Pyroscope coordinator and SWFS are deployed and integrated with the workers")
def deploy_and_integrate_minimal_cluster(juju: Juju, coordinator_charm):
    deploy_swfs(juju)

    charm_url, channel, resources = coordinator_charm
    juju.deploy(
        charm_url,
        PYROSCOPE_APP,
        channel=channel,
        resources=resources,
        trust=True,
    )
    juju.integrate(PYROSCOPE_APP + ":s3", SWFS_APP)
    for role in ALL_ROLES:
        juju.integrate(
            PYROSCOPE_APP + ":pyroscope-cluster", role + ":pyroscope-cluster"
        )


@then("both the coordinator and the workers become active")
def coordinator_and_workers_are_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_ROLES),
        timeout=5000,
    )


@then("juju-doctor passes")
def juju_doctor_passes(juju: Juju):
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
