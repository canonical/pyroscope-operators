Feature: self-monitoring
  Pyroscope's coordinator and workers send their metrics to the OpenTelemetry
  Collector over "metrics-endpoint", their logs over "logging" and their traces
  over "charm-tracing" and "workload-tracing", and the alert rules for the
  metrics and the logs with them. Pyroscope provides its dashboards and
  datasource to Grafana over "grafana-dashboard" and "grafana-source", and its
  item to Catalogue over "catalogue". The OpenTelemetry Collector stands for
  Prometheus, Loki and Tempo: it is blocked without a backend to send to, but it
  receives, and tells apart what each application sends.

  Background:
    Given Pyroscope is deployed with a worker for every role
    And the OpenTelemetry Collector counts the telemetry of every Pyroscope application

  Scenario: The OpenTelemetry Collector receives the metrics of every Pyroscope application
    When Pyroscope is related to the OpenTelemetry Collector over "metrics-endpoint"
    Then the OpenTelemetry Collector has metrics from every Pyroscope application

  Scenario: The OpenTelemetry Collector receives the metrics of Pyroscope's nginx
    When Pyroscope is related to the OpenTelemetry Collector over "metrics-endpoint"
    Then the OpenTelemetry Collector has nginx metrics from Pyroscope

  Scenario: The OpenTelemetry Collector gets Pyroscope's alert rules for metrics
    When Pyroscope is related to the OpenTelemetry Collector over "metrics-endpoint"
    Then the OpenTelemetry Collector has alert rules from Pyroscope over "metrics-endpoint"

  Scenario: The OpenTelemetry Collector receives the logs of every Pyroscope application
    When Pyroscope is related to the OpenTelemetry Collector over "logging"
    Then the OpenTelemetry Collector has logs from every Pyroscope application

  Scenario: The OpenTelemetry Collector gets Pyroscope's alert rules for logs
    When Pyroscope is related to the OpenTelemetry Collector over "logging"
    Then the OpenTelemetry Collector has alert rules from Pyroscope over "logging"

  Scenario: The OpenTelemetry Collector receives the charm traces of every Pyroscope application
    When Pyroscope is related to the OpenTelemetry Collector over "charm-tracing"
    Then the OpenTelemetry Collector has charm traces from every Pyroscope application

  Scenario: The OpenTelemetry Collector receives the workload traces of every Pyroscope worker
    When Pyroscope is related to the OpenTelemetry Collector over "workload-tracing"
    Then the OpenTelemetry Collector has workload traces from every Pyroscope worker

  Scenario: Grafana gets Pyroscope's dashboards
    When Pyroscope is related to Grafana over "grafana-dashboard"
    Then Grafana has dashboards from Pyroscope

  Scenario: Grafana gets Pyroscope as a datasource
    When Pyroscope is related to Grafana over "grafana-source"
    Then Grafana has a datasource for Pyroscope

  Scenario: Catalogue gets an item for Pyroscope
    When Pyroscope is related to Catalogue over "catalogue"
    Then Catalogue has an item for Pyroscope
