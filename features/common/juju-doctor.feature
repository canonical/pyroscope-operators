Feature: juju-doctor cluster consistency probe

  @integration
  Scenario: Distributed cluster passes the cluster-consistency probe
    Given all worker roles are deployed
    When the coordinator and S3 are deployed and integrated with the workers
    Then the full cluster reaches active/idle
    And the juju-doctor cluster-consistency probe passes
