Feature: profiling-with-collector-tls

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector with TLS
    Given a pyroscope cluster is deployed
    * an otel collector charm is deployed and integrated with pyroscope over profiling
    * a certificates provider charm is deployed
    * the certificates provider charm is integrated with pyroscope over certificates
    * the certificates provider charm is integrated with otel collector over receive-ca-cert
    When we emit a profile to the otel collector using otlp grpc
    Then the profile should be ingested by pyroscope
