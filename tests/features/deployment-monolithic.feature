Feature: deployment-monolithic
  The Pyroscope coordinator, however many units it has, is blocked until it is
  related to an s3 backend over "s3" and to a worker over "pyroscope-cluster".
  Pyroscope is healthy once it is, and the coordinator is blocked again when
  its s3 relation is removed.

  Scenario Outline: The coordinator is blocked when it is deployed alone
    Given the coordinator has <units> units
    Then the coordinator is blocked

    Examples:
      | units |
      | 1     |
      | 2     |

  Scenario: Pyroscope is healthy once the coordinator has an s3 backend and a worker
    Given the coordinator has 1 unit
    When Pyroscope is related to an s3 backend over "s3"
    And Pyroscope is related to a worker over "pyroscope-cluster"
    Then Pyroscope is healthy

  Scenario: The coordinator is blocked again when its s3 relation is removed
    Given Pyroscope is deployed
    When Pyroscope's s3 relation is removed
    Then the coordinator is blocked
