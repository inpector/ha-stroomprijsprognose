"""Tests for sensor value extraction logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from stroomprijsprognose.sensor import SENSOR_DESCRIPTIONS, StroomprijsprognoseSensor

NOW = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)


def make_coordinator_mock(forecast_overrides: list[dict] | None = None) -> MagicMock:
    """Create a mock coordinator with realistic processed data."""
    if forecast_overrides is not None:
        forecast = forecast_overrides
    else:
        forecast = []
        for h in range(72):
            retail = 20.0 + h * 0.12
            forecast.append(
                {
                    "timestamp": NOW + timedelta(hours=h),
                    "retail_total_ct_kwh": retail,
                    "retail_total_ct_kwh_all": retail,
                    "retail_forecast_total_ct_kwh": retail - 2.0,
                    "retail_day_ahead_total_ct_kwh": retail if h < 12 else None,
                    "price_source": "day_ahead" if h < 12 else "forecast",
                }
            )

    # Compute derived values matching coordinator logic
    current_slot = forecast[0] if forecast else None
    next_slot = forecast[1] if len(forecast) > 1 else None

    # Price level: current is first slot (cheapest = 20.0, highest ~28.52)
    price_level = None
    price_percentage = None
    if current_slot and forecast:
        prices = sorted(s["retail_total_ct_kwh_all"] for s in forecast)
        lowest, highest = prices[0], prices[-1]
        current_price = current_slot["retail_total_ct_kwh_all"]
        if highest != lowest:
            pct = (current_price - lowest) / (highest - lowest) * 100
            if pct <= 20:
                price_level = "very_cheap"
            elif pct <= 40:
                price_level = "cheap"
            elif pct <= 60:
                price_level = "normal"
            elif pct <= 80:
                price_level = "expensive"
            else:
                price_level = "very_expensive"
        else:
            price_level = "normal"
        if highest > 0:
            price_percentage = current_price / highest * 100

    mock = MagicMock()
    mock.plz = "66386"
    mock.country = "DE"
    mock.data = {
        "generated_at": NOW.isoformat(),
        "currency": "EUR",
        "unit": "ct/kWh",
        "forecast": forecast,
        "current_slot": current_slot,
        "next_slot": next_slot,
        "price_level": price_level,
        "price_percentage": price_percentage,
        "last_updated": NOW,
        "summary": {
            "slots": len(forecast),
            "retail_avg_ct_kwh": 24.0,
        },
        "assumptions": {
            "country": "DE",
            "supplier_markup_ct_kwh": 2.4,
            "levies_and_taxes_excl_vat_ct_kwh": 3.2,
            "vat_percent": 19,
        },
        "cheapest_slots": sorted(
            forecast, key=lambda s: s["retail_total_ct_kwh_all"]
        )[:5],
        "most_expensive_slots": sorted(
            forecast, key=lambda s: s["retail_total_ct_kwh_all"], reverse=True
        )[:5],
        "lowest_next_8h": sorted(
            [s for s in forecast if s["timestamp"] <= NOW + timedelta(hours=8)],
            key=lambda s: s["retail_total_ct_kwh_all"],
        )[:3],
    }
    return mock


def make_sensor(
    sensor_key: str, coordinator: MagicMock | None = None
) -> StroomprijsprognoseSensor:
    """Create a sensor instance for testing."""
    if coordinator is None:
        coordinator = make_coordinator_mock()
    description = SENSOR_DESCRIPTIONS[sensor_key]
    return StroomprijsprognoseSensor(
        coordinator, "test_entry", sensor_key, description
    )


class TestCurrentPriceSensor:
    def test_returns_current_slot_retail(self) -> None:
        sensor = make_sensor("current_price")
        assert sensor.native_value == 20.0

    def test_no_data_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data = None
        sensor = make_sensor("current_price", coord)
        assert sensor.native_value is None

    def test_no_current_slot_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data["current_slot"] = None
        sensor = make_sensor("current_price", coord)
        assert sensor.native_value is None


class TestNextPriceSensor:
    def test_returns_next_slot_retail(self) -> None:
        sensor = make_sensor("next_price")
        assert sensor.native_value == 20.12

    def test_no_next_slot_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data["next_slot"] = None
        sensor = make_sensor("next_price", coord)
        assert sensor.native_value is None


class TestPriceLevelSensor:
    def test_returns_level(self) -> None:
        sensor = make_sensor("price_level")
        assert sensor.native_value in (
            "very_cheap", "cheap", "normal", "expensive", "very_expensive"
        )

    def test_no_data_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data = None
        sensor = make_sensor("price_level", coord)
        assert sensor.native_value is None


class TestPricePercentageSensor:
    def test_returns_percentage(self) -> None:
        sensor = make_sensor("price_percentage")
        assert sensor.native_value is not None
        assert 0 <= sensor.native_value <= 100

    def test_no_data_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data = None
        sensor = make_sensor("price_percentage", coord)
        assert sensor.native_value is None


class TestLastUpdatedSensor:
    def test_returns_timestamp(self) -> None:
        sensor = make_sensor("last_updated")
        assert sensor.native_value == NOW

    def test_no_data_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data = None
        sensor = make_sensor("last_updated", coord)
        assert sensor.native_value is None


class TestMinMaxAvgSensors:
    def test_lowest_price(self) -> None:
        sensor = make_sensor("lowest_price")
        assert sensor.native_value == 20.0

    def test_highest_price(self) -> None:
        sensor = make_sensor("highest_price")
        assert sensor.native_value == pytest.approx(28.52, 0.01)

    def test_average_price(self) -> None:
        sensor = make_sensor("average_price")
        expected = 20.0 + 0.12 * 71 / 2
        assert sensor.native_value == pytest.approx(expected, 0.01)

    def test_empty_forecast_returns_none(self) -> None:
        coord = make_coordinator_mock()
        coord.data["forecast"] = []
        coord.data["current_slot"] = None
        for key in ("lowest_price", "highest_price", "average_price"):
            sensor = make_sensor(key, coord)
            assert sensor.native_value is None


class TestTimestampSensors:
    def test_lowest_price_time(self) -> None:
        sensor = make_sensor("lowest_price_time")
        assert sensor.native_value == NOW

    def test_highest_price_time(self) -> None:
        sensor = make_sensor("highest_price_time")
        assert sensor.native_value == NOW + timedelta(hours=71)

    def test_lowest_next_8h_time(self) -> None:
        sensor = make_sensor("lowest_next_8h_price_time")
        assert sensor.native_value == NOW


class TestPriceSourceSensor:
    def test_day_ahead(self) -> None:
        sensor = make_sensor("price_source")
        assert sensor.native_value == "day_ahead"

    def test_forecast(self) -> None:
        coord = make_coordinator_mock()
        coord.data["current_slot"] = coord.data["forecast"][15]
        sensor = make_sensor("price_source", coord)
        assert sensor.native_value == "forecast"


class TestForecastSlotsSensor:
    def test_forecast_slot_count(self) -> None:
        sensor = make_sensor("forecast_slots")
        assert sensor.native_value == 60


class TestAttributes:
    def test_main_sensor_has_attributes(self) -> None:
        sensor = make_sensor("current_price")
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "hourly_prices" in attrs
        assert "cheapest_slots" in attrs
        assert "price_level" in attrs

    def test_non_main_sensor_has_no_attributes(self) -> None:
        for key in SENSOR_DESCRIPTIONS:
            if key == "current_price":
                continue
            sensor = make_sensor(key)
            assert sensor.extra_state_attributes is None

    def test_hourly_prices_timestamps_are_isoformat(self) -> None:
        sensor = make_sensor("current_price")
        attrs = sensor.extra_state_attributes
        for entry in attrs["hourly_prices"]:
            assert isinstance(entry["timestamp"], str)

    def test_attribute_summary_dict(self) -> None:
        sensor = make_sensor("current_price")
        attrs = sensor.extra_state_attributes
        assert isinstance(attrs["summary"], dict)


class TestUnitOfMeasurement:
    def test_price_sensor_unit(self) -> None:
        for key in (
            "current_price",
            "lowest_price",
            "highest_price",
            "average_price",
            "next_price",
        ):
            sensor = make_sensor(key)
            assert sensor.native_unit_of_measurement == "ct/kWh"

    def test_price_source_no_unit(self) -> None:
        sensor = make_sensor("price_source")
        assert sensor.native_unit_of_measurement is None

    def test_price_level_no_unit(self) -> None:
        sensor = make_sensor("price_level")
        assert sensor.native_unit_of_measurement is None

    def test_forecast_slots_unit(self) -> None:
        sensor = make_sensor("forecast_slots")
        assert sensor.native_unit_of_measurement == "h"

    def test_price_percentage_unit(self) -> None:
        sensor = make_sensor("price_percentage")
        assert sensor.native_unit_of_measurement == "%"

    def test_timestamp_sensors_no_unit(self) -> None:
        for key in (
            "lowest_price_time",
            "highest_price_time",
            "lowest_next_8h_price_time",
            "last_updated",
        ):
            sensor = make_sensor(key)
            assert sensor.native_unit_of_measurement is None


class TestEntityCategories:
    def test_diagnostic_sensors_have_category(self) -> None:
        from homeassistant.helpers.entity import EntityCategory
        diagnostic_keys = {
            "current_forecast_price",
            "current_day_ahead_price",
            "price_source",
            "forecast_slots",
            "last_updated",
        }
        for key in diagnostic_keys:
            desc = SENSOR_DESCRIPTIONS[key]
            assert desc.entity_category == EntityCategory.DIAGNOSTIC, (
                f"{key} should have DIAGNOSTIC entity category"
            )

    def test_primary_sensors_have_no_category(self) -> None:
        primary_keys = {
            "current_price", "next_price", "lowest_price", "highest_price",
            "average_price", "price_level", "lowest_price_time",
            "highest_price_time", "lowest_next_8h_price_time", "price_percentage",
        }
        for key in primary_keys:
            desc = SENSOR_DESCRIPTIONS[key]
            assert desc.entity_category is None, (
                f"{key} should have no entity category"
            )