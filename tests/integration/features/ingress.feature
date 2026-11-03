Feature: ingress

  Scenario: Nginx UI route before ingress
    Given a pyroscope cluster and traefik are deployed
    When we check the HTTP endpoint before integrating ingress
    Then we can hit the HTTP endpoint through nginx

  Scenario: Nginx gRPC server route before ingress
    Given a pyroscope cluster and traefik are deployed
    When we check the gRPC endpoint before integrating ingress
    Then we can hit the gRPC endpoint through nginx

  Scenario: Nginx UI route with ingress
    Given a pyroscope cluster and traefik are deployed
    When we integrate the pyroscope cluster with traefik over ingress
    Then the coordinator, worker, and traefik are all in active/idle state
    And we can hit the HTTP endpoint through nginx

  Scenario: Nginx gRPC server route with ingress
    Given a pyroscope cluster and traefik are deployed
    When we integrate the pyroscope cluster with traefik over ingress
    Then the coordinator, worker, and traefik are all in active/idle state
    And we can hit the gRPC endpoint through nginx

  Scenario: Nginx UI route after ingress is removed
    Given a model with traefik and the pyroscope cluster integrated
    When we remove the ingress relation
    Then the coordinator and worker are in active/idle state
    And we can once again hit the HTTP endpoint through nginx

  Scenario: Nginx gRPC server route after ingress is removed
    Given a model with traefik and the pyroscope cluster integrated
    When we remove the ingress relation
    Then the coordinator and worker are in active/idle state
    And we can once again hit the gRPC endpoint through nginx