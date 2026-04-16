Feature: self-monitoring

  Background:
    Given a cluster is deployed and integrated with COS

  @integration
  Scenario: The application can be queried as a Grafana datasource
    Then a datasource is provisioned in grafana

  @integration
  Scenario: Metrics alert rules are sent to prometheus
    Then alert rules are sent to prometheus

  @integration
  Scenario: Loki alert rules are sent to loki
    Then loki alert rules are sent to loki

  @integration
  Scenario: Dashboards are provisioned
    Then Dashboards are provisioned

  @integration
  Scenario: Application logs are sent to loki
    Then Application logs are sent to loki

  @integration
  Scenario: Charm traces are sent to tempo
    Then charm traces are sent to tempo

  @integration
  Scenario: Metrics are sent to prometheus
    Then metrics are sent to prometheus
