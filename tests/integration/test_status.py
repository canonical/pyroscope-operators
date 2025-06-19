
#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
from jubilant import Juju, all_blocked

from conftest import PYROSCOPE_APP, S3_APP
from helpers import get_unit_ip_address, emit_profile, get_profiles_patiently
from coordinator.src.nginx_config import _nginx_port


def test_pyroscope_blocks_if_s3_goes_away(juju: Juju):
    # GIVEN a pyroscope cluster
    # WHEN s3-relation is removed
    juju.remove_relation(S3_APP, PYROSCOPE_APP)
    # THEN pyroscope coordinator is in blocked state
    juju.wait(lambda status: jubilant.all_blocked(status, PYROSCOPE_APP),
              timeout=1000)

def test_scale_pyroscope_up_stays_blocked(juju: Juju):
    # GIVEN a pyroscope cluster with no s3 integrator
    # WHEN coordinator is scaled
    juju.cli("add-unit", PYROSCOPE_APP, "-n", "1")
    # THEN the coordinator stays in blocked state
    juju.wait(
        lambda status: all_blocked(status, PYROSCOPE_APP),
        timeout=1000
    )

def test_profiles_ingestion_fails(juju: Juju):
    # GIVEN a pyroscope cluster with no s3 integrator
    # WHEN we emit a profile through Pyroscope's HTTP API server
    hostname = get_unit_ip_address(juju, PYROSCOPE_APP, 0)
    emit_profile(f"{hostname}:{_nginx_port}")
    # THEN we fail to query any profile
    # AND we get an empty list of samples
    assert not get_profiles_patiently(f"{hostname}:{_nginx_port}")
