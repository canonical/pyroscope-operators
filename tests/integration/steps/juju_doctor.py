# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about the probes of juju-doctor."""

import jubilant
import pytest
import sh
from pytest_bdd import then


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
