# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import sh
from jubilant import Juju, all_active, all_blocked

from tests.integration.helpers import (
    ALL_ROLES,
    PYROSCOPE_APP,
    WORKER_APP,
    deploy_s3,
    BUCKET_NAME,
    S3_APP,
    _deploy_and_configure_minio,
)


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


@pytest.mark.setup
def test_deploy_workers(juju: Juju, worker_charm):
    # GIVEN an empty model

    # WHEN deploying the workers with recommended scale
    for role in ALL_ROLES:
        _deploy_worker(juju, worker_charm, role, 1)

    # THEN workers will be blocked because of missing coordinator integration
    juju.wait(
        lambda status: all_blocked(status, *ALL_ROLES),
        timeout=1000,
    )


def test_all_active_when_coordinator_and_s3_added(juju: Juju, coordinator_charm):
    # GIVEN a model with workers

    # WHEN deploying and integrating the minimal pyroscope cluster
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
        juju.integrate(PYROSCOPE_APP + ":pyroscope-cluster", role + ":pyroscope-cluster")

    # THEN both the coordinator and the workers become active
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_ROLES),
        timeout=5000,
    )


def test_juju_doctor_probes(juju: Juju):
    # GIVEN the full model
    # THEN juju-doctor passes
    try:
        sh.uvx(
            "juju-doctor",
            "check",
            probe="file://../probes/cluster-consistency.yaml",
            model=juju.model,
        )
    except sh.ErrorReturnCode as e:
        pytest.fail(f"juju-doctor failed:\n{e.stderr.decode()}")
