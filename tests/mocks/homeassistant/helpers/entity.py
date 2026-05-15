# Mock homeassistant.helpers.entity

from enum import StrEnum


class EntityCategory(StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"