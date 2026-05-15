"""Diagnostics support for Stroomprijsprognose."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import StroomprijsprognoseCoordinator

TO_REDACT: list[str] = []

# Use the typed config entry from __init__
StroomprijsprognoseConfigEntry = ConfigEntry[StroomprijsprognoseCoordinator]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: StroomprijsprognoseConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": entry.data,
            "options": entry.options,
        },
        "coordinator_data": coordinator.data,
        "last_update_success": coordinator.last_update_success,
        "last_update_time": coordinator.last_update_success_time.isoformat()
        if coordinator.last_update_success_time
        else None,
    }