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

from .const import BASE_URL, CONF_COUNTRY, CONF_HOURS, CONF_PLZ, DOMAIN

_LOGGER = logging.getLogger(__name__)


class StroomprijsprognoseCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch electricity price forecasts."""

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
        self.country = country.lower()
        self.hours = hours
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        url = (
            f"{BASE_URL}/api/v1/hourly-forecast"
            f"?hours={self.hours}&country={self.country}&plz={self.plz}"
        )

        try:
            async with asyncio.timeout(30):
                response = await self._session.get(url)
                response.raise_for_status()
                data = await response.json()
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching data from {url}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

        if "series" not in data or "summary" not in data:
            raise UpdateFailed("Invalid API response: missing series or summary")

        return self._process_data(data)

    def _process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process raw API data into structured format."""
        series: list[dict[str, Any]] = data["series"]
        summary: dict[str, Any] = data["summary"]
        assumptions: dict[str, Any] = data.get("assumptions", {})
        now = dt_util.utcnow()

        forecast: list[dict[str, Any]] = []
        for slot in series:
            ts = datetime.fromisoformat(slot["timestamp"].replace("Z", "+00:00"))
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

        # Find current hour slot
        current_slot = self._find_current_slot(forecast, now)

        # Cheapest/most expensive slots by retail_total_ct_kwh
        sorted_by_price = sorted(forecast, key=lambda s: s["retail_total_ct_kwh_all"])
        cheapest_5 = sorted_by_price[:5]
        most_expensive_5 = sorted_by_price[-5:][::-1]

        # Lowest in next 8 hours
        cutoff = now + timedelta(hours=8)
        next_8h = [s for s in forecast if s["timestamp"] <= cutoff and s["timestamp"] >= now]
        lowest_next_8h = sorted(next_8h, key=lambda s: s["retail_total_ct_kwh_all"])[:3]

        return {
            "generated_at": data.get("generated_at"),
            "currency": data["currency"],
            "unit": data["unit"],
            "forecast": forecast,
            "current_slot": current_slot,
            "summary": summary,
            "assumptions": assumptions,
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
        # Fallback: closest slot within the hour
        for slot in forecast:
            if abs((slot["timestamp"] - now).total_seconds()) < 3600:
                return slot
        return forecast[0] if forecast else None
