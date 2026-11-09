Feature: profiling-with-collector-tls
  Skipped until #439 is fixed: otelcol 0.130 rejects the OTLP profiles schema
  Pyroscope v2 needs, and every collector channel still ships 0.130.

  @skip
  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector with TLS
    Given a Pyroscope cluster is deployed
    * an OTel Collector charm is deployed and integrated with Pyroscope over profiling
    * a certificates provider charm is deployed
    * the certificates provider charm is integrated with Pyroscope over certificates
    * the certificates provider charm is integrated with OTel Collector over receive-ca-cert
    When we emit a profile to the OTel Collector using OTLP gRPC
    Then the profile should be ingested by Pyroscope
