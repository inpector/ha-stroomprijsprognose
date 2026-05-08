"""Diagnostics support for Stroomprijsprognose."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT: list[str] = []


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator is None:
        return {"error": "no coordinator found"}

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
