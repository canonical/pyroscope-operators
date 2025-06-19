
#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import requests
import logging
import pytest
from jubilant import Juju, all_active, any_error
from tenacity import retry, stop_after_attempt, wait_fixed

from conftest import ALL_WORKERS, PYROSCOPE_APP
from helpers import get_unit_ip_address

PROMETHEUS_APP="prometheus"
LOKI_APP="loki"

logger = logging.getLogger(__name__)

@pytest.mark.setup
def test_deploy_self_monitoring_stack(juju: Juju):
    # GIVEN a model with pyroscope cluster
    # WHEN we deploy a monitoring stack
    juju.deploy("prometheus-k8s", app=PROMETHEUS_APP, channel="edge", trust=True)
    juju.deploy("loki-k8s", app=LOKI_APP, channel="edge", trust=True)
    # THEN monitoring stack is in active/idle state
    juju.wait(
        lambda status: all_active(status, PROMETHEUS_APP, LOKI_APP),
        error=any_error,
        timeout=2000,
    )

@pytest.mark.setup
def test_relate_self_monitoring_stack(juju: Juju):
    # GIVEN a model with a pyroscope cluster, and a monitoring stack
    # WHEN we integrate the pyroscope cluster over self-monitoring relations
    juju.integrate(PYROSCOPE_APP + ":metrics-endpoint", PROMETHEUS_APP + ":metrics-endpoint")
    juju.integrate(PYROSCOPE_APP + ":logging", LOKI_APP + ":logging")

    # THEN the coordinator, all workers, and the monitoring stack are all in active/idle state
    juju.wait(
        lambda status: all_active(status, PROMETHEUS_APP, LOKI_APP, PYROSCOPE_APP, *ALL_WORKERS),
        error=any_error,
        timeout=2000,
        delay=5,
        successes=12,
    )

@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def test_self_monitoring_metrics_ingestion(juju: Juju):
    # GIVEN a pyroscope cluster integrated with prometheus over metrics-endpoint
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    # WHEN we query the metrics for the coordinator and each of the workers
    url = f"http://{address}:9090/api/v1/query"
    for app in (PYROSCOPE_APP, *ALL_WORKERS):
        params = {"query": f"up{{juju_application='{app}'}}"}
        # THEN we should get a successful response and at least one result
        try:
            response = requests.get(url, params=params)
            data = response.json()
            assert data["status"] == "success", f"Metrics query failed for app '{app}'"
            assert len(data["data"]["result"]) > 0, f"No metrics found for app '{app}'"
        except requests.exceptions.RequestException as e:
            assert False, f"Request to Prometheus failed for app '{app}': {e}"

@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def test_self_monitoring_logs_ingestion(juju: Juju):
    # GIVEN a pyroscope cluster integrated with loki over logging
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    # WHEN we query the logs for each worker
    # Use query_range for a longer default time interval
    url = f"http://{address}:3100/loki/api/v1/query_range"
    for app in ALL_WORKERS:
        query = f'{{juju_application="{app}"}}'
        params = {"query": query}
        # THEN we should get a successful response and at least one result
        try:
            response = requests.get(url, params=params)
            data = response.json()
            assert data["status"] == "success", f"Log query failed for app '{app}'"
            assert len(data["data"]["result"]) > 0, f"No logs found for app '{app}'"
        except requests.exceptions.RequestException as e:
            assert False, f"Request to Loki failed for app '{app}': {e}"

@pytest.mark.teardown
def test_teardown_self_monitoring_stack(juju: Juju):
    # GIVEN a pyroscope cluster with self-monitoring relations
    # WHEN we remove the self-monitoring stack
    juju.remove_application(PROMETHEUS_APP)
    # THEN the coordinato and all workers in active/idle state
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_WORKERS),
        error=any_error,
        timeout=2000,
        delay=5,
        successes=3,
    )
