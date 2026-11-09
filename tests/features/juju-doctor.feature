Feature: juju-doctor

  Scenario: juju-doctor passes on a Pyroscope cluster with the recommended scale
    Given the workers are deployed with the recommended scale
    Then the workers are blocked because of the missing coordinator integration
    When the Pyroscope coordinator and SWFS are deployed and integrated with the workers
    Then both the coordinator and the workers become active
    And juju-doctor passes
