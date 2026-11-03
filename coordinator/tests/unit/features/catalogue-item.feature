Feature: catalogue-item

  Scenario Outline: Catalogue URL reflects TLS and ingress configuration
    Given TLS is "<tls>" and ingress is "<ingress>"
    When the charm reconciles
    Then the catalogue entry URL is "<expected_url>"

    Examples:
      | tls   | ingress | expected_url                                                       |
      | false | absent  | http://foo.com:8080                                                |
      | true  | absent  | https://foo.com:8080                                               |
      | false | k8s     | http://pyroscope-coordinator-k8s.test.svc.cluster.local:8080       |
      | true  | k8s     | https://pyroscope-coordinator-k8s.test.svc.cluster.local:8080      |
      | false | ready   | http://example.com/test-pyroscope-coordinator-k8s                  |
      | true  | ready   | https://example.com/test-pyroscope-coordinator-k8s                 |