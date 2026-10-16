"""What stays home: by default, and by the user's rules (okf/spec/01-telemetry.md, 1.5).

A default here is removed only by a new decision; adding one needs none
(okf/decisions/sensitive-data-stays-home-by-default.md).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_registry import RegistryEntry

from .const import (
    CONF_ATTRIBUTES,
    CONF_EXCLUDE,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_DEVICE_CLASSES,
    CONF_INCLUDE,
)
from .describe import area_id
from .otlp import AttributeValue

# Where people are, and what cameras see.
EXCLUDED_DOMAINS = frozenset({"device_tracker", "person", "zone", "camera", "image"})

# Integrations whose entities describe a person rather than the home: the companion app's phone
# sensors report location, activity, sleep, steps, networks and notifications.
EXCLUDED_PLATFORMS = frozenset({"mobile_app"})

# Body measurements, for sensors and binary sensors. Home Assistant has no device class for most of
# them, so they are recognized by a unit only a body has, or by words in the entity id.
BODY_DOMAINS = frozenset({"sensor", "binary_sensor"})
BODY_UNITS = frozenset({"bpm", "beats/min", "breaths/min", "steps", "mg/dL", "mmol/L"})
BODY_WORDS = re.compile(
    r"(?:^|_)(?:heart_?rate|hrv|blood_(?:pressure|glucose|oxygen)|systolic|diastolic|glucose|spo2"
    r"|oxygen_saturation|respiratory_rate|body_(?:temperature|fat|mass|weight)|bmi|weight|sleep|asleep"
    r"|steps|vo2_?max)(?:_|$)"
)


def is_excluded(state: State, entry: RegistryEntry | None) -> bool:
    """Whether an entity's states stay home."""
    if state.domain in EXCLUDED_DOMAINS:
        return True
    if entry is not None and entry.platform in EXCLUDED_PLATFORMS:
        return True
    if state.domain in BODY_DOMAINS:
        return (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) in BODY_UNITS
            or BODY_WORDS.search(state.object_id) is not None
        )
    return False


@dataclass(frozen=True)
class Rules:
    """The user's choices, from the integration's options."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    exclude_areas: frozenset[str] = frozenset()
    exclude_device_classes: frozenset[str] = frozenset()
    attributes: tuple[str, ...] = ()

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> Rules:
        def names(key: str) -> tuple[str, ...]:
            return tuple(name.strip() for name in options.get(key) or () if name and name.strip())

        return cls(
            include=tuple(name.lower() for name in names(CONF_INCLUDE)),
            exclude=tuple(name.lower() for name in names(CONF_EXCLUDE)),
            exclude_areas=frozenset(names(CONF_EXCLUDE_AREAS)),
            exclude_device_classes=frozenset(names(CONF_EXCLUDE_DEVICE_CLASSES)),
            attributes=names(CONF_ATTRIBUTES),
        )

    def excluded(self, hass: HomeAssistant, state: State, entry: RegistryEntry | None) -> bool:
        """Whether an entity's states stay home. What the user leaves out stays out, even if included."""
        if _matches(state.entity_id, self.exclude):
            return True
        if state.attributes.get(ATTR_DEVICE_CLASS) in self.exclude_device_classes:
            return True
        if self.exclude_areas and area_id(hass, entry) in self.exclude_areas:
            return True
        return is_excluded(state, entry) and not _matches(state.entity_id, self.include)

    def allowed_attributes(self, state: State) -> dict[str, AttributeValue]:
        """The attributes the user allows, as `ha.attr.<name>`."""
        allowed: dict[str, AttributeValue] = {}
        for name in self.attributes:
            value = state.attributes.get(name)
            if isinstance(value, (bool, int, str)) or (isinstance(value, float) and math.isfinite(value)):
                allowed[f"ha.attr.{name}"] = value
            elif value is not None:
                allowed[f"ha.attr.{name}"] = json.dumps(value, default=str)
        return allowed


def _matches(entity_id: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(entity_id, pattern) for pattern in patterns)
