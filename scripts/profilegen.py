#!/usr/bin/env python3
"""Utility script to generate a mock CPU profile and export it using OTLP gRPC to a profiling backend (i.e. Pyroscope/Otel Collector).

Builds the stack-table revision of the OTLP profiles schema (Sample.stack_index into
ProfilesDictionary.stack_table), which is what Pyroscope v2 parses.

Requires opentelemetry-proto >= 1.43.0: earlier releases numbered Sample's fields
differently from the Go module, so profiles decoded as garbage and were answered 200
without being ingested.
"""

import logging
import os
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

# index 0 must be "" (empty string) by convention
_STRINGS = ["", "cpu", "nanoseconds", "profilegen-main-function", "service.name"]
_CPU_STRINDEX = 1
_NANOSECONDS_STRINDEX = 2
_FUNCTION_STRINDEX = 3
_SERVICE_NAME_STRINDEX = 4


def _build_profile() -> profiles_pb2.Profile:
    # all indices below reference the dictionary tables built alongside this profile
    sample_type = profiles_pb2.ValueType(
        type_strindex=_CPU_STRINDEX, unit_strindex=_NANOSECONDS_STRINDEX
    )
    sample = profiles_pb2.Sample(
        stack_index=0,
        attribute_indices=[0],  # attribute_table[0], i.e. service.name
        values=[100],  # nanoseconds
    )

    return profiles_pb2.Profile(
        sample_type=sample_type,
        samples=[sample],
        period_type=sample_type,
        period=1,
    )


def _build_profile_dictionary(service_name: str) -> profiles_pb2.ProfilesDictionary:
    function = profiles_pb2.Function(name_strindex=_FUNCTION_STRINDEX)
    location = profiles_pb2.Location(
        mapping_index=0, lines=[profiles_pb2.Line(function_index=0)]
    )
    # the indirection that replaced Sample.locations_start_index/length
    stack = profiles_pb2.Stack(location_indices=[0])
    attribute = profiles_pb2.KeyValueAndUnit(
        key_strindex=_SERVICE_NAME_STRINDEX,
        value=common_pb2.AnyValue(string_value=service_name),
    )

    return profiles_pb2.ProfilesDictionary(
        string_table=_STRINGS,
        mapping_table=[profiles_pb2.Mapping()],
        location_table=[location],
        function_table=[function],
        stack_table=[stack],
        attribute_table=[attribute],
    )


def emit_profile(
    endpoint: str,
    service_name: str,
    insecure: bool,
    ca_path: Optional[str] = None,
    server_name: Optional[str] = None,
):
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
        # override the server name as the certificate might not match the actual hostname we're connecting to
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


if __name__ == "__main__":
    emit_profile(
        endpoint=os.getenv("PROFILEGEN_ENDPOINT", "127.0.0.1:4317"),
        service_name=os.getenv("PROFILEGEN_SERVICE", "profilegen-service"),
        insecure=os.getenv("PROFILEGEN_INSECURE", "True").lower() in ("true", "1"),
        ca_path=os.getenv("PROFILEGEN_CA_PATH", None),
        server_name=os.getenv("PROFILEGEN_SERVER_NAME", None),
    )
