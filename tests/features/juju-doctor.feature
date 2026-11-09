Feature: juju-doctor
  The juju-doctor probes pass on a Pyroscope cluster with a worker for every
  role.

  Scenario: juju-doctor passes on a cluster with a worker for every role
    Given a worker is deployed for every role
    Then the workers are blocked
    When the coordinator is deployed with an s3 backend and related to the workers
    Then Pyroscope is healthy
    And juju-doctor passes
