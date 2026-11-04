Feature: profiling-with-collector

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector
    Given a Pyroscope cluster is deployed
    * an OTel Collector charm is deployed and integrated with Pyroscope over profiling
    When we emit a profile to the OTel Collector using OTLP gRPC
    Then the profile should be ingested by Pyroscope
