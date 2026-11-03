Feature: pyroscope-cluster

  Scenario: Coordinator complies with the pyroscope_cluster v0 interface
    Given the coordinator is configured for the pyroscope_cluster interface version 0
    When the interface test runs
    Then the interface test passes