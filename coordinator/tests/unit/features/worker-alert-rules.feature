Feature: worker-alert-rules

  Scenario: Metastore raft alerts reference exported metric names
    Given the worker alert rules file is loaded
    Then "PyroscopeMetastoreRaftNoLeader" expr references pyroscope_metastore_raft_state
    And "PyroscopeMetastoreRaftMultipleLeaders" expr references pyroscope_metastore_raft_state
    And "PyroscopeMetastoreRaftLogStoreTimeouts" expr references pyroscope_metastore_raft_log_store_write_timeouts_total

  Scenario: The no-leader alert handles a missing leader series per cluster
    Given the "PyroscopeMetastoreRaftNoLeader" alert expression
    Then it contains an OR condition keyed by juju_model_uuid and juju_application
    And it includes a zero-filled series grouped by juju_model_uuid and juju_application

  Scenario: Compaction-worker alerts reference exported failure metrics
    Given the worker alert rules file is loaded
    Then "PyroscopeCompactionWorkerJobFailures" expr references pyroscope_compaction_worker_jobs_completed_total
    And "PyroscopeCompactionWorkerBlockDeletionFailures" expr references pyroscope_compaction_worker_blocks_deleted_total
