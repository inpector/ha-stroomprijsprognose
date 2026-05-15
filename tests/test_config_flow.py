"""Tests for config flow schema validation and options flow structure."""

from __future__ import annotations

import pytest
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from stroomprijsprognose.config_flow import (
    StroomprijsprognoseConfigFlow,
    StroomprijsprognoseOptionsFlow,
)
from stroomprijsprognose.const import (
    CONF_COUNTRY,
    CONF_HOURS,
    CONF_PLZ,
    CONF_UPDATE_INTERVAL,
    COUNTRIES,
    DEFAULT_COUNTRY,
    DEFAULT_HOURS,
    DEFAULT_UPDATE_INTERVAL,
)


class TestUserStepSchema:
    def test_valid_input(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        result = schema({"plz": "66386", "country": "DE"})
        assert result["plz"] == "66386"
        assert result["country"] == "DE"

    def test_default_country(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        result = schema({"plz": "10115"})
        assert result["country"] == "DE"

    def test_invalid_country_rejected(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        with pytest.raises(vol.Invalid):
            schema({"plz": "12345", "country": "US"})

    def test_missing_plz_rejected(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        with pytest.raises(vol.Invalid):
            schema({"country": "DE"})

    def test_plz_as_number_rejected(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        with pytest.raises(vol.Invalid):
            schema({"plz": 66386})

    def test_all_countries_accepted(self) -> None:
        schema = vol.Schema({
            vol.Required(CONF_PLZ): str,
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
        })
        for country in COUNTRIES:
            result = schema({"plz": "12345", "country": country})
            assert result["country"] == country


class TestOptionsFlowSchema:
    def test_valid_options(self) -> None:
        schema = vol.Schema({
            vol.Optional(CONF_HOURS, default=DEFAULT_HOURS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=96)
            ),
            vol.Optional(
                CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
        })
        result = schema({"hours": "24", "update_interval": "10"})
        assert result["hours"] == 24
        assert result["update_interval"] == 10

    def test_defaults(self) -> None:
        schema = vol.Schema({
            vol.Optional(CONF_HOURS, default=DEFAULT_HOURS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=96)
            ),
            vol.Optional(
                CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
        })
        result = schema({})
        assert result["hours"] == DEFAULT_HOURS
        assert result["update_interval"] == DEFAULT_UPDATE_INTERVAL

    def test_hours_out_of_range(self) -> None:
        schema = vol.Schema({
            vol.Optional(CONF_HOURS, default=DEFAULT_HOURS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=96)
            ),
        })
        with pytest.raises(vol.Invalid):
            schema({"hours": "100"})

    def test_update_interval_out_of_range(self) -> None:
        schema = vol.Schema({
            vol.Optional(
                CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
        })
        with pytest.raises(vol.Invalid):
            schema({"update_interval": "1"})


class TestOptionsFlowInit:
    """Tests for OptionsFlow initialization (HA 2024.11+ pattern)."""

    def test_options_flow_init_takes_no_args(self) -> None:
        """OptionsFlow must not require config_entry in __init__.

        HA 2024.11+ sets config_entry after init. Passing it manually
        causes a 500 error in newer HA versions.
        """
        flow = StroomprijsprognoseOptionsFlow()
        assert flow is not None

    def test_options_flow_config_entry_set_by_framework(self) -> None:
        """config_entry should be settable after construction (framework behavior)."""
        flow = StroomprijsprognoseOptionsFlow()
        entry = ConfigEntry()
        entry.options = {"hours": 48, "update_interval": 10}
        # Framework sets config_entry after init
        flow.config_entry = entry
        assert flow.config_entry is entry
        assert flow.config_entry.options["hours"] == 48

    def test_options_flow_access_before_set_raises(self) -> None:
        """Accessing config_entry before framework sets it must raise."""
        flow = StroomprijsprognoseOptionsFlow()
        with pytest.raises(AttributeError):
            _ = flow.config_entry

    def test_get_options_flow_returns_instance(self) -> None:
        """async_get_options_flow should return an OptionsFlow instance
        without requiring config_entry as constructor argument."""
        result = StroomprijsprognoseConfigFlow.async_get_options_flow(
            ConfigEntry()
        )
        assert isinstance(result, OptionsFlow)
        assert isinstance(result, StroomprijsprognoseOptionsFlow)
