Feature: configuration
  Pyroscope can be configured through the "retention_period" option, and
  removes the profiles that are older than it.

  Background:
    Given Pyroscope is deployed

  Scenario: Pyroscope removes profiles according to its retention period
    Given the "retention_period" option is "1m"
    When a profile is emitted to Pyroscope
    Then Pyroscope has ingested the profile
    And Pyroscope removes the profile after "1m"
