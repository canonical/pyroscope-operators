# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from pathlib import Path
import tempfile

from pytest import fixture
from pytest_bdd import given

from tests.integration.helpers import (
    CHANNELS,
    charm_and_channel_and_resources,
    ensure_monolithic_cluster,
    OTEL_COLLECTOR_APP,
    PYROSCOPE_APP,
    related_apps,
    SSC_APP,
    WORKER_APP,
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


@given("a Pyroscope cluster is deployed")
def pyroscope_cluster_is_deployed(juju: Juju):
    ensure_monolithic_cluster(juju)


@given(
    "an OTel Collector charm is deployed and integrated with Pyroscope over profiling"
)
def collector_is_integrated_with_pyroscope(juju: Juju):
    if OTEL_COLLECTOR_APP not in juju.status().apps:
        juju.deploy(
            "opentelemetry-collector-k8s",
            OTEL_COLLECTOR_APP,
            channel=CHANNELS["opentelemetry-collector-k8s"],
            trust=True,
        )
    if OTEL_COLLECTOR_APP not in related_apps(juju, PYROSCOPE_APP, "profiling"):
        juju.integrate(f"{PYROSCOPE_APP}:profiling", OTEL_COLLECTOR_APP)
    juju.wait(
        lambda status: all_active(
            status, PYROSCOPE_APP, WORKER_APP, OTEL_COLLECTOR_APP
        ),
        timeout=10 * 60,
        error=lambda status: any_error(status, PYROSCOPE_APP, WORKER_APP),
        delay=10,
        successes=6,
    )
