Feature: pebble-plan

  Scenario Outline: Pyroscope command line reflects the configured role set
    Given a pyroscope-cluster with a placeholder worker config
    And the worker is configured with roles "<roles>"
    When a workload pebble ready event is fired
    Then pyroscope pebble plan is generated
    And the command targets "<roles>" sorted
    And the command pins -architecture.storage=v2

    Examples:
      | roles                        |
      | all                          |
      | query-frontend               |
      | query-frontend,query-backend |

  Scenario Outline: Metastore raft identity is injected for metastore-capable roles
    Given a pyroscope-cluster with a placeholder worker config
    And the worker is configured with roles "<roles>"
    When a workload pebble ready event is fired
    Then pyroscope pebble plan is generated
    And the command includes raft server-id/advertise-address/bind-address flags: "<has_raft>"

    Examples:
      | roles         | has_raft |
      | all           | yes      |
      | metastore     | yes      |
      | query-backend | no       |

  Scenario: Readiness check targets the unit's own FQDN
    Given a pyroscope-cluster with a placeholder worker config
    When a workload pebble ready event is fired
    Then pyroscope pebble plan is generated
    And the ready check URL is "http://<unit-fqdn>:4040/ready"

  Scenario: Pebble service is running and the charm status is active
    Given a pyroscope-cluster with a placeholder worker config
    And the worker is configured with roles
    When a workload pebble ready event is fired
    Then the pebble service is running
    And the charm status is active
    And the charm status message contains the configured roles

  Scenario: HTTPS proxy is forwarded into the service environment
    Given a pyroscope-cluster with a placeholder worker config
    And the JUJU_CHARM_HTTPS_PROXY environment variable is set to "0.0.0.1"
    When a workload pebble ready event is fired
    Then pyroscope pebble plan is generated
    And the service environment contains https_proxy set to "0.0.0.1"

  Scenario: Workload tracing environment variables are configured
    Given a workload tracing endpoint in the pyroscope-cluster config
    When a workload pebble ready event is fired
    Then the pebble plan contains the workload tracing-related environment variables
    And OTEL_TRACES_EXPORTER is set to "otlp"
    And OTEL_EXPORTER_OTLP_TRACES_ENDPOINT is set to the tracing endpoint followed by "/v1/traces"
    And OTEL_RESOURCE_ATTRIBUTES contains the Juju topology attributes