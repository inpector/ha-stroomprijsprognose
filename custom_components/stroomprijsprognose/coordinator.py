"""DataUpdateCoordinator for Stroomprijsprognose API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import API_CACHE_GRACE_SECONDS, API_TIMEOUT_SECONDS, BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class StroomprijsprognoseCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch electricity price forecasts.

    Uses smart caching: full API calls happen at the configured update interval
    or when an hour boundary is crossed. Between full fetches, derived values
    (current_slot, lowest_next_8h) are recomputed from cached forecast data
    without hitting the API.
    """

    config_entry: Any  # ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        plz: str,
        country: str,
        hours: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval),
        )
        self.plz = plz
        self.country = country.upper()
        self.hours = hours
        self._update_interval_minutes = update_interval
        self._session = async_get_clientsession(hass)

        # Cache state
        self._last_api_fetch: datetime | None = None
        self._last_fetch_hour: int | None = None
        self._cached_processed: dict[str, Any] | None = None
        self._force_refresh: bool = False

    def request_force_refresh(self) -> None:
        """Mark that the next update must bypass cache and fetch from API."""
        self._force_refresh = True

    def _needs_api_fetch(self, now: datetime) -> bool:
        """Determine whether a full API fetch is needed.

        Fetches from API when:
        - No cached data exists (first run)
        - Force refresh was requested
        - An hour boundary was crossed and past the grace period
        - The configured update_interval has elapsed since last fetch
          (but not during grace period after hour boundary)

        Within the grace period after an hour boundary, we recompute
        derived values from cache instead of hitting the API.
        """
        if self._cached_processed is None:
            return True
        if self._force_refresh:
            return True
        if self._last_api_fetch is None:
            return True

        # Hour boundary crossed: check grace period
        current_hour = now.hour
        if self._last_fetch_hour is not None and current_hour != self._last_fetch_hour:
            seconds_into_hour = now.minute * 60 + now.second
            if seconds_into_hour < API_CACHE_GRACE_SECONDS:
                # Within grace period — recompute from cache
                return False
            # Past grace period — fetch fresh data
            return True

        # No hour boundary: normal interval check
        elapsed = (now - self._last_api_fetch).total_seconds()
        if elapsed >= self._update_interval_minutes * 60:
            return True

        return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API or recompute derived values from cache."""
        now = dt_util.utcnow()

        if self._needs_api_fetch(now):
            raw = await self._fetch_api_data()
            self._cached_processed = self._process_api_data(raw, now)
            self._last_api_fetch = now
            self._last_fetch_hour = now.hour
            self._force_refresh = False
            return self._cached_processed

        # Recompute time-dependent derived values from cached forecast
        return self._recompute_derived(self._cached_processed, now)

    async def _fetch_api_data(self) -> dict[str, Any]:
        """Fetch raw data from the API endpoint."""
        url = (
            f"{BASE_URL}/api/v1/hourly-forecast"
            f"?hours={self.hours}&country={self.country.lower()}&plz={self.plz}"
        )

        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS):
                response = await self._session.get(url)
                response.raise_for_status()
                data = await response.json()
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching data from {url}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        if "series" not in data or "summary" not in data:
            raise UpdateFailed("Invalid API response: missing series or summary")

        return data

    def _process_api_data(self, data: dict[str, Any], now: datetime) -> dict[str, Any]:
        """Process raw API data into structured format."""
        series: list[dict[str, Any]] = data["series"]
        summary: dict[str, Any] = data["summary"]
        assumptions: dict[str, Any] = data.get("assumptions", {})

        # Map API fields to internal keys; retail_total_ct_kwh_all is the
        # all-inclusive retail price (grid fees + taxes + markup) used for
        # cheapest/most-expensive ranking and sensor display.
        forecast: list[dict[str, Any]] = []
        for slot in series:
            ts_raw = slot["timestamp"]
            ts = dt_util.parse_datetime(ts_raw) or datetime.fromisoformat(
                ts_raw.replace("Z", "+00:00")
            )
            forecast.append({
                "timestamp": ts,
                "price_ct_kwh": slot["effective_ct_kwh"],
                "forecast_ct_kwh": slot["forecast_model_ct_kwh"],
                "day_ahead_ct_kwh": slot.get("day_ahead_ct_kwh"),
                "early_auction_ct_kwh": slot.get("early_auction_ct_kwh"),
                "retail_total_ct_kwh": slot["retail_effective_total_ct_kwh"],
                "retail_forecast_total_ct_kwh": slot["retail_forecast_total_ct_kwh"],
                "retail_day_ahead_total_ct_kwh": slot.get("retail_day_ahead_total_ct_kwh"),
                "retail_early_auction_total_ct_kwh": slot.get("retail_early_auction_total_ct_kwh"),
                "retail_total_ct_kwh_all": slot["retail_total_ct_kwh"],
                "price_source": slot["price_source"],
            })

        return {
            "generated_at": data.get("generated_at"),
            "currency": data["currency"],
            "unit": data["unit"],
            "forecast": forecast,
            "summary": summary,
            "assumptions": assumptions,
            **self._compute_derived(forecast, now),
        }

    def _recompute_derived(self, cached: dict[str, Any], now: datetime) -> dict[str, Any]:
        """Recompute time-dependent derived values from cached forecast data.

        Only current_slot and lowest_next_8h change between API calls
        (they depend on the current time). Forecast list, summary,
        assumptions, and rankings remain stable.
        """
        forecast = cached.get("forecast", [])
        return {
            "generated_at": cached.get("generated_at"),
            "currency": cached.get("currency"),
            "unit": cached.get("unit"),
            "forecast": forecast,
            "summary": cached.get("summary", {}),
            "assumptions": cached.get("assumptions", {}),
            **self._compute_derived(forecast, now),
        }

    @staticmethod
    def _compute_derived(forecast: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
        """Compute all derived values from forecast and current time."""
        current_slot = StroomprijsprognoseCoordinator._find_current_slot(forecast, now)

        # Top-5 cheapest and most expensive slots (descending for most-expensive)
        sorted_by_price = sorted(forecast, key=lambda s: s["retail_total_ct_kwh_all"])
        cheapest_5 = sorted_by_price[:5]
        most_expensive_5 = sorted_by_price[-5:][::-1]

        # Lowest in next 8 hours
        cutoff = now + timedelta(hours=8)
        next_8h = [s for s in forecast if s["timestamp"] <= cutoff and s["timestamp"] >= now]
        lowest_next_8h = sorted(next_8h, key=lambda s: s["retail_total_ct_kwh_all"])[:3]

        return {
            "current_slot": current_slot,
            "cheapest_slots": cheapest_5,
            "most_expensive_slots": most_expensive_5,
            "lowest_next_8h": lowest_next_8h,
        }

    @staticmethod
    def _find_current_slot(
        forecast: list[dict[str, Any]], now: datetime
    ) -> dict[str, Any] | None:
        """Find the forecast slot matching the current hour."""
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        for slot in forecast:
            if slot["timestamp"] == current_hour:
                return slot
        # Fallback: closest slot within 1 hour of now
        for slot in forecast:
            if abs((slot["timestamp"] - now).total_seconds()) < 3600:
                return slot
        # Last resort: use first available slot so sensors always have data
        return forecast[0] if forecast else None