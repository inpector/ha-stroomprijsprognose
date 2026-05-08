# Sensor Reference

Complete reference for all Stroomprijsprognose sensors.

## Sensor List

### `sensor.stroomprijsprognose_current_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** enabled
- **Value:** `retail_effective_total_ct_kwh` for the current clock hour

This is the main sensor. Its state is the total retail price for the current hour — the price you actually pay, including all fees and taxes.

**Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| `hourly_prices` | list[dict] | All 72 forecast slots |
| `cheapest_slots` | list[dict] | Top 5 cheapest hours |
| `most_expensive_slots` | list[dict] | Top 5 most expensive hours |
| `lowest_next_8h` | list[dict] | Cheapest slots within next 8 hours |
| `summary` | dict | API summary (avg/min/max) |
| `assumptions` | dict | Grid fees, supplier markup, VAT used |
| `generated_at` | str | ISO timestamp of API generation |
| `forecast_hours` | int | Number of forecast slots available |
| `plz` | str | Configured postal code |
| `country` | str | Configured country |

Each slot dict in arrays:
```json
{
  "timestamp": "2026-05-08T12:00:00+00:00",
  "retail_total_ct_kwh": 26.34,
  "price_source": "day_ahead"
}
```

### `sensor.stroomprijsprognose_lowest_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** enabled
- **Value:** Minimum `retail_total_ct_kwh` across all forecast slots

### `sensor.stroomprijsprognose_highest_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** enabled
- **Value:** Maximum `retail_total_ct_kwh` across all forecast slots

### `sensor.stroomprijsprognose_average_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** enabled
- **Value:** Arithmetic mean of `retail_total_ct_kwh` across all forecast slots

### `sensor.stroomprijsprognose_lowest_price_time`

- **Device class:** timestamp
- **Default:** enabled
- **Value:** UTC timestamp of the forecast slot with the lowest retail price

### `sensor.stroomprijsprognose_highest_price_time`

- **Device class:** timestamp
- **Default:** enabled
- **Value:** UTC timestamp of the forecast slot with the highest retail price

### `sensor.stroomprijsprognose_lowest_next_8h_price_time`

- **Device class:** timestamp
- **Default:** enabled
- **Value:** UTC timestamp of the cheapest slot within the next 8 hours (from now, not from current hour)

Use this for "should I run the dishwasher now or wait until X?"

### `sensor.stroomprijsprognose_current_forecast_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** disabled
- **Value:** `retail_forecast_total_ct_kwh` for current hour (model-based forecast component only)

### `sensor.stroomprijsprognose_current_day_ahead_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** disabled
- **Value:** `retail_day_ahead_total_ct_kwh` for current hour. `unavailable` when no day-ahead data exists for this slot.

### `sensor.stroomprijsprognose_price_source`

- **Default:** disabled
- **Values:** `day_ahead`, `forecast`, or `unavailable`
- **Description:** Indicates whether the current hour's price comes from the EPEX day-ahead auction or from the model forecast.

### `sensor.stroomprijsprognose_forecast_slots`

- **Unit:** hours
- **State class:** measurement
- **Default:** disabled
- **Value:** Count of forecast slots that use model-based (non-day-ahead) pricing.

## Price Sources

The API uses two price sources:

1. **Day-Ahead (`day_ahead`):** Prices from the EPEX SPOT day-ahead auction. Exact, fixed prices. Usually available for the next 12-36 hours.

2. **Forecast (`forecast`):** Model-predicted prices for hours beyond the day-ahead horizon. Less precise, but directionally useful.

The `price_source` sensor tells you which source the current hour uses.
