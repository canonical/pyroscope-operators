# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about what Pyroscope sends to an OTel Collector, and provides to Grafana and Catalogue.

The OTel Collector stands for the COS stack: it has no backend to send to, so it is blocked,
but its receivers work, and it counts what they accept.
"""

import base64
import json
import lzma
import re

import jubilant
import pytest
from observability_clients import Grafana
from pytest_bdd import parsers, then
from tenacity import retry, stop_after_delay, wait_fixed

from tests.integration.helpers import (
    ALL_WORKERS,
    CATALOGUE_APP,
    GRAFANA_APP,
    NGINX_EXPORTER_PORT,
    OTEL_COLLECTOR_APP,
    PYROSCOPE_APP,
    get_unit_ip_address,
)

PYROSCOPE_APPS = (PYROSCOPE_APP, *ALL_WORKERS)

# The telemetry trails the relation that sends it, so the steps retry until it arrives.
_five_minutes = retry(stop=stop_after_delay(60 * 5), wait=wait_fixed(10), reraise=True)

# A charm only sends a trace when it handles an event, and Pyroscope is related to the
# collector once the model has settled, so the retry outlasts the 5 minutes between
# update-status events.
_ten_minutes = retry(stop=stop_after_delay(60 * 10), wait=wait_fixed(10), reraise=True)


@pytest.fixture(scope="module")
def grafana(juju: jubilant.Juju) -> Grafana:
    # NB this fixture can only be accessed after GRAFANA has been deployed.
    # obtain the admin password via juju action, and pass it as basic auth in the URL
    result = juju.run(GRAFANA_APP + "/0", "get-admin-password")
    password = result.results["admin-password"]
    address = get_unit_ip_address(juju, GRAFANA_APP, 0)
    return Grafana(url=f"http://admin:{password}@{address}:3000")


def accepted(juju: jubilant.Juju, kind: str, receiver: str) -> float:
    """How many `kind` the collector's receivers named `receiver...` accepted so far.

    The collector serves its metrics on its loopback only, so they are read from its pod.
    """
    metrics = juju.ssh(
        f"{OTEL_COLLECTOR_APP}/0", "curl -s http://localhost:8888/metrics"
    )
    pattern = rf'^otelcol_receiver_accepted_{kind}{{[^}}]*receiver="{receiver}[^"]*"[^}}]*}} (\S+)$'
    return sum(float(value) for value in re.findall(pattern, metrics, re.MULTILINE))


def relation_data(juju: jubilant.Juju, endpoint: str) -> dict:
    """The application data Pyroscope publishes to the collector over its `endpoint`."""
    unit = f"{OTEL_COLLECTOR_APP}/0"
    out = juju.cli("show-unit", unit, "--endpoint", endpoint, "--format", "json")
    return json.loads(out)[unit]["relation-info"][0]["application-data"]


def decode_alert_rules(raw: str) -> dict:
    """The alert rules of a relation: plain JSON, or LZMA-compressed and base64-encoded when large."""
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = raw
    if isinstance(decoded, str):
        decoded = json.loads(lzma.decompress(base64.b64decode(decoded)))
    return decoded


def apps_of(rules_or_jobs: list, key: str) -> set:
    """The values of the `key` label on the alert rules, or on the targets of the scrape jobs."""
    apps = set()
    for item in rules_or_jobs:
        apps.add(item.get("labels", {}).get(key))
        for static_config in item.get("static_configs", []):
            apps.add(static_config.get("labels", {}).get(key))
        for relabel in item.get("relabel_configs", []):
            if relabel.get("target_label") == key:
                apps.add(relabel.get("replacement"))
    return apps


@then("the OTel Collector has metrics from Pyroscope")
@_five_minutes
def collector_has_metrics(juju: jubilant.Juju):
    data = relation_data(juju, "metrics-endpoint")
    scrape_jobs = json.loads(data["scrape_jobs"])
    # the coordinator's own jobs carry no labels: the collector labels them from the metadata
    scraped = apps_of(scrape_jobs, "juju_application") | {
        json.loads(data["scrape_metadata"])["application"]
    }
    for app in PYROSCOPE_APPS:
        assert app in scraped, f"The collector doesn't scrape app '{app}'"
    assert accepted(juju, "metric_points", "prometheus/metrics-endpoint") > 0, (
        "The collector accepted no metrics from Pyroscope"
    )


@then("the OTel Collector has nginx metrics from Pyroscope")
@_five_minutes
def collector_has_nginx_metrics(juju: jubilant.Juju):
    scrape_jobs = json.loads(relation_data(juju, "metrics-endpoint")["scrape_jobs"])
    targets = [
        target
        for job in scrape_jobs
        for static_config in job.get("static_configs", [])
        for target in static_config.get("targets", [])
    ]
    assert any(target.endswith(f":{NGINX_EXPORTER_PORT}") for target in targets), (
        "The collector doesn't scrape Pyroscope's nginx exporter"
    )


@then(
    parsers.parse('the OTel Collector has alert rules from Pyroscope over "{endpoint}"')
)
@_five_minutes
def collector_has_alert_rules(juju: jubilant.Juju, endpoint: str):
    # the collector is the provider of "receive-loki-logs", the endpoint Pyroscope reaches over "logging"
    otelcol_endpoint = "receive-loki-logs" if endpoint == "logging" else endpoint
    rules = decode_alert_rules(relation_data(juju, otelcol_endpoint)["alert_rules"])
    labelled = apps_of(
        [rule for group in rules["groups"] for rule in group["rules"]],
        "juju_application",
    )
    for app in PYROSCOPE_APPS:
        assert app in labelled, f"No alert rules found for app '{app}'"


@then("the OTel Collector has logs from Pyroscope")
@_five_minutes
def collector_has_logs(juju: jubilant.Juju):
    assert accepted(juju, "log_records", "loki/") > 0, (
        "The collector accepted no logs from Pyroscope"
    )


@then("the OTel Collector has charm traces from Pyroscope")
@_ten_minutes
def collector_has_charm_traces(juju: jubilant.Juju):
    # Pyroscope's charms send their traces over OTLP, and nothing else sends spans
    assert accepted(juju, "spans", "otlp/") > 0, (
        "The collector accepted no charm traces from Pyroscope"
    )


@then("Pyroscope's workers send their workload traces to the OTel Collector")
@_five_minutes
def workers_send_workload_traces(juju: jubilant.Juju):
    for app in ALL_WORKERS:
        plan = juju.ssh(
            f"{app}/0",
            "PEBBLE_SOCKET=/charm/container/pebble.socket pebble plan",
            container="pyroscope",
        )
        assert re.search(
            rf"^\s*OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: http://{OTEL_COLLECTOR_APP}\.",
            plan,
            re.M,
        ), f"'{app}' doesn't send its workload traces to the collector"


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
@retry(stop=stop_after_delay(60 * 15), wait=wait_fixed(10), reraise=True)
def grafana_has_datasource(grafana: Grafana):
    """Verify that the pyroscope datasource is registered in grafana."""
    assert grafana.has_datasource(type="grafana-pyroscope-datasource")
