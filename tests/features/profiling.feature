Feature: profiling

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC
    Given a Pyroscope cluster is deployed
    When we emit a profile to Pyroscope using OTLP gRPC
    Then the profile should be ingested by Pyroscope
