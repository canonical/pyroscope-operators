# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import sh
from jubilant import Juju, all_active, all_blocked

from tests.integration.helpers import (
    ALL_ROLES,
    PYROSCOPE_APP,
    SWFS_APP,
    deploy_swfs,
)

from pytest_bdd import given, when, then


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


@given("an empty model")
def test_model_is_empty(juju: Juju):
    assert juju.status().apps == {}


@pytest.mark.setup
@when("deploying the workers with recommended scale")
def test_deploy_workers(juju: Juju, worker_charm):
    for role in ALL_ROLES:
        _deploy_worker(juju, worker_charm, role, 1)


@then("workers will be blocked because of missing coordinator integration")
def test_workers_blocked(juju: Juju):
    juju.wait(
        lambda status: all_blocked(status, *ALL_ROLES),
        timeout=1000,
    )


@given("a model with workers")
def test_model_has_workers(juju: Juju):
    apps = juju.status().apps
    assert all(role in apps for role in ALL_ROLES)


@when("deploying and integrating the minimal Pyroscope cluster")
def test_deploy_and_integrate_minimal_cluster(juju: Juju, coordinator_charm):
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
def test_coordinator_and_workers_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_ROLES),
        timeout=5000,
    )


@given("the full model")
def test_full_model(juju: Juju):
    apps = juju.status().apps
    assert PYROSCOPE_APP in apps
    assert SWFS_APP in apps
    assert all(role in apps for role in ALL_ROLES)


@then("juju-doctor passes")
def test_juju_doctor_probes(juju: Juju):
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
