# Home Assistant Stroomprijsprognose Integration

Custom Home Assistant component for electricity price forecasts from [stroomprijsprognose.nl](https://stroomprijsprognose.nl). Provides hourly retail electricity prices (incl. grid fees, levies, VAT) based on your postal code.

> **Warning: Vibe-Coded**
> This integration was generated through vibe-coding — AI-driven code generation with minimal human review.
>
> - **Tool:** Claude Code (Anthropic)
> - **Model:** DeepSeek V4 Pro (via cloud routing)
> - **Mode:** Caveman (ultra-compressed communication)
> - **Method:** Plan → generate all files → single review pass → ship
>
> No human has verified every line. Test before relying on it for financial decisions.

## Features

- 72-hour electricity price forecast via [stroomprijsprognose.nl API](https://stroomprijsprognose.nl/api/v1/hourly-forecast)
- Retail prices include: grid fees, levies, taxes, VAT — automatically determined by postal code
- 11 sensors: current price, min/max/avg, best times, price source tracking
- Rich attributes on main sensor for template automations
- Configurable via Home Assistant UI (no YAML needed)
- Force refresh service
- Full German and English translations

## Supported Countries

| Code | Country |
|------|---------|
| DE   | Germany |
| NL   | Netherlands |
| BE   | Belgium |
| AT   | Austria |
| CH   | Switzerland |
| LU   | Luxembourg |

## Installation

### HACS (recommended)

1. Add this repository as custom repository in HACS
2. Install "Stroomprijsprognose Electricity Prices"
3. Restart Home Assistant

### Manual

```bash
cd /path/to/your/homeassistant/config
cp -r custom_components/stroomprijsprognose custom_components/
# Restart Home Assistant
```

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "Stroomprijsprognose"
3. Enter your postal code and select your country
4. Click Submit

The integration fetches data every 15 minutes. Adjust interval in the integration options.

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| `sensor.stroomprijsprognose_current_price` | ct/kWh | Retail price for current hour |
| `sensor.stroomprijsprognose_lowest_price` | ct/kWh | Cheapest retail price in forecast |
| `sensor.stroomprijsprognose_highest_price` | ct/kWh | Most expensive retail price |
| `sensor.stroomprijsprognose_average_price` | ct/kWh | Average retail price over forecast |
| `sensor.stroomprijsprognose_lowest_price_time` | datetime | When the cheapest hour is |
| `sensor.stroomprijsprognose_highest_price_time` | datetime | When the most expensive hour is |
| `sensor.stroomprijsprognose_lowest_next_8h_price_time` | datetime | Cheapest slot in next 8 hours |

See [docs/sensors.md](docs/sensors.md) for full sensor reference.

## Automation Examples

Start washing machine when price drops below 20 ct/kWh:

```yaml
alias: "Washing machine on cheap power"
trigger:
  - platform: numeric_state
    entity_id: sensor.stroomprijsprognose_current_price
    below: 20
action:
  - service: switch.turn_on
    target:
      entity_id: switch.washing_machine
```

More examples: [docs/automations.md](docs/automations.md)

## Template Usage

Access forecast data in templates:

```jinja2
{# Cheapest hour today #}
{{ state_attr('sensor.stroomprijsprognose_current_price', 'cheapest_slots')[0].timestamp }}

{# Price in 3 hours #}
{{ state_attr('sensor.stroomprijsprognose_current_price', 'hourly_prices')[3].retail_total_ct_kwh }}

{# Count hours below 15 ct/kWh #}
{{ state_attr('sensor.stroomprijsprognose_current_price', 'hourly_prices')
   | selectattr('retail_total_ct_kwh', 'lt', 15) | list | count }}
```

## API

This integration uses the free public API at [stroomprijsprognose.nl](https://stroomprijsprognose.nl).

- Endpoint: `/api/v1/hourly-forecast`
- Rate limiting: Unknown, be reasonable
- No API key required
- Data updates roughly every 15 minutes

## Development

### Running Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

47 tests covering coordinator data processing, sensor value extraction, config flow schema validation, and unit handling. Tests use a mock `homeassistant` package — no HA runtime needed.

### CI/CD

Two GitHub Actions workflows:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `test.yml` | push/PR on `main` | pytest on Python 3.12 + 3.13 |
| `release.yml` | manual (`workflow_dispatch`) | Creates versioned release |

### Creating a Release

1. Go to **Actions → Create Release → Run workflow**
2. Enter version: `v1.0.0` (must match `vX.Y.Z`)
3. Optionally add release notes (markdown)
4. Click **Run workflow**

The workflow:
- Validates version format and checks tag doesn't exist
- Builds a `.zip` release asset with the version injected into `manifest.json`
- Creates an annotated Git tag
- Publishes a GitHub release with the zip attached

## Vibe-Code Transparency

| Aspect | Detail |
|--------|--------|
| **AI Tool** | Claude Code CLI (Anthropic) |
| **Model** | DeepSeek V4 Pro |
| **Human review** | Single pass, no line-by-line audit |
| **Tests** | 47 pytest tests (AI-generated, not human-verified) |
| **Prompt method** | Caveman mode (ultra-compressed), plan-first |
| **Files** | 100% AI generated in iterative batches |
| **Disclaimer** | Not production-validated. Use at your own risk. |

## License

MIT — see [LICENSE](LICENSE).
