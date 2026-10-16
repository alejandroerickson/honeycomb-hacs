"""Helpers shared by the tests."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_API_KEY
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.const import CONF_REGION, CONF_SERVICE_NAME

TRACES_URL = "https://api.honeycomb.io/v1/traces"
ENTRY_DATA = {CONF_API_KEY: "test-key", CONF_REGION: "us", CONF_SERVICE_NAME: "home-assistant"}


def sent_spans(aioclient_mock: AiohttpClientMocker) -> list[dict[str, Any]]:
    """Every span posted to Honeycomb, in order."""
    return [
        span
        for _method, url, body, _headers in aioclient_mock.mock_calls
        if str(url) == TRACES_URL
        for resource_spans in body["resourceSpans"]
        for scope_spans in resource_spans["scopeSpans"]
        for span in scope_spans["spans"]
    ]


def attributes(span: dict[str, Any]) -> dict[str, Any]:
    """A span's attributes as a plain dict."""
    return {
        item["key"]: int(value) if kind == "intValue" else value
        for item in span["attributes"]
        for kind, value in item["value"].items()
    }
