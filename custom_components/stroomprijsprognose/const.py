"""Constants for the Stroomprijsprognose integration."""

from typing import Final

DOMAIN: Final = "stroomprijsprognose"
NAME: Final = "Stroomprijsprognose"
BASE_URL: Final = "https://stroomprijsprognose.nl"

CONF_PLZ: Final = "plz"
CONF_COUNTRY: Final = "country"
CONF_HOURS: Final = "hours"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_SUPPLIER_MARKUP: Final = "supplier_markup_ct_kwh"
CONF_LEVIES_AND_TAXES: Final = "levies_and_taxes_ct_kwh"
CONF_VAT_PERCENT: Final = "vat_percent"

DEFAULT_COUNTRY: Final = "DE"
DEFAULT_HOURS: Final = 72
DEFAULT_UPDATE_INTERVAL: Final = 15  # minutes

MIN_HOURS: Final = 1
MAX_HOURS: Final = 96
MIN_UPDATE_INTERVAL: Final = 5
MAX_UPDATE_INTERVAL: Final = 60

COUNTRIES: Final = ["DE", "NL", "BE", "AT", "CH", "LU"]
