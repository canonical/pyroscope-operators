from unittest.mock import MagicMock
import pytest
import yaml

from charm_config import CharmConfig, PyroscopeCoordinatorConfigModel
from pyroscope import Pyroscope


def mock_coordinator():
    mm = MagicMock()
    mm.cluster.gather_addresses.return_value = ("192.0.2.0", "192.0.2.1")
    mm.cluster.gather_addresses_by_role.return_value = {
        "all": {"192.0.2.0", "192.0.2.1"}
    }
    mm._s3_config = {
        "endpoint": "s3-endpoint",
        "region": "s3-region",
        "access_key_id": "s3-access_key",
        "secret_access_key": "s3-secret_key",
        "bucket_name": "s3-bucket",
        "insecure": True,
        "tls_ca_path": "s3-tls_ca_path",
    }
    return mm


@pytest.mark.parametrize("url", ("/", None, "foo.com"))
def test_pyroscope(url, coordinator_charm_config):
    # this test was added for the one and only purpose to achieve 100% coverage.
    cfg = Pyroscope(url, coordinator_charm_config)
    assert cfg.config(mock_coordinator())


def test_reporting_enabled_by_default(coordinator_charm_config):
    """When reporting_enabled is True (default), no analytics section should appear."""
    cfg = Pyroscope("foo.com", coordinator_charm_config)
    config_dict = yaml.safe_load(cfg.config(mock_coordinator()))
    assert "analytics" not in config_dict


def test_reporting_disabled():
    """When reporting_enabled is False, analytics.reporting_enabled should be False."""
    charm_config = CharmConfig(
        pyroscope_charm_config_model=PyroscopeCoordinatorConfigModel(
            retention_period="1d", reporting_enabled=False
        )
    )
    cfg = Pyroscope("foo.com", charm_config)
    config_dict = yaml.safe_load(cfg.config(mock_coordinator()))
    assert config_dict["analytics"] == {"reporting_enabled": False}
