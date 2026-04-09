Feature: self-monitoring

  Background:
    Given a pyroscope cluster is deployed and integrated with COS

  Scenario: Pyroscope can be queried as a Grafana datasource
    Then a pyroscope datasource is provisioned in grafana

  Scenario: Metrics alert rules are sent to prometheus
    Then alert rules are sent to prometheus

  Scenario: Loki alert rules are sent to loki
    Then loki alert rules are sent to loki

  Scenario: Dashboards are provisioned
    Then Dashboards are provisioned

  Scenario: Catalogue items are provisioned
    Then catalogue items are provisioned

  Scenario: Pyroscope logs are sent to loki
    Then Pyroscope logs are sent to loki

  Scenario: Charm traces are sent to tempo
    Then charm traces are sent to tempo

  Scenario: Metrics are sent to prometheus
    Then metrics are sent to prometheus
