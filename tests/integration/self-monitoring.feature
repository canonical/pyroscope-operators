Feature: self-monitoring

  Scenario: Pyroscope can be queried as a Grafana datasource
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then a pyroscope datasource is provisioned in grafana

  Scenario: Metrics alert rules are sent to prometheus
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then alert rules are sent to prometheus

  Scenario: loki alert rules are sent to loki
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then loki alert rules are sent to loki

  Scenario: Dashboards are provisioned
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then dashboards are sent to grafana

  Scenario: Catalogue items are provisioned
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then catalogue items are provisioned

  Scenario: Pyroscope logs are sent to loki
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then Pyroscope logs are sent to loki

  Scenario: Charm traces are sent to tempo
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then charm traces are sent to tempo

  Scenario: metrics are sent to prometheus
    Given a pyroscope cluster is deployed with COS
    When we integrate pyroscope and COS
    Then metrics are sent to prometheus
