# Troubleshooting

[Deutsche Fassung](../de/troubleshooting.md) · [Back to the index](README.md)

Start with two places:

- The sensor **Monitoring problems** on the device. Its attribute `problems` lists what the watchdog has found.
- **Settings → System → Repairs** for the three repair issues.

For anything unexpected, use **Download diagnostics** on the CheckBaby entry. The file contains the event log with the cause of every decision.

CheckBaby has been installed on a real Home Assistant once so far. Nothing is confirmed yet about a real Frigate, a push on a real phone, a real AI provider or a radar sensor, so a mismatch with any of them is a real possibility. If something does not behave as described here, the MQTT topic and payload, or the error from the Home Assistant log, are the most useful things for a bug report.

## Monitoring problems

The names are the ones in the attribute `problems`. In a notification they appear in words.

| Problem | In the notification | Cause | What to do |
|---|---|---|---|
| `mqtt` | MQTT disconnected | The MQTT integration is not loaded or has lost the broker. | Check the broker and the MQTT integration. CheckBaby subscribes by itself once MQTT is back. |
| `frigate` | Frigate offline | `<prefix>/available` does not say `online`, or nothing arrived on it within two minutes after the start. | Check that Frigate is running, that MQTT is enabled in Frigate, and that the topic prefix in the CheckBaby options matches Frigate's `topic_prefix`. |
| `audio_level` | no sound from the camera | No value on `<prefix>/<camera>/audio/dBFS` for more than 60 seconds. Without Frigate: the sound level sensor has no numeric value. | Check that the stream has an audio track, that the input has the role `audio`, that audio detection is enabled for this camera, and that the "Frigate camera name" is spelled exactly as in Frigate. |
| `microphone` | microphone signal flat | Levels arrive, but the value has not changed at all for 10 minutes. | The microphone may be dead or muted in the camera's settings. Listen to the stream. This check applies to Frigate's level only, not to a sound level sensor entity. |
| `cry_sensor` | crying sensor unavailable | Without Frigate: the crying sensor is unavailable or unknown. | Check the device that provides it. |
| `camera` | camera unavailable | The camera entity does not exist or is unavailable. | Check the camera integration in Home Assistant. Alerts still work; the picture and the AI assessment do not. |
| `engine` | vital engine offline | The vital engine reported `offline`, or sent no state for more than 30 seconds. | Check that the engine runs, that it reaches the broker, that its ID matches "Vital engine ID" and that its topic prefix is still `checkbaby/engine`. |
| `vital_sensor` | radar sensor unavailable | The breathing rate sensor has no numeric value, or it has not reported for more than 120 seconds. | Check the radar device and its Wi-Fi. If the device is fine, the sensor probably reports only when its value changes: make it report regularly, and remove filters that suppress repeated values. |
| `notify` | a notification target is missing | A configured phone's notify service does not exist; or no phone is configured and no local alarm device is set or reachable. | See [No notification arrives on the phone](#no-notification-arrives-on-the-phone). |
| `local_alarm` | local alarm unreachable | An entity chosen under "Local alarm" is missing or `unavailable` in Home Assistant, for example a smart lamp that is switched off at the wall switch. | Give the device power and check its integration. The delivery report of "Test alert" names the device. A lamp used as an alarm must stay switched on at the wall. |
| `sleep_place` | no sleep place is active | The entry has no sleep place. | Add one with "Add sleep place". |

The problems have two grades:

- **Minor:** `camera` and `local_alarm` always, and `engine` and `vital_sensor` as long as the switch "Breathing-movement alert" is off. They are shown in the list, the binary sensor "Monitoring problem" is on and the alert level shows "Hint", but no notification is sent and the state does not change.
- **Serious:** all others, and `engine` and `vital_sensor` once the switch "Breathing-movement alert" is on. While Monitoring is on, they raise the warning "Monitoring of (name) is impaired" and, after five minutes, a critical alert. With `mqtt` (when a Frigate camera is used), `frigate`, `audio_level`, `cry_sensor` or `sleep_place` the state also shows "Unknown".

If you use an outage buzzer (dead-man buzzer): its sign of life stops only while a serious problem exists. A minor problem does not make the buzzer sound.

In the first two minutes after a start, a source that has simply not reported yet is not a problem.

## Repair issues

| Issue | Cause | What to do |
|---|---|---|
| CheckBaby cannot alert anyone for (name) | Neither a phone nor a local alarm is configured. | Open **Configure → Who is told** on the entry and tick a phone or choose a local alarm. |
| No sleep place is set up for (name) | The entry has no sleep place, for example because you deleted the only one. | Add one on the entry with "Add sleep place". |
| CheckBaby needs MQTT for (name) | The active sleep place uses a Frigate camera or the vital engine, but the MQTT integration is not set up. | Set up MQTT. CheckBaby notices within seconds, subscribes to its topics and removes the issue. If the issue stays, reload the CheckBaby entry. |

## No notification arrives on the phone

Start with the test alert, because it reports where it went.

### The test alert does not arrive

1. **Press "Test alert"** on the device page (it is listed under Diagnostic). It works even while Monitoring is off.
2. **Read the delivery report.** Open Home Assistant's notifications (the bell in the sidebar). Besides the alert itself there is a second entry that says where the alert went:

   | The report says | What to do |
   |---|---|
   | "No phone is chosen, so no push was sent." | Open **Configure → Who is told** on the CheckBaby entry and tick the phone under "Phones". |
   | "Could NOT be sent to: notify.…" | Home Assistant does not have this notify service any more, or the service reported an error. This happens for example after a phone was renamed or the app was installed again. Open **Configure → Who is told**: a target that no longer exists is still listed, with a "?" behind its name. Untick it and tick the phone under its current name. |
   | "Sent to: notify.…" | Home Assistant handed the message over. If nothing shows on the phone, the reason is on the phone or on the way to it; continue at 4. |
   | "Local alarm NOT reachable: …" | See `local_alarm` in the table above. |

3. **The phone is not in the list under "Phones"?** Open the Home Assistant app on that phone and sign in to your Home Assistant. The phone then appears in the list under its device name. The documentation of the companion app says that a restart of Home Assistant can be needed before a new phone shows up.
4. **The report says "Sent", but nothing shows on the phone:**
   - Check in the phone's settings that the Home Assistant app is allowed to send notifications.
   - On iOS, also allow critical alerts, see [A critical alert does not sound](#a-critical-alert-does-not-sound).
   - On Android, check Do Not Disturb and the battery optimisation: allow the app to override Do Not Disturb and exclude it from battery optimisation, so that the phone does not put it to sleep.
   - Check the connection. A push normally needs the internet, at home and on the phone.
5. **Look at the log.** Switch on debug logging: **Settings → Devices & services → CheckBaby**, then **Enable debug logging** in the menu of the entry. Or put this into `configuration.yaml` and restart:

   ```yaml
   logger:
     logs:
       custom_components.checkbaby: debug
   ```

   Press "Test alert" again and look at the full log under **Settings → System → Logs**. If you used the menu, switching debug logging off again offers the log as a download. It contains lines such as `Alert test (critical, first) goes to ['mobile_app_annas_iphone']`, or `goes to no phone` if none is chosen, and `Local alarm on: [...]` when the local alarm is switched. A notify service that failed is logged with its error.

### The test alert arrives, but a real alert does not

The path to the phone is fine then, and the reason is in the rules.

1. **Is Monitoring on, and privacy mode off?** While Monitoring is off or privacy mode is on, only smoke/CO and the test alert notify.
2. **Who is on duty?** A warning goes only to the phone selected in "On duty" at first, and to all phones after three minutes.
3. **Is the phone ticked only under "Babysitters' phones"?** Those phones receive alerts only while the mode is "Babysitter".
4. **Is a quiet time running?** After "Quiet for 5 min", warnings are held back.
5. **Was it only a hint?** Hints (for example loose objects in the bed, a room slightly too warm, no internet) are never sent. They show in the sensors "Alert level" and "Alert reason".
6. **Did someone count as being with the child?** While the door contact is open, or the camera sees a person and you turned that option on, the state is "Attended" and child-related alerts pause. If the state is "Attended" without anyone in the room, Frigate probably detects the child as a person: turn the option off.
7. **Did the same warning just end?** A warning that was on the phones and comes back within two minutes is not sent again.

If the notification arrives without a picture: the sleep place needs a camera entity, and the phone must be able to reach your Home Assistant, away from home through the external address.

If "Seen" on the notification does nothing: the button needs a connection from the phone back to Home Assistant. Use the button "Seen" on the dashboard instead.

## A critical alert does not sound

A critical alert is meant to sound although the phone is silent or on Do Not Disturb. The phone only allows that if the companion app has the permission. What follows is taken from the companion app's documentation and not from our own test.

**iPhone**

- Open the phone's **Settings → Notifications → Home Assistant** and turn on **Critical Alerts**. iOS asks for this permission the first time a critical alert arrives; if you declined then, turn it on here.
- Critical alerts have their own volume. CheckBaby sends them at full volume.

**Android**

- CheckBaby sends critical alerts on the channel `alarm_stream`, which plays over the alarm volume. Check that the **alarm volume** is not at zero.
- Allow the Home Assistant app to **override Do Not Disturb** (the phone's settings for Do Not Disturb access), and exclude the app from **battery optimisation**.
- Warnings use a separate channel named "CheckBaby". Its sound and importance can be changed in the app's notification settings; make sure it is not muted.

Then repeat the test: phone silent, Do Not Disturb on, press "Test alert".

If it still stays silent, rely on the local alarm and your fallback monitor, and report what you found.

## Crying is not detected

1. **Does Frigate report crying?** Watch the topic with an MQTT tool while you play a recording of a crying baby next to the camera:

   ```bash
   mosquitto_sub -h BROKER -u USER -P PASSWORD -v -t 'frigate/+/audio/#'
   ```

   You should see `frigate/<camera>/audio/dBFS` with changing numbers and `frigate/<camera>/audio/crying` switching to `ON`.
2. **No `dBFS` at all:** the stream has no sound or the audio role is missing. See [Frigate](frigate.md).
3. **`dBFS` arrives, `crying` never turns `ON`:** `crying` is missing in Frigate's `listen` list (it is not a default), or Frigate's thresholds (`min_volume`, the label's `threshold`) are too strict for your room.
4. **`crying` turns `ON` in MQTT, but the binary sensor "Crying" stays off:** the "Frigate camera name" in the sleep place or the topic prefix under **Configure → Other devices and settings** does not match, or a different sleep place is active.
5. **The binary sensor "Crying" turns on, but no warning comes:** the crying has to last without a break. Check "Crying before a warning" and "Sensitivity". If Frigate switches `crying` off and on again every few seconds, the count restarts each time; look at Frigate's `max_not_heard`.
6. **Then check the list under [No notification arrives on the phone](#no-notification-arrives-on-the-phone).**

If a sleep place has both a Frigate camera name and a crying sensor, only Frigate is used and the crying sensor is ignored. To use the crying sensor, clear the Frigate camera name.

## The state is "Unknown"

"Unknown" means CheckBaby does not know how the child is. The reasons: privacy mode is on; a core source has a problem (look at "Monitoring problems"); or CheckBaby has just started and the sources have not reported yet.

## The AI assessment does nothing

- **Press "AI check now"** on the device page and read the result in Home Assistant's notifications (the bell in the sidebar). It shows the AI's verdict, or it says why no check ran: no AI task chosen, sending pictures not confirmed, privacy mode on, the sleep place has no camera entity, a check is already running, or the AI gave no usable answer (with the provider's error).
- An AI model **and** the consent tick are needed, from the setup or under **Configure → AI assessment**. The list under "AI model (an "AI task" of Home Assistant)" is empty until an AI integration has been added to Home Assistant (Google Gemini, OpenRouter, Ollama); see [AI assessment](ai-assessment.md#what-an-ai-task-is-and-where-it-comes-from).
- The switch "AI assessment" is on by default. If someone switched it off, the automatic assessments pause.
- The sleep place needs a camera entity.
- Automatic assessments run only while Monitoring is on, privacy mode is off and nobody is with the child.
- The sensor "AI calls in the last hour" shows whether the budget is used up.
- If "AI assessment available" is off, the last attempt failed: every AI task timed out after 20 seconds, returned an error or gave an answer without the required fields. The result of "AI check now" and the event log in the diagnostics name the error. Some providers may not accept a camera image through AI Task; that has not been tried yet.

## "Breathing movement" stays unknown

No vital source is usable. With a radar: the entity has no numeric state, or it has not reported for more than 120 seconds. With the vital engine: it reports `unusable` (covered, too dark, child not in the picture), it is offline, or its messages do not arrive. See [Vital sources](vital-sources.md).

## The entity IDs in the examples do not exist

The examples use a child named "baby". Your IDs contain your child's name, and on a Home Assistant set to German they are built from the German entity names. See [Entities and actions](entities-and-actions.md#entity-ids-depend-on-the-language).

## The local alarm does not switch off

The local alarm follows the alerts. It is switched off when the alert that switched it on is acknowledged with "Seen", is over, or, for a warning, is snoozed with "Quiet for 5 min". A local alarm that is on because of a critical alert is not switched off by "Quiet for 5 min"; tap "Seen".

CheckBaby compares the alarm with the alerts every two seconds and also after a restart, so an alarm that was left on is switched off by itself. If a siren stays on although the sensor "Alert level" shows no warning or critical alert, switch it off by hand and send the diagnostics.
