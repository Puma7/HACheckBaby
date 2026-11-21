# CheckBaby documentation

[Deutsche Fassung](../de/README.md)

CheckBaby is a Home Assistant integration that turns signals from Frigate, optional sensors and an optional AI assessment into a baby monitor. **It is not a medical device.** It supports your supervision and the rules for safe infant sleep; it replaces neither.

**Status of this documentation.** Every page describes what the code does today. The integration is covered by automated tests, but it has not yet run against a real camera, a real Frigate, a phone or a radar sensor. Where a page relies on the documentation of Frigate, ESPHome or the companion app instead of our own measurement, it says so.

## Pages

| Page | What it covers |
|---|---|
| [Installation](installation.md) | Requirements, installation through HACS, the setup dialog step by step, the first function test |
| [Frigate](frigate.md) | What CheckBaby reads from Frigate over MQTT, which Frigate settings it needs, and how to run without Frigate |
| [How it works](how-it-works.md) | Child states, the three alert levels, acknowledge and snooze, on duty, modes, the watchdog, the learned noise floor, privacy mode, restarts |
| [Entities and actions](entities-and-actions.md) | Every entity and every action with its fields and return values |
| [AI assessment](ai-assessment.md) | What the AI is asked, when, what it may and may not do, consent and privacy |
| [Vital sources](vital-sources.md) | The breathing-movement hint: radar sensor, vital engine, the rule, shadow mode, known limits |
| [Hardware](hardware.md) | Camera candidates, the buying trap, bill of materials, mounting and cable safety |
| [Safety and privacy](safety-and-privacy.md) | Intended use and limits, safe-sleep basics, network isolation, cloud AI, recording other people |
| [Troubleshooting](troubleshooting.md) | Every monitoring problem and repair issue with cause and fix; missing pushes; silent critical alerts; crying not detected |

## Examples

All examples are untested on real hardware. Each file says so at the top and explains what to adjust.

| File | What it is |
|---|---|
| [`dashboard.yaml`](../examples/dashboard.yaml) | Dashboard view made of standard cards, for a Home Assistant set to English |
| [`dashboard.de.yaml`](../examples/dashboard.de.yaml) | The same view for a Home Assistant set to German (the entity IDs differ, see [Entities and actions](entities-and-actions.md#entity-ids-depend-on-the-language)) |
| [`frigate-camera.yaml`](../examples/frigate-camera.yaml) | Frigate camera section with audio detection for crying |
| [`esphome-mr60bha2.yaml`](../examples/esphome-mr60bha2.yaml) | ESPHome configuration for the Seeed MR60BHA2 radar kit |
| [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml) | ESP32 with a buzzer that sounds when Home Assistant stops sending a heartbeat |
| [`quiet_house.yaml`](../../blueprints/automation/checkbaby/quiet_house.yaml) | Automation blueprint: run actions while the child sleeps and when it wakes |
| [`alert_light.yaml`](../../blueprints/automation/checkbaby/alert_light.yaml) | Automation blueprint: a light shows warning and critical alerts by colour |

The plan behind the project, including what is not built yet, is in [MASTERPLAN.md](../MASTERPLAN.md) (German).
