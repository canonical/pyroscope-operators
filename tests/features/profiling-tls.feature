Feature: profiling-tls

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC with TLS
    Given a Pyroscope cluster is deployed
    And a certificates provider charm is deployed and integrated with Pyroscope
    When we emit a profile to Pyroscope using OTLP gRPC over TLS
    Then the profile should be ingested by Pyroscope
