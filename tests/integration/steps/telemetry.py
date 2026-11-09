# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about what the COS charms receive from Pyroscope, and provide back."""

import json
import re

import jubilant
import pytest
import requests
from pytest_bdd import then
from requests.auth import HTTPBasicAuth
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_fixed,
)
from tenacity import wait_exponential as wexp

from tests.integration.helpers import (
    ALL_WORKERS,
    CATALOGUE_APP,
    GRAFANA_APP,
    LOKI_APP,
    PROMETHEUS_APP,
    PYROSCOPE_APP,
    TEMPO_APP,
    get_unit_ip_address,
)


@pytest.fixture(scope="module")
def grafana_admin_creds(juju: jubilant.Juju) -> str:
    # NB this fixture can only be accessed after GRAFANA has been deployed.
    # obtain admin credentials via juju action, formatted as "username:password" (for basicauth)
    result = juju.run(GRAFANA_APP + "/0", "get-admin-password")
    return f"admin:{result.results['admin-password']}"


@then("Prometheus has metrics from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def prometheus_has_metrics(juju: jubilant.Juju):
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


@then("Prometheus has nginx metrics from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def prometheus_has_nginx_metrics(juju: jubilant.Juju):
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


@then("Prometheus has alert rules from Pyroscope")
def prometheus_has_alert_rules(juju: jubilant.Juju):
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


@then("Tempo has charm traces from Pyroscope")
@retry(stop=stop_after_attempt(30), wait=wait_fixed(5))
def tempo_has_charm_traces(juju: jubilant.Juju):
    address = get_unit_ip_address(juju, TEMPO_APP, 0)
    url = f"http://{address}:3200/api/search/tag/juju_application/values"
    response = requests.get(url)
    tags = response.json()["tagValues"]
    expected_apps = {PYROSCOPE_APP, *ALL_WORKERS}

    for app in expected_apps:
        assert app in tags


@then("Tempo has workload traces from Pyroscope")
@retry(stop=stop_after_attempt(30), wait=wait_fixed(5))
def tempo_has_workload_traces(juju: jubilant.Juju):
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
    assert traces, f"No pyroscope-worker traces found in Tempo. Tempo response: {data}"


@then("Loki has logs from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def loki_has_logs(juju: jubilant.Juju):
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


@then("Loki has alert rules from Pyroscope")
def loki_has_alert_rules(juju: jubilant.Juju):
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    url = f"http://{address}:3100/loki/api/v1/rules"
    try:
        response = requests.get(url)
        for app in (PYROSCOPE_APP, *ALL_WORKERS):
            assert app in response.text, f"No Loki alert rules found for app '{app}'"
    except requests.exceptions.RequestException as e:
        assert False, f"Request to Loki failed: {e}"


@then("Catalogue has an item for Pyroscope")
def catalogue_has_item(juju: jubilant.Juju):
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


@then("Grafana has dashboards from Pyroscope")
def grafana_has_dashboards(juju: jubilant.Juju):
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


@then("Grafana has a datasource for Pyroscope")
@retry(
    wait=wexp(multiplier=2, min=1, max=30), stop=stop_after_delay(60 * 15), reraise=True
)
def grafana_has_datasource(juju: jubilant.Juju, grafana_admin_creds):
    """Verify that the pyroscope datasource is registered in grafana."""
    graf_ip = get_unit_ip_address(juju, GRAFANA_APP, 0)
    res = requests.get(f"http://{grafana_admin_creds}@{graf_ip}:3000/api/datasources")
    assert "grafana-pyroscope-datasource" in {ds["type"] for ds in res.json()}
