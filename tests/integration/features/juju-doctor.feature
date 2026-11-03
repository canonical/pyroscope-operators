Feature: juju-doctor

  Scenario: Deploy workers
    Given an empty model
    When deploying the workers with recommended scale
    Then workers will be blocked because of missing coordinator integration

  Scenario: Add coordinator and SWFS
    Given a model with workers
    When deploying and integrating the minimal pyroscope cluster
    Then both the coordinator and the workers become active

  Scenario: Run juju-doctor probes
    Given the full model
    Then juju-doctor passes