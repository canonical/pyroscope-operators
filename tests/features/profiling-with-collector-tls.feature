Feature: profiling-with-collector-tls
  With a certificate from a CA over "certificates", Pyroscope ingests the
  profiles sent to an OTel Collector that is related to it over "profiling".
  Skipped until #439 is fixed: otelcol 0.130 rejects the OTLP profiles schema
  Pyroscope v2 needs, and every collector channel still ships 0.130.

  Background:
    Given Pyroscope is deployed

  @skip
  Scenario: Pyroscope ingests profiles sent through an OTel Collector with TLS
    Given Pyroscope is related to the OTel Collector over "profiling"
    And Pyroscope is related to a CA over "certificates"
    And the OTel Collector is related to a CA over "receive-ca-cert"
    When a profile is emitted to the OTel Collector
    Then Pyroscope has ingested the profile from the OTel Collector
