Feature: profiling
  Pyroscope ingests the profiles sent to it over OTLP gRPC.

  Background:
    Given Pyroscope is deployed

  Scenario: Pyroscope ingests profiles over OTLP gRPC
    When a profile is emitted to Pyroscope
    Then Pyroscope has ingested the profile
