"""Constants for the Honeycomb integration."""

from typing import Final

DOMAIN: Final = "honeycomb"

CONF_REGION: Final = "region"
CONF_SERVICE_NAME: Final = "service_name"

DEFAULT_SERVICE_NAME: Final = "home-assistant"

# Honeycomb's API hosts, by the region a team's data lives in.
REGIONS: Final = {
    "us": "https://api.honeycomb.io",
    "eu": "https://api.eu1.honeycomb.io",
}
DEFAULT_REGION: Final = "us"

# Honeycomb authenticates every request, ingest and API alike, with this header.
HEADER_API_KEY: Final = "X-Honeycomb-Team"

# The instrumentation scope every span is sent under.
SCOPE_NAME: Final = "honeycomb-hacs"

# Options: what the user includes, leaves out, and allows (okf/spec/01-telemetry.md, 1.5).
CONF_INCLUDE: Final = "include"
CONF_EXCLUDE: Final = "exclude"
CONF_EXCLUDE_AREAS: Final = "exclude_areas"
CONF_EXCLUDE_DEVICE_CLASSES: Final = "exclude_device_classes"
CONF_ATTRIBUTES: Final = "attributes"
