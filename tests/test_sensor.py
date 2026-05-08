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

    mock = MagicMock()
    mock.plz = "66386"
    mock.country = "de"
    mock.data = {
        "generated_at": NOW.isoformat(),
        "currency": "EUR",
        "unit": "ct/kWh",
        "forecast": forecast,
        "current_slot": forecast[0] if forecast else None,
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
        assert sensor.native_value == NOW.isoformat()

    def test_highest_price_time(self) -> None:
        sensor = make_sensor("highest_price_time")
        assert sensor.native_value == (NOW + timedelta(hours=71)).isoformat()

    def test_lowest_next_8h_time(self) -> None:
        sensor = make_sensor("lowest_next_8h_price_time")
        assert sensor.native_value == NOW.isoformat()


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
        ):
            sensor = make_sensor(key)
            assert sensor.native_unit_of_measurement == "ct/kWh"

    def test_price_source_no_unit(self) -> None:
        sensor = make_sensor("price_source")
        assert sensor.native_unit_of_measurement is None

    def test_forecast_slots_unit(self) -> None:
        sensor = make_sensor("forecast_slots")
        assert sensor.native_unit_of_measurement == "h"

    def test_timestamp_sensors_no_unit(self) -> None:
        for key in (
            "lowest_price_time",
            "highest_price_time",
            "lowest_next_8h_price_time",
        ):
            sensor = make_sensor(key)
            assert sensor.native_unit_of_measurement is None
