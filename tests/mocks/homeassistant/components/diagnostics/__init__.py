# Mock homeassistant.components.diagnostics

from typing import Any


def async_redact_data(data: Any, to_redact: list[str]) -> Any:
    return data
