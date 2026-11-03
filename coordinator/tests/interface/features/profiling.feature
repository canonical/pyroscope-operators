Feature: profiling

  Scenario: Coordinator complies with the profiling v0 interface
    Given the coordinator is configured for the profiling interface version 0
    When the interface test runs
    Then the interface test passes