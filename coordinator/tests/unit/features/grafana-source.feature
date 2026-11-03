Feature: grafana-source

  Scenario: Datasource URL uses the unit hostname when there is no ingress
    Given no ingress relation and this unit's hostname is "foo.com"
    When the charm reconciles
    Then the published datasource URL is "http://foo.com:8080"

  Scenario: Datasource URL uses the app's Kubernetes service URL when the unit hostname is a Kubernetes FQDN
    Given no ingress relation and this unit's hostname is a Kubernetes FQDN
    When the charm reconciles
    Then the published datasource URL uses the app's Kubernetes service FQDN and HTTP server port

  Scenario: Datasource URL uses the ingress external URL once ingress is ready
    Given an ingress relation that is ready
    When the charm reconciles
    Then the published datasource URL is the external ingress URL with the model-app prefix