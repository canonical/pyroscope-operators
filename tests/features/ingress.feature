Feature: ingress

  Background:
    Given a Pyroscope cluster and Traefik are deployed

  Scenario: The coordinator responds directly when it has no ingress
    Given the Pyroscope cluster is not integrated with Traefik over ingress
    Then we can hit the HTTP endpoint directly on the coordinator
    And we can hit the gRPC endpoint directly on the coordinator

  Scenario: The coordinator responds through the ingress once it is integrated
    Given the Pyroscope cluster is not integrated with Traefik over ingress
    When we integrate the Pyroscope cluster with Traefik over ingress
    Then the coordinator, worker, and Traefik are all in active/idle state
    And we can hit the HTTP endpoint through the ingress
    And we can hit the gRPC endpoint through the ingress

  Scenario: The coordinator responds directly again after the ingress is removed
    Given the Pyroscope cluster is integrated with Traefik over ingress
    When we remove the ingress relation
    Then the coordinator and worker are in active/idle state
    And we can hit the HTTP endpoint directly on the coordinator
    And we can hit the gRPC endpoint directly on the coordinator
