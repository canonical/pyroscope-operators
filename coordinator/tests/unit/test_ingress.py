import ops
from ops.testing import PeerRelation, State


def _purge_default_juju_keys(databag: dict):
    DEFAULT_JUJU_KEYS = {"egress-subnets", "ingress-address", "private-address"}
    return {k: v for k, v in databag.items() if k not in DEFAULT_JUJU_KEYS}


def test_ingress_follower(
    context,
    s3,
    all_worker,
    nginx_container,
    nginx_prometheus_exporter_container,
    ingress,
):
    # GIVEN a follower unit in a happy state, with ingress
    state_in = State(
        relations=[
            PeerRelation("peers", peers_data={1: {}, 2: {}}),
            s3,
            all_worker,
            ingress,
        ],
        containers=[nginx_container, nginx_prometheus_exporter_container],
        unit_status=ops.ActiveStatus(),
        leader=False,
    )

    # WHEN we process an update-status event
    state_out = context.run(
        context.on.update_status(),
        state_in,
    )

    # THEN the state is still happy
    assert state_out.unit_status.name == "active"
    # AND THEN we haven't published ingress details in this unit's databags
    assert not _purge_default_juju_keys(
        state_out.get_relation(ingress.id).local_unit_data
    )
