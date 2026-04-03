Feature: profiling-tls

  Scenario: Pyroscope is able to ingest profiles via OTLP gRPC with TLS
    Given a pyroscope cluster is deployed
    * a certificates provider charm is deployed and integrated with pyroscope
    When we emit a profile to pyroscope using otlp grpc over TLS
    Then the profile should be ingested by pyroscope
