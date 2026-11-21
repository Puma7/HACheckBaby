# Changelog

## 0.0.3 (unreleased)

- Setup: a new optional page for the AI assessment, with a note on where the model itself is added (Google Gemini, OpenRouter or a local model, as their own Home Assistant integrations).
- Options: three short pages (who is told, AI assessment, other devices) instead of one long form.
- The switch "AI assessment" is on by default and only pauses the assessment; it runs once an AI task and the consent are set.
- After setup, a note says to switch on "Monitoring" and to press "Test alert" once.
- The version number now follows the release tags.
- Who is told: the phones are chosen with tick boxes. Every phone with the Home Assistant companion app is listed by its device name; other notify services are listed as `notify.<name>`; a target that no longer exists stays in the list with a "?" so that it can be unticked. In the first installation on a real Home Assistant, a phone chosen in the earlier search field was not saved.
- Several babysitter phones: the field is now "Babysitters' phones", with tick boxes. They are told only while the mode is "Babysitter", in addition to the parents' phones. A phone ticked only there is refused with a message of its own.
- The field for the heartbeat buttons of a dead-man buzzer is now called "Sign of life for an outage buzzer (optional)" and explains what such a buzzer is.
- The heartbeat for an outage buzzer continues when only minor problems exist (a lost camera picture, an unused vital source, an unreachable local alarm while a phone is set up). It stops for serious problems only.
- New monitoring problem `local_alarm` ("local alarm unreachable"): a local alarm entity is missing or unavailable, for example a smart lamp switched off at the wall. It is a minor problem. If no phone is set up and no local alarm entity can be reached, `notify` is raised instead, which is serious.
- Alerts also appear in Home Assistant's own notifications (the bell in the sidebar): created when an alert is first sent or rises a level, removed when it ends or is answered.
- "Test alert" writes a delivery report there that stays after the test is answered: which notify services accepted the message, which could not be reached, which local alarm entities are set or unreachable, and what to check on the phone.
- The buttons "Quick check", "Send night report" and "AI check now" show their result in Home Assistant's notifications and send it to the phone on duty. "AI check now" shows the verdict with confidence and reason, or says why no check ran. The actions `checkbaby.quick_check` and `checkbaby.night_report` write the notification too when called with `notify: true`; `checkbaby.assess_now` is unchanged.
- The AI field is now labelled "AI model (an "AI task" of Home Assistant)" and explains where an AI task comes from.
- Fixed: an ended hint or snoozed warning no longer swallows the first notification of the next real warning.
- Fixed: right after a restart of Home Assistant, phones and devices of other integrations that were still loading counted as missing and raised a monitoring warning. They are judged once Home Assistant has finished starting.
- Fixed: a second test alert at warning level within two minutes of the first was raised without a notification.
- Documentation: the phone as the main alarm and the local alarm as the path without internet, wall displays and tablets, a checklist "No notification arrives on the phone", what an AI task is.

## 0.0.2

Fixes found by the lab (a real Home Assistant with simulated devices): a false "attended" state for 20 seconds after every start, a critical monitoring failure for a radar without a reading while the breathing-movement alert was off, a local alarm that came late after the step to critical, and a state that lagged behind the crying warning.

## 0.0.1

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
