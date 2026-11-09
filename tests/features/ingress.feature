Feature: ingress

  Background:
    Given a Pyroscope cluster and Traefik are deployed

  Scenario: Nginx routes respond before ingress is integrated
    Given the Pyroscope cluster is not integrated with Traefik over ingress
    Then we can hit the HTTP endpoint through nginx
    * we can hit the gRPC endpoint through nginx

  Scenario: Ingress routes respond once ingress is integrated
    Given the Pyroscope cluster is not integrated with Traefik over ingress
    When we integrate the Pyroscope cluster with Traefik over ingress
    Then the coordinator, worker, and Traefik are all in active/idle state
    * we can hit the HTTP endpoint through the ingress
    * we can hit the gRPC endpoint through the ingress

  Scenario: Nginx routes respond again after ingress is removed
    Given the Pyroscope cluster is integrated with Traefik over ingress
    When we remove the ingress relation
    Then the coordinator and worker are in active/idle state
    * we can hit the HTTP endpoint through nginx
    * we can hit the gRPC endpoint through nginx
