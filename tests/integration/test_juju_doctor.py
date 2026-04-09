# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import sh
from jubilant import Juju, all_active, all_blocked
from pytest_bdd import scenarios, given, when, then

from tests.integration.helpers import (
    ALL_ROLES,
    PYROSCOPE_APP,
    deploy_s3,
    BUCKET_NAME,
    S3_APP,
    _deploy_and_configure_minio,
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


@given("all worker roles are deployed")
def deploy_workers(juju: Juju, worker_charm):
    for role in ALL_ROLES:
        _deploy_worker(juju, worker_charm, role, 1)
    juju.wait(
        lambda status: all_blocked(status, *ALL_ROLES),
        timeout=1000,
    )


@when("the coordinator and S3 are deployed and integrated with the workers")
def deploy_coordinator_and_s3(juju: Juju, coordinator_charm):
    _deploy_and_configure_minio(juju)
    deploy_s3(juju, bucket_name=BUCKET_NAME, s3_integrator_app=S3_APP)

    charm_url, channel, resources = coordinator_charm
    juju.deploy(
        charm_url,
        PYROSCOPE_APP,
        channel=channel,
        resources=resources,
        trust=True,
    )
    juju.integrate(PYROSCOPE_APP + ":s3", S3_APP + ":s3-credentials")
    for role in ALL_ROLES:
        juju.integrate(
            PYROSCOPE_APP + ":pyroscope-cluster", role + ":pyroscope-cluster"
        )


@then("the full cluster reaches active/idle")
def cluster_active(juju: Juju):
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_ROLES),
        timeout=5000,
    )


@then("the juju-doctor cluster-consistency probe passes")
def juju_doctor_probe_passes(juju: Juju):
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
