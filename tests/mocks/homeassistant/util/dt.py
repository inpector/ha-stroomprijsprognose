# Mock homeassistant.util.dt
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str) -> datetime | None:
    """Parse an ISO 8601 datetime string, returning None on failure."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
