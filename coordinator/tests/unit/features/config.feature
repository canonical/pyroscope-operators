Feature: config

  Scenario: Server config uses the fixed HTTP listen port
    Given an S3 relation and a worker relation
    When the Pyroscope config is generated
    Then server.http_listen_port equals 4040

  Scenario Outline: Segment-writer replication factor scales with writer count
    Given <n> segment-writer worker addresses
    When the Pyroscope config is generated
    Then segment_writer.lifecycler.ring.replication_factor is <rf>

    Examples:
      | n | rf |
      | 1 | 1  |
      | 3 | 3  |

  Scenario Outline: Metastore Raft config bootstraps from metastore worker addresses
    Given <n> metastore worker addresses
    When the Pyroscope config is generated
    Then metastore.raft.bootstrap_expect_peers equals <n>
    And metastore.raft.bootstrap_peers lists each address with the Raft port
    And metastore.address lists every metastore unit on the gRPC port

    Examples:
      | n |
      | 1 |
      | 3 |

  Scenario: Query-backend address is a headless dns:/// target
    Given query-backend worker addresses
    When the Pyroscope config is generated
    Then query_backend.address uses the dns:/// scheme on the shared headless service and grpc port

  Scenario Outline: Memberlist config joins all known worker peers
    Given <n> worker peer addresses
    When the Pyroscope config is generated
    Then memberlist.bind_port equals 7946
    Then memberlist.join_members lists every peer on the memberlist port

    Examples:
      | n |
      | 1 |
      | 3 |

  Scenario: S3 storage config is built from the s3 relation data
    Given an s3 relation providing endpoint, region, keys, bucket and TLS settings
    When the Pyroscope config is generated
    Then storage.backend is "s3"
    And storage.s3 matches the s3 relation data
  
  Scenario: API base URL is absent without ingress
    Given an S3 relation and a worker relation
    And no ingress relation is configured
    When the Pyroscope config is generated
    Then api does not contain a base-url

  Scenario: API base URL reflects the ingress path prefix
    Given an ingress relation is configured and ready
    When the Pyroscope config is generated
    Then api.base-url equals the model-specific coordinator path prefix

  Scenario Outline: retention_period config maps to limits.retention_period
    Given retention_period config is "<config>"
    When the Pyroscope config is generated
    Then limits.retention_period is <expected>

    Examples:
      | config  | expected |
      | unset   | "1d"     |
      | "7d"    | "7d"     |
      | invalid | 0        |

  Scenario: Deprecated config options have no effect on the generated config
    Given deletion_delay and cleanup_interval are set, alongside a valid retention_period
    When the Pyroscope config is generated
    Then neither deletion_delay nor cleanup_interval appears in the generated config
    And retention_period remains "7d"