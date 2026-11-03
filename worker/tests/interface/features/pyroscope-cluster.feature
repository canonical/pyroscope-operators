Feature: pyroscope-cluster

  Scenario: Worker complies with the pyroscope_cluster v0 interface
    Given the worker charm is configured for the pyroscope_cluster interface version 0
    When the interface test runs
    Then the interface test passes