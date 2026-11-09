Feature: scaling-monolithic

  Scenario: Coordinator blocks when deployed alone
    Given a Pyroscope coordinator is deployed with no other relations
    Then the coordinator is blocked

  Scenario: Coordinator stays blocked when scaled up without s3 or workers
    Given a Pyroscope coordinator is deployed with no other relations
    When we scale the coordinator to 2 units
    Then the coordinator is blocked

  Scenario: Coordinator and worker become active once an s3 backend is integrated
    Given a Pyroscope coordinator is deployed with no other relations
    When we integrate the coordinator with an s3 backend and a worker that runs every role
    Then the coordinator and the worker are active

  Scenario: Coordinator blocks again if the s3 integration is removed
    Given the coordinator, s3 backend and worker are all integrated and active
    When we remove the s3 relation
    Then the coordinator is blocked
