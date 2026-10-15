"""Tests for sending spans to Honeycomb."""

from __future__ import annotations

from datetime import UTC, datetime

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.honeycomb import sender as sender_module
from custom_components.honeycomb.otlp import Span
from custom_components.honeycomb.sender import SpanSender

from .common import TRACES_URL, sent_spans

START = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def _span(number: int) -> Span:
    return Span(f"span {number}", START, START, {})


@pytest.fixture
async def sender(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> SpanSender:
    return SpanSender(
        hass,
        api_key="test-key",
        region="us",
        resource={"service.name": "home-assistant"},
        scope_version="0.1.0",
    )


def _names(aioclient_mock: AiohttpClientMocker) -> list[str]:
    return [span["name"] for span in sent_spans(aioclient_mock)]


async def test_flush(sender: SpanSender, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(TRACES_URL)
    sender.add(_span(0))
    sender.add(_span(1))
    await sender.async_flush()
    assert aioclient_mock.call_count == 1
    _method, _url, body, headers = aioclient_mock.mock_calls[0]
    assert headers["X-Honeycomb-Team"] == "test-key"
    resource_spans = body["resourceSpans"][0]
    assert resource_spans["resource"]["attributes"] == [
        {"key": "service.name", "value": {"stringValue": "home-assistant"}}
    ]
    assert resource_spans["scopeSpans"][0]["scope"] == {"name": "honeycomb-hacs", "version": "0.1.0"}
    assert _names(aioclient_mock) == ["span 0", "span 1"]
    assert sender.queued == 0


async def test_nothing_queued(sender: SpanSender, aioclient_mock: AiohttpClientMocker) -> None:
    await sender.async_flush()
    assert aioclient_mock.call_count == 0


async def test_eu_region(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post("https://api.eu1.honeycomb.io/v1/traces")
    sender = SpanSender(hass, api_key="test-key", region="eu", resource={}, scope_version="0.1.0")
    sender.add(_span(0))
    await sender.async_flush()
    assert aioclient_mock.call_count == 1


async def test_batches(
    hass: HomeAssistant,
    sender: SpanSender,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sender_module, "MAX_BATCH", 2)
    aioclient_mock.post(TRACES_URL)
    for number in range(5):
        sender.add(_span(number))
    await hass.async_block_till_done()
    await sender.async_flush()
    assert [
        len(body["resourceSpans"][0]["scopeSpans"][0]["spans"]) for _, _, body, _ in aioclient_mock.mock_calls
    ] == [
        2,
        2,
        1,
    ]
    assert _names(aioclient_mock) == [f"span {number}" for number in range(5)]


async def test_full_batch_is_sent_at_once(
    hass: HomeAssistant,
    sender: SpanSender,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sender_module, "MAX_BATCH", 2)
    aioclient_mock.post(TRACES_URL)
    sender.add(_span(0))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 0
    sender.add(_span(1))
    await hass.async_block_till_done()
    assert _names(aioclient_mock) == ["span 0", "span 1"]


@pytest.mark.parametrize(
    "failure",
    [
        {"status": 500},
        {"status": 503},
        {"status": 429},
        {"exc": aiohttp.ClientConnectionError()},
        {"exc": TimeoutError()},
    ],
)
async def test_kept_when_honeycomb_fails(
    sender: SpanSender, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture, failure: dict
) -> None:
    aioclient_mock.post(TRACES_URL, **failure)
    sender.add(_span(0))
    sender.add(_span(1))
    await sender.async_flush()
    await sender.async_flush()
    assert aioclient_mock.call_count == 2
    assert sender.queued == 2
    assert caplog.text.count("Cannot send to Honeycomb") == 1

    aioclient_mock.clear_requests()
    aioclient_mock.post(TRACES_URL)
    sender.add(_span(2))
    await sender.async_flush()
    assert _names(aioclient_mock) == ["span 0", "span 1", "span 2"]
    assert "Sending to Honeycomb again" in caplog.text


async def test_refused_batch_is_dropped(
    sender: SpanSender, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
) -> None:
    aioclient_mock.post(TRACES_URL, status=400, text="bad span")
    sender.add(_span(0))
    await sender.async_flush()
    assert sender.queued == 0
    assert "Honeycomb refused 1 spans (HTTP 400): bad span" in caplog.text


async def test_full_queue_drops_oldest(
    sender: SpanSender,
    aioclient_mock: AiohttpClientMocker,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(sender_module, "MAX_QUEUE", 3)
    aioclient_mock.post(TRACES_URL)
    for number in range(5):
        sender.add(_span(number))
    assert sender.queued == 3
    assert caplog.text.count("dropping the oldest") == 1
    await sender.async_flush()
    assert _names(aioclient_mock) == ["span 2", "span 3", "span 4"]
    assert "2 spans were dropped" in caplog.text


async def test_failed_batch_returns_ahead_of_newer_spans(
    sender: SpanSender, aioclient_mock: AiohttpClientMocker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When spans arrive during a failed send and fill the queue, the oldest are the ones dropped."""
    monkeypatch.setattr(sender_module, "MAX_QUEUE", 3)

    async def _fail_while_more_arrive(method, url, data):
        sender.add(_span(3))
        sender.add(_span(4))
        return AiohttpClientMockResponse(method, url, status=500)

    aioclient_mock.post(TRACES_URL, side_effect=_fail_while_more_arrive)
    for number in range(3):
        sender.add(_span(number))
    await sender.async_flush()
    assert sender.queued == 3

    aioclient_mock.clear_requests()
    aioclient_mock.post(TRACES_URL)
    await sender.async_flush()
    assert _names(aioclient_mock) == ["span 2", "span 3", "span 4"]
