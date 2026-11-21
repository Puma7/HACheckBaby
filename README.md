# CheckBaby

A local baby monitor for Home Assistant, built on Frigate and installed through HACS. It turns Frigate's crying, sound-level and motion signals, optional sensors and an optional AI assessment into a child state and three levels of alerts.

[Deutsche Fassung](README.de.md) · [Documentation](docs/en/README.md) · [Dokumentation](docs/de/README.md)

**CheckBaby is not a medical device.** It cannot prevent sudden infant death and it can fail without warning. It supports your supervision and the rules for safe infant sleep; it does not replace either. Keep a simple baby monitor as a fallback.

## Status and limits

Read this before you install it. Version numbers follow the release tags (0.0.1, 0.0.2, …); HACS offers an update when a new release is published.

- The integration is covered by automated tests that run against Home Assistant 2026.2 and 2026.10.
- It also runs in a lab ([lab/README.md](lab/README.md), German): a real Home Assistant with a real MQTT broker, a stand-in for Frigate, simulated phones, sensors and camera, a scripted AI model and the real vital engine process. The lab walks through the setup, the alert chain, failures and restarts in real time.
- **A first installation on a real Home Assistant has taken place, and little more than that.** It led to the fixes in version 0.0.3: phones are now chosen with tick boxes, because a phone chosen in the earlier search field was not saved, and alerts and results are also shown in Home Assistant's own notifications, so that something is visible without a phone.
- **There is still no confirmed evidence that a push arrives on a real phone** and sounds through Do Not Disturb. Nothing is known yet about the MQTT topics of a real Frigate, about a real AI provider (Gemini, OpenRouter, Ollama) accepting the camera picture and judging it well, or about a radar sensor. The lab cannot show any of this. Whether it matches your system is what the first evening will show.
- The vital engine (`engine/`) has been tested with artificial signals only and has never seen a real camera or a real child.
- The hardware examples (Frigate configuration, ESPHome for the radar and the buzzer, blueprints) are untested on real hardware. The English example dashboard was loaded in the lab; the German one was not.
- The breathing-movement hint is unvalidated on infants and switched off by default. It is a hint, not a medical measurement.

## What works today

"Works" means: implemented and covered by the automated tests and the lab. What version 0.0.3 adds (ticking the phones, Home Assistant's notifications, the delivery report) is covered by the automated tests.

- **Setup in the user interface:** five short pages (child, sleep place, who is told, optional AI assessment, intended-use notice), then one switch and one test button. The phones are ticked in a list of the devices that have the companion app; nothing has to be typed. Several sleep places per child, several children.
- **Sources:** Frigate over MQTT (crying, scream, sound level, motion, person, cat or dog in the bed zone, availability), or plain entities for crying, motion and level. Optional door contact, bed presence, room climate, smoke/CO, internet connectivity.
- **Child state:** asleep, restless, awake, crying, attended, not in bed, unknown. Changes follow durations, not single events.
- **Alerts in three levels:** hint, warning, critical. Push notifications with a camera picture and the buttons "Seen", "Quiet for 5 min" and "Live"; critical alerts sent so that they sound through Do Not Disturb, repeated every 30 seconds; a local alarm (siren, light) after a minute; "on duty" and a babysitter mode with phones of its own. Every warning and critical alert also appears in Home Assistant's own notifications, and "Test alert" writes a report there on where the alert went.
- **Watchdog:** every source is watched, and a failure is reported instead of showing "asleep". Losing only the picture, an unused vital source or a local alarm device (while a phone is set up) is shown as a hint without waking anyone. Messages on shutdown and after an interruption; an optional sign of life for an outage buzzer (dead-man buzzer) of your own, which sounds when Home Assistant falls silent.
- **Learned noise floor**, so that white noise does not count as noise all night.
- **AI assessment (optional):** add Google Gemini, OpenRouter or a local model as its own Home Assistant integration, pick it in CheckBaby and confirm; it then runs by itself. One camera image through Home Assistant's AI Task with a fixed answer structure, budget, timeout and fallback order. The AI reaches a warning on its own, a critical alert only after a confirming second look, and it cannot clear or lower an alert from another source.
- **Breathing-movement hint (optional, shadow mode by default):** a rule over a radar entity and the vital engine.
- **Also:** audio relay to a speaker, sleeping bag suggestion, sleep log, quick check and night report as buttons and actions, with the result in Home Assistant's notifications and on the phone, a "Quiet time" sensor and an alert event for your own automations, diagnostics download.

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
3. Go to Settings → Devices & services → Add integration → CheckBaby and answer five short pages.
4. On the device page, press "Test alert" with your phone silenced and check that it sounds. The bell in Home Assistant then shows where the alert went. Switch on "Monitoring" when the child sleeps.

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

See [AGENTS.md](AGENTS.md), the [lab](lab/README.md) and the [checklist for the tests on real hardware](docs/development/phase-0-checkliste.md) (both German). Changes are listed in [CHANGELOG.md](CHANGELOG.md).
