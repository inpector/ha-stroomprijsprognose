"""Sensor platform for Stroomprijsprognose electricity prices."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StroomprijsprognoseCoordinator

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "current_price": SensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        icon="mdi:cash-clock",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "current_forecast_price": SensorEntityDescription(
        key="current_forecast_price",
        translation_key="current_forecast_price",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    "current_day_ahead_price": SensorEntityDescription(
        key="current_day_ahead_price",
        translation_key="current_day_ahead_price",
        icon="mdi:calendar-today",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    "lowest_price": SensorEntityDescription(
        key="lowest_price",
        translation_key="lowest_price",
        icon="mdi:arrow-down-bold-circle",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "highest_price": SensorEntityDescription(
        key="highest_price",
        translation_key="highest_price",
        icon="mdi:arrow-up-bold-circle",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "average_price": SensorEntityDescription(
        key="average_price",
        translation_key="average_price",
        icon="mdi:sigma",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "lowest_price_time": SensorEntityDescription(
        key="lowest_price_time",
        translation_key="lowest_price_time",
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    "highest_price_time": SensorEntityDescription(
        key="highest_price_time",
        translation_key="highest_price_time",
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    "lowest_next_8h_price_time": SensorEntityDescription(
        key="lowest_next_8h_price_time",
        translation_key="lowest_next_8h_price_time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    "price_source": SensorEntityDescription(
        key="price_source",
        translation_key="price_source",
        icon="mdi:source-commit",
        entity_registry_enabled_default=False,
    ),
    "forecast_slots": SensorEntityDescription(
        key="forecast_slots",
        translation_key="forecast_slots",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_registry_enabled_default=False,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: StroomprijsprognoseCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[StroomprijsprognoseSensor] = []
    for key, description in SENSOR_DESCRIPTIONS.items():
        entities.append(
            StroomprijsprognoseSensor(coordinator, entry.entry_id, key, description)
        )

    async_add_entities(entities)


class StroomprijsprognoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Stroomprijsprognose electricity price data."""

    coordinator: StroomprijsprognoseCoordinator

    def __init__(
        self,
        coordinator: StroomprijsprognoseCoordinator,
        entry_id: str,
        sensor_key: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{sensor_key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"Stroomprijsprognose {coordinator.plz}",
            "manufacturer": "Stroomprijsprognose.nl",
            "model": "Electricity Price Forecast",
            "configuration_url": f"https://stroomprijsprognose.nl/api/v1/hourly-forecast?hours=72&country={coordinator.country}&plz={coordinator.plz}",
        }
        self._sensor_key = sensor_key
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        data = self.coordinator.data
        if not data:
            return None

        forecast = data.get("forecast", [])
        current_slot = data.get("current_slot")
        summary = data.get("summary", {})

        match self._sensor_key:
            case "current_price":
                if current_slot:
                    return current_slot["retail_total_ct_kwh"]
                return None
            case "current_forecast_price":
                if current_slot:
                    return current_slot["retail_forecast_total_ct_kwh"]
                return None
            case "current_day_ahead_price":
                if current_slot:
                    val = current_slot.get("retail_day_ahead_total_ct_kwh")
                    return round(val, 2) if val is not None else None
                return None
            case "lowest_price":
                return round(min(s["retail_total_ct_kwh_all"] for s in forecast), 2) if forecast else None
            case "highest_price":
                return round(max(s["retail_total_ct_kwh_all"] for s in forecast), 2) if forecast else None
            case "average_price":
                if forecast:
                    avg = sum(s["retail_total_ct_kwh_all"] for s in forecast) / len(forecast)
                    return round(avg, 2)
                return None
            case "lowest_price_time":
                if forecast:
                    min_slot = min(forecast, key=lambda s: s["retail_total_ct_kwh_all"])
                    return min_slot["timestamp"]
                return None
            case "highest_price_time":
                if forecast:
                    max_slot = max(forecast, key=lambda s: s["retail_total_ct_kwh_all"])
                    return max_slot["timestamp"]
                return None
            case "lowest_next_8h_price_time":
                lowest_next = data.get("lowest_next_8h", [])
                if lowest_next:
                    return lowest_next[0]["timestamp"]
                return None
            case "forecast_slots":
                return sum(1 for s in forecast if s["price_source"] == "forecast")
            case "price_source":
                if current_slot:
                    return current_slot.get("price_source", "unavailable")
                return None
            case _:
                return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        match self._sensor_key:
            case "price_source":
                return None
            case "forecast_slots":
                return UnitOfTime.HOURS
            case _ if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
                return None
            case _:
                return self.coordinator.data.get("unit", "ct/kWh") if self.coordinator.data else "ct/kWh"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes (on main current_price sensor only)."""
        data = self.coordinator.data
        if not data or self._sensor_key != "current_price":
            return None

        forecast = data.get("forecast", [])
        attrs: dict[str, Any] = {
            "generated_at": data.get("generated_at"),
            "plz": self.coordinator.plz,
            "country": self.coordinator.country.upper(),
            "currency": data.get("currency", "EUR"),
            "unit": data.get("unit", "ct/kWh"),
            "summary": dict(data.get("summary", {})),
            "assumptions": dict(data.get("assumptions", {})),
            "forecast_hours": len(forecast),
        }

        # Hourly prices as compact list for templates
        attrs["hourly_prices"] = [
            {
                "timestamp": s["timestamp"].isoformat(),
                "retail_total_ct_kwh": s["retail_total_ct_kwh_all"],
                "price_source": s["price_source"],
            }
            for s in forecast
        ]

        attrs["cheapest_slots"] = [
            {
                "timestamp": s["timestamp"].isoformat(),
                "retail_total_ct_kwh": s["retail_total_ct_kwh_all"],
                "price_source": s["price_source"],
            }
            for s in data.get("cheapest_slots", [])
        ]

        attrs["most_expensive_slots"] = [
            {
                "timestamp": s["timestamp"].isoformat(),
                "retail_total_ct_kwh": s["retail_total_ct_kwh_all"],
                "price_source": s["price_source"],
            }
            for s in data.get("most_expensive_slots", [])
        ]

        attrs["lowest_next_8h"] = [
            {
                "timestamp": s["timestamp"].isoformat(),
                "retail_total_ct_kwh": s["retail_total_ct_kwh_all"],
                "price_source": s["price_source"],
            }
            for s in data.get("lowest_next_8h", [])
        ]

        return attrs
