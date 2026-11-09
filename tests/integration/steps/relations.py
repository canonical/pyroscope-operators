# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Steps relating Pyroscope to the charms it integrates with."""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import jubilant
from pytest_bdd import given, parsers, when

from tests.integration.helpers import (
    CATALOGUE_APP,
    CHANNELS,
    GRAFANA_APP,
    OTEL_COLLECTOR_APP,
    PYROSCOPE_APP,
    SSC_APP,
    SWFS_APP,
    TRAEFIK_APP,
    WORKER_APP,
    deploy_monolithic_worker,
    deploy_swfs,
    related_apps,
)
from tests.integration.steps.deployment import (
    pyroscope_is_deployed,
    settled_apps,
    wait_for_active,
)


def from_charmhub(
    charm: str, channel: Optional[str] = None, trust: bool = True
) -> Callable[[jubilant.Juju, str], object]:
    def deploy(juju: jubilant.Juju, app: str) -> None:
        juju.deploy(charm, app, channel=channel, trust=trust)

    return deploy


@dataclass(frozen=True)
class Counterpart:
    """A charm Pyroscope relates to, under the name the feature files use for it.

    `endpoint` is the endpoint of the counterpart to relate to, when the application alone
    is ambiguous. A counterpart that does not `settle` leaves the model blocked until another
    one is related, so the steps do not wait for the model after relating to it.
    """

    app: str
    deploy: Callable[[jubilant.Juju, str], object]
    endpoint: Optional[str] = None
    timeout: float = 2000
    settles: bool = True

    @property
    def target(self) -> str:
        return f"{self.app}:{self.endpoint}" if self.endpoint else self.app


COUNTERPARTS: Dict[str, Counterpart] = {
    "a CA": Counterpart(
        SSC_APP, from_charmhub("self-signed-certificates", trust=False)
    ),
    "Catalogue": Counterpart(
        CATALOGUE_APP,
        from_charmhub("catalogue-k8s", CHANNELS["catalogue-k8s"], trust=False),
    ),
    "Grafana": Counterpart(
        GRAFANA_APP, from_charmhub("grafana-k8s", CHANNELS["grafana-k8s"])
    ),
    "Traefik": Counterpart(
        TRAEFIK_APP,
        lambda juju, app: juju.deploy(
            "traefik-k8s", app, channel="latest/stable", base="ubuntu@26.04", trust=True
        ),
    ),
    "the OpenTelemetry Collector": Counterpart(
        OTEL_COLLECTOR_APP,
        from_charmhub(
            "opentelemetry-collector-k8s", CHANNELS["opentelemetry-collector-k8s"]
        ),
    ),
    # The coordinator is blocked until it has both an s3 backend and a worker, so relate to
    # the s3 backend first.
    "an s3 backend": Counterpart(
        SWFS_APP, lambda juju, _: deploy_swfs(juju), settles=False
    ),
    "a worker": Counterpart(
        WORKER_APP,
        lambda juju, _: deploy_monolithic_worker(juju),
        endpoint="pyroscope-cluster",
    ),
}


def app_of(subject: str) -> str:
    """The application a feature file means by `subject`: Pyroscope, or a counterpart."""
    return PYROSCOPE_APP if subject == "Pyroscope" else COUNTERPARTS[subject].app


def relate_to(juju: jubilant.Juju, subject: str, name: str, endpoint: str) -> None:
    """Relate `subject` over `endpoint` to the named counterpart, deploying it if needed."""
    app = app_of(subject)
    counterpart = COUNTERPARTS[name]
    if counterpart.app not in juju.status().apps:
        counterpart.deploy(juju, counterpart.app)
    if counterpart.app not in related_apps(juju, app, endpoint):
        juju.integrate(f"{app}:{endpoint}", counterpart.target)
    if counterpart.settles:
        # Every application in the model settles, including the rest of a deployed stack.
        wait_for_active(juju, *settled_apps(juju), timeout=counterpart.timeout)


def remove_relations(juju: jubilant.Juju, endpoint: str) -> None:
    """Remove every relation of Pyroscope over `endpoint`."""
    for related_app in related_apps(juju, PYROSCOPE_APP, endpoint):
        juju.remove_relation(f"{PYROSCOPE_APP}:{endpoint}", related_app)
    juju.wait(
        lambda status: not status.apps[PYROSCOPE_APP].relations.get(endpoint),
        timeout=600,
        delay=10,
        successes=3,
    )


@given(parsers.parse('{subject} is related to {name} over "{endpoint}"'))
@when(parsers.parse('{subject} is related to {name} over "{endpoint}"'))
def is_related(juju: jubilant.Juju, subject: str, name: str, endpoint: str):
    relate_to(juju, subject, name, endpoint)


@given(parsers.parse("Pyroscope serves over {scheme}"))
def pyroscope_serves_over(juju: jubilant.Juju, scheme: str):
    """Pyroscope serves over HTTPS when it is related to a CA, and over HTTP otherwise."""
    pyroscope_is_deployed(juju)
    if scheme == "HTTPS":
        relate_to(juju, "Pyroscope", "a CA", "certificates")
    else:
        remove_relations(juju, "certificates")
        wait_for_active(juju, PYROSCOPE_APP, WORKER_APP, SWFS_APP)


@given(parsers.parse("Pyroscope has no {endpoint} relation"))
@when(parsers.parse("Pyroscope's {endpoint} relation is removed"))
def has_no_relation(juju: jubilant.Juju, endpoint: str):
    remove_relations(juju, endpoint)
