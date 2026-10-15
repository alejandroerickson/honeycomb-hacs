"""What stays home by default (okf/spec/01-telemetry.md, 1.5).

A default here is removed only by a new decision; adding one needs none
(okf/decisions/sensitive-data-stays-home-by-default.md).
"""

from __future__ import annotations

import re

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import State
from homeassistant.helpers.entity_registry import RegistryEntry

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
