"""Tests for spans and their OTLP/JSON encoding."""

from datetime import UTC, datetime, timedelta

from custom_components.honeycomb.otlp import Span, encode_request, unix_nano

START = datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=UTC)


def test_unix_nano_is_exact() -> None:
    assert unix_nano(START) == 1767323045_678901000


def test_span() -> None:
    span = Span(
        "light on",
        START,
        START + timedelta(seconds=1.5),
        {"text": "x", "flag": True, "count": 3, "value": 1.5},
        trace_id="ab" * 16,
        span_id="cd" * 8,
    )
    assert span.to_otlp() == {
        "traceId": "ab" * 16,
        "spanId": "cd" * 8,
        "name": "light on",
        "kind": 1,
        "startTimeUnixNano": "1767323045678901000",
        "endTimeUnixNano": "1767323047178901000",
        "attributes": [
            {"key": "text", "value": {"stringValue": "x"}},
            {"key": "flag", "value": {"boolValue": True}},
            {"key": "count", "value": {"intValue": "3"}},
            {"key": "value", "value": {"doubleValue": 1.5}},
        ],
    }


def test_parent() -> None:
    span = Span("child", START, START, {}, parent_span_id="ef" * 8)
    assert span.to_otlp()["parentSpanId"] == "ef" * 8


def test_ids_are_random() -> None:
    first, second = Span("a", START, START, {}), Span("b", START, START, {})
    assert len(first.trace_id) == 32 and len(first.span_id) == 16
    assert first.trace_id != second.trace_id and first.span_id != second.span_id
    int(first.trace_id, 16), int(first.span_id, 16)


def test_request() -> None:
    span = Span("a", START, START, {})
    assert encode_request([span], {"service.name": "home-assistant"}, "honeycomb-hacs", "0.1.0") == {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "home-assistant"}}]
                },
                "scopeSpans": [
                    {"scope": {"name": "honeycomb-hacs", "version": "0.1.0"}, "spans": [span.to_otlp()]}
                ],
            }
        ]
    }
