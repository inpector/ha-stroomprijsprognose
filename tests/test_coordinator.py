"""Tests for StroomprijsprognoseCoordinator data processing logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from stroomprijsprognose.coordinator import StroomprijsprognoseCoordinator

NOW = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)


def process_data(api_data: dict) -> dict:
    """Call _process_data on raw API response with monkeypatched utcnow."""
    coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
    from homeassistant.util import dt as mock_dt

    with patch.object(mock_dt, "utcnow", return_value=NOW):
        return coord._process_data(api_data)


class TestProcessData:
    """Tests for _process_data raw API → structured data."""

    def test_forecast_slot_count(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        assert len(result["forecast"]) == 72

    def test_slot_timestamps_are_datetime(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        for s in result["forecast"]:
            assert isinstance(s["timestamp"], datetime)

    def test_price_source_day_ahead(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        for s in result["forecast"][:12]:
            assert s["price_source"] == "day_ahead"

    def test_price_source_forecast(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        for s in result["forecast"][12:]:
            assert s["price_source"] == "forecast"

    def test_current_slot_found(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        assert result["current_slot"] is not None
        assert result["current_slot"]["timestamp"] == NOW

    def test_cheapest_slots_sorted(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        prices = [s["retail_total_ct_kwh_all"] for s in result["cheapest_slots"]]
        assert prices == sorted(prices)
        assert len(result["cheapest_slots"]) == 5

    def test_most_expensive_slots_sorted(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        prices = [s["retail_total_ct_kwh_all"] for s in result["most_expensive_slots"]]
        assert prices == sorted(prices, reverse=True)

    def test_lowest_next_8h_non_empty(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        assert len(result["lowest_next_8h"]) >= 1
        cutoff = NOW + timedelta(hours=8)
        for s in result["lowest_next_8h"]:
            assert s["timestamp"] >= NOW
            assert s["timestamp"] <= cutoff

    def test_summary_preserved(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        assert result["summary"]["slots"] == 72

    def test_assumptions_preserved(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        assert result["assumptions"]["country"] == "DE"
        assert result["assumptions"]["vat_percent"] == 19

    def test_prices_are_float(self, sample_api_response: dict) -> None:
        result = process_data(sample_api_response)
        for s in result["forecast"]:
            assert isinstance(s["retail_total_ct_kwh_all"], float)

    def test_invalid_response_missing_series(self) -> None:
        bad_data = {"api_version": "v1"}
        with pytest.raises(KeyError):
            process_data(bad_data)


class TestFindCurrentSlot:
    """Tests for _find_current_slot static method."""

    def test_exact_match(self) -> None:
        forecast = [
            {
                "timestamp": datetime(2026, 5, 8, 11, 0, 0, tzinfo=timezone.utc),
                "retail_total_ct_kwh_all": 25.0,
                "price_source": "day_ahead",
            },
            {
                "timestamp": datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
                "retail_total_ct_kwh_all": 26.0,
                "price_source": "day_ahead",
            },
        ]
        result = StroomprijsprognoseCoordinator._find_current_slot(forecast, NOW)
        assert result is not None
        assert result["retail_total_ct_kwh_all"] == 26.0

    def test_fallback_closest(self) -> None:
        forecast = [
            {
                "timestamp": datetime(2026, 5, 8, 12, 15, 0, tzinfo=timezone.utc),
                "retail_total_ct_kwh_all": 26.0,
                "price_source": "day_ahead",
            },
        ]
        result = StroomprijsprognoseCoordinator._find_current_slot(forecast, NOW)
        assert result is not None

    def test_fallback_first_slot(self) -> None:
        forecast = [
            {
                "timestamp": datetime(2026, 5, 9, 0, 0, 0, tzinfo=timezone.utc),
                "retail_total_ct_kwh_all": 30.0,
                "price_source": "forecast",
            },
        ]
        result = StroomprijsprognoseCoordinator._find_current_slot(forecast, NOW)
        assert result is not None
        assert result["retail_total_ct_kwh_all"] == 30.0

    def test_empty_forecast_returns_none(self) -> None:
        result = StroomprijsprognoseCoordinator._find_current_slot([], NOW)
        assert result is None
