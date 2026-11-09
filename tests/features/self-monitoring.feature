Feature: self-monitoring
  Pyroscope sends its metrics to Prometheus over "metrics-endpoint", its logs
  to Loki over "logging" and its traces to Tempo over "charm-tracing" and
  "workload-tracing". It provides its dashboards and datasource to Grafana
  over "grafana-dashboard" and "grafana-source", and its item to Catalogue
  over "catalogue".

  Background:
    Given Pyroscope is deployed with a worker for every role

  Scenario: Prometheus receives Pyroscope's metrics
    When Pyroscope is related to Prometheus over "metrics-endpoint"
    Then Prometheus has metrics from Pyroscope

  Scenario: Prometheus receives the metrics of Pyroscope's nginx
    When Pyroscope is related to Prometheus over "metrics-endpoint"
    Then Prometheus has nginx metrics from Pyroscope

  Scenario: Prometheus gets Pyroscope's alert rules
    When Pyroscope is related to Prometheus over "metrics-endpoint"
    Then Prometheus has alert rules from Pyroscope

  Scenario: Loki receives Pyroscope's logs
    When Pyroscope is related to Loki over "logging"
    Then Loki has logs from Pyroscope

  Scenario: Loki gets Pyroscope's alert rules
    When Pyroscope is related to Loki over "logging"
    Then Loki has alert rules from Pyroscope

  Scenario: Tempo receives Pyroscope's charm traces
    When Pyroscope is related to Tempo over "charm-tracing"
    Then Tempo has charm traces from Pyroscope

  Scenario: Tempo receives Pyroscope's workload traces
    When Pyroscope is related to Tempo over "workload-tracing"
    Then Tempo has workload traces from Pyroscope

  Scenario: Grafana gets Pyroscope's dashboards
    When Pyroscope is related to Grafana over "grafana-dashboard"
    Then Grafana has dashboards from Pyroscope

  Scenario: Grafana gets Pyroscope as a datasource
    When Pyroscope is related to Grafana over "grafana-source"
    Then Grafana has a datasource for Pyroscope

  Scenario: Catalogue gets an item for Pyroscope
    When Pyroscope is related to Catalogue over "catalogue"
    Then Catalogue has an item for Pyroscope
