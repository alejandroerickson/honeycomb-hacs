"""Spans, and their encoding as OTLP/JSON.

The encoding follows https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding: ids in hex,
64-bit integers as strings, enums as numbers.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

type AttributeValue = str | bool | int | float

SPAN_KIND_INTERNAL = 1

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def new_trace_id() -> str:
    """A random 16-byte trace id, in hex."""
    return secrets.token_hex(16)


def new_span_id() -> str:
    """A random 8-byte span id, in hex."""
    return secrets.token_hex(8)


def unix_nano(when: datetime) -> int:
    """Nanoseconds since the epoch, exact to the microsecond a datetime holds."""
    return (when - _EPOCH) // timedelta(microseconds=1) * 1000


@dataclass(slots=True)
class Span:
    """One span, ready to send."""

    name: str
    start: datetime
    end: datetime
    attributes: dict[str, AttributeValue]
    trace_id: str = field(default_factory=new_trace_id)
    span_id: str = field(default_factory=new_span_id)
    parent_span_id: str | None = None

    def to_otlp(self) -> dict[str, Any]:
        """The span as an OTLP/JSON object."""
        span: dict[str, Any] = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "name": self.name,
            "kind": SPAN_KIND_INTERNAL,
            "startTimeUnixNano": str(unix_nano(self.start)),
            "endTimeUnixNano": str(unix_nano(self.end)),
            "attributes": encode_attributes(self.attributes),
        }
        if self.parent_span_id:
            span["parentSpanId"] = self.parent_span_id
        return span


def encode_value(value: AttributeValue) -> dict[str, Any]:
    """An attribute's value as an OTLP AnyValue."""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}


def encode_attributes(attributes: dict[str, AttributeValue]) -> list[dict[str, Any]]:
    """Attributes as OTLP key-value pairs."""
    return [{"key": key, "value": encode_value(value)} for key, value in attributes.items()]


def encode_request(
    spans: list[Span], resource: dict[str, AttributeValue], scope_name: str, scope_version: str
) -> dict[str, Any]:
    """The body of a request to `/v1/traces`."""
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": encode_attributes(resource)},
                "scopeSpans": [
                    {
                        "scope": {"name": scope_name, "version": scope_version},
                        "spans": [span.to_otlp() for span in spans],
                    }
                ],
            }
        ]
    }
