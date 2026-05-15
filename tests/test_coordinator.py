"""Tests for StroomprijsprognoseCoordinator data processing and caching logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from stroomprijsprognose.coordinator import StroomprijsprognoseCoordinator

NOW = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)


def process_api_data(api_data: dict) -> dict:
    """Call _process_api_data on raw API response with monkeypatched utcnow."""
    coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
    from homeassistant.util import dt as mock_dt

    with patch.object(mock_dt, "utcnow", return_value=NOW):
        return coord._process_api_data(api_data, NOW)


class TestProcessApiData:
    """Tests for _process_api_data raw API → structured data."""

    def test_forecast_slot_count(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert len(result["forecast"]) == 72

    def test_slot_timestamps_are_datetime(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        for s in result["forecast"]:
            assert isinstance(s["timestamp"], datetime)

    def test_price_source_day_ahead(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        for s in result["forecast"][:12]:
            assert s["price_source"] == "day_ahead"

    def test_price_source_forecast(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        for s in result["forecast"][12:]:
            assert s["price_source"] == "forecast"

    def test_current_slot_found(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["current_slot"] is not None
        assert result["current_slot"]["timestamp"] == NOW

    def test_cheapest_slots_sorted(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        prices = [s["retail_total_ct_kwh_all"] for s in result["cheapest_slots"]]
        assert prices == sorted(prices)
        assert len(result["cheapest_slots"]) == 5

    def test_most_expensive_slots_sorted(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        prices = [s["retail_total_ct_kwh_all"] for s in result["most_expensive_slots"]]
        assert prices == sorted(prices, reverse=True)

    def test_lowest_next_8h_non_empty(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert len(result["lowest_next_8h"]) >= 1
        cutoff = NOW + timedelta(hours=8)
        for s in result["lowest_next_8h"]:
            assert s["timestamp"] >= NOW
            assert s["timestamp"] <= cutoff

    def test_summary_preserved(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["summary"]["slots"] == 72

    def test_assumptions_preserved(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["assumptions"]["country"] == "DE"
        assert result["assumptions"]["vat_percent"] == 19

    def test_prices_are_float(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        for s in result["forecast"]:
            assert isinstance(s["retail_total_ct_kwh_all"], float)

    def test_invalid_response_missing_series(self) -> None:
        bad_data = {"api_version": "v1"}
        with pytest.raises(KeyError):
            process_api_data(bad_data)


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


class TestNeedsApiFetch:
    """Tests for _needs_api_fetch cache decision logic."""

    def _make_coordinator(self) -> StroomprijsprognoseCoordinator:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        coord._update_interval_minutes = 15
        coord._cached_processed = None
        coord._last_api_fetch = None
        coord._last_fetch_hour = None
        coord._force_refresh = False
        return coord

    def test_needs_fetch_when_no_cache(self) -> None:
        coord = self._make_coordinator()
        assert coord._needs_api_fetch(NOW) is True

    def test_needs_fetch_when_force_refresh_set(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = NOW.hour
        coord._force_refresh = True
        assert coord._needs_api_fetch(NOW) is True

    def test_no_fetch_within_interval_same_hour(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = NOW.hour
        coord._force_refresh = False
        # 10 minutes later, same hour, interval not elapsed
        later = NOW + timedelta(minutes=10)
        assert coord._needs_api_fetch(later) is False

    def test_needs_fetch_after_interval_elapsed(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = NOW.hour
        coord._force_refresh = False
        # 20 minutes later, same hour, but interval (15 min) elapsed
        later = NOW + timedelta(minutes=20)
        assert coord._needs_api_fetch(later) is True

    def test_needs_fetch_after_hour_boundary_with_grace(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW  # 12:00
        coord._last_fetch_hour = 12
        coord._force_refresh = False
        # 13:06 — hour boundary crossed, past grace period (300s = 5min)
        later = NOW + timedelta(hours=1, minutes=6)
        assert coord._needs_api_fetch(later) is True

    def test_no_fetch_within_grace_after_hour_boundary(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW  # 12:00
        coord._last_fetch_hour = 12
        coord._force_refresh = False
        # 13:03 — hour boundary crossed, but within grace period (300s)
        later = NOW + timedelta(hours=1, minutes=3)
        assert coord._needs_api_fetch(later) is False


class TestRecomputeDerived:
    """Tests for _recompute_derived time-dependent recomputation."""

    def test_current_slot_updates_on_hour_boundary(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result_12 = coord._process_api_data(sample_api_response, NOW)
        assert result_12["current_slot"]["timestamp"] == NOW

        # One hour later, current_slot should shift
        later = NOW + timedelta(hours=1)
        result_13 = coord._recompute_derived(result_12, later)
        assert result_13["current_slot"]["timestamp"] == later

    def test_forecast_list_preserved(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result = coord._process_api_data(sample_api_response, NOW)
        recomputed = coord._recompute_derived(result, NOW)
        assert recomputed["forecast"] is result["forecast"]
        assert len(recomputed["forecast"]) == 72

    def test_summary_preserved(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result = coord._process_api_data(sample_api_response, NOW)
        recomputed = coord._recompute_derived(result, NOW)
        assert recomputed["summary"] == result["summary"]

    def test_lowest_next_8h_shifts_with_time(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result = coord._process_api_data(sample_api_response, NOW)
        later = NOW + timedelta(hours=4)
        recomputed = coord._recompute_derived(result, later)
        # After shifting 4 hours forward, the 8h window is different
        cutoff = later + timedelta(hours=8)
        for s in recomputed["lowest_next_8h"]:
            assert s["timestamp"] >= later
            assert s["timestamp"] <= cutoff

    def test_force_refresh_clears_flag(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        coord._force_refresh = False
        coord.request_force_refresh()
        assert coord._force_refresh is True