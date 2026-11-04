Feature: retention

  Scenario: Pyroscope removes profiles according to retention policy
    Given a Pyroscope cluster is deployed
    When we set retention time to "1m" and emit a profile to Pyroscope using OTLP gRPC
    Then the profile should be removed after "1m"