Feature: self-monitoring
  Pyroscope sends its metrics to the OTel Collector over "metrics-endpoint",
  its logs over "logging" and its traces over "charm-tracing" and
  "workload-tracing", and the alert rules for the metrics and the logs with
  them. It provides its dashboards and datasource to Grafana over
  "grafana-dashboard" and "grafana-source", and its item to Catalogue over
  "catalogue". The OTel Collector stands for Prometheus, Loki and Tempo: it is
  blocked without a backend to send to, but its receivers count what they get.

  Background:
    Given Pyroscope is deployed with a worker for every role

  Scenario: The OTel Collector receives Pyroscope's metrics
    When Pyroscope is related to the OTel Collector over "metrics-endpoint"
    Then the OTel Collector has metrics from Pyroscope

  Scenario: The OTel Collector receives the metrics of Pyroscope's nginx
    When Pyroscope is related to the OTel Collector over "metrics-endpoint"
    Then the OTel Collector has nginx metrics from Pyroscope

  Scenario: The OTel Collector gets Pyroscope's alert rules for metrics
    When Pyroscope is related to the OTel Collector over "metrics-endpoint"
    Then the OTel Collector has alert rules from Pyroscope over "metrics-endpoint"

  Scenario: The OTel Collector receives Pyroscope's logs
    When Pyroscope is related to the OTel Collector over "logging"
    Then the OTel Collector has logs from Pyroscope

  Scenario: The OTel Collector gets Pyroscope's alert rules for logs
    When Pyroscope is related to the OTel Collector over "logging"
    Then the OTel Collector has alert rules from Pyroscope over "logging"

  Scenario: The OTel Collector receives Pyroscope's charm traces
    When Pyroscope is related to the OTel Collector over "charm-tracing"
    Then the OTel Collector has charm traces from Pyroscope

  Scenario: Pyroscope's workers send their workload traces to the OTel Collector
    When Pyroscope is related to the OTel Collector over "workload-tracing"
    Then Pyroscope's workers send their workload traces to the OTel Collector

  Scenario: Grafana gets Pyroscope's dashboards
    When Pyroscope is related to Grafana over "grafana-dashboard"
    Then Grafana has dashboards from Pyroscope

  Scenario: Grafana gets Pyroscope as a datasource
    When Pyroscope is related to Grafana over "grafana-source"
    Then Grafana has a datasource for Pyroscope

  Scenario: Catalogue gets an item for Pyroscope
    When Pyroscope is related to Catalogue over "catalogue"
    Then Catalogue has an item for Pyroscope
