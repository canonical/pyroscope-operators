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
from jubilant import Juju, all_active
from tenacity import (
    stop_after_attempt,
    wait_fixed,
)
from requests.auth import HTTPBasicAuth
from pytest_bdd import given, scenarios, then

from tests.integration.helpers import (
    ALL_WORKERS,
    PYROSCOPE_APP,
    ALL_ROLES,
    SWFS_APP,
    deploy_distributed_cluster,
    get_unit_ip_address,
    CHANNELS,
    COS_COMPONENTS,
    PROMETHEUS_APP,
    LOKI_APP,
    TEMPO_APP,
    TEMPO_WORKER_APP,
    CATALOGUE_APP,
    GRAFANA_APP,
)

scenarios("self-monitoring.feature")

logger = logging.getLogger(__name__)


def deploy_and_integrate_cos(juju: Juju):
    """Deploy a distributed Pyroscope cluster and the COS components, and integrate them."""
    # don't allow it to block so we can deploy all asynchronously
    deploy_distributed_cluster(juju, ALL_ROLES, wait_for_idle=False)

    # loki
    juju.deploy("loki-k8s", app=LOKI_APP, channel=CHANNELS["loki-k8s"], trust=True)
    juju.integrate(PYROSCOPE_APP + ":logging", LOKI_APP + ":logging")

    # prometheus
    juju.deploy(
        "prometheus-k8s",
        app=PROMETHEUS_APP,
        channel=CHANNELS["prometheus-k8s"],
        trust=True,
    )
    juju.integrate(
        PYROSCOPE_APP + ":metrics-endpoint", PROMETHEUS_APP + ":metrics-endpoint"
    )

    # tempo
    juju.deploy(
        "tempo-coordinator-k8s",
        app=TEMPO_APP,
        channel=CHANNELS["tempo-coordinator-k8s"],
        trust=True,
    )
    juju.deploy(
        "tempo-worker-k8s",
        app=TEMPO_WORKER_APP,
        channel=CHANNELS["tempo-worker-k8s"],
        trust=True,
    )
    juju.integrate(TEMPO_APP, TEMPO_WORKER_APP)
    juju.integrate(TEMPO_APP, SWFS_APP)
    juju.integrate(PYROSCOPE_APP + ":charm-tracing", TEMPO_APP + ":tracing")
    juju.integrate(PYROSCOPE_APP + ":workload-tracing", TEMPO_APP + ":tracing")

    # catalogue
    juju.deploy(
        "catalogue-k8s",
        CATALOGUE_APP,
        channel=CHANNELS["catalogue-k8s"],
    )
    juju.integrate(PYROSCOPE_APP, CATALOGUE_APP)

    # grafana
    juju.deploy(
        "grafana-k8s",
        GRAFANA_APP,
        channel=CHANNELS["grafana-k8s"],
        trust=True,
    )
    juju.integrate(PYROSCOPE_APP + ":grafana-dashboard", GRAFANA_APP)
    juju.integrate(PYROSCOPE_APP + ":grafana-source", GRAFANA_APP)


@given("a Pyroscope cluster and COS are deployed and integrated")
def pyroscope_cluster_and_cos_are_integrated(juju: Juju):
    if PYROSCOPE_APP not in juju.status().apps:
        deploy_and_integrate_cos(juju)
    juju.wait(
        lambda status: all_active(
            status, *COS_COMPONENTS, PYROSCOPE_APP, *ALL_WORKERS, SWFS_APP
        ),
        timeout=3000,
        delay=5,
        successes=5,
    )


@then("metrics are sent to Prometheus")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def metrics_are_sent_to_prometheus(juju: Juju):
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    url = f"http://{address}:9090/api/v1/query"
    for app in (PYROSCOPE_APP, *ALL_WORKERS):
        params = {"query": f"up{{juju_application='{app}'}}"}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            assert data["status"] == "success", f"Metrics query failed for app '{app}'"
            assert len(data["data"]["result"]) > 0, f"No metrics found for app '{app}'"
        except requests.exceptions.RequestException as e:
            assert False, f"Request to Prometheus failed for app '{app}': {e}"


@then("nginx metrics are sent to Prometheus")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def nginx_metrics_are_sent_to_prometheus(juju: Juju):
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    url = f"http://{address}:9090/api/v1/query"
    app = PYROSCOPE_APP
    params = {"query": f"nginx_up{{juju_application='{app}'}}"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        assert data["status"] == "success", f"Metrics query failed for app '{app}'"
        assert len(data["data"]["result"]) > 0, f"No metrics found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Prometheus failed for app '{app}': {e}"


@then("charm traces are sent to Tempo")
@retry(stop=stop_after_attempt(30), wait=wait_fixed(5))
def charm_traces_are_sent_to_tempo(juju: Juju):
    address = get_unit_ip_address(juju, TEMPO_APP, 0)
    url = f"http://{address}:3200/api/search/tag/juju_application/values"
    response = requests.get(url)
    tags = response.json()["tagValues"]
    expected_apps = {PYROSCOPE_APP, *ALL_WORKERS}

    for app in expected_apps:
        assert app in tags


@then("worker workload traces are sent to Tempo")
@retry(stop=stop_after_attempt(30), wait=wait_fixed(5))
def worker_workload_traces_are_sent_to_tempo(juju: Juju):
    address = get_unit_ip_address(juju, TEMPO_APP, 0)
    url = f"http://{address}:3200/api/search"

    response = requests.get(
        url,
        params={"tags": 'service.name="pyroscope-worker"'},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    traces = data.get("traces", [])
    assert traces, (
        "No pyroscope-worker traces found in Tempo. "
        f"Tempo response: {data}"
    )


@then("Pyroscope logs are sent to Loki")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def pyroscope_logs_are_sent_to_loki(juju: Juju):
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    # Use query_range for a longer default time interval
    url = f"http://{address}:3100/loki/api/v1/query_range"
    for app in ALL_WORKERS:
        query = f'{{juju_application="{app}"}}'
        params = {"query": query}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            assert data["status"] == "success", f"Log query failed for app '{app}'"
            assert len(data["data"]["result"]) > 0, f"No logs found for app '{app}'"
        except requests.exceptions.RequestException as e:
            assert False, f"Request to Loki failed for app '{app}': {e}"


@then("Catalogue items are provisioned")
def catalogue_items_are_provisioned(juju: Juju):
    catalogue_unit = f"{CATALOGUE_APP}/0"
    # get Pyroscope's catalogue item URL
    out = juju.cli(
        "show-unit", catalogue_unit, "--endpoint", "catalogue", "--format", "json"
    )
    pyroscope_app_databag = json.loads(out)[catalogue_unit]["relation-info"][0][
        "application-data"
    ]
    url = pyroscope_app_databag["url"]
    # query the url from inside the container in case the url is a K8s fqdn
    response = juju.ssh(f"{PYROSCOPE_APP}/0", f"curl {url}")
    assert "<title>Pyroscope</title>" in response


@then("dashboards are provisioned")
def dashboards_are_provisioned(juju: Juju):
    address = get_unit_ip_address(juju, GRAFANA_APP, 0)
    grafana_unit = f"{GRAFANA_APP}/0"
    out = juju.cli("run", grafana_unit, "get-admin-password")
    match = re.search(r"admin-password:\s*(\S+)", out)
    if match:
        pw = match.group(1)
        url = f"http://{address}:3000/api/dashboards/tags"
        auth = HTTPBasicAuth("admin", pw)
        params = {"tag": PYROSCOPE_APP}
        try:
            response = requests.get(url, auth=auth, params=params)
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


@then("a Pyroscope datasource is provisioned in Grafana")
@retry(
    wait=wexp(multiplier=2, min=1, max=30), stop=stop_after_delay(60 * 15), reraise=True
)
def datasource_is_provisioned_in_grafana(juju: Juju, grafana_admin_creds):
    """Verify that the pyroscope datasource is registered in grafana."""
    graf_ip = get_unit_ip_address(juju, GRAFANA_APP, 0)
    res = requests.get(f"http://{grafana_admin_creds}@{graf_ip}:3000/api/datasources")
    assert "grafana-pyroscope-datasource" in {ds["type"] for ds in res.json()}


@then("alert rules are sent to Prometheus")
def alert_rules_are_sent_to_prometheus(juju: Juju):
    address = get_unit_ip_address(juju, PROMETHEUS_APP, 0)
    url = f"http://{address}:9090/api/v1/rules"
    try:
        response = requests.get(url)
        data = response.json()
        assert data["status"] == "success", "Alerts query failed for"
        groups = data["data"]["groups"]
        assert len(groups) > 0, "No alerts found"
        labels_apps = {
            rule["labels"].get("juju_application", "")
            for group in groups
            for rule in group.get("rules", [])
        }
        for app in (PYROSCOPE_APP, *ALL_WORKERS):
            assert app in labels_apps, f"No alert rules found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Prometheus failed: {e}"


@then("Loki alert rules are sent to Loki")
def loki_alert_rules_are_sent_to_loki(juju: Juju):
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    url = f"http://{address}:3100/loki/api/v1/rules"
    try:
        response = requests.get(url)
        for app in (PYROSCOPE_APP, *ALL_WORKERS):
            assert app in response.text, f"No Loki alert rules found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Loki failed: {e}"
