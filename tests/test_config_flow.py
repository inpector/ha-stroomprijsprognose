"""Tests for config flow schema validation."""

from __future__ import annotations

import pytest
import voluptuous as vol

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
