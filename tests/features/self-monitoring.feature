Feature: self-monitoring

  Background:
    Given a Pyroscope cluster is deployed with COS
    When we integrate Pyroscope and COS

  Scenario: Metrics are sent to Prometheus
    Then metrics are sent to Prometheus

  Scenario: Nginx metrics are sent to Prometheus
    Then nginx metrics are sent to Prometheus

  Scenario: Charm traces are sent to Tempo
    Then charm traces are sent to Tempo

  Scenario: Worker workload traces are sent to Tempo
    Then worker workload traces are sent to Tempo

  Scenario: Pyroscope logs are sent to Loki
    Then Pyroscope logs are sent to Loki

  Scenario: Catalogue items are provisioned
    Then Catalogue items are provisioned

  Scenario: Dashboards are provisioned
    Then dashboards are provisioned

  Scenario: Pyroscope can be queried as a Grafana datasource
    Then a Pyroscope datasource is provisioned in Grafana

  Scenario: Alert rules are sent to Prometheus
    Then alert rules are sent to Prometheus

  Scenario: Loki alert rules are sent to Loki
    Then Loki alert rules are sent to Loki
