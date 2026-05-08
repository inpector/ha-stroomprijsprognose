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
    VERSION = 1


class OptionsFlow:
    def __init__(self) -> None:
        pass
