Feature: profiling-interface

  Scenario Outline: Coordinator publishes its OTLP gRPC endpoint without ingress
    Given internal TLS is "<tls>"
    And no ingress relation is configured
    When the profiling relation is reconciled
    Then the published OTLP gRPC endpoint uses the coordinator gRPC port
    And the published insecure flag is "<insecure>"

    Examples:
      | tls   | insecure |
      | false | true     |
      | true  | false    |

  Scenario Outline: Coordinator publishes its OTLP gRPC endpoint through ingress
    Given internal TLS is "<internal_tls>"
    And ingress TLS is "<ingress_tls>"
    When the profiling relation is reconciled
    Then the published OTLP gRPC endpoint uses the external host and coordinator gRPC port
    And the published insecure flag is "<insecure>"

    Examples:
      | internal_tls | ingress_tls | insecure |
      | false        | false       | true     |
      | false        | true        | false    |
      | true         | false       | true     |
      | true         | true        | false    |

  Scenario: Requirer side returns an empty list when no endpoint is provided
    Given a profiling relation databag without endpoint data
    When ProfilingEndpointRequirer.get_endpoints is called
    Then it returns an empty list

  Scenario Outline: Requirer side parses the provided endpoint
    Given a profiling relation databag with OTLP gRPC endpoint "foo.com:1234"
    And the insecure value is "<insecure>"
    When ProfilingEndpointRequirer.get_endpoints is called
    Then it returns an endpoint with address "foo.com:1234"
    And its insecure value is <insecure>