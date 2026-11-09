# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps about what Pyroscope sends to an OpenTelemetry Collector, and provides to Grafana and Catalogue.

The OpenTelemetry Collector stands for the COS stack: it has no backend to send to, so it is blocked,
but its receivers work. To tell which application each item of telemetry comes from, it is
configured with a `filter` processor per application and signal, whose conditions match the
application's `juju_application`. The collector counts what each processor drops on its own
metrics, and the steps read those counts.
"""

import base64
import json
import lzma
import re

import jubilant
import pytest
from observability_clients import Grafana
from pytest_bdd import given, parsers, then
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
from tests.integration.steps.relations import COUNTERPARTS

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


def counting_processors() -> str:
    """The collector's `processors` config: one `filter` processor per application and signal.

    A `filter` processor drops the items its conditions match, and the collector counts them
    in `otelcol_processor_filter_*_filtered{filter="filter/<name>/..."}`, so each processor
    counts the items of its own application only. The applications are distinct, so what one
    drops is never what another counts. The collector's own metrics are scraped from a
    receiver of its own, so they are never counted.

    The `juju_application` of a log is an attribute (a Loki label); on the other signals it is
    a resource attribute, or an attribute of a data point. A charm's traces are the only ones
    whose resource has a `charm_type`, which tells them from the workload's traces.
    """

    def processor(signal: str, context: str, condition: str) -> dict:
        return {"error_mode": "ignore", signal: {context: [condition]}}

    processors = {}
    for app in PYROSCOPE_APPS:
        resource = f'resource.attributes["juju_application"] == "{app}"'
        attribute = f'attributes["juju_application"] == "{app}"'
        charm = 'resource.attributes["charm_type"] != nil'
        workload = 'resource.attributes["charm_type"] == nil'
        processors[f"filter/metrics_{app}"] = processor(
            "metrics", "datapoint", f"{resource} or {attribute}"
        )
        processors[f"filter/logs_{app}"] = processor(
            "logs", "log_record", f"{resource} or {attribute}"
        )
        processors[f"filter/charm_traces_{app}"] = processor(
            "traces", "span", f"{resource} and {charm}"
        )
        if app in ALL_WORKERS:
            processors[f"filter/workload_traces_{app}"] = processor(
                "traces", "span", f"{resource} and {workload}"
            )
    # JSON is YAML, which is what the charm parses
    return json.dumps(processors)


def dropped(juju: jubilant.Juju, kind: str, processor: str) -> float:
    """How many `kind` (datapoints, logs or spans) the collector's `processor` has matched so far.

    The collector serves its metrics on its loopback only, so they are read from its pod.
    A processor that has matched nothing may have no counter at all.
    """
    metrics = juju.ssh(
        f"{OTEL_COLLECTOR_APP}/0", "curl -s http://localhost:8888/metrics"
    )
    pattern = rf'^otelcol_processor_filter_{kind}_filtered{{[^}}]*filter="filter/{re.escape(processor)}/[^"]*"[^}}]*}} (\S+)$'
    return sum(float(value) for value in re.findall(pattern, metrics, re.MULTILINE))


def assert_every_app_has(juju: jubilant.Juju, apps, kind: str, signal: str, what: str):
    """Every one of `apps` has `kind` counted by its `signal` processor."""
    missing = [app for app in apps if not dropped(juju, kind, f"{signal}_{app}")]
    assert not missing, f"The collector received no {what} from {', '.join(missing)}"


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


@given(
    "the OpenTelemetry Collector counts the telemetry of every Pyroscope application"
)
def collector_counts_telemetry(juju: jubilant.Juju):
    counterpart = COUNTERPARTS["the OpenTelemetry Collector"]
    if counterpart.app not in juju.status().apps:
        counterpart.deploy(juju, counterpart.app)
    juju.config(
        OTEL_COLLECTOR_APP,
        {
            "processors": counting_processors(),
            # the collector keeps 1% of the workloads' traces by default
            "tracing_sampling_rate_workload": "100",
        },
    )


@then("the OpenTelemetry Collector has metrics from every Pyroscope application")
@_five_minutes
def collector_has_metrics(juju: jubilant.Juju):
    assert_every_app_has(juju, PYROSCOPE_APPS, "datapoints", "metrics", "metrics")


@then("the OpenTelemetry Collector has nginx metrics from Pyroscope")
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
    parsers.parse(
        'the OpenTelemetry Collector has alert rules from Pyroscope over "{endpoint}"'
    )
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


@then("the OpenTelemetry Collector has logs from every Pyroscope application")
@_five_minutes
def collector_has_logs(juju: jubilant.Juju):
    assert_every_app_has(juju, PYROSCOPE_APPS, "logs", "logs", "logs")


@then("the OpenTelemetry Collector has charm traces from every Pyroscope application")
@_ten_minutes
def collector_has_charm_traces(juju: jubilant.Juju):
    assert_every_app_has(juju, PYROSCOPE_APPS, "spans", "charm_traces", "charm traces")


@then("the OpenTelemetry Collector has workload traces from every Pyroscope worker")
@_ten_minutes
def collector_has_workload_traces(juju: jubilant.Juju):
    assert_every_app_has(
        juju, ALL_WORKERS, "spans", "workload_traces", "workload traces"
    )


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
