Feature: profiling

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC
    Given a pyroscope cluster is deployed
    When we emit a profile to pyroscope using otlp grpc
    Then the profile should be ingested by pyroscope
