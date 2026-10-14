from pathlib import Path

import yaml


ALERT_RULES_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "prometheus_alert_rules"
    / "workers"
    / "alerts.yaml"
)


def _rules_by_name():
    rule_groups = yaml.safe_load(ALERT_RULES_PATH.read_text())["groups"]
    return {
        rule["alert"]: rule
        for group in rule_groups
        for rule in group["rules"]
    }


def test_metastore_raft_alerts_use_exported_metric_names():
    rules = _rules_by_name()

    assert "pyroscope_metastore_raft_state" in rules[
        "PyroscopeMetastoreRaftNoLeader"
    ]["expr"]
    assert "pyroscope_metastore_raft_state" in rules[
        "PyroscopeMetastoreRaftMultipleLeaders"
    ]["expr"]
    assert "pyroscope_metastore_raft_log_store_write_timeouts_total" in rules[
        "PyroscopeMetastoreRaftLogStoreTimeouts"
    ]["expr"]


def test_no_leader_alert_handles_a_missing_leader_series_per_cluster():
    expression = _rules_by_name()["PyroscopeMetastoreRaftNoLeader"]["expr"]

    assert "or on (juju_model_uuid, juju_application)" in expression
    assert "0 * sum by (juju_model_uuid, juju_application)" in expression


def test_compaction_alerts_use_exported_failure_metrics():
    rules = _rules_by_name()

    assert "pyroscope_compaction_worker_jobs_completed_total" in rules[
        "PyroscopeCompactionWorkerJobFailures"
    ]["expr"]
    assert "pyroscope_compaction_worker_blocks_deleted_total" in rules[
        "PyroscopeCompactionWorkerBlockDeletionFailures"
    ]["expr"]
