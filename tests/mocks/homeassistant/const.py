# Mock homeassistant.const

from enum import StrEnum


PERCENTAGE = "%"


class Platform(StrEnum):
    SENSOR = "sensor"


class UnitOfTime(StrEnum):
    HOURS = "h"
    MINUTES = "min"
    SECONDS = "s"
