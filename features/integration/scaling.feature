Feature: scaling

  Scenario: Coordinator transitions through blocked and active states
    Given a pyroscope coordinator is deployed without S3 or workers
    Then the coordinator reports blocked status
    When the coordinator is scaled up to 2 units
    Then the coordinator reports blocked status
    When S3 and workers are deployed and integrated with the coordinator
    Then the coordinator reports active status
    When the S3 relation is removed
    Then the coordinator reports blocked status
