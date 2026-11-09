# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about Pyroscope's own deployment: deploying, scaling, configuring, health.

Every feature runs in its own model (pytest-jubilant's module-scoped `juju` fixture),
so the scenarios of a feature share it. `Given` steps are idempotent: they bring the
model to the state they describe, whatever an earlier scenario left.
"""

import jubilant
from pytest_bdd import given, parsers, then, when

from tests.integration.helpers import (
    ALL_ROLES,
    ALL_WORKERS,
    PYROSCOPE_APP,
    SWFS_APP,
    WORKER_APP,
    deploy_distributed_cluster,
    ensure_monolithic_cluster,
)


def wait_for_active(juju: jubilant.Juju, *apps: str, timeout: float = 2000) -> None:
    juju.wait(
        lambda status: (
            jubilant.all_active(status, *apps)
            and jubilant.all_agents_idle(status, *apps)
        ),
        timeout=timeout,
        delay=10,
        successes=3,
    )


def scale(juju: jubilant.Juju, coordinator_charm, units: int) -> None:
    """Scale the coordinator to `units`, deploying it first if needed.

    A coordinator without an s3 backend and workers is blocked, so this waits for the
    units to exist rather than for them to be active.
    """
    if PYROSCOPE_APP not in juju.status().apps:
        url, channel, resources = coordinator_charm
        juju.deploy(
            url, PYROSCOPE_APP, channel=channel, resources=resources, trust=True
        )
    current = len(juju.status().apps[PYROSCOPE_APP].units)
    if units > current:
        juju.add_unit(PYROSCOPE_APP, num_units=units - current)
    elif units < current:
        juju.remove_unit(PYROSCOPE_APP, num_units=current - units)
    juju.wait(
        lambda status: len(status.apps[PYROSCOPE_APP].units) == units, timeout=1000
    )


@given("Pyroscope is deployed")
def pyroscope_is_deployed(juju: jubilant.Juju):
    ensure_monolithic_cluster(juju)
    wait_for_active(juju, PYROSCOPE_APP, WORKER_APP, SWFS_APP)


@given("Pyroscope is deployed with a worker for every role")
def pyroscope_is_deployed_with_every_role(juju: jubilant.Juju):
    if PYROSCOPE_APP not in juju.status().apps:
        deploy_distributed_cluster(juju, ALL_ROLES, wait_for_idle=False)
    wait_for_active(juju, PYROSCOPE_APP, *ALL_WORKERS, SWFS_APP)


@given(parsers.re(r"the coordinator has (?P<units>\d+) units?"))
def coordinator_has_units(juju: jubilant.Juju, coordinator_charm, units: str):
    scale(juju, coordinator_charm, int(units))


@given(parsers.parse('the "{option}" option is "{value}"'))
def option_is_set(juju: jubilant.Juju, option: str, value: str):
    juju.config(PYROSCOPE_APP, {option: value})
    # juju.config returns before the services restart
    wait_for_active(juju, PYROSCOPE_APP, WORKER_APP)


@when(parsers.re(r"the coordinator is scaled to (?P<units>\d+) units?"))
def coordinator_is_scaled(juju: jubilant.Juju, coordinator_charm, units: str):
    scale(juju, coordinator_charm, int(units))


@then("Pyroscope is healthy")
def pyroscope_is_healthy(juju: jubilant.Juju):
    """Every application in the model is active and idle."""
    wait_for_active(juju, *juju.status().apps)


@then("the coordinator is blocked")
def coordinator_is_blocked(juju: jubilant.Juju):
    # the coordinator is blocked because of the missing s3 and workers integration
    juju.wait(lambda status: jubilant.all_blocked(status, PYROSCOPE_APP), timeout=1000)
