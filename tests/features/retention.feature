Feature: retention
  Pyroscope removes the profiles that are older than its "retention_period"
  option.

  Background:
    Given Pyroscope is deployed

  Scenario: Pyroscope removes profiles according to its retention policy
    Given the "retention_period" option is "1m"
    When a profile is emitted to Pyroscope
    Then Pyroscope has ingested the profile
    And Pyroscope removes the profile after "1m"
