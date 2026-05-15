# Mock homeassistant.core

from typing import Any, Callable
from unittest.mock import MagicMock


class HomeAssistant(MagicMock):
    pass


class ServiceCall(MagicMock):
    pass


# TypedDict-like alias for service response data
type ServiceResponse = dict[str, Any]


class SupportsService:
    ONLY = "only"


def callback(fn: Callable) -> Callable:
    """Decorator that marks a function as safe to call from the event loop."""
    return fn
