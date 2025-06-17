# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
import yaml
from pathlib import Path
import os
import subprocess
from minio import Minio

from typing import Literal, Optional, Sequence, Union
from pytest_jubilant import pack_charm
from jubilant import Juju
import jubilant
from coordinator.src.pyroscope_config import PyroscopeRole
from coordinator.src.nginx_config import _nginx_port

# Application names used uniformly across the tests
ACCESS_KEY = "accesskey"
SECRET_KEY = "secretkey"
BUCKET_NAME = "pyroscope"
MINIO_APP = "minio"
S3_APP = "s3-integrator"
WORKER_APP = "pyroscope-worker"
PYROSCOPE_APP = "pyroscope"
TRAEFIK_APP = "trfk"
ALL_ROLES = [role.value for role in PyroscopeRole.all_nonmeta()]
ALL_WORKERS = [f"{WORKER_APP}-" + role for role in ALL_ROLES]
SAMPLE_PROFILE_DATA = "foo;bar 100"

logger = logging.getLogger(__name__)

def get_unit_ip_address(juju: Juju, app_name: str, unit_no: int):
    """Return a juju unit's IP address."""
    return juju.status().apps[app_name].units[f"{app_name}/{unit_no}"].address

def charm_and_channel_and_resources(role: Literal["coordinator", "worker"], charm_path_key: str, charm_channel_key: str):
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
            _get_resources(charm_path.parent),
        )
    # else try to pack the charm
    for _ in range(3):
        logger.info(f"packing Pyroscope {role} charm...")
        try:
            pth = pack_charm(Path() / role).charm.absolute()
        except subprocess.CalledProcessError:
            logger.warning(f"Failed to build Pyroscope {role}. Trying again!")
            continue
        os.environ[charm_path_key] = str(pth)
        return pth, None, _get_resources(pth.parent / role)
    raise subprocess.CalledProcessError

def deploy_distributed_cluster(juju: Juju, roles: Sequence[str], coordinator_deployed_as=None):
    """Deploy a pyroscope distributed cluster."""
    worker_charm_url, channel, resources = charm_and_channel_and_resources("worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL")

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

def deploy_monolithic_cluster(juju: Juju, coordinator_deployed_as=None):
    """Deploy a pyroscope-monolithic cluster."""
    worker_charm_url, channel, resources = charm_and_channel_and_resources("worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL")

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
        coordinator_charm_url, channel, resources = charm_and_channel_and_resources("coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL")
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

def _get_resources(path: Union[str, Path]):
    meta = yaml.safe_load((Path(path) / "charmcraft.yaml").read_text())
    resources_meta = meta.get("resources", {})
    return {res_name: res_meta["upstream-source"] for res_name, res_meta in resources_meta.items()}

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

def get_ingress_proxied_endpoint(juju: Juju):
    result = juju.run(f"{TRAEFIK_APP}/0", "show-proxied-endpoints")
    endpoints = json.loads(result.results["proxied-endpoints"])
    assert PYROSCOPE_APP in endpoints
    return endpoints[PYROSCOPE_APP]["url"]


def emit_profile(
        address,
        service_name: Optional[str] = "profilegen"
    ):
    """Emit profiling data to a Pyroscope backend using a simple `Text` format."""
    endpoint = f"http://{address}:{_nginx_port}/ingest"
    params = {
        "name": service_name,
    }
    try:
        response = requests.post(endpoint, params=params, data=SAMPLE_PROFILE_DATA)
        assert response.ok, f"Expected 2xx, got {response.status_code}: {response.text}"
        return response.ok
    # network-related issues
    except requests.exceptions.RequestException as e:
        assert False, f"Unexpected error: {e}"

def get_profiles(    
    address,
    service_name: Optional[str] = "profilegen" 
):
    """Query the Pyroscope backend for profiles with the service_name label."""
    endpoint = f"http://{address}:{_nginx_port}/pyroscope/render"
    params = {
        "query": f'process_cpu:cpu:nanoseconds:cpu:nanoseconds{{service_name="{service_name}"}}',
        "from": "now-1h"
    }
    try:
        response = requests.get(endpoint, params=params)
        assert response.ok, f"Expected 2xx, got {response.status_code}: {response.text}"
        samples = response.json()["timeline"]["samples"]
        assert any(samples), "No samples found"
        return samples
    # network-related issues
    except requests.exceptions.RequestException as e:
        assert False, f"Unexpected error: {e}"

# retry up to 5 times, waiting 4 seconds between attempts
@retry(stop=stop_after_attempt(5), wait=wait_fixed(4))
def get_profiles_patiently(
    address,
    service_name: Optional[str] = "profilegen" 
):
    logger.info(f"polling {address} for service {service_name!r} profiles...")
    return get_profiles(address, service_name)

