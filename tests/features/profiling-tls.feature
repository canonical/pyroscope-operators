Feature: profiling-tls
  With a certificate from a CA over "certificates", Pyroscope ingests the
  profiles sent to it over OTLP gRPC with TLS.

  Background:
    Given Pyroscope is deployed
    And Pyroscope is related to a CA over "certificates"

  Scenario: Pyroscope ingests profiles over OTLP gRPC with TLS
    When a profile is emitted to Pyroscope
    Then Pyroscope has ingested the profile
