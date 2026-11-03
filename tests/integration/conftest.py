# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from pathlib import Path
import tempfile

from pytest import fixture

from tests.integration.helpers import (
    charm_and_channel_and_resources,
    SSC_APP,
    PYROSCOPE_APP,
    WORKER_APP,
    TRAEFIK_APP,
    OTEL_COLLECTOR_APP,
    ALL_WORKERS,
    COS_COMPONENTS,
)
from jubilant import Juju, all_active, any_error

logger = logging.getLogger(__name__)


@fixture(scope="session")
def coordinator_charm():
    """Pyroscope coordinator used for integration testing."""
    return charm_and_channel_and_resources(
        "coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL"
    )


@fixture(scope="session")
def worker_charm():
    """Pyroscope worker used for integration testing."""
    return charm_and_channel_and_resources(
        "worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL"
    )


@fixture(scope="module")
def ca_cert_path(juju: Juju):
    """Provides a temporary file path to a CA certificate obtained from a deployed self-signed-certificates charm."""
    result = juju.run(f"{SSC_APP}/0", "get-ca-certificate")
    ca_cert = result.results["ca-certificate"]
    tmp_file_path = Path(tempfile.mkstemp(suffix=".pem")[1])
    tmp_file_path.write_text(ca_cert)

    yield tmp_file_path

    tmp_file_path.unlink(missing_ok=True)


@fixture(scope="module")
def teardown_ingress_stack(request, juju: Juju):
    """Remove the pyroscope + worker + traefik stack deployed for ingress tests."""
    yield
    if request.config.getoption("--no-teardown"):
        return
    juju.remove_application(PYROSCOPE_APP)
    juju.remove_application(WORKER_APP)
    juju.remove_application(TRAEFIK_APP)


@fixture(scope="module")
def teardown_collector_profiling_relation(request, juju: Juju):
    """Remove the profiling relation to the otel collector and wait for settle.

    Shared by test_profiling_with_collector.py and test_profiling_with_collector_tls.py.
    """
    yield
    if request.config.getoption("--no-teardown"):
        return
    juju.remove_relation(f"{PYROSCOPE_APP}:profiling", OTEL_COLLECTOR_APP)
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, WORKER_APP),
        timeout=10 * 60,
        error=lambda status: any_error(status, PYROSCOPE_APP, WORKER_APP),
        delay=10,
        successes=6,
    )


@fixture(scope="module")
def teardown_self_monitoring_stack(request, juju: Juju):
    """Remove COS components, then workers, then the coordinator."""
    yield
    if request.config.getoption("--no-teardown"):
        return
    for app in COS_COMPONENTS:
        juju.remove_application(app)
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_WORKERS),
        error=lambda status: any_error(status, PYROSCOPE_APP, *ALL_WORKERS),
        timeout=2000,
        delay=10,
        successes=3,
    )
    for worker_name in ALL_WORKERS:
        juju.remove_application(worker_name)
    juju.remove_application(PYROSCOPE_APP)