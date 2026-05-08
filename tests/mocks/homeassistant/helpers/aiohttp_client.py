# Mock homeassistant.helpers.aiohttp_client

from unittest.mock import MagicMock


def async_get_clientsession(hass):
    return MagicMock()
