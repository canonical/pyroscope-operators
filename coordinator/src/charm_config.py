#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Config of the Charm."""

import dataclasses
import logging

import ops
from pydantic import (  # pylint: disable=no-name-in-module,import-error
    BaseModel,
    Field,
    StrictStr,
    ValidationError,
)

logger = logging.getLogger(__name__)

TIMESPEC_REGEXP = r"^(0|[0-9]+(y|w|d|h|m|s|ms))$"


class CharmConfigInvalidError(Exception):
    """Exception raised when a charm configuration is found to be invalid."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CharmConfigInvalidError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class PyroscopeCoordinatorConfigModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Represent the Pyroscope Coordinator charm's configuration options."""

    retention_period: StrictStr = Field(default="1d", pattern=TIMESPEC_REGEXP)
    deletion_delay: StrictStr = Field(default="12h", pattern=TIMESPEC_REGEXP)
    cleanup_interval: StrictStr = Field(default="15m", pattern=TIMESPEC_REGEXP)


@dataclasses.dataclass
class CharmConfig:
    """Represents the state of the Pyroscope Coordinator charm config.

    Attributes:
        retention_period: Delete blocks containing samples older than the specified retention
            period.
        deletion_delay: Time before a block marked for deletion is deleted from bucket.
        cleanup_interval: How frequently compactor should run blocks cleanup and maintenance,
            as well as update the bucket index.
    """

    retention_period: StrictStr
    deletion_delay: StrictStr
    cleanup_interval: StrictStr

    def __init__(
        self, *, pyroscope_charm_config_model: PyroscopeCoordinatorConfigModel
    ):
        """Initialize a new instance of the CharmConfig class.

        Args:
            pyroscope_charm_config_model: Configuration model for Pyroscope Coordinator charm.
        """
        self.retention_period = pyroscope_charm_config_model.retention_period
        self.deletion_delay = pyroscope_charm_config_model.deletion_delay
        self.cleanup_interval = pyroscope_charm_config_model.cleanup_interval

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
    ) -> "CharmConfig":
        """Initialize a new instance of the CharmConfig class from the associated charm."""
        try:
            return cls(
                pyroscope_charm_config_model=PyroscopeCoordinatorConfigModel(
                    **charm.config  # pyright: ignore[reportArgumentType]
                )
            )
        except ValidationError as exc:
            error_fields: list = []
            for error in exc.errors():
                if param := error["loc"]:
                    error_fields.extend(param)
                else:
                    value_error_msg: ValueError = error["ctx"]["error"]  # type: ignore
                    error_fields.extend(str(value_error_msg).split())
            error_fields.sort()
            error_field_str = ", ".join(f"'{f}'" for f in error_fields)
            raise CharmConfigInvalidError(
                f"The following configurations are not valid: [{error_field_str}]"
            ) from exc
