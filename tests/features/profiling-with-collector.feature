Feature: profiling-with-collector
  Skipped until #439 is fixed: otelcol 0.130 rejects the OTLP profiles schema
  Pyroscope v2 needs, and every collector channel still ships 0.130.

  @skip
  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector
    Given a Pyroscope cluster is deployed
    And an OTel Collector charm is deployed and integrated with Pyroscope over profiling
    When we emit a profile to the OTel Collector using OTLP gRPC
    Then the profile should be ingested by Pyroscope
