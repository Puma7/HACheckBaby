# Changelog

## 0.1.0 (unreleased)

First version that monitors. Everything listed is covered by automated tests against Home Assistant 2026.2 and 2026.10. Nothing has run against a real Frigate, camera, phone or radar sensor yet. CheckBaby is not a medical device.

### Integration

- Setup dialog: child (name, birth date or due date), first sleep place, who is told, intended-use notice. Further sleep places as sub-entries. Options for the babysitter's phone, heartbeat buttons, smoke/CO detectors, internet sensor, speaker, AI tasks with consent and budget, Frigate topic prefix and dashboard path.
- Sources: Frigate over MQTT (`audio/crying`, `audio/scream`, `audio/dBFS`, `motion`, `person`, cat/dog in the bed zone, `available`), or entities for crying, motion and sound level. Optional door contact, bed presence, room temperature and humidity, smoke/CO, internet connectivity.
- Child state from durations: asleep, restless, awake, crying, attended, not in bed, unknown.
- Alerts in three levels (hint, warning, critical) for crying, pet in bed, left the bed (toddlers), room climate, smoke/CO, monitoring failure, no internet and an interruption of monitoring.
- Notifications for the iOS and Android companion apps in one message, with a camera picture and the actions "Seen", "Quiet for 5 min" and "Live". Critical alerts as iOS critical alerts and on the Android alarm channel, repeated every 30 seconds. Warnings go to whoever is on duty first and to everyone after three minutes. Local alarm (siren, light, switch) after one minute, at once while the internet is down.
- Acknowledge and snooze; babysitter mode; sensitivity; adjustable thresholds.
- Watchdog for MQTT, Frigate, sound level, a flat microphone, crying sensor, camera, vital engine, radar sensor, notification targets and a missing sleep place. The state shows "unknown" when a core source is down. Message on shutdown, alert after an interruption, heartbeat buttons for an external dead-man buzzer. Repair issues for a missing alert target, a missing sleep place and missing MQTT.
- Learned noise floor that follows the room's own sound.
- Optional AI assessment through `ai_task` with one camera image and a fixed answer structure; fallback order, 20-second timeout, hourly budget, consent. Guard rails: a warning at most on its own, critical only after a confirming second look, no way to clear or lower alerts from other sources, prone rules by age profile.
- Optional breathing-movement hint from a radar breathing-rate entity and the vital engine: fusion "any" or "all", a floor of 20 seconds, shadow mode by default. Unvalidated on infants.
- Audio relay to a speaker, sleeping bag suggestion, sleep log with wake-ups and crying time, quick check and night report as buttons and as actions with return values, a "Quiet time" sensor and an alert event entity for automations.
- Settings, active alerts, the sleep log and the noise floor survive restarts. Diagnostics download with the event log and without the child's details.
- Translations in English and German.

### Vital engine (`engine/`)

- Separate program that looks for breathing-like movement in a camera sub-stream and publishes it over MQTT. Tested with artificial signals only; never run against a real camera. See `engine/README.md`.

### Documentation and examples

- User documentation in English and German (`docs/en`, `docs/de`).
- Examples: dashboard in two language variants, Frigate camera configuration, ESPHome for the Seeed MR60BHA2 and for a dead-man buzzer, two automation blueprints (quiet house, alert light). All untested on real hardware.
