# Honeycomb for Home Assistant

See what your home is doing, and why, in [Honeycomb](https://www.honeycomb.io/).

This [HACS](https://hacs.xyz/) integration sends what happens in a Home Assistant home to
Honeycomb as traces:

- **How long every state lasted.** When a light turns off, a door closes or the heating stops,
  one span covers the time it was on, open or heating, with the entity's domain, area and device
  class. Ask "how long do doors stay open, by door" or "which devices drop off the network, and
  for how long" across the whole house, with nothing to configure.
- **What people did, and how the house responded.** A tap on a dashboard, a voice command or a
  phone-app action becomes a trace: the request, then each device's response and how long it took.
- **Automation runs, with what they caused.** Each run is a trace from its trigger to its end, with
  the service calls it made and the state changes they produced. A command a device ignored shows
  up as a call with no effect, or as superseded when a newer command reached it first.
- **What devices were doing.** A thermostat set to heat is not always heating: each heating
  run is a span of its own, with the temperatures when it ended.
- **Home Assistant's own health:** how long it took to start, restarts, integrations failing to
  load, devices going unavailable.

It runs inside Home Assistant, so there is nothing else to host, and it reads only Home Assistant's
public interfaces, so it does not break when Home Assistant's internals change.

> **Status: early.** 0.1.0 is the first release. See the [roadmap](okf/spec/02-roadmap.md).

## Install

[![Open your Home Assistant instance and open this repository in the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alejandroerickson&repository=honeycomb-hacs&category=integration)

1. In HACS, add this repository as a custom repository (category **Integration**):
   `https://github.com/alejandroerickson/honeycomb-hacs`. The button above does this for you.
2. Install **Honeycomb** and restart Home Assistant.
3. **Settings › Devices & services › Add integration › Honeycomb.** Paste an ingest key from the
   Honeycomb environment the home's telemetry should go to, and choose the region your team is in.
4. To choose what else is sent or left out: **Settings › Devices & services › Honeycomb ›
   Configure**.

Turn it off by disabling the integration.

## What it sends, and what it does not

By default it leaves out people's locations (`device_tracker`, `person`, `zone`), phones' sensors
from the companion app, sensors that describe a body (heart rate, sleep, steps and the like), and
cameras. What else stays home is yours to choose under **Configure**: leave out entities by pattern
(`sensor.*_power`), area or device class; send any of the defaults anyway by naming them; and send
attributes such as `brightness`. See [what is sent](okf/spec/01-telemetry.md).

## Develop

```sh
scripts/bootstrap.sh   # Python 3.14 with uv; turns on the git hooks
uv run pytest
```

How the repository works, the decisions behind it and the full specification are in
[`okf/`](okf/index.md).

## Licence

[MIT](LICENSE).
