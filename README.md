# CheckBaby

A local, smart baby monitor for Home Assistant, built on Frigate and installed through HACS.

[Deutsche Fassung](README.de.md)

**Status: early development.** The integration installs and can be set up for a child, but it does not monitor anything yet. Detection, alerts and the watchdog arrive with version 0.1 (phase 1 of the plan).

**CheckBaby is not a medical device.** It cannot prevent sudden infant death and it can fail without warning. It supports your supervision and the rules for safe infant sleep; it does not replace either.

## Plan

The full plan (in German) is in [docs/MASTERPLAN.md](docs/MASTERPLAN.md): architecture, alert levels, hardware, feature list and roadmap.

## Install (for testing)

1. In HACS, add `https://github.com/Puma7/HACheckBaby` as a custom repository of type "Integration".
2. Install "CheckBaby" and restart Home Assistant.
3. Go to Settings → Devices & services → Add integration → CheckBaby.

Requires Home Assistant 2026.2 or newer.

## Development

See [AGENTS.md](AGENTS.md).
