# Mock homeassistant.components.sensor
from __future__ import annotations

from enum import StrEnum
from typing import Any
from unittest.mock import MagicMock


class SensorDeviceClass(StrEnum):
    TIMESTAMP = "timestamp"


class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"


class SensorEntityDescription:
    def __init__(
        self,
        key: str,
        translation_key: str | None = None,
        icon: str | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        native_unit_of_measurement: str | None = None,
        suggested_display_precision: int | None = None,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        self.key = key
        self.translation_key = translation_key
        self.icon = icon
        self.device_class = device_class
        self.state_class = state_class
        self.native_unit_of_measurement = native_unit_of_measurement
        self.suggested_display_precision = suggested_display_precision
        self.entity_registry_enabled_default = entity_registry_enabled_default


class SensorEntity(MagicMock):
    entity_description: SensorEntityDescription | None = None
