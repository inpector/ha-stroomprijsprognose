"""Config flow for the Stroomprijsprognose integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_COUNTRY,
    CONF_HOURS,
    CONF_PLZ,
    CONF_UPDATE_INTERVAL,
    COUNTRIES,
    DEFAULT_COUNTRY,
    DEFAULT_HOURS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_HOURS,
    MAX_UPDATE_INTERVAL,
    MIN_HOURS,
    MIN_UPDATE_INTERVAL,
)


class StroomprijsprognoseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Stroomprijsprognose."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate API connectivity before creating entry
            plz = user_input[CONF_PLZ]
            country = user_input[CONF_COUNTRY]
            valid = await self._test_api(plz, country)
            if not valid:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{country.lower()}_{plz}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Stroomprijsprognose {plz} ({country.upper()})",
                    data={
                        CONF_PLZ: plz,
                        CONF_COUNTRY: country,
                    },
                    options={
                        CONF_HOURS: DEFAULT_HOURS,
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                    },
                )

        data_schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of postal code or country."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        current_plz = entry.data.get(CONF_PLZ, "")
        current_country = entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)

        if user_input is not None:
            plz = user_input[CONF_PLZ]
            country = user_input[CONF_COUNTRY]
            valid = await self._test_api(plz, country)
            if not valid:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PLZ: plz,
                        CONF_COUNTRY: country,
                    },
                    reason="reconfigure_successful",
                )

        data_schema = vol.Schema({
            vol.Required(CONF_PLZ, default=current_plz): str,
            vol.Required(CONF_COUNTRY, default=current_country): vol.In(COUNTRIES),
        })

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> StroomprijsprognoseOptionsFlow:
        """Get the options flow for this handler."""
        return StroomprijsprognoseOptionsFlow(config_entry)

    async def _test_api(self, plz: str, country: str) -> bool:
        """Test if the API responds with valid data for given plz and country."""
        from .coordinator import StroomprijsprognoseCoordinator

        session = async_get_clientsession(self.hass)
        # Build a temporary coordinator just for connection testing
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        coord._session = session
        return await coord.test_api_connection(plz, country)  # noqa: SLF001


class StroomprijsprognoseOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Stroomprijsprognose."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        data_schema = vol.Schema({
            vol.Required(
                CONF_HOURS,
                default=options.get(CONF_HOURS, DEFAULT_HOURS),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_HOURS, max=MAX_HOURS)),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
            ),
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)