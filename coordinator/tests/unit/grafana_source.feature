Feature: Grafana datasource URL configuration
  The Pyroscope coordinator exposes its HTTP endpoint to Grafana via the
  grafana-source relation. The advertised URL depends on whether an ingress
  relation is present and how the unit's hostname resolves.

  Scenario: No ingress and external FQDN
    Given the coordinator is deployed without ingress
    And the unit FQDN resolves to "foo.com"
    When an update-status event is processed
    Then the Grafana datasource host is "http://foo.com:8080"

  Scenario: No ingress and Kubernetes cluster-internal FQDN
    Given the coordinator is deployed without ingress
    And the unit FQDN resolves to a Kubernetes cluster-internal address
    When an update-status event is processed
    Then the Grafana datasource host uses the Kubernetes service FQDN

  Scenario: Ingress configured
    Given the coordinator is deployed with an ingress relation
    And the unit FQDN resolves to "foo.com"
    When an update-status event is processed
    Then the Grafana datasource host uses the ingress external URL
