Feature: deployment-distributed
  The workers of a distributed Pyroscope cluster, one for every role, are
  blocked until the coordinator is related to them over "pyroscope-cluster",
  and the cluster is healthy once the coordinator also has an s3 backend over
  "s3".

  Scenario: The workers are blocked without the coordinator
    Given a worker is deployed for every role
    Then the workers are blocked

  Scenario: The cluster is healthy once the coordinator has an s3 backend and the workers
    Given a worker is deployed for every role
    When the coordinator is deployed with an s3 backend and related to the workers
    Then Pyroscope is healthy
