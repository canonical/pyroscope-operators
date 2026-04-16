# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging

import pytest
from jubilant import Juju, all_active
from pytest_bdd import given, scenarios, then

from tests.integration.helpers import (
    ALL_ROLES,
    INTEGRATION_TESTERS_CHANNEL,
    PYROSCOPE_APP,
    deploy_distributed_cluster,
)

CATALOGUE_APP = "catalogue"

logger = logging.getLogger(__name__)

scenarios("catalogue.feature")


@pytest.fixture(scope="module")
def _cos_cluster(juju: Juju):
    """Deploy pyroscope with catalogue integration. Runs once per module."""
    deploy_distributed_cluster(juju, ALL_ROLES, wait_for_idle=False)
    juju.deploy("catalogue-k8s", CATALOGUE_APP, channel=INTEGRATION_TESTERS_CHANNEL)
    juju.integrate(PYROSCOPE_APP, CATALOGUE_APP)
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, CATALOGUE_APP),
        timeout=1200,
        delay=5,
        successes=5,
    )


@given("a pyroscope cluster is deployed with catalogue")
def cluster_with_catalogue(_cos_cluster):
    pass


@then("catalogue items are provisioned")
def catalogue_integration(juju: Juju):
    catalogue_unit = f"{CATALOGUE_APP}/0"
    out = juju.cli(
        "show-unit", catalogue_unit, "--endpoint", "catalogue", "--format", "json"
    )
    pyroscope_app_databag = json.loads(out)[catalogue_unit]["relation-info"][0][
        "application-data"
    ]
    url = pyroscope_app_databag["url"]
    # query the url from inside the container in case the url is a K8s fqdn
    response = juju.ssh(f"{PYROSCOPE_APP}/0", f"curl {url}")
    assert "<title>Grafana Pyroscope</title>" in response
