Feature: nginx-config

  Scenario Outline: Upstreams contain the correct port
    Given a port number <port>
    When upstreams configuration is generated
    Then it contains the correct port <port>

    Examples:
      | port |
      | 4040 |
      | 4209 |

  Scenario: Server ports map to the correct locations
    Given information if TLS is enabled
    When a mapping of server ports is generated
    Then the locations are mapped to the right port

  Scenario Outline: Ingest paths are routed to the distributor
    Given the HTTP locations the coordinator serves
    When we look up an ingest path "<path>"
    Then it is routed to the distributor

    Examples:
      | path                   |
      | /push.v1.PusherService |
      | /ingest                |

  Scenario Outline: UI paths are routed to the query-frontend
    Given the HTTP locations the coordinator serves
    When we look up a UI path "<path>"
    Then it is routed at the query-frontend, not at the generic worker upstream

    Examples:
      | path    |
      | /       |
      | /assets |

  Scenario: Rendered config proxies the push API
    Given a rendered config with a distributor in the cluster
    Then the rendered config contains the push API location