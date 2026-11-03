Feature: ingress-config

  Scenario: HTTP router routes under the model-app path prefix
    Given a leader unit with ingress ready
    When traefik config is generated
    Then the http router rule is PathPrefix of the model-app prefix
    And it applies the strip-prefix middleware

  Scenario: gRPC router matches any host and skips the strip-prefix middleware
    Given a leader unit with ingress ready
    When traefik config is generated
    Then the grpc router rule is HostRegexp matching any host
    And it does not apply the strip-prefix middleware

  Scenario: TLS enabled redirects HTTP and gRPC endpoints to HTTPS
    Given HTTP and gRPC endpoints are configured
    And TLS is enabled
    When Traefik ingress config is generated
    Then each endpoint has a redirectScheme middleware
    And each redirect targets the HTTPS scheme

  Scenario: TLS disabled serves gRPC over h2c to the load balancer
    Given TLS is disabled
    When traefik config is generated
    Then the grpc service load balancer uses the h2c scheme

  Scenario: Static config declares a dedicated entrypoint for the gRPC port only
    Given the http and grpc endpoint definitions
    When the static traefik config is generated
    Then the grpc entrypoint is configured on port 1234