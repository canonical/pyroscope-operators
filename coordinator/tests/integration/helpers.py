# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Literal, Optional, Sequence

import jubilant
from jubilant import Juju
from minio import Minio
from pytest_jubilant import get_resources, pack

REPO_ROOT = Path(__file__).resolve().parents[2]

CI_TRUE_VALUES = {"1", "true", "yes"}
COORDINATOR_CHARM_FILENAME = "pyroscope-coordinator-k8s_ubuntu@24.04-amd64.charm"
WORKER_CHARM_FILENAME = "pyroscope-worker-k8s_ubuntu@24.04-amd64.charm"

# Application names used uniformly across the tests
ACCESS_KEY = "accesskey"
SECRET_KEY = "secretkey"
BUCKET_NAME = "pyroscope"
MINIO_APP = "minio"
S3_APP = "s3-integrator"
WORKER_APP = "pyroscope-worker"
PYROSCOPE_APP = "pyroscope"
TRAEFIK_APP = "trfk"
OTEL_COLLECTOR_APP = "opentelemetry-collector"
SSC_APP = "ssc"
# we don't import this from the coordinator module because that'd mean we need to
# bring in the whole charm's dependencies just to run the integration tests
ALL_ROLES = [
    "querier",
    "query-frontend",
    "query-scheduler",
    "ingester",
    "distributor",
    "compactor",
    "store-gateway",
    "tenant-settings",
    "ad-hoc-profiles",
]
ALL_WORKERS = [f"{WORKER_APP}-" + role for role in ALL_ROLES]
S3_CREDENTIALS = {
    "access-key": ACCESS_KEY,
    "secret-key": SECRET_KEY,
}
INTEGRATION_TESTERS_CHANNEL = "2/edge"
PROFILEGEN_SCRIPT_PATH = REPO_ROOT / "scripts" / "profilegen.py"

logger = logging.getLogger(__name__)


def _ci_enabled() -> bool:
    return os.getenv("CI", "").strip().lower() in CI_TRUE_VALUES


def _set_ci_charm_paths_if_unset() -> None:
    if not _ci_enabled():
        return

    coordinator_path = Path.cwd() / COORDINATOR_CHARM_FILENAME
    worker_path = Path.cwd() / WORKER_CHARM_FILENAME

    if coordinator_path.is_file() and not os.getenv("COORDINATOR_CHARM_PATH"):
        os.environ["COORDINATOR_CHARM_PATH"] = str(coordinator_path)
    if worker_path.is_file() and not os.getenv("WORKER_CHARM_PATH"):
        os.environ["WORKER_CHARM_PATH"] = str(worker_path)


def get_unit_ip_address(juju: Juju, app_name: str, unit_no: int):
    """Return a juju unit's IP address."""
    return juju.status().apps[app_name].units[f"{app_name}/{unit_no}"].address


def charm_and_channel_and_resources(
    role: Literal["coordinator", "worker"], charm_path_key: str, charm_channel_key: str
):
    """Pyroscope coordinator or worker charm used for integration testing.

    Build once per session and reuse it in all integration tests to save some minutes/hours.
    """
    _set_ci_charm_paths_if_unset()
    # If a local path is set and the file/directory exists, prefer it over charmhub.
    # When the path is set but the file is absent (e.g. worker not pre-packed),
    # fall through to the channel check so the charm is fetched from charmhub instead.
    if path_from_env := os.getenv(charm_path_key):
        charm_path = Path(path_from_env).absolute()
        if charm_path.exists():
            logger.info("Using local %s charm: %s", role, charm_path)
            if charm_path.suffix == ".charm":
                # Pre-built .charm file (e.g. CRAFT_ARTIFACT from charmcraft test).
                # OCI image resources are not embedded in the .charm archive — Juju
                # needs their upstream-source URIs at deploy time.  Read them from
                # charmcraft.yaml in the same directory as the packed charm file,
                # which is the charm source root both locally and in the spread VM.
                return charm_path, None, get_resources(charm_path.parent)
            # Ensure we read resources from the charm source directory for the
            # requested role, rather than from the parent of a packed charm file
            # which may be the repository root and contain a different charm's
            # metadata.
            return (
                charm_path,
                None,
                get_resources(REPO_ROOT / role),
            )
        logger.info(
            "Local %s charm not found at %s; falling back to charmhub.",
            role,
            charm_path,
        )
    # deploy charm from charmhub
    if channel_from_env := os.getenv(charm_channel_key):
        charm = f"pyroscope-{role}-k8s"
        logger.info("Using published %s charm from %s", charm, channel_from_env)
        return charm, channel_from_env, None
    # else try to pack the charm
    for _ in range(3):
        logger.info("packing Pyroscope %s charm...", role)
        try:
            pth = pack(REPO_ROOT / role)
        except subprocess.CalledProcessError:
            logger.warning("Failed to build Pyroscope %s. Trying again!", role)
            continue
        os.environ[charm_path_key] = str(pth)
        return pth, None, get_resources(REPO_ROOT / role)
    raise subprocess.CalledProcessError(1, f"pack {role}")


def deploy_distributed_cluster(
    juju: Juju,
    roles: Sequence[str],
    coordinator_deployed_as=None,
    wait_for_idle: bool = True,
):
    """Deploy a pyroscope distributed cluster."""
    worker_charm_url, channel, resources = charm_and_channel_and_resources(
        "worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL"
    )

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

    return _deploy_cluster(
        juju,
        all_workers,
        coordinator_deployed_as=coordinator_deployed_as,
        wait_for_idle=wait_for_idle,
    )


def deploy_monolithic_cluster(
    juju: Juju, coordinator_deployed_as=None, wait_for_idle: bool = True
):
    """Deploy a pyroscope-monolithic cluster."""
    worker_charm_url, channel, resources = charm_and_channel_and_resources(
        "worker", "WORKER_CHARM_PATH", "WORKER_CHARM_CHANNEL"
    )

    juju.deploy(
        worker_charm_url,
        app=WORKER_APP,
        channel=channel,
        trust=True,
        resources=resources,
    )
    return _deploy_cluster(
        juju,
        [WORKER_APP],
        coordinator_deployed_as=coordinator_deployed_as,
        wait_for_idle=wait_for_idle,
    )


def _deploy_cluster(
    juju: Juju,
    workers: Sequence[str],
    coordinator_deployed_as: str = None,
    wait_for_idle: bool = False,
):
    logger.info("deploying cluster")

    if coordinator_deployed_as:
        coordinator_app = coordinator_deployed_as
    else:
        coordinator_charm_url, channel, resources = charm_and_channel_and_resources(
            "coordinator", "COORDINATOR_CHARM_PATH", "COORDINATOR_CHARM_CHANNEL"
        )
        juju.deploy(
            coordinator_charm_url,
            PYROSCOPE_APP,
            channel=channel,
            resources=resources,
            trust=True,
        )
        coordinator_app = PYROSCOPE_APP

    for worker in workers:
        juju.integrate(
            coordinator_app + ":pyroscope-cluster", worker + ":pyroscope-cluster"
        )

    # we can't conditionally wait_for_idle for minio, because we need its IP soon to call deploy_s3
    _deploy_and_configure_minio(juju)

    deploy_s3(juju, bucket_name=BUCKET_NAME, s3_integrator_app=S3_APP)
    juju.integrate(coordinator_app + ":s3", S3_APP + ":s3-credentials")

    if wait_for_idle:
        logger.info("waiting for cluster to be active/idle...")
        juju.wait(
            lambda status: jubilant.all_active(
                status, coordinator_app, *workers, S3_APP
            ),
            timeout=2000,
            delay=5,
            successes=3,
        )
    return [coordinator_app, *workers, S3_APP, MINIO_APP]


def deploy_s3(juju, bucket_name: str, s3_integrator_app: str):
    """Deploy and configure a s3 integrator.

    Assumes there's a MINIO_APP deployed and ready.
    """
    logger.info(f"deploying {s3_integrator_app=}")
    # latest revision of s3-integrator creates buckets under relation name, we pin to a working version
    juju.deploy(
        "s3-integrator",
        s3_integrator_app,
        channel="2/edge",
        revision=157,  # FIXME: regression in 2/edge breaks bucket name in databag
        base="ubuntu@24.04",
    )

    logger.info(f"provisioning {bucket_name=} on {s3_integrator_app=}")
    minio_addr = get_unit_ip_address(juju, MINIO_APP, 0)
    mc_client = Minio(
        f"{minio_addr}:9000",
        **{key.replace("-", "_"): value for key, value in S3_CREDENTIALS.items()},
        secure=False,
    )
    # create pyroscope bucket
    found = mc_client.bucket_exists(bucket_name)
    if not found:
        mc_client.make_bucket(bucket_name)

    logger.info("configuring s3 integrator...")
    secret_uri = juju.cli(
        "add-secret",
        f"{s3_integrator_app}-creds",
        *(f"{key}={val}" for key, val in S3_CREDENTIALS.items()),
    )
    juju.cli("grant-secret", f"{s3_integrator_app}-creds", s3_integrator_app)

    # configure s3-integrator
    juju.config(
        s3_integrator_app,
        {
            "endpoint": f"minio-0.minio-endpoints.{juju.model}.svc.cluster.local:9000",
            "bucket": bucket_name,
            "credentials": secret_uri.strip(),
        },
    )


def _deploy_and_configure_minio(juju: Juju):
    if MINIO_APP not in juju.status().apps:
        juju.deploy(MINIO_APP, channel="edge", trust=True, config=S3_CREDENTIALS)
    juju.wait(
        lambda status: status.apps[MINIO_APP].is_active,
        error=jubilant.any_error,
        delay=5,
        successes=3,
        timeout=2000,
    )


def get_ingress_proxied_hostname(juju: Juju):
    return json.loads(
        juju.run(TRAEFIK_APP + "/0", "show-proxied-endpoints").results[
            "proxied-endpoints"
        ]
    )[TRAEFIK_APP]["url"].split("://")[1]


def emit_profile(
    endpoint: str,
    service_name: str = "profilegen",
    tls: bool = False,
    ca_path: Optional[str] = None,
    server_name: Optional[str] = None,
):
    env = os.environ.copy()

    profilegen_env = {
        "PROFILEGEN_SERVICE": service_name,
        "PROFILEGEN_ENDPOINT": endpoint,
        "PROFILEGEN_INSECURE": str(not tls),
    }
    if ca_path:
        profilegen_env["PROFILEGEN_CA_PATH"] = ca_path
    if server_name:
        profilegen_env["PROFILEGEN_SERVER_NAME"] = server_name

    env.update(profilegen_env)

    cmd = f"python {str(PROFILEGEN_SCRIPT_PATH)}"

    logger.info(f"running profilegen with env: {profilegen_env!r}")
    out = subprocess.run(
        shlex.split(cmd), text=True, capture_output=True, check=True, env=env
    )
    logger.info(f"profilegen completed; stdout={out.stdout!r}")
