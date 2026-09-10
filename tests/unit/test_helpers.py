# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
import pytest

from tests.integration.helpers import _resolve_packed_charm


def test_packed_charm_in_cwd_is_returned_as_is(tmp_path):
    project_dir = tmp_path / "worker"
    project_dir.mkdir()
    packed = tmp_path / "pyroscope-worker-k8s_ubuntu@26.04-amd64.charm"
    packed.touch()

    assert _resolve_packed_charm(packed, project_dir) == packed


def test_packed_charm_left_in_project_dir_is_found(tmp_path):
    project_dir = tmp_path / "worker"
    project_dir.mkdir()
    charm = project_dir / "pyroscope-worker-k8s_ubuntu@26.04-amd64.charm"
    charm.touch()

    assert _resolve_packed_charm(tmp_path / charm.name, project_dir) == charm


def test_missing_packed_charm_raises(tmp_path):
    project_dir = tmp_path / "worker"
    project_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        _resolve_packed_charm(tmp_path / "missing.charm", project_dir)
