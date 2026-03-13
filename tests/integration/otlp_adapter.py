#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Adapter script that generates a synthetic CPU profile and exports it via OTLP gRPC.

Acts as a bridge between profilecli-style profile data and OTLP delivery, for use in
integration tests that require OTLP ingestion (e.g. through an OTel Collector, or over TLS).
"""

import argparse
import logging
from pathlib import Path
from typing import Optional

import grpc
from opentelemetry.proto.collector.profiles.v1development import (
    profiles_service_pb2,
    profiles_service_pb2_grpc,
)
from opentelemetry.proto.common.v1 import common_pb2
from opentelemetry.proto.profiles.v1development import profiles_pb2

logger = logging.getLogger(__name__)


def _build_profile() -> profiles_pb2.Profile:
    sample_type = profiles_pb2.ValueType(
        type_strindex=1,  # "cpu"
        unit_strindex=2,  # "nanoseconds"
    )

    # stack_index refers to the Stack entry in ProfilesDictionary.stack_table.
    sample = profiles_pb2.Sample(
        stack_index=0,
        values=[100],
        attribute_indices=[0],
    )

    return profiles_pb2.Profile(
        sample_type=sample_type,
        samples=[sample],
        period_type=sample_type,
        period=1,
    )


def _build_profile_dictionary(service_name: str) -> profiles_pb2.ProfilesDictionary:
    # index 0 must be "" (empty string) by convention
    string_table = [
        "",
        "cpu",
        "nanoseconds",
        "otlp-adapter-function",
        "service.name",
        service_name,
    ]

    function = profiles_pb2.Function(
        name_strindex=3,  # "otlp-adapter-function"
    )

    location = profiles_pb2.Location(
        mapping_index=0,
        lines=[profiles_pb2.Line(function_index=0)],
    )

    # stack_table[0] references location_table[0]
    stack = profiles_pb2.Stack(location_indices=[0])

    # attribute_table uses KeyValueAndUnit; key and unit are string-table indices
    attribute = profiles_pb2.KeyValueAndUnit(
        key_strindex=4,  # "service.name"
        value=common_pb2.AnyValue(string_value=service_name),
    )

    return profiles_pb2.ProfilesDictionary(
        string_table=string_table,
        location_table=[location],
        function_table=[function],
        mapping_table=[profiles_pb2.Mapping()],
        attribute_table=[attribute],
        stack_table=[stack],
    )


def emit_profile(
    endpoint: str,
    service_name: str,
    insecure: bool,
    ca_path: Optional[str] = None,
    server_name: Optional[str] = None,
):
    """Generate a synthetic CPU profile and export it via OTLP gRPC."""
    profile = _build_profile()
    profile_dictionary = _build_profile_dictionary(service_name)

    request = profiles_service_pb2.ExportProfilesServiceRequest(
        resource_profiles=[
            profiles_pb2.ResourceProfiles(
                scope_profiles=[profiles_pb2.ScopeProfiles(profiles=[profile])],
            )
        ],
        dictionary=profile_dictionary,
    )

    if insecure:
        channel = grpc.insecure_channel(endpoint)
    else:
        ca_cert_bytes = (
            Path(ca_path).read_bytes() if ca_path and Path(ca_path).exists() else None
        )
        # Override the server name when the certificate may not match the IP we connect to.
        options = (
            (("grpc.ssl_target_name_override", server_name),) if server_name else ()
        )
        channel = grpc.secure_channel(
            endpoint,
            grpc.ssl_channel_credentials(root_certificates=ca_cert_bytes),
            options=options,
        )

    stub = profiles_service_pb2_grpc.ProfilesServiceStub(channel)
    stub.Export(request)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="gRPC endpoint (host:port)")
    parser.add_argument(
        "--service-name", default="otlp-adapter", help="Service name for the profile"
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        default=False,
        help="Use an insecure (plaintext) gRPC channel",
    )
    parser.add_argument("--ca-path", default=None, help="Path to CA certificate file for TLS")
    parser.add_argument(
        "--server-name",
        default=None,
        help="Override the TLS server name (SNI), useful when connecting via IP",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    emit_profile(
        endpoint=args.endpoint,
        service_name=args.service_name,
        insecure=args.insecure,
        ca_path=args.ca_path,
        server_name=args.server_name,
    )
