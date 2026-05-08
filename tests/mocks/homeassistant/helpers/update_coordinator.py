# Mock homeassistant.helpers.update_coordinator
from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator:
    data: dict[str, Any] | None = None

    def __init__(
        self,
        hass: Any,
        logger: Any,
        name: str,
        update_interval: timedelta,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.last_update_success = True
        self.last_update_success_time = None

    async def async_config_entry_first_refresh(self) -> None:
        self.data = await self._async_update_data()

    async def async_request_refresh(self) -> None:
        self.data = await self._async_update_data()

    async def _async_update_data(self) -> dict[str, Any]:
        raise NotImplementedError()


class CoordinatorEntity(MagicMock):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__()
        self.coordinator = coordinator
