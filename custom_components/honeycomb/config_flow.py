"""Config flow for Honeycomb: an API key, the region its team lives in, and a service name.

The options flow holds the user's choices of what else to send or leave out
(okf/spec/01-telemetry.md, 1.5).
"""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    AreaSelector,
    AreaSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_ATTRIBUTES,
    CONF_EXCLUDE,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_DEVICE_CLASSES,
    CONF_INCLUDE,
    CONF_REGION,
    CONF_SERVICE_NAME,
    DEFAULT_REGION,
    DEFAULT_SERVICE_NAME,
    DOMAIN,
    HEADER_API_KEY,
    REGIONS,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Required(CONF_REGION, default=DEFAULT_REGION): SelectSelector(
            SelectSelectorConfig(options=list(REGIONS), translation_key=CONF_REGION)
        ),
        vol.Required(CONF_SERVICE_NAME, default=DEFAULT_SERVICE_NAME): str,
    }
)


# Names typed in, one per chip: entity id patterns, device classes, attribute names.
_NAMES = SelectSelector(SelectSelectorConfig(options=[], multiple=True, custom_value=True))

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EXCLUDE, default=[]): _NAMES,
        vol.Optional(CONF_EXCLUDE_AREAS, default=[]): AreaSelector(AreaSelectorConfig(multiple=True)),
        vol.Optional(CONF_EXCLUDE_DEVICE_CLASSES, default=[]): _NAMES,
        vol.Optional(CONF_INCLUDE, default=[]): _NAMES,
        vol.Optional(CONF_ATTRIBUTES, default=[]): _NAMES,
    }
)


class CannotConnect(Exception):
    """Honeycomb could not be reached."""


class InvalidAuth(Exception):
    """Honeycomb refused the API key."""


async def validate_api_key(session: aiohttp.ClientSession, api_key: str, region: str) -> dict[str, Any]:
    """Ask Honeycomb whom the key belongs to; return its answer."""
    try:
        async with session.get(
            f"{REGIONS[region]}/1/auth",
            headers={HEADER_API_KEY: api_key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status in (401, 403):
                raise InvalidAuth
            resp.raise_for_status()
            return await resp.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise CannotConnect from err


class HoneycombConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Honeycomb from the UI."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HoneycombOptionsFlow:
        """What to send: the options."""
        return HoneycombOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the key and check it with Honeycomb."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                auth = await validate_api_key(
                    async_get_clientsession(self.hass),
                    user_input[CONF_API_KEY],
                    user_input[CONF_REGION],
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                team = (auth.get("team") or {}).get("slug")
                environment = (auth.get("environment") or {}).get("slug")
                if team:
                    await self.async_set_unique_id(f"{team}/{environment or ''}")
                    self._abort_if_unique_id_configured()
                title = " / ".join(
                    (auth.get(k) or {}).get("name")
                    for k in ("team", "environment")
                    if (auth.get(k) or {}).get("name")
                )
                return self.async_create_entry(title=title or "Honeycomb", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input),
            errors=errors,
        )


class HoneycombOptionsFlow(OptionsFlowWithReload):
    """Choose what else to send, and what to leave out."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """One form; saving it reloads the integration with the new choices."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.config_entry.options),
        )
