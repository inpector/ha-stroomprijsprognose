# Mock homeassistant.config_entries
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class ConfigEntry(MagicMock):
    entry_id: str = "test_entry_id"
    data: dict[str, Any] = {}
    options: dict[str, Any] = {}
    title: str = ""


class ConfigFlow:
    """Mock ConfigFlow that absorbs domain= keyword like real HA."""

    VERSION = 1

    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._domain = domain


class OptionsFlow:
    """Mock OptionsFlow matching HA 2024.11+ behavior.

    config_entry is set by the framework after init, not passed to __init__.
    """

    def __init__(self) -> None:
        self._config_entry: ConfigEntry | None = None

    @property
    def config_entry(self) -> ConfigEntry:
        if self._config_entry is None:
            raise AttributeError(
                "config_entry is not available during __init__. "
                "It is set by the framework after initialization."
            )
        return self._config_entry

    @config_entry.setter
    def config_entry(self, value: ConfigEntry) -> None:
        self._config_entry = value