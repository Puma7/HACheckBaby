# CheckBaby

A local baby monitor for Home Assistant, built on Frigate and installed through HACS. It turns Frigate's crying, sound-level and motion signals, optional sensors and an optional AI assessment into a child state and three levels of alerts.

[Deutsche Fassung](README.de.md) · [Documentation](docs/en/README.md) · [Dokumentation](docs/de/README.md)

**CheckBaby is not a medical device.** It cannot prevent sudden infant death and it can fail without warning. It supports your supervision and the rules for safe infant sleep; it does not replace either. Keep a simple baby monitor as a fallback.

## Status and limits

Version 0.1.0 is unreleased. Read this before you install it.

- The integration is covered by automated tests that run against Home Assistant 2026.2 and 2026.10.
- **It has not yet run against a real Frigate, camera, phone or radar sensor.** The MQTT topics, the format of the push notifications and the AI call follow the documentation of Frigate, the companion app and Home Assistant. Whether they match your system is what the first evening will show.
- The vital engine (`engine/`) has been tested with artificial signals only and has never seen a real camera or a real child.
- All hardware examples (Frigate configuration, ESPHome for the radar and the buzzer, dashboards, blueprints) are untested on real hardware.
- The breathing-movement hint is unvalidated on infants and switched off by default. It is a hint, not a medical measurement.

## What works today

"Works" means: implemented and covered by the automated tests.

- **Setup in the user interface:** child, sleep places with their camera and sensors, who is told, intended-use notice. Several sleep places per child, several children.
- **Sources:** Frigate over MQTT (crying, scream, sound level, motion, person, cat or dog in the bed zone, availability), or plain entities for crying, motion and level. Optional door contact, bed presence, room climate, smoke/CO, internet connectivity.
- **Child state:** asleep, restless, awake, crying, attended, not in bed, unknown. Changes follow durations, not single events.
- **Alerts in three levels:** hint, warning, critical. Push notifications with a camera picture and the buttons "Seen", "Quiet for 5 min" and "Live"; critical alerts sent so that they sound through Do Not Disturb, repeated every 30 seconds; a local alarm (siren, light) after a minute; "on duty" and a babysitter mode.
- **Watchdog:** every source is watched, and a failure is reported instead of showing "asleep". Messages on shutdown and after an interruption; heartbeat for an external dead-man buzzer.
- **Learned noise floor**, so that white noise does not count as noise all night.
- **AI assessment (optional):** one camera image through Home Assistant's AI Task with a fixed answer structure, budget, timeout and fallback order. The AI reaches a warning on its own, a critical alert only after a confirming second look, and it cannot clear or lower an alert from another source.
- **Breathing-movement hint (optional, shadow mode by default):** a rule over a radar entity and the vital engine.
- **Also:** audio relay to a speaker, sleeping bag suggestion, sleep log, quick check and night report as buttons and actions, a "Quiet time" sensor and an alert event for your own automations, diagnostics download.

Not built yet, among other things: a guided function test, a warning before an update, a custom dashboard card, cough detection, a Baby Buddy link. The full list is in section 11 of [docs/MASTERPLAN.md](docs/MASTERPLAN.md) (German).

## Requirements

- Home Assistant 2026.2 or newer, with HACS
- An MQTT broker and the MQTT integration
- Frigate with audio detection for the camera at the bed; `crying` has to be added to its `listen` list, because it is not a Frigate default
- The Home Assistant companion app on the parents' phones
- Recommended: a siren or light in your bedroom as a local alarm that works without the internet

## Install

1. In HACS, add `https://github.com/Puma7/HACheckBaby` as a custom repository of type "Integration".
2. Download "CheckBaby" and restart Home Assistant.
3. Go to Settings → Devices & services → Add integration → CheckBaby.
4. Press the button "Test alert" with your phone silenced, and check that it sounds.

The steps in detail, including the first function test, are in [Installation](docs/en/installation.md).

## Documentation

| | |
|---|---|
| [Installation](docs/en/installation.md) | Requirements, setup dialog, first function test |
| [Frigate](docs/en/frigate.md) | MQTT topics, Frigate settings, running without Frigate |
| [How it works](docs/en/how-it-works.md) | States, alert levels, watchdog, privacy mode |
| [Entities and actions](docs/en/entities-and-actions.md) | Every entity and action |
| [AI assessment](docs/en/ai-assessment.md) | What the AI may and may not do, consent |
| [Vital sources](docs/en/vital-sources.md) | The breathing-movement hint and its limits |
| [Hardware](docs/en/hardware.md) | Cameras, bill of materials, cable safety |
| [Safety and privacy](docs/en/safety-and-privacy.md) | Intended use, safe sleep, privacy |
| [Troubleshooting](docs/en/troubleshooting.md) | Problems and fixes |

Examples are in [docs/examples](docs/examples) and [blueprints](blueprints/automation/checkbaby).

## Development

See [AGENTS.md](AGENTS.md) and the [checklist for the tests on real hardware](docs/development/phase-0-checkliste.md) (German). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
