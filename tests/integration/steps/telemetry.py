# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about what the COS charms receive from Pyroscope, and provide back."""

import json

import jubilant
import pytest
import requests
from observability_clients import Grafana, Loki, Prometheus, Tempo
from pytest_bdd import then
from tenacity import retry, stop_after_attempt, stop_after_delay, wait_fixed
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

PYROSCOPE_APPS = (PYROSCOPE_APP, *ALL_WORKERS)


@pytest.fixture(scope="module")
def grafana(juju: jubilant.Juju) -> Grafana:
    # NB this fixture can only be accessed after GRAFANA has been deployed.
    # obtain the admin password via juju action, and pass it as basic auth in the URL
    result = juju.run(GRAFANA_APP + "/0", "get-admin-password")
    password = result.results["admin-password"]
    address = get_unit_ip_address(juju, GRAFANA_APP, 0)
    return Grafana(url=f"http://admin:{password}@{address}:3000")


@then("Prometheus has metrics from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def prometheus_has_metrics(juju: jubilant.Juju):
    prometheus = Prometheus(
        url=f"http://{get_unit_ip_address(juju, PROMETHEUS_APP, 0)}:9090"
    )
    for app in PYROSCOPE_APPS:
        assert prometheus.has_metric("up", {"juju_application": app}), (
            f"No metrics found for app '{app}'"
        )


@then("Prometheus has nginx metrics from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def prometheus_has_nginx_metrics(juju: jubilant.Juju):
    prometheus = Prometheus(
        url=f"http://{get_unit_ip_address(juju, PROMETHEUS_APP, 0)}:9090"
    )
    assert prometheus.has_metric("nginx_up", {"juju_application": PYROSCOPE_APP}), (
        f"No nginx metrics found for app '{PYROSCOPE_APP}'"
    )


@then("Prometheus has alert rules from Pyroscope")
def prometheus_has_alert_rules(juju: jubilant.Juju):
    prometheus = Prometheus(
        url=f"http://{get_unit_ip_address(juju, PROMETHEUS_APP, 0)}:9090"
    )
    for app in PYROSCOPE_APPS:
        assert prometheus.has_alert_rules({"juju_application": app}), (
            f"No alert rules found for app '{app}'"
        )


# A charm only sends a trace when it handles an event, and Pyroscope is related to Tempo
# once the model has settled, so the retry outlasts the 5 minutes between update-status events.
@then("Tempo has charm traces from Pyroscope")
@retry(stop=stop_after_delay(60 * 10), wait=wait_fixed(10), reraise=True)
def tempo_has_charm_traces(juju: jubilant.Juju):
    tempo = Tempo(url=f"http://{get_unit_ip_address(juju, TEMPO_APP, 0)}:3200")
    # Tempo returns the values as plain strings, which Tempo.has_tag_value doesn't expect
    values = tempo.get_tag_values("juju_application")["tagValues"]
    for app in PYROSCOPE_APPS:
        assert app in values, f"No charm traces found for app '{app}'"


@then("Tempo has workload traces from Pyroscope")
@retry(stop=stop_after_delay(60 * 10), wait=wait_fixed(10), reraise=True)
def tempo_has_workload_traces(juju: jubilant.Juju):
    tempo = Tempo(url=f"http://{get_unit_ip_address(juju, TEMPO_APP, 0)}:3200")
    assert tempo.has_traces('{ .service.name =~ "pyroscope-worker.*" }'), (
        "No pyroscope-worker traces found in Tempo"
    )


@then("Loki has logs from Pyroscope")
@retry(stop=stop_after_attempt(5), wait=wait_fixed(10))
def loki_has_logs(juju: jubilant.Juju):
    loki = Loki(url=f"http://{get_unit_ip_address(juju, LOKI_APP, 0)}:3100")
    for app in ALL_WORKERS:
        assert loki.has_log_line(f'{{juju_application="{app}"}}'), (
            f"No logs found for app '{app}'"
        )


@then("Loki has alert rules from Pyroscope")
def loki_has_alert_rules(juju: jubilant.Juju):
    # Loki's rules API answers in YAML, which Loki.has_alert_rules doesn't expect
    address = get_unit_ip_address(juju, LOKI_APP, 0)
    rules = requests.get(f"http://{address}:3100/loki/api/v1/rules").text
    for app in PYROSCOPE_APPS:
        assert app in rules, f"No Loki alert rules found for app '{app}'"


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
def grafana_has_dashboards(grafana: Grafana):
    assert grafana.has_dashboard_with_tag(PYROSCOPE_APP)


@then("Grafana has a datasource for Pyroscope")
@retry(
    wait=wexp(multiplier=2, min=1, max=30), stop=stop_after_delay(60 * 15), reraise=True
)
def grafana_has_datasource(grafana: Grafana):
    """Verify that the pyroscope datasource is registered in grafana."""
    assert grafana.has_datasource(type="grafana-pyroscope-datasource")
