#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import subprocess
import shlex


def assert_profile_is_ingested(hostname: str, service_name: str = "profilegen"):
    cmd = (
        "curl -s --get --data-urlencode "
        f"'query=process_cpu:cpu:nanoseconds:cpu:nanoseconds{{service_name=\"{service_name}\"}}' "
        '--data-urlencode "from=now-1h" '
        f"http://{hostname}:8080/pyroscope/render"
    )
    out = subprocess.run(shlex.split(cmd), text=True, capture_output=True)
    flames = json.loads(out.stdout)

    # equivalent to: jq -r '.flamebearer.levels[0] | add'"
    tot_levels = sum(flames["flamebearer"]["levels"][0])
    # if there's no data, this will be a zeroes array.
    assert tot_levels > 0, f"No data in graph obtained by {cmd}"
