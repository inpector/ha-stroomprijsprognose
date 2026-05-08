"""Stroomprijsprognose electricity price forecast integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_COUNTRY,
    CONF_HOURS,
    CONF_PLZ,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import StroomprijsprognoseCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Stroomprijsprognose from a config entry."""
    plz: str = entry.data[CONF_PLZ]
    country: str = entry.data[CONF_COUNTRY]
    hours: int = entry.options.get(CONF_HOURS, entry.data.get(CONF_HOURS, 72))
    update_interval: int = entry.options.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
    )

    coordinator = StroomprijsprognoseCoordinator(
        hass=hass,
        update_interval=update_interval,
        plz=plz,
        country=country,
        hours=hours,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register services
    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle force_refresh service call."""
        entry_id = call.data.get("entry_id")
        if entry_id and entry_id in hass.data.get(DOMAIN, {}):
            await hass.data[DOMAIN][entry_id].async_request_refresh()
        elif not entry_id:
            for coord in hass.data.get(DOMAIN, {}).values():
                await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "force_refresh", handle_force_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "force_refresh")
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
