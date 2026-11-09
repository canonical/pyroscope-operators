Feature: profiling-with-collector
  Pyroscope ingests the profiles sent to an OTel Collector that is related to
  it over "profiling". Skipped until #439 is fixed: otelcol 0.130 rejects the
  OTLP profiles schema Pyroscope v2 needs, and every collector channel still
  ships 0.130.

  Background:
    Given Pyroscope is deployed

  @skip
  Scenario: Pyroscope ingests profiles sent through an OTel Collector
    Given Pyroscope is related to the OTel Collector over "profiling"
    When a profile is emitted to the OTel Collector
    Then Pyroscope has ingested the profile from the OTel Collector
