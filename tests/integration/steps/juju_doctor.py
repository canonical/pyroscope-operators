# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about the probes of juju-doctor on a cluster with a worker for every role."""

import jubilant
import pytest
import sh
from pytest_bdd import given, then, when

from tests.integration.helpers import (
    ALL_ROLES,
    PYROSCOPE_APP,
    SWFS_APP,
    deploy_swfs,
)


def _deploy_worker(juju: jubilant.Juju, worker_charm, role: str, scale: int):
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


@given("a worker is deployed for every role")
def worker_is_deployed_for_every_role(juju: jubilant.Juju, worker_charm):
    for role in ALL_ROLES:
        if role not in juju.status().apps:
            _deploy_worker(juju, worker_charm, role, 1)


@when("the coordinator is deployed with an s3 backend and related to the workers")
def coordinator_is_deployed_and_related(juju: jubilant.Juju, coordinator_charm):
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


@then("the workers are blocked")
def workers_are_blocked(juju: jubilant.Juju):
    # the workers are blocked because of the missing coordinator integration
    juju.wait(
        lambda status: jubilant.all_blocked(status, *ALL_ROLES),
        timeout=1000,
    )


@then("juju-doctor passes")
def juju_doctor_passes(juju: jubilant.Juju):
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
