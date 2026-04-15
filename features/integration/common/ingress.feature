Feature: ingress

  Background:
    Given a pyroscope cluster is deployed alongside Traefik

  Scenario: Pyroscope endpoints before, during, and after ingress integration
    Then the HTTP endpoint is accessible directly through nginx
    And the gRPC endpoint is accessible directly through nginx
    When Traefik is integrated with pyroscope over ingress
    Then the HTTP endpoint is accessible via the ingress hostname
    And the gRPC endpoint is accessible via the ingress hostname
    When the ingress integration is removed
    Then the HTTP endpoint is accessible directly through nginx
    And the gRPC endpoint is accessible directly through nginx
