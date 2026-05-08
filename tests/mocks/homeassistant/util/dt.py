# Mock homeassistant.util.dt
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
