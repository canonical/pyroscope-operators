Feature: ingress
  Pyroscope's HTTP and gRPC endpoints are served by the coordinator's nginx,
  and are also reachable through the ingress when Pyroscope is related to one
  over "ingress".

  Background:
    Given Pyroscope is deployed

  Scenario: Pyroscope answers on the coordinator when it has no ingress
    Given Pyroscope has no ingress relation
    Then Pyroscope's HTTP endpoint answers on the coordinator
    And Pyroscope's gRPC endpoint answers on the coordinator

  Scenario: Pyroscope answers through the ingress when it has one
    Given Pyroscope has no ingress relation
    When Pyroscope is related to Traefik over "ingress"
    Then Pyroscope's HTTP endpoint answers through the ingress
    And Pyroscope's gRPC endpoint answers through the ingress

  Scenario: Pyroscope answers on the coordinator again once its ingress is removed
    Given Pyroscope is related to Traefik over "ingress"
    When Pyroscope's ingress relation is removed
    Then Pyroscope's HTTP endpoint answers on the coordinator
    And Pyroscope's gRPC endpoint answers on the coordinator
