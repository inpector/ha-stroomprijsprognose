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
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_UNIT, DOMAIN
from .coordinator import StroomprijsprognoseCoordinator

# Coordinator-driven updates need no parallelism limit
PARALLEL_UPDATES = 0

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    # --- Primary sensors (enabled, no entity category) ---
    "current_price": SensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        icon="mdi:cash-clock",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "next_price": SensorEntityDescription(
        key="next_price",
        translation_key="next_price",
        icon="mdi:cash-clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
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
    "price_level": SensorEntityDescription(
        key="price_level",
        translation_key="price_level",
        icon="mdi:speedometer",
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
    # --- Secondary sensors (disabled by default, no entity category) ---
    "price_percentage": SensorEntityDescription(
        key="price_percentage",
        translation_key="price_percentage",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
    ),
    # --- Diagnostic sensors (disabled, entity_category=DIAGNOSTIC) ---
    "current_forecast_price": SensorEntityDescription(
        key="current_forecast_price",
        translation_key="current_forecast_price",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "current_day_ahead_price": SensorEntityDescription(
        key="current_day_ahead_price",
        translation_key="current_day_ahead_price",
        icon="mdi:calendar-today",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "price_source": SensorEntityDescription(
        key="price_source",
        translation_key="price_source",
        icon="mdi:source-commit",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "forecast_slots": SensorEntityDescription(
        key="forecast_slots",
        translation_key="forecast_slots",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "last_updated": SensorEntityDescription(
        key="last_updated",
        translation_key="last_updated",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: StroomprijsprognoseCoordinator = entry.runtime_data

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
        next_slot = data.get("next_slot")

        match self._sensor_key:
            # Primary price sensors
            case "current_price":
                if current_slot:
                    return current_slot["retail_total_ct_kwh"]
                return None
            case "next_price":
                if next_slot:
                    return next_slot["retail_total_ct_kwh"]
                return None
            case "lowest_price":
                return min(s["retail_total_ct_kwh_all"] for s in forecast) if forecast else None
            case "highest_price":
                return max(s["retail_total_ct_kwh_all"] for s in forecast) if forecast else None
            case "average_price":
                if forecast:
                    return sum(s["retail_total_ct_kwh_all"] for s in forecast) / len(forecast)
                return None

            # Classification sensors
            case "price_level":
                return data.get("price_level")
            case "price_percentage":
                return data.get("price_percentage")

            # Timestamp sensors
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
            case "last_updated":
                return data.get("last_updated")

            # Diagnostic sensors
            case "current_forecast_price":
                if current_slot:
                    return current_slot["retail_forecast_total_ct_kwh"]
                return None
            case "current_day_ahead_price":
                if current_slot:
                    return current_slot.get("retail_day_ahead_total_ct_kwh")
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
            case "price_source" | "price_level":
                return None
            case "forecast_slots":
                return UnitOfTime.HOURS
            case "price_percentage":
                return PERCENTAGE
            case _ if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
                return None
            case _:
                return self.coordinator.data.get("unit", DEFAULT_UNIT) if self.coordinator.data else DEFAULT_UNIT

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes on the current_price sensor only.

        Consolidating all detail data on one sensor avoids bloating HA's
        state machine with duplicate attributes across 15+ sensor entities.
        """
        data = self.coordinator.data
        if not data or self._sensor_key != "current_price":
            return None

        forecast = data.get("forecast", [])
        attrs: dict[str, Any] = {
            "generated_at": data.get("generated_at"),
            "plz": self.coordinator.plz,
            "country": self.coordinator.country,
            "currency": data.get("currency", "EUR"),
            "unit": data.get("unit", "ct/kWh"),
            "summary": dict(data.get("summary", {})),
            "assumptions": dict(data.get("assumptions", {})),
            "forecast_hours": len(forecast),
            "price_level": data.get("price_level"),
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