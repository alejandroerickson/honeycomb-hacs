"""What every span about an entity says about it: what it is, where it is, and what device it is."""

from __future__ import annotations

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)

from .otlp import AttributeValue


def describe(hass: HomeAssistant, state: State, entry: er.RegistryEntry | None) -> dict[str, AttributeValue]:
    """The entity's attributes, leaving out any with no value."""
    attributes: dict[str, AttributeValue | None] = {
        "ha.entity_id": state.entity_id,
        "ha.domain": state.domain,
        "ha.friendly_name": state.attributes.get(ATTR_FRIENDLY_NAME),
        "ha.device_class": state.attributes.get(ATTR_DEVICE_CLASS),
        "ha.unit": state.attributes.get(ATTR_UNIT_OF_MEASUREMENT),
    }
    if entry is not None:
        attributes["ha.integration"] = entry.platform
        device = dr.async_get(hass).async_get(entry.device_id) if entry.device_id else None
        if device is not None:
            attributes["ha.device"] = device.name_by_user or device.name
            attributes["ha.device.manufacturer"] = device.manufacturer
            attributes["ha.device.model"] = device.model
        attributes.update(_area_and_floor(hass, entry.area_id or (device.area_id if device else None)))
    return {key: value for key, value in attributes.items() if value is not None}


def _area_and_floor(hass: HomeAssistant, area_id: str | None) -> dict[str, str]:
    """The area and its floor, by name."""
    if area_id is None or (area := ar.async_get(hass).async_get_area(area_id)) is None:
        return {}
    names = {"ha.area": area.name}
    if area.floor_id and (floor := fr.async_get(hass).async_get_floor(area.floor_id)):
        names["ha.floor"] = floor.name
    return names
