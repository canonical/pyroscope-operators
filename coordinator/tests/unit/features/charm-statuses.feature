Feature: charm-statuses

  Scenario: Monolithic coordinator blocks without S3 or workers
    Given a monolithic coordinator unit with no S3 or worker relations
    When the start event is handled
    Then the unit status is blocked

  Scenario: Scaled coordinator blocks without S3 or workers
    Given a scaled coordinator unit with a peers relation but no S3 or worker relations
    When the start event is handled
    Then the unit status is blocked

  Scenario: Scaled coordinator becomes active with S3 and workers
    Given a scaled coordinator unit with S3 and all worker roles
    When the start event is handled
    Then the unit status is active

  Scenario: Coordinator reports the UI URL in its active status message
    Given a coordinator unit with S3 and all worker roles
    When the start event is handled
    Then the status message is "UI ready at http://foo.com:8080"

  Scenario: Invalid retention_period config blocks the coordinator
    Given a coordinator unit with an invalid "retention_period" config value
    When the config-changed event is handled
    Then the unit status is blocked
    And the status message is "The following configurations are not valid: ['retention_period']"

  Scenario: Kubernetes patch failure surfaces as charm status
    Given the k8s service patch reports a blocked status with message "`juju trust` this application"
    When the update-status event is handled
    Then the unit status is blocked with message "`juju trust` this application"

  Scenario: Kubernetes patch waiting status surfaces as charm status
    Given the k8s service patch reports a waiting status with message "waiting"
    When the update-status event is handled
    Then the unit status is waiting with message "waiting"