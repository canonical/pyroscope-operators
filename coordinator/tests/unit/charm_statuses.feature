Feature: Coordinator charm status reporting
  The coordinator reports its operational status to the Juju operator.
  The status reflects whether all required relations and configurations are in place.

  Scenario: Blocked without any dependencies
    Given the coordinator has no peer units
    When the charm starts
    Then the charm unit status is "blocked"

  Scenario: Blocked without required relations in scaled mode
    Given the coordinator has peer units
    When the charm starts
    Then the charm unit status is "blocked"

  Scenario: Active when all dependencies are present
    Given the coordinator has peer units
    And the coordinator has an S3 relation
    And the coordinator has a worker relation
    When the charm starts
    Then the charm unit status is "active"
    And the status message contains "UI ready"

  Scenario: Blocked when Kubernetes resource patch fails
    Given the coordinator has peer units
    And the coordinator has an S3 relation
    And the coordinator has a worker relation
    And the Kubernetes resource patch reports blocked status
    When an update-status event is processed
    Then the charm unit status is "blocked"
    And the status message is "`juju trust` this application"

  Scenario: Blocked when retention period config is invalid
    Given the coordinator has peer units
    And the coordinator has an S3 relation
    And the coordinator has a worker relation
    And the retention_period config is "invalid"
    When a config-changed event is processed
    Then the charm unit status is "blocked"
    And the status message is "The following configurations are not valid: ['retention_period']"

  Scenario: Waiting when Kubernetes resource patch is waiting
    Given the coordinator has peer units
    And the coordinator has an S3 relation
    And the coordinator has a worker relation
    And the Kubernetes resource patch reports waiting status
    When an update-status event is processed
    Then the charm unit status is "waiting"
    And the status message is "waiting"
