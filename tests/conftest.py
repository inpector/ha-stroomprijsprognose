"""Test fixtures and mocks for Stroomprijsprognose tests."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

# Inject mock homeassistant package before any real imports
_MOCKS_DIR = os.path.join(os.path.dirname(__file__), "mocks")
_COMPONENT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components"
)
sys.path.insert(0, _MOCKS_DIR)
sys.path.insert(0, _COMPONENT_DIR)

# ---------------------------------------------------------------------------
# Sample API response
# ---------------------------------------------------------------------------

NOW = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)


def build_sample_slot(
    hour_offset: int,
    price_source: str = "forecast",
    effective_ct_kwh: float = 5.0,
    forecast_model_ct_kwh: float = 4.5,
    day_ahead_ct_kwh: float | None = None,
    retail_total_ct_kwh: float = 26.0,
) -> dict:
    """Build a single API slot dict matching the real API shape."""
    ts = (NOW + timedelta(hours=hour_offset)).isoformat().replace("+00:00", ".000Z")
    return {
        "timestamp": ts,
        "effective_ct_kwh": effective_ct_kwh,
        "forecast_ct_kwh": effective_ct_kwh,
        "forecast_model_ct_kwh": forecast_model_ct_kwh,
        "day_ahead_ct_kwh": day_ahead_ct_kwh,
        "early_auction_ct_kwh": None,
        "price_source": price_source,
        "retail_total_ct_kwh": retail_total_ct_kwh,
        "retail_forecast_total_ct_kwh": effective_ct_kwh + 3.5,
        "retail_day_ahead_total_ct_kwh": retail_total_ct_kwh if day_ahead_ct_kwh is not None else None,
        "retail_early_auction_total_ct_kwh": None,
        "retail_effective_total_ct_kwh": retail_total_ct_kwh,
        "retail_price_source": price_source,
    }


@pytest.fixture
def sample_api_response() -> dict:
    """Build a 72-slot API response with known values."""
    slots = []
    for h in range(72):
        if h < 12:
            price = 20.0 + h * 0.5
            slots.append(
                build_sample_slot(
                    h,
                    price_source="day_ahead",
                    effective_ct_kwh=price - 3.5,
                    day_ahead_ct_kwh=price - 3.5,
                    retail_total_ct_kwh=price,
                )
            )
        else:
            price = 15.0 + (h - 12) * 0.3
            slots.append(
                build_sample_slot(
                    h,
                    price_source="forecast",
                    effective_ct_kwh=price - 3.5,
                    retail_total_ct_kwh=price,
                )
            )

    return {
        "api_version": "v1",
        "generated_at": NOW.isoformat(),
        "currency": "EUR",
        "unit": "ct/kWh",
        "timezone": "Europe/Berlin",
        "source": {
            "provider": "firestore",
            "collection": "TestData",
            "document": "TestDoc",
            "updated_at": NOW.isoformat(),
        },
        "request": {
            "hours": 72,
            "country": "DE",
            "plz": "66386",
            "postal_code": "66386",
            "include_current_day": False,
            "prefer_day_ahead": True,
        },
        "assumptions": {
            "country": "DE",
            "netzgebiet_id": "VNB_566",
            "netzgebiet_label": "Test Grid",
            "grid_fee_source": "plz_prefix_fallback",
            "supplier_markup_ct_kwh": 2.4,
            "levies_and_taxes_excl_vat_ct_kwh": 3.2,
            "vat_percent": 19,
        },
        "summary": {
            "slots": 72,
            "forecast_avg_ct_kwh": 6.39,
            "forecast_min_ct_kwh": -18.33,
            "forecast_max_ct_kwh": 15.57,
            "retail_avg_ct_kwh": 26.17,
            "retail_min_ct_kwh": 20.0,
            "retail_max_ct_kwh": 33.0,
        },
        "series": slots,
    }
