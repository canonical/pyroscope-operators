Feature: worker-ports

  Scenario Outline: Coordinator opens the right ports per worker role
    Given a worker reports role "<role>"
    When the coordinator computes worker ports
    Then it opens ports <ports>

    Examples:
      | role                     | ports                                  |
      | all                      | memberlist, http, grpc, metastore-raft |
      | metastore                | memberlist, http, grpc, metastore-raft |
      | metastore,segment-writer | memberlist, http, grpc, metastore-raft |
      | query-backend            | memberlist, http, grpc                 |
      | distributor              | memberlist, http, grpc                 |
