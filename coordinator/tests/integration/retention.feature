Feature: retention

  Scenario: Pyroscope removes profiles according to retention policy
    Given a pyroscope cluster is deployed
    When we configure retention policy to "1m" and emit a profile
    Then the profile should be removed after "1m"
