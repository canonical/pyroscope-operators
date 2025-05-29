
import logging
import pytest
from jubilant import Juju, all_blocked
from pathlib import Path
from helpers import WORKER_APP, WORKER_RESOURCES

logger = logging.getLogger(__name__)

@pytest.mark.setup
def test_deploy_worker(juju: Juju, coordinator_charm: Path):
    juju.deploy(
        coordinator_charm, WORKER_APP, resources=WORKER_RESOURCES, trust=True
    )

    # coordinator will be blocked because of missing s3 and workers integration
    juju.wait(
        lambda status: all_blocked(status, WORKER_APP),
        timeout=1000,
        delay=5,
        successes=3,
    )


def test_scale_worker_up_stays_blocked(juju: Juju):
    juju.cli("add-unit", WORKER_APP, "-n", "1")
    juju.wait(
        lambda status: all_blocked(status, WORKER_APP),
        timeout=1000,
        delay=5,
        successes=3,
    )


@pytest.mark.teardown
def test_teardown(juju: Juju):
    juju.remove_application(WORKER_APP)
