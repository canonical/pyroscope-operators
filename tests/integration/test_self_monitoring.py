# !/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import re
from tenacity import retry, stop_after_delay
from tenacity import wait_exponential as wexp

import pytest
import requests
from jubilant import Juju, all_active, any_error
from tenacity import (
    stop_after_attempt,
    wait_fixed,
)
from requests.auth import HTTPBasicAuth
from pytest_bdd import given, then

from helpers import (
    deploy_distributed_cluster,
    ALL_WORKERS,
    PYROSCOPE_APP,
    ALL_ROLES,
    get_unit_ip_address,
    deploy_s3,
    INTEGRATION_TESTERS_CHANNEL,
)

PROMETHEUS_APP = "prometheus"
LOKI_APP = "loki"
TEMPO_APP = "tempo"
TEMPO_WORKER_APP = "tempo-worker"
TEMPO_S3_APP = "tempo-s3-bucket"
CATALOGUE_APP = "catalogue"
GRAFANA_APP = "grafana"
TEMPO_S3_BUCKET = "tempo"
COS_COMPONENTS = (
    PROMETHEUS_APP,
    LOKI_APP,
    TEMPO_WORKER_APP,
    TEMPO_APP,
    TEMPO_S3_APP,
    CATALOGUE_APP,
    GRAFANA_APP,
)

logger = logging.getLogger(__name__)


@given("a pyroscope cluster is deployed with COS")
@given("we integrate pyroscope and COS")
@pytest.mark.setup
def test_setup(juju: Juju):
    # GIVEN an empty model
    # WHEN we deploy a pyroscope cluster with distributed workers
    # don't allow it to block so we can deploy all asynchronously
    pyro_apps = deploy_distributed_cluster(juju, ALL_ROLES, wait_for_idle=False)

    # AND we deploy & integrate with loki
    juju.deploy(
        "loki-k8s", app=LOKI_APP, channel=INTEGRATION_TESTERS_CHANNEL, trust=True
    )
    juju.integrate(PYROSCOPE_APP + ":logging", LOKI_APP + ":logging")

    # AND prometheus
    juju.deploy(
        "prometheus-k8s",
        app=PROMETHEUS_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
        trust=True,
    )
    juju.integrate(
        PYROSCOPE_APP + ":metrics-endpoint", PROMETHEUS_APP + ":metrics-endpoint"
    )

    # AND tempo
    juju.deploy(
        "tempo-coordinator-k8s",
        app=TEMPO_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
        trust=True,
    )
    juju.deploy(
        "tempo-worker-k8s",
        app=TEMPO_WORKER_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
        trust=True,
    )
    juju.integrate(TEMPO_APP, TEMPO_WORKER_APP)
    deploy_s3(juju, bucket_name=TEMPO_S3_BUCKET, s3_integrator_app=TEMPO_S3_APP)
    juju.integrate(TEMPO_APP, TEMPO_S3_APP + ":s3-credentials")
    juju.integrate(PYROSCOPE_APP + ":charm-tracing", TEMPO_APP + ":tracing")
    juju.integrate(PYROSCOPE_APP + ":workload-tracing", TEMPO_APP + ":tracing")

    # AND catalogue
    juju.deploy(
        "catalogue-k8s",
        CATALOGUE_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
    )
    juju.integrate(PYROSCOPE_APP, CATALOGUE_APP)

    # AND grafana
    juju.deploy(
        "grafana-k8s",
        GRAFANA_APP,
        channel=INTEGRATION_TESTERS_CHANNEL,
        trust=True,
    )
    juju.integrate(PYROSCOPE_APP + ":grafana-dashboard", GRAFANA_APP)
    juju.integrate(PYROSCOPE_APP + ":grafana-source", GRAFANA_APP)

    # THEN the pyroscope cluster and the cos components get to active/idle
    juju.wait(
        lambda status: all_active(status, *COS_COMPONENTS, *pyro_apps),
        timeout=3000,
        delay=5,
        successes=5,
    )


@then("metrics are sent to prometheus")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def test_metrics_integration(juju: Juju):
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


@then("metrics are sent to prometheus")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def test_metrics_nginx_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with prometheus over metrics-endpoint
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    # WHEN we query for a metric from nginx-prometheus-exporter in the coordinator
    url = f"http://{address}:9090/api/v1/query"
    app = PYROSCOPE_APP
    params = {"query": f"nginx_up{{juju_application='{app}'}}"}
    # THEN we should get a successful response and at least one result
    try:
        response = requests.get(url, params=params)
        data = response.json()
        assert data["status"] == "success", f"Metrics query failed for app '{app}'"
        assert len(data["data"]["result"]) > 0, f"No metrics found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Prometheus failed for app '{app}': {e}"


@then("charm traces are sent to tempo")
@retry(stop=stop_after_attempt(30), wait=wait_fixed(5))
def test_charm_tracing_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with tempo over charm-tracing
    address = get_unit_ip_address(juju, TEMPO_APP, 0)
    # WHEN we query the tags for all ingested traces in Tempo
    url = f"http://{address}:3200/api/search/tag/juju_application/values"
    response = requests.get(url)
    tags = response.json()["tagValues"]
    # THEN each pyroscope charm has sent some charm traces
    expected_apps = {PYROSCOPE_APP, *ALL_WORKERS}

    for app in expected_apps:
        assert app in tags


@then("Pyroscope logs are sent to loki")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def test_logging_integration(juju: Juju):
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


@then("catalogue items are provisioned")
def test_catalogue_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with catalogue
    catalogue_unit = f"{CATALOGUE_APP}/0"
    # get Pyroscope's catalogue item URL
    out = juju.cli(
        "show-unit", catalogue_unit, "--endpoint", "catalogue", "--format", "json"
    )
    pyroscope_app_databag = json.loads(out)[catalogue_unit]["relation-info"][0][
        "application-data"
    ]
    url = pyroscope_app_databag["url"]
    # WHEN we query the Pyroscope catalogue item URL
    # query the url from inside the container in case the url is a K8s fqdn
    response = juju.ssh(f"{PYROSCOPE_APP}/0", f"curl {url}")
    # THEN we receive a 200 OK response (0 exit status)
    # AND we confirm the response is from the Pyroscope UI (via the page title)
    assert "<title>Grafana Pyroscope</title>" in response


@then("Dashboards are provisioned")
def test_dashboard_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with grafana
    address = get_unit_ip_address(juju, GRAFANA_APP, 0)
    grafana_unit = f"{GRAFANA_APP}/0"
    # WHEN we search for a dashboard with Pyroscope's tag in Grafana
    out = juju.cli("run", grafana_unit, "get-admin-password")
    match = re.search(r"admin-password:\s*(\S+)", out)
    if match:
        pw = match.group(1)
        url = f"http://{address}:3000/api/dashboards/tags"
        auth = HTTPBasicAuth("admin", pw)
        params = {"tag": PYROSCOPE_APP}
        try:
            response = requests.get(url, auth=auth, params=params)
            # THEN we find an existing tag
            assert PYROSCOPE_APP in response.text
        except requests.exceptions.RequestException:
            assert False
    else:
        raise RuntimeError("No password in grafana's output")


@pytest.fixture(scope="module")
def grafana_admin_creds(juju) -> str:
    # NB this fixture can only be accessed after GRAFANA has been deployed.
    # obtain admin credentials via juju action, formatted as "username:password" (for basicauth)
    result = juju.run(GRAFANA_APP + "/0", "get-admin-password")
    return f"admin:{result.results['admin-password']}"


@then("a pyroscope datasource is provisioned in grafana")
@retry(
    wait=wexp(multiplier=2, min=1, max=30), stop=stop_after_delay(60 * 15), reraise=True
)
def test_grafana_source_integration(juju: Juju, grafana_admin_creds):
    """Verify that the pyroscope datasource is registered in grafana."""
    graf_ip = get_unit_ip_address(juju, GRAFANA_APP, 0)
    res = requests.get(f"http://{grafana_admin_creds}@{graf_ip}:3000/api/datasources")
    assert "pyroscope" in {ds["type"] for ds in res.json()}


@then("alert rules are sent to prometheus")
def test_alert_rules_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with prometheus over metrics-endpoint
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    # WHEN we query for alert rules
    url = f"http://{address}:9090/api/v1/rules"
    # THEN we should get a successful response
    try:
        response = requests.get(url)
        data = response.json()
        assert data["status"] == "success", "Alerts query failed for"
        groups = data["data"]["groups"]
        # AND there are non-empty alert rule groups
        assert len(groups) > 0, "No alerts found"
        # AND for every pyroscope app, there is at least one alert rule
        labels_apps = {
            rule["labels"].get("juju_application", "")
            for group in groups
            for rule in group.get("rules", [])
        }
        for app in (PYROSCOPE_APP, *ALL_WORKERS):
            assert app in labels_apps, f"No alert rules found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Prometheus failed: {e}"


@then("loki alert rules are sent to loki")
def test_loki_alert_rules_integration(juju: Juju):
    # GIVEN a pyroscope cluster integrated with loki
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    # WHEN we query for alert rules
    url = f"http://{address}:3100/loki/api/v1/rules"
    # THEN we should get a successful response
    try:
        response = requests.get(url)
        # AND for every pyroscope app, there is at least one loki alert rule
        for app in (PYROSCOPE_APP, *ALL_WORKERS):
            assert app in response.text, f"No Loki alert rules found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Loki failed: {e}"


@pytest.mark.teardown
def test_teardown(juju: Juju):
    # GIVEN a pyroscope cluster with core cos relations
    # WHEN we remove the cos components
    for app in COS_COMPONENTS:
        juju.remove_application(app)

    # THEN the coordinator and all workers eventually reach active/idle state
    juju.wait(
        lambda status: all_active(status, PYROSCOPE_APP, *ALL_WORKERS),
        error=lambda status: any_error(status, PYROSCOPE_APP, *ALL_WORKERS),
        timeout=2000,
        delay=10,
        successes=3,
    )


@pytest.mark.teardown
def test_teardown_pyroscope(juju: Juju):
    for worker_name in ALL_WORKERS:
        juju.remove_application(worker_name)
    juju.remove_application(PYROSCOPE_APP)
