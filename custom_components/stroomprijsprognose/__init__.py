"""Stroomprijsprognose electricity price forecast integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_COUNTRY,
    CONF_HOURS,
    CONF_PLZ,
    CONF_UPDATE_INTERVAL,
    DEFAULT_HOURS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import StroomprijsprognoseCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Typed ConfigEntry with runtime_data holding the coordinator
type StroomprijsprognoseConfigEntry = ConfigEntry[StroomprijsprognoseCoordinator]

# Service schemas (defined once at module level)
FORCE_REFRESH_SCHEMA = vol.Schema({
    vol.Optional("entry_id"): str,
})
GET_PRICES_SCHEMA = vol.Schema({
    vol.Optional("entry_id"): str,
})


async def async_setup_entry(hass: HomeAssistant, entry: StroomprijsprognoseConfigEntry) -> bool:
    """Set up Stroomprijsprognose from a config entry."""
    plz: str = entry.data[CONF_PLZ]
    country: str = entry.data[CONF_COUNTRY]
    hours: int = entry.options.get(CONF_HOURS, entry.data.get(CONF_HOURS, DEFAULT_HOURS))
    update_interval: int = entry.options.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
    )

    coordinator = StroomprijsprognoseCoordinator(
        hass=hass,
        entry=entry,
        plz=plz,
        country=country,
        hours=hours,
        update_interval=update_interval,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        from homeassistant.exceptions import ConfigEntryNotReady
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {err}") from err

    # Modern runtime_data pattern replaces hass.data[DOMAIN]
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register services once (idempotent — HA ignores duplicate registration)
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: StroomprijsprognoseConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and not _all_coordinators(hass):
        hass.services.async_remove(DOMAIN, "force_refresh")
        hass.services.async_remove(DOMAIN, "get_prices")
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: StroomprijsprognoseConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services. Called from async_setup_entry.

    Uses hass.data to track registration and avoid duplicate calls.
    Services are removed in async_unload_entry when the last entry is removed.
    """
    if hass.data.get(f"{DOMAIN}_services_registered"):
        return
    hass.data[f"{DOMAIN}_services_registered"] = True

    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle force_refresh service call.

        Sets the force-refresh flag to bypass cache on next update,
        then triggers an immediate refresh.
        """
        entry_id = call.data.get("entry_id")
        if entry_id:
            coord = _get_coordinator(hass, entry_id)
            coord.request_force_refresh()
            await coord.async_request_refresh()
        else:
            for coord in _all_coordinators(hass):
                coord.request_force_refresh()
                await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "force_refresh", handle_force_refresh, schema=FORCE_REFRESH_SCHEMA
    )

    async def handle_get_prices(call: ServiceCall) -> dict[str, Any]:
        """Return cached forecast price data as a service response.

        Enables template sensors, dashboard charts, and automations
        that need access to the raw price data.
        """
        entry_id = call.data.get("entry_id")
        coord = _get_coordinator_or_any(hass, entry_id)
        if coord is None or not coord.data:
            raise _service_validation_error(f"No price data available for {DOMAIN}")

        data = coord.data
        forecast = data.get("forecast", [])
        return {
            "generated_at": data.get("generated_at"),
            "currency": data.get("currency"),
            "unit": data.get("unit"),
            "plz": coord.plz,
            "country": coord.country,
            "prices": [
                {
                    "timestamp": s["timestamp"].isoformat(),
                    "retail_total_ct_kwh": s["retail_total_ct_kwh_all"],
                    "price_source": s["price_source"],
                }
                for s in forecast
            ],
        }

    # supports_response requires HA 2024.8+
    try:
        from homeassistant.core import SupportsService
        hass.services.async_register(
            DOMAIN, "get_prices", handle_get_prices,
            schema=GET_PRICES_SCHEMA, supports_response=SupportsService.ONLY,
        )
    except (ImportError, TypeError):
        # Fallback for older HA: register without supports_response
        hass.services.async_register(
            DOMAIN, "get_prices", handle_get_prices, schema=GET_PRICES_SCHEMA,
        )


def _service_validation_error(message: str) -> Exception:
    """Create a ServiceValidationError if available, else ValueError."""
    try:
        from homeassistant.exceptions import ServiceValidationError
        return ServiceValidationError(message)
    except ImportError:
        return ValueError(message)


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> StroomprijsprognoseCoordinator:
    """Get coordinator by entry_id, raising if not found."""
    entries = hass.config_entries.async_entries(DOMAIN)
    for e in entries:
        if e.entry_id == entry_id:
            return e.runtime_data
    raise _service_validation_error(f"Entry {entry_id} not found")


def _get_coordinator_or_any(
    hass: HomeAssistant, entry_id: str | None
) -> StroomprijsprognoseCoordinator | None:
    """Get coordinator by entry_id, or any coordinator if entry_id is None."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return None
    if entry_id:
        for e in entries:
            if e.entry_id == entry_id:
                return e.runtime_data
        return None
    return entries[0].runtime_data


def _all_coordinators(hass: HomeAssistant) -> list[StroomprijsprognoseCoordinator]:
    """Return all active coordinators."""
    return [e.runtime_data for e in hass.config_entries.async_entries(DOMAIN)]