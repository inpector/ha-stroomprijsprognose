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

    def test_next_slot_found(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["next_slot"] is not None
        assert result["next_slot"]["timestamp"] == NOW + timedelta(hours=1)

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

    def test_price_level_computed(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["price_level"] in (
            "very_cheap", "cheap", "normal", "expensive", "very_expensive"
        )

    def test_price_percentage_computed(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["price_percentage"] is not None
        assert 0 <= result["price_percentage"] <= 100

    def test_last_updated_computed(self, sample_api_response: dict) -> None:
        result = process_api_data(sample_api_response)
        assert result["last_updated"] == NOW


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


class TestFindNextSlot:
    """Tests for _find_next_slot static method."""

    def test_exact_next_hour(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 25.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 26.0, "price_source": "day_ahead"},
        ]
        result = StroomprijsprognoseCoordinator._find_next_slot(forecast, NOW)
        assert result is not None
        assert result["retail_total_ct_kwh_all"] == 26.0

    def test_fallback_first_after_now(self) -> None:
        forecast = [
            {"timestamp": NOW + timedelta(hours=2), "retail_total_ct_kwh_all": 28.0, "price_source": "forecast"},
        ]
        result = StroomprijsprognoseCoordinator._find_next_slot(forecast, NOW)
        assert result is not None
        assert result["retail_total_ct_kwh_all"] == 28.0

    def test_empty_forecast_returns_none(self) -> None:
        result = StroomprijsprognoseCoordinator._find_next_slot([], NOW)
        assert result is None


class TestPriceLevel:
    """Tests for _compute_price_level static method."""

    def test_lowest_price_is_very_cheap(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 10.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 50.0, "price_source": "day_ahead"},
        ]
        current = {"retail_total_ct_kwh_all": 10.0}
        result = StroomprijsprognoseCoordinator._compute_price_level(forecast, current)
        assert result == "very_cheap"

    def test_highest_price_is_very_expensive(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 10.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 50.0, "price_source": "day_ahead"},
        ]
        current = {"retail_total_ct_kwh_all": 50.0}
        result = StroomprijsprognoseCoordinator._compute_price_level(forecast, current)
        assert result == "very_expensive"

    def test_equal_prices_is_normal(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 25.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 25.0, "price_source": "day_ahead"},
        ]
        current = {"retail_total_ct_kwh_all": 25.0}
        result = StroomprijsprognoseCoordinator._compute_price_level(forecast, current)
        assert result == "normal"

    def test_no_current_slot_returns_none(self) -> None:
        result = StroomprijsprognoseCoordinator._compute_price_level([], None)
        assert result is None

    def test_empty_forecast_returns_none(self) -> None:
        result = StroomprijsprognoseCoordinator._compute_price_level([], {"retail_total_ct_kwh_all": 10.0})
        assert result is None


class TestPricePercentage:
    """Tests for _compute_price_percentage static method."""

    def test_max_price_is_100(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 10.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 50.0, "price_source": "day_ahead"},
        ]
        current = {"retail_total_ct_kwh_all": 50.0}
        result = StroomprijsprognoseCoordinator._compute_price_percentage(forecast, current)
        assert result == 100.0

    def test_half_price_is_50(self) -> None:
        forecast = [
            {"timestamp": NOW, "retail_total_ct_kwh_all": 0.0, "price_source": "day_ahead"},
            {"timestamp": NOW + timedelta(hours=1), "retail_total_ct_kwh_all": 100.0, "price_source": "day_ahead"},
        ]
        current = {"retail_total_ct_kwh_all": 50.0}
        result = StroomprijsprognoseCoordinator._compute_price_percentage(forecast, current)
        assert result == 50.0

    def test_no_current_slot_returns_none(self) -> None:
        result = StroomprijsprognoseCoordinator._compute_price_percentage([], None)
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
        later = NOW + timedelta(minutes=10)
        assert coord._needs_api_fetch(later) is False

    def test_needs_fetch_after_interval_elapsed(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = NOW.hour
        coord._force_refresh = False
        later = NOW + timedelta(minutes=20)
        assert coord._needs_api_fetch(later) is True

    def test_needs_fetch_after_hour_boundary_with_grace(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = 12
        coord._force_refresh = False
        later = NOW + timedelta(hours=1, minutes=6)
        assert coord._needs_api_fetch(later) is True

    def test_no_fetch_within_grace_after_hour_boundary(self) -> None:
        coord = self._make_coordinator()
        coord._cached_processed = {"forecast": []}
        coord._last_api_fetch = NOW
        coord._last_fetch_hour = 12
        coord._force_refresh = False
        later = NOW + timedelta(hours=1, minutes=3)
        assert coord._needs_api_fetch(later) is False


class TestRecomputeDerived:
    """Tests for _recompute_derived time-dependent recomputation."""

    def test_current_slot_updates_on_hour_boundary(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result_12 = coord._process_api_data(sample_api_response, NOW)
        assert result_12["current_slot"]["timestamp"] == NOW

        later = NOW + timedelta(hours=1)
        result_13 = coord._recompute_derived(result_12, later)
        assert result_13["current_slot"]["timestamp"] == later

    def test_next_slot_updates_on_hour_boundary(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result_12 = coord._process_api_data(sample_api_response, NOW)
        assert result_12["next_slot"]["timestamp"] == NOW + timedelta(hours=1)

        later = NOW + timedelta(hours=1)
        result_13 = coord._recompute_derived(result_12, later)
        assert result_13["next_slot"]["timestamp"] == NOW + timedelta(hours=2)

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
        cutoff = later + timedelta(hours=8)
        for s in recomputed["lowest_next_8h"]:
            assert s["timestamp"] >= later
            assert s["timestamp"] <= cutoff

    def test_force_refresh_clears_flag(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        coord._force_refresh = False
        coord.request_force_refresh()
        assert coord._force_refresh is True

    def test_price_level_recomputed(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result = coord._process_api_data(sample_api_response, NOW)
        assert "price_level" in result
        assert result["price_level"] in (
            "very_cheap", "cheap", "normal", "expensive", "very_expensive"
        )

    def test_last_updated_recomputed(self, sample_api_response: dict) -> None:
        coord = StroomprijsprognoseCoordinator.__new__(StroomprijsprognoseCoordinator)
        result = coord._process_api_data(sample_api_response, NOW)
        later = NOW + timedelta(minutes=10)
        recomputed = coord._recompute_derived(result, later)
        assert recomputed["last_updated"] == later