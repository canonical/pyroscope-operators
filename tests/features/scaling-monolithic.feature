Feature: scaling-monolithic
  The Pyroscope coordinator is blocked, however many units it has, until it is
  related to an s3 backend over "s3" and to a worker over "pyroscope-cluster",
  and is blocked again when its s3 relation is removed.

  Scenario: The coordinator is blocked when it is deployed alone
    Given the coordinator has 1 unit
    Then the coordinator is blocked

  Scenario: The coordinator stays blocked when it is scaled up
    Given the coordinator has 1 unit
    When the coordinator is scaled to 2 units
    Then the coordinator is blocked

  Scenario: Pyroscope is healthy once the coordinator has an s3 backend and a worker
    Given the coordinator has 1 unit
    When Pyroscope is related to an s3 backend over "s3"
    And Pyroscope is related to a worker over "pyroscope-cluster"
    Then Pyroscope is healthy

  Scenario: The coordinator is blocked again when its s3 relation is removed
    Given Pyroscope is deployed
    When Pyroscope's s3 relation is removed
    Then the coordinator is blocked
