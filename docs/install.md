# Installation

Detailed installation instructions for the Stroomprijsprognose integration.

## Requirements

- Home Assistant 2024.1 or newer
- Internet connection (API is cloud-hosted)

## HACS Installation

1. Open HACS in Home Assistant
2. Click the three-dot menu → **Custom repositories**
3. Paste the repository URL
4. Select **Integration** as category
5. Click **Add**
6. Search for "Stroomprijsprognose" in HACS
7. Click **Download**
8. Restart Home Assistant

## Manual Installation

```bash
# 1. Navigate to your Home Assistant config directory
cd /path/to/your/homeassistant/config

# 2. Create custom_components if it doesn't exist
mkdir -p custom_components

# 3. Copy the integration
cp -r /path/to/this/repo/custom_components/stroomprijsprognose custom_components/

# 4. Verify the structure
ls custom_components/stroomprijsprognose/
# Should show: __init__.py  manifest.json  const.py  coordinator.py
#              sensor.py  config_flow.py  diagnostics.py  services.yaml
#              strings.json  translations/

# 5. Restart Home Assistant
```

Or use the Home Assistant terminal add-on:

```bash
# Inside the Home Assistant terminal
wget -qO- https://github.com/your/repo/archive/main.tar.gz | tar xz -C /config/custom_components/ --strip-components=2
ha core restart
```

## Docker / Container

If running Home Assistant in Docker, mount a volume and copy there:

```bash
docker cp custom_components/stroomprijsprognose \
  homeassistant:/config/custom_components/stroomprijsprognose

docker restart homeassistant
```

## Configuration

After installation, restart Home Assistant. Then:

1. **Settings → Devices & Services**
2. Click **+ Add Integration** (bottom right)
3. Search for **Stroomprijsprognose**
4. Enter your **postal code** (e.g., `66386`)
5. Select your **country** (e.g., `DE`)
6. Click **Submit**

### Advanced Options

Click **Configure** on the integration entry to adjust:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| Forecast Hours | 72 | 1–96 | Number of hours to fetch |
| Update Interval | 15 | 5–60 | Minutes between API calls |
| Supplier Markup | (API default) | any | Override supplier markup in ct/kWh |
| Levies & Taxes | (API default) | any | Override levies in ct/kWh |
| VAT Percent | (API default) | 0–30 | Override VAT percentage |

> **Note:** Price overrides are stored but not yet applied to sensor values. Use template sensors for custom calculations. Client-side recalculation is planned for v1.1.

## Multiple Locations

Add the integration multiple times with different postal codes. Each instance creates its own set of sensors with the PLZ in the entity ID.

## Troubleshooting

### Integration fails to load

Check the Home Assistant logs:
```
Settings → System → Logs
```

Search for "stroomprijsprognose". Common issues:
- Invalid postal code → API returns error
- Network timeout → Check firewall / internet
- Rate limiting → Reduce update interval

### "ConfigEntryNotReady" on startup

The API might be temporarily unavailable. The integration retries automatically.
