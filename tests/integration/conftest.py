# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging

from jubilant import Juju
from pytest import fixture

from tests.integration.helpers import get_unit_ip_address
from pathlib import Path
import os
import subprocess
from minio import Minio

from typing import Literal, Sequence
from pytest_jubilant import get_resources, pack
import jubilant
from coordinator.src.pyroscope_config import PyroscopeRole


# Application names used uniformly across the tests
ACCESS_KEY = "accesskey"
SECRET_KEY = "secretkey"
BUCKET_NAME = "pyroscope"
MINIO_APP = "minio"
S3_APP = "s3-integrator"
WORKER_APP = "pyroscope-worker"
PYROSCOPE_APP = "pyroscope"
SSC_APP = "ssc"
ALL_ROLES = [role.value for role in PyroscopeRole.all_nonmeta()]
ALL_WORKERS = [f"{WORKER_APP}-" + role for role in ALL_ROLES]

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption(
        "--tls",
        action="store",
        choices=["true", "false"],
        default="false",
        help="Enable TLS (true/false)"
    )
    parser.addoption(
        "--monolithic",
        action="store",
        choices=["true", "false"],
        default="false",
        help="Enable monolithic mode (true/false)"
    )

def _charm_and_channel_and_resources(role: Literal["coordinator", "worker"], charm_path_key: str, charm_channel_key: str):
    """Pyrosocope coordinator or worker charm used for integration testing.

    Build once per session and reuse it in all integration tests to save some minutes/hours.
    """
    # deploy charm from charmhub
    if channel_from_env := os.getenv(charm_channel_key):
        charm = f"pyroscope-{role}-k8s"
        logger.info(f"Using published {charm} charm from {channel_from_env}")
        return charm, channel_from_env, None
    # else deploy from a charm packed locally
    elif path_from_env := os.getenv(charm_path_key):
        charm_path = Path(path_from_env).absolute()
        logger.info("Using local {role} charm: %s", charm_path)
        return (
            charm_path,
            None,
            get_resources(charm_path.parent),
        )
    # else try to pack the charm
    for _ in range(3):
        logger.info(f"packing Pyroscope {role} charm...")
        try:
            pth = pack(Path() / role).charm.absolute()
        except subprocess.CalledProcessError:
            logger.warning(f"Failed to build Pyroscope {role}. Trying again!")
            continue
        os.environ[charm_path_key] = str(pth)
        return pth, None, get_resources(pth.parent / role)
    raise subprocess.CalledProcessError


def _deploy_distributed_cluster(juju: Juju, roles: Sequence[str], coordinator_deployed_as=None):
    """Deploy a pyroscope distributed cluster."""
    worker_charm_url, channel, resources = _charm_and_channel_and_resources("worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL")

    all_workers = []

    for role in roles:
        worker_name = f"{WORKER_APP}-{role}"
        all_workers.append(worker_name)

        juju.deploy(
            worker_charm_url,
            app=worker_name,
            channel=channel,
            trust=True,
            config={"role-all": False, f"role-{role}": True},
            resources=resources,
        )

    _deploy_cluster(juju, all_workers, coordinator_deployed_as=coordinator_deployed_as)

def _deploy_monolithic_cluster(juju: Juju, coordinator_deployed_as=None):
    """Deploy a pyroscope-monolithic cluster."""
    worker_charm_url, channel, resources = _charm_and_channel_and_resources("worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL")

    juju.deploy(
        worker_charm_url,
        app=WORKER_APP,
        channel=channel,
        trust=True,
        resources=resources,
    )
    _deploy_cluster(juju, [WORKER_APP], coordinator_deployed_as=coordinator_deployed_as)

def _deploy_cluster(juju: Juju, workers: Sequence[str], coordinator_deployed_as: str = None):
    if coordinator_deployed_as:
        coordinator_app = coordinator_deployed_as
    else:
        coordinator_charm_url, channel, resources = _charm_and_channel_and_resources("coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL")
        juju.deploy(
            coordinator_charm_url, PYROSCOPE_APP, channel=channel, resources=resources, trust=True
        )
        coordinator_app = PYROSCOPE_APP

    juju.deploy(S3_APP, channel="edge")

    juju.integrate(coordinator_app + ":s3", S3_APP + ":s3-credentials")
    for worker in workers:
        juju.integrate(coordinator_app + ":pyroscope-cluster", worker + ":pyroscope-cluster")

    _deploy_and_configure_minio(juju)

    juju.wait(
        lambda status: jubilant.all_active(status, coordinator_app, *workers, S3_APP),
        timeout=2000,
        delay=5,
        successes=3,
    )

def _deploy_and_configure_minio(juju: Juju):
    keys = {
        "access-key": ACCESS_KEY,
        "secret-key": SECRET_KEY,
    }
    juju.deploy(MINIO_APP, channel="edge", trust=True, config=keys)
    juju.wait(
        lambda status: status.apps[MINIO_APP].is_active,
        error=jubilant.any_error,
        delay=5,
        successes=3,
    )
    minio_addr = get_unit_ip_address(juju, MINIO_APP, 0)

    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        secure=False,
    )

    # create pyroscope bucket
    found = mc_client.bucket_exists(BUCKET_NAME)
    if not found:
        mc_client.make_bucket(BUCKET_NAME)

    # configure s3-integrator
    juju.config(S3_APP, {
        "endpoint": f"minio-0.minio-endpoints.{juju.model}.svc.cluster.local:9000",
        "bucket": BUCKET_NAME,
    })
    task = juju.run(S3_APP + "/0", "sync-s3-credentials", params=keys)
    assert task.status == "completed"

def _setup_tls(juju: Juju, monolithic: bool):
    """Deploy a certificates provider app and relate it to an existing pyroscope cluster."""
    juju.deploy("self-signed-certificates", SSC_APP)
    juju.integrate(PYROSCOPE_APP + ":certificates", SSC_APP + ":certificates")

    workers = ALL_WORKERS if not monolithic else (WORKER_APP, )
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, *workers, SSC_APP),
        timeout=2000,
        delay=10,
        successes=3,
    )

def _teardown_tls(juju: Juju, monolithic: bool):
    """Remove a certificates provider app."""
    juju.remove_application(SSC_APP)

    workers = ALL_WORKERS if not monolithic else (WORKER_APP, )
    juju.wait(
        lambda status: jubilant.all_active(status, PYROSCOPE_APP, *workers),
        timeout=2000,
        delay=10,
        successes=3,
    )
    
def _remove_pyroscope_cluster(juju: Juju, monolithic: bool):
    """Remove a monolithic or distributed pyroscope cluster."""
    juju.remove_application(PYROSCOPE_APP)
    workers = ALL_WORKERS if not monolithic else (WORKER_APP, )
    for worker in workers:
        juju.remove_application(worker)   

@fixture(scope="session")
def coordinator_charm():
    """Pyroscope coordinator used for integration testing."""
    return _charm_and_channel_and_resources("coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL")

@fixture(scope="session")
def worker_charm():
    """Pyroscope worker used for integration testing."""
    return _charm_and_channel_and_resources("worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL")

# TODO: add True when TLS is supported
@fixture(scope="session")
def tls(pytestconfig):
    return pytestconfig.getoption("tls") == "true"

@fixture(scope="session")
def monolithic(pytestconfig):
    return pytestconfig.getoption("monolithic") == "true"

@fixture(scope="module", autouse=True)
# @contextmanager
def pyroscope_deployment(pytestconfig, juju, tls, monolithic):
    # setup
    if not pytestconfig.getoption('--no-setup'):
        _deploy_monolithic_cluster(juju) if monolithic else  _deploy_distributed_cluster(juju, ALL_ROLES) 
        if tls:
            _setup_tls(juju, monolithic)
    yield
    # teardown
    if not pytestconfig.getoption('--no-teardown'):
        if tls:
            _teardown_tls(juju, monolithic)
        _remove_pyroscope_cluster(juju, monolithic)


 
