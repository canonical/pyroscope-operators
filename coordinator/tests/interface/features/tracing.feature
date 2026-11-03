Feature: tracing

  Scenario: Coordinator complies with the tracing v2 interface
    Given the coordinator charm is configured for the tracing interface version 2
    When the interface test runs
    Then the interface test passes