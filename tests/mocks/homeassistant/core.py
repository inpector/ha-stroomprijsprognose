# Mock homeassistant.core

from typing import Any, Callable
from unittest.mock import MagicMock


class HomeAssistant(MagicMock):
    pass


class ServiceCall(MagicMock):
    pass


def callback(fn: Callable) -> Callable:
    """Decorator that marks a function as safe to call from the event loop."""
    return fn
