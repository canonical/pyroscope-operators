Feature: profiling-with-collector-tls

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC through an OTel Collector with TLS
    Given a Pyroscope cluster is deployed
    * an OTel Collector charm is deployed and integrated with Pyroscope over profiling
    * a certificates provider charm is deployed
    * the certificates provider charm is integrated with Pyroscope over certificates
    * the certificates provider charm is integrated with OTel Collector over receive-ca-cert
    When we emit a profile to the OTel Collector using OTLP gRPC
    Then the profile should be ingested by Pyroscope
