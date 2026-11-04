Feature: ingress

  Scenario: Nginx routes respond before ingress is integrated
    Given a Pyroscope cluster and Traefik are deployed
    Then we can hit the HTTP endpoint through nginx
    * we can hit the gRPC endpoint through nginx

  Scenario: Nginx routes respond once ingress is integrated
    Given a Pyroscope cluster and Traefik are deployed
    When we integrate the Pyroscope cluster with Traefik over ingress
    Then the coordinator, worker, and Traefik are all in active/idle state
    * we can hit the HTTP endpoint through nginx
    * we can hit the gRPC endpoint through nginx

  Scenario: Nginx routes respond again after ingress is removed
    Given a model with Traefik and the Pyroscope cluster integrated
    When we remove the ingress relation
    Then the coordinator and worker are in active/idle state
    * we can once again hit the HTTP endpoint through nginx
    * we can once again hit the gRPC endpoint through nginx
