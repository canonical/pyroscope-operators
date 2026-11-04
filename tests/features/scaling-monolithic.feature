Feature: scaling-monolithic

  Scenario: Coordinator blocks when deployed alone
    Given a Pyroscope coordinator is deployed with no other relations
    Then the coordinator is blocked

  Scenario: Coordinator stays blocked when scaled up without s3 or workers
    Given a Pyroscope coordinator is deployed with no other relations
    When we add a coordinator unit
    Then the coordinator is blocked

  Scenario: Coordinator and workers become active once s3 and a full role set are integrated
    Given a Pyroscope coordinator is deployed with no other relations
    When we deploy an s3 backend and a full monolithic set of workers, and integrate them
    Then the coordinator and workers are active

  Scenario: Coordinator blocks again if the s3 integration is removed
    Given the coordinator, s3 backend and workers are all integrated and active
    When we remove the s3 relation
    Then the coordinator is blocked