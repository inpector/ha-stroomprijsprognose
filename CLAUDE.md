# Stroomprijsprognose HA Integration

Home Assistant custom component for electricity price forecasts from stroomprijsprognose.nl.

## Architecture

Standard HA coordinator pattern with runtime_data:
- `coordinator.py` — DataUpdateCoordinator, fetches `/api/v1/hourly-forecast`, processes into structured dict
- `sensor.py` — 15 sensors (10 primary, 5 diagnostic), `PARALLEL_UPDATES = 0`, main `current_price` carries detail attributes
- `config_flow.py` — Config + options + reconfigure flow (voluptuous schemas, API validation)
- `__init__.py` — Entry setup, service registration (`force_refresh`, `get_prices`), typed ConfigEntry with runtime_data
- `const.py` — All constants, thresholds, defaults
- `diagnostics.py` — Redacted config dump for debugging

## Key Patterns

- `entry.runtime_data = coordinator` replaces `hass.data[DOMAIN][entry.entry_id]`
- `StroomprijsprognoseConfigEntry = ConfigEntry[StroomprijsprognoseCoordinator]` typed entry
- Coordinator passes `config_entry=entry` to `DataUpdateCoordinator.__init__`
- Smart caching: `_needs_api_fetch()` checks interval, hour boundary + 5-min grace period, force refresh flag
- `_recompute_derived()` recomputes time-dependent values from cache without API calls
- Diagnostic sensors use `EntityCategory.DIAGNOSTIC`, appear under Diagnostics section
- `get_prices` service uses `SupportsService.ONLY` + `ServiceResponse` pattern
- Reconfigure flow via `async_step_reconfigure` + `async_update_reload_and_abort`

## Key Conventions

- Country stored in **uppercase** internally; lowercased only for API URL parameter
- `retail_total_ct_kwh_all` is the all-inclusive price used for ranking (cheapest/most expensive)
- `retail_total_ct_kwh` (without `_all`) is the effective retail price for the current source
- Timestamps parsed via `dt_util.parse_datetime()` with `datetime.fromisoformat` fallback
- Sensor `native_value` returns raw floats — no manual `round()`, `suggested_display_precision` handles display
- `force_refresh` service accepts optional `entry_id` (voluptuous schema validated)
- `get_prices` service returns cached forecast data as `ServiceResponse` dict
- API timeout: 30s (`API_TIMEOUT_SECONDS` in const.py)
- Default unit: `ct/kWh` (`DEFAULT_UNIT` in const.py)
- Cache grace period: 300s (`API_CACHE_GRACE_SECONDS` in const.py)

## Sensors

| Key | Category | Unit | Default |
|-----|----------|------|---------|
| current_price | primary | ct/kWh | enabled |
| next_price | primary | ct/kWh | enabled |
| lowest_price | primary | ct/kWh | enabled |
| highest_price | primary | ct/kWh | enabled |
| average_price | primary | ct/kWh | enabled |
| price_level | primary | — | enabled |
| lowest_price_time | primary | datetime | enabled |
| highest_price_time | primary | datetime | enabled |
| lowest_next_8h_price_time | primary | datetime | enabled |
| price_percentage | primary | % | disabled |
| current_forecast_price | diagnostic | ct/kWh | disabled |
| current_day_ahead_price | diagnostic | ct/kWh | disabled |
| price_source | diagnostic | — | disabled |
| forecast_slots | diagnostic | h | disabled |
| last_updated | diagnostic | datetime | disabled |

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-test.txt
pytest tests/ -v
```

88 tests, mock `homeassistant` package in `tests/mocks/`. No HA runtime needed.

## Commits

Follow conventional commits: `type(scope): subject`. Scope is subsystem: `sensor`, `coordinator`, `config`, `ci`, etc.