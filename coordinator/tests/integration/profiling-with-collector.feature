Feature: profiling-with-collector

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector
    Given a pyroscope cluster is deployed
    * an otel collector charm is deployed and integrated with pyroscope over profiling
    When we emit a profile to the otel collector using otlp grpc
    Then the profile should be ingested by pyroscope
