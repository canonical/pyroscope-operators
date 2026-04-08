Feature: Catalogue item URL construction
  The coordinator advertises its URL to the Juju catalogue via the catalogue relation.
  The URL scheme (http/https) and hostname depend on TLS configuration and ingress presence.

  Scenario Outline: Catalogue URL without ingress — <tls_label> TLS
    Given the coordinator is deployed without ingress for catalogue
    And TLS is <tls_label>
    When a catalogue update-status event is processed
    Then the catalogue URL is "<expected_url>"

    Examples:
      | tls_label | expected_url            |
      | without   | http://foo.com:8080     |
      | with      | https://foo.com:8080    |

  Scenario Outline: Catalogue URL with Kubernetes cluster-internal FQDN — <tls_label> TLS
    Given the coordinator is deployed without ingress for catalogue
    And the FQDN resolves to a Kubernetes cluster-internal address
    And TLS is <tls_label>
    When a catalogue update-status event is processed
    Then the catalogue URL is "<expected_url>"

    Examples:
      | tls_label | expected_url                                                         |
      | without   | http://pyroscope-coordinator-k8s.test.svc.cluster.local:8080         |
      | with      | https://pyroscope-coordinator-k8s.test.svc.cluster.local:8080        |

  Scenario Outline: Catalogue URL with ingress — <tls_label> TLS
    Given the coordinator is deployed with ingress for catalogue using <tls_label> TLS
    When a catalogue update-status event is processed
    Then the catalogue URL is "<expected_url>"

    Examples:
      | tls_label | expected_url                                              |
      | without   | http://example.com/test-pyroscope-coordinator-k8s        |
      | with      | https://example.com/test-pyroscope-coordinator-k8s       |
