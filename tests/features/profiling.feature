Feature: profiling
  Pyroscope ingests the profiles sent to it over OTLP gRPC, directly or through
  an OTel Collector that is related to it over "profiling", and serves over
  HTTP or, with a certificate from a CA over "certificates", over HTTPS.
  The scenarios through an OTel Collector are skipped until #439 is fixed:
  otelcol 0.130 rejects the OTLP profiles schema Pyroscope v2 needs, and every
  collector channel still ships 0.130.

  Scenario Outline: Pyroscope ingests profiles over OTLP gRPC
    Given Pyroscope serves over <scheme>
    When a profile is emitted to Pyroscope
    Then Pyroscope has ingested the profile

    Examples:
      | scheme |
      | HTTP   |
      | HTTPS  |

  @skip
  Scenario: Pyroscope ingests profiles sent through an OTel Collector
    Given Pyroscope serves over HTTP
    And Pyroscope is related to the OTel Collector over "profiling"
    When a profile is emitted to the OTel Collector
    Then Pyroscope has ingested the profile from the OTel Collector

  @skip
  Scenario: Pyroscope ingests profiles sent through an OTel Collector over HTTPS
    Given Pyroscope serves over HTTPS
    And Pyroscope is related to the OTel Collector over "profiling"
    And the OTel Collector is related to a CA over "receive-ca-cert"
    When a profile is emitted to the OTel Collector
    Then Pyroscope has ingested the profile from the OTel Collector
