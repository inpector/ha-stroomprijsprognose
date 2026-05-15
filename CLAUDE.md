# Stroomprijsprognose HA Integration

Home Assistant custom component for electricity price forecasts from stroomprijsprognose.nl.

## Architecture

Standard HA coordinator pattern:
- `coordinator.py` — DataUpdateCoordinator, fetches `/api/v1/hourly-forecast`, processes into structured dict
- `sensor.py` — 11 sensors, main `current_price` carries all detail attributes
- `config_flow.py` — Config + options flow (voluptuous schemas)
- `__init__.py` — Entry setup, service registration, reload handling
- `const.py` — All constants, thresholds, defaults
- `diagnostics.py` — Redacted config dump for debugging

## Key Conventions

- Country stored in **uppercase** internally; lowercased only for API URL parameter
- `retail_total_ct_kwh_all` is the all-inclusive price used for ranking (cheapest/most expensive)
- `retail_total_ct_kwh` (without `_all`) is the effective retail price for the current source
- Timestamps parsed via `dt_util.parse_datetime()` with `datetime.fromisoformat` fallback
- Sensor `native_value` returns raw floats — no manual `round()`, `suggested_display_precision` handles display
- `force_refresh` service accepts optional `entry_id` (voluptuous schema validated)
- API timeout: 30s (`API_TIMEOUT_SECONDS` in const.py)
- Default unit: `ct/kWh` (`DEFAULT_UNIT` in const.py)

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-test.txt
pytest tests/ -v
```

47 tests, mock `homeassistant` package in `tests/mocks/`. No HA runtime needed.

## Commits

Follow conventional commits: `type(scope): subject`. Scope is subsystem: `sensor`, `coordinator`, `config`, `ci`, etc.