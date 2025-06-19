# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

from typing import Optional
from jubilant import Juju

SAMPLE_PROFILE_DATA = "foo;bar 100"

logger = logging.getLogger(__name__)

def get_unit_ip_address(juju: Juju, app_name: str, unit_no: int):
    """Return a juju unit's IP address."""
    return juju.status().apps[app_name].units[f"{app_name}/{unit_no}"].address

def emit_profile(
        address:str,
        service_name: Optional[str] = "profilegen"
    ):
    """Emit profiling data to a Pyroscope backend using a simple `Text` format."""
    scheme = "" if address.startswith("http") else "http://"
    base_url = f"{scheme}{address}"
    endpoint = f"{base_url}/ingest"
    params = {
        "name": service_name,
    }
    try:
        response = requests.post(endpoint, params=params, data=SAMPLE_PROFILE_DATA)
        assert response.ok, f"Expected 2xx, got {response.status_code}: {response.text}"
        return response.ok
    # network-related issues
    except requests.exceptions.RequestException as e:
        assert False, f"Unexpected error: {e}"

def get_profiles(    
    address,
    service_name: Optional[str] = "profilegen" 
):
    """Query the Pyroscope backend for profiles with the service_name label."""
    scheme = "" if address.startswith("http") else "http://"
    base_url = f"{scheme}{address}"
    endpoint = f"{base_url}/pyroscope/render"
    params = {
        "query": f'process_cpu:cpu:nanoseconds:cpu:nanoseconds{{service_name="{service_name}"}}',
        "from": "now-1h"
    }
    try:
        response = requests.get(endpoint, params=params)
        assert response.ok, f"Expected 2xx, got {response.status_code}: {response.text}"
        samples = response.json()["timeline"]["samples"]
        assert any(samples), "No samples found"
        return any(samples)
    # network-related issues
    except requests.exceptions.RequestException as e:
        assert False, f"Unexpected error: {e}"

# retry up to 5 times, waiting 4 seconds between attempts
@retry(stop=stop_after_attempt(5), wait=wait_fixed(4))
def get_profiles_patiently(
    address,
    service_name: Optional[str] = "profilegen" 
):
    logger.info(f"polling {address} for service {service_name!r} profiles...")
    return get_profiles(address, service_name)
