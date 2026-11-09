Feature: juju-doctor
  The juju-doctor probes pass on a Pyroscope cluster with a worker for every
  role.

  Background:
    Given Pyroscope is deployed with a worker for every role

  Scenario: juju-doctor passes on a cluster with a worker for every role
    Then juju-doctor passes
