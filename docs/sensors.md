# Sensor Reference

Complete reference for all Stroomprijsprognose sensors.

## Sensor Categories

| Category | Description |
|----------|-------------|
| **Primary** | Actionable sensors used in automations and dashboards |
| **Diagnostic** | Metadata/debugging sensors (disabled by default, shown under diagnostics) |

## Primary Sensors

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
| `data` | list[dict] | Graph-ready `{x, y}` pairs for chart cards |
| `cheapest_slots` | list[dict] | Top 5 cheapest hours |
| `most_expensive_slots` | list[dict] | Top 5 most expensive hours |
| `lowest_next_8h` | list[dict] | Cheapest slots within next 8 hours |
| `price_level` | str | Current price classification |
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

The `data` attribute uses a chart-friendly format:
```json
{
  "x": "2026-05-08T12:00:00+00:00",
  "y": 26.34
}
```

Use it in apexcharts-card:
```yaml
type: custom:apexcharts-card
series:
  - entity: sensor.stroomprijsprognose_current_price
    attribute: data
    type: line
    data_generator: |
      return entity.attributes.data.map(d => [new Date(d.x).getTime(), d.y])
```

### `sensor.stroomprijsprognose_next_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Default:** enabled
- **Value:** `retail_effective_total_ct_kwh` for the next clock hour

Use this for "should I wait?" automations — compare `current_price` vs `next_price` to decide whether to run an appliance now or in the next hour.

### `sensor.stroomprijsprognose_price_level`

- **Default:** enabled
- **Values:** `very_cheap`, `cheap`, `normal`, `expensive`, `very_expensive
- **Description:** Human-readable price classification based on the current price's percentile position within the forecast range.

Percentile thresholds:
| Level | Percentile |
|-------|------------|
| `very_cheap` | 0–20% |
| `cheap` | 20–40% |
| `normal` | 40–60% |
| `expensive` | 60–80% |
| `very_expensive` | 80–100% |

Use this for simple automations without comparing raw numbers:
```yaml
trigger:
  - platform: state
    entity_id: sensor.stroomprijsprognose_price_level
    to: "very_cheap"
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

### `sensor.stroomprijsprognose_price_percentage`

- **Unit:** %
- **State class:** measurement
- **Default:** disabled
- **Value:** Current price as percentage of the highest price in the forecast

Useful for gauge cards and threshold automations. A value of 50 means the current price is halfway between the lowest and highest.

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

## Diagnostic Sensors

These sensors are disabled by default and appear under the Diagnostics section of the device page.

### `sensor.stroomprijsprognose_current_forecast_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Category:** diagnostic
- **Value:** `retail_forecast_total_ct_kwh` for current hour (model-based forecast component only)

### `sensor.stroomprijsprognose_current_day_ahead_price`

- **Unit:** ct/kWh
- **State class:** measurement
- **Category:** diagnostic
- **Value:** `retail_day_ahead_total_ct_kwh` for current hour. `unavailable` when no day-ahead data exists for this slot.

### `sensor.stroomprijsprognose_price_source`

- **Category:** diagnostic
- **Values:** `day_ahead`, `forecast`, or `unavailable`
- **Description:** Indicates whether the current hour's price comes from the EPEX day-ahead auction or from the model forecast.

### `sensor.stroomprijsprognose_forecast_slots`

- **Unit:** hours
- **State class:** measurement
- **Category:** diagnostic
- **Value:** Count of forecast slots that use model-based (non-day-ahead) pricing.

### `sensor.stroomprijsprognose_last_updated`

- **Device class:** timestamp
- **Category:** diagnostic
- **Value:** When the API data was last successfully fetched

## Price Sources

The API uses two price sources:

1. **Day-Ahead (`day_ahead`):** Prices from the EPEX SPOT day-ahead auction. Exact, fixed prices. Usually available for the next 12-36 hours.

2. **Forecast (`forecast`):** Model-predicted prices for hours beyond the day-ahead horizon. Less precise, but directionally useful.

The `price_source` sensor tells you which source the current hour uses.

## Smart Caching

The integration uses smart caching to reduce API calls:

- Full API fetch at the configured interval (default 15 min) or when an hour boundary is crossed (after a 5-minute grace period)
- Between fetches, time-dependent values (`current_slot`, `next_slot`, `lowest_next_8h`, `price_level`, `price_percentage`) are recomputed locally from cached forecast data
- This reduces API calls by ~50% while keeping sensors up-to-date

## Services

### Force Refresh

Call `stroomprijsprognose.force_refresh` to bypass cache and trigger an immediate API fetch:

```yaml
# Refresh all configured instances
service: stroomprijsprognose.force_refresh

# Refresh a specific instance
service: stroomprijsprognose.force_refresh
data:
  entry_id: "abc123..."
```

### Get Prices

Call `stroomprijsprognose.get_prices` to return cached price data as a service response. Useful in templates and automations:

```yaml
service: stroomprijsprognose.get_prices
response_variable: prices
```

Returns:
```json
{
  "generated_at": "2026-05-08T12:00:00+00:00",
  "currency": "EUR",
  "unit": "ct/kWh",
  "plz": "66386",
  "country": "DE",
  "prices": [
    {"timestamp": "2026-05-08T12:00:00+00:00", "retail_total_ct_kwh": 26.0, "price_source": "day_ahead"},
    ...
  ]
}
```