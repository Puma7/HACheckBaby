# How it works

[Deutsche Fassung](../de/how-it-works.md) · [Back to the index](README.md)

CheckBaby looks at its signals every two seconds, and at once when a watched entity changes. Each time it does three things: it works out the child's state, it decides which alerts should be active, and it decides who has to be told now.

All durations on this page are the values in the code. Those you can change are marked; the entities that change them are listed in [Entities and actions](entities-and-actions.md). None of the timings have been tuned with a real child yet.

## The child's state

The sensor **State** has seven values. A change always depends on how long something has lasted, never on a single event.

| State | Meaning |
|---|---|
| Asleep | In bed and calm. |
| Restless | Movement or noise for a while, but not awake yet. |
| Awake | Awake, or just put down, and not crying. |
| Crying | Crying or screaming. |
| Attended | Someone is with the child. Child-related alerts pause. |
| Not in bed | The presence sensor says the bed is empty. |
| Unknown | CheckBaby cannot tell, because a core source is down or privacy mode is on. |

"Noise" here means that the sound level is above the learned noise floor by more than the margin you set (15 dB by default). "Calm" means no movement and no noise.

The rules are checked in this order:

1. **Unknown** if a core source has a problem (see [the watchdog](#the-watchdog)) or privacy mode is on. A missing signal is never shown as "Asleep".
2. **Attended** while the door contact is open or the camera sees a person (if you turned that option on), and for 20 seconds after the door closed or the person left.
3. **Not in bed** while the presence sensor is off.
4. **Crying** once crying has been heard without a break for 8 seconds, or screaming for 3 seconds. If the crying time before a warning is shorter than 8 seconds (through "Sensitivity" or babysitter mode), the state follows that shorter time, so that it never lags behind the warning. The state stays "Crying" until neither has been heard for 60 seconds; then it becomes "Awake".
5. Otherwise the state moves like this:

| From | To | When |
|---|---|---|
| Asleep | Restless | Movement or noise without a break for 20 seconds |
| Restless | Asleep | Calm for 120 seconds |
| Restless | Awake | Still moving or noisy 180 seconds after becoming restless |
| Awake | Asleep | Calm for 300 seconds |
| Attended, Not in bed | Awake | As soon as the reason ends; the child counts as awake until it has been calm for 300 seconds |
| Unknown | Asleep or Awake | When the signal is back: asleep if there is neither movement nor noise at that moment, otherwise awake |

These seven durations are fixed in this version. The plan foresees setting them per age profile; that is not implemented.

The state is worked out even while Monitoring is off. Only the alerts depend on the switch.

With the actions `checkbaby.start_sleep` and `checkbaby.end_sleep` you can set the state to "Asleep" or "Awake" by hand; the rules continue from there.

## Which alerts exist

| Alert reason | Level | When |
|---|---|---|
| Crying | Warning, then critical | Crying or screaming without a break for 15 seconds (adjustable, scaled by sensitivity and mode). Critical once the warning has been unanswered for 180 seconds (adjustable). It ends when the state leaves "Crying", that is about a minute after the crying stopped, or when someone enters. |
| No breathing movement | Critical | See [Vital sources](vital-sources.md). Only recorded, not announced, while the switch "Breathing-movement alert" is off. |
| Airway risk, Prone position, Loose objects in bed, Camera view blocked | Hint to critical | From the AI assessment only, see [AI assessment](ai-assessment.md). |
| Left the bed | Warning | Toddler profile only: the presence sensor switches from on to off while nobody is with the child. |
| Pet in bed | Warning | Frigate sees a cat or dog in the bed zone. |
| Room climate | Hint or warning | The room temperature has been outside the range you set for 10 minutes. A warning if it is off by more than 3 °C, otherwise a hint. Humidity is displayed only. |
| Smoke or CO | Critical | One of the configured detectors is on. Passed through even while Monitoring is off or privacy mode is on. |
| Monitoring failure | Hint, or warning, then critical | At least one monitoring problem exists. A minor problem is a hint. Any other problem is a warning and becomes critical after 5 minutes. See [the watchdog](#the-watchdog). |
| No internet | Hint | The internet connectivity sensor is off. |
| Monitoring was interrupted | Warning | After a start: Monitoring was on and CheckBaby was not running for two minutes or longer. |
| Test alert | Critical (or warning) | You pressed "Test alert". |

Except for smoke and the test alert, alerts are only raised while **Monitoring is on and privacy mode is off**. While the state is "Attended", crying, no breathing movement, left the bed and the AI alerts are paused and cleared; monitoring failure, climate, pet, internet and smoke stay active.

Screaming does not go straight to critical. It is treated like crying with a shorter confirmation time; it becomes critical through the "unanswered for three minutes" rule.

## The three alert levels

The sensor **Alert level** shows the highest level among the active alerts, **Alert reason** shows which alert that is.

### Hint

Nothing is sent. The alert shows in the two sensors and in the event log of the diagnostics download.

### Warning

1. **At once:** a notification to the phone that is on duty (to all phones if "On duty" is "Everyone", and always to all in babysitter mode). It carries the camera picture and three buttons: **Seen**, **Quiet for 5 min** and **Live**, which opens your dashboard. On iOS it is sent as time-sensitive.
2. **After 60 seconds without a reaction**, for crying and "left the bed" only: the local alarm is switched on. While the internet connectivity sensor is off, this happens at once.
3. **After 180 seconds without a reaction:** the notification is sent once more, now to all phones.

If the same warning ends and comes back within 120 seconds, it becomes active again without a new notification. This keeps a signal that flickers from buzzing your phone every few seconds. The rule only looks at a warning that was actually on the phones: a hint that ends, an alert that was only recorded, or a warning that was held back by "Quiet for 5 min" does not hold back the first notification of the next warning.

### Critical

1. **At once:** a notification to all phones, whoever is on duty. On iOS it is sent as a critical alert at full volume, on Android on the channel `alarm_stream`, so that it sounds through silent mode and Do Not Disturb. This needs a permission on the phone, see [Troubleshooting](troubleshooting.md#a-critical-alert-does-not-sound).
2. **Every 30 seconds:** the notification is repeated until someone acknowledges it or the cause ends.
3. **Local alarm:** switched on once a notification of this alert has gone unanswered for 60 seconds (at once while the internet is down). The minute counts from the first unanswered notification, also if that one was still a warning. An alert that turns critical after its warning was ignored for a minute or more therefore switches the local alarm on together with the step to critical.

Critical alerts are never held back by snooze or by the 120-second rule.

The local alarm follows the state of the alerts. It is on while an unanswered alert has reached the local step, and it is switched off as soon as that alert is acknowledged, snoozed or over.

A local alarm that is already on stays on when its warning becomes critical.

### Example: crying that nobody answers

With the default settings, counted from the moment Frigate reports crying:

| Time | What happens |
|---|---|
| 8 s | State becomes "Crying". |
| 15 s | Warning to the phone on duty. |
| 75 s | Local alarm on. |
| 195 s | The alert becomes critical: notification to all phones. The local alarm stays on. |
| every 30 s after that | The critical notification is repeated. |

The repeat to all phones after 180 seconds coincides with the step to critical here, so you see one notification, not two.

## Where an alert arrives

A warning or a critical alert can take three paths: the phone, the notifications of Home Assistant itself, and the local alarm. A hint takes none of them; it only shows in the sensors.

### The phone is the main alarm

The notification of the Home Assistant companion app is what is meant to wake you. A critical alert is sent so that it sounds although the phone is silent or on Do Not Disturb. The phone has to allow that, see [Troubleshooting](troubleshooting.md#a-critical-alert-does-not-sound).

A notification normally travels from Home Assistant through the servers of Apple or Google to the phone. It therefore needs the internet, at home and on the phone. According to its documentation, the companion app can also receive notifications directly over the home network: on Android with the setting "Persistent connection" in the app's settings, on iOS as "local push" while the phone is on a Wi-Fi network that is listed as internal in the app. This is a feature of the companion app that you switch on there. CheckBaby has not been tried with it.

### Home Assistant's own notifications

Every warning and every critical alert also appears in Home Assistant's own notifications (the bell in the sidebar). So something is always visible without a phone, for example on a tablet on the wall.

- The entry is created when the alert is first sent, and renewed when the alert rises a level.
- It is removed when the alert ends, when someone taps "Seen", or when the warning is held back with "Quiet for 5 min".
- A **test alert** writes a second entry, the delivery report. It lists which notify services accepted the message, which could not be reached, which local alarm devices are set and which of them are unreachable, and it says what to check on the phone if nothing showed up there. The report stays after the test is answered. "Accepted" means that Home Assistant handed the message over without an error; whether it showed up on the phone is something only you can see.
- The results of the buttons "Quick check", "Send night report" and "AI check now" appear there too, see [Entities and actions](entities-and-actions.md#buttons).

These entries make no sound. They are a place to look, not an alarm.

### The local alarm

The field "Local alarm (siren, light, switch)" is for devices that Home Assistant switches itself. It is the path that works with no internet at all, as long as the device is controlled locally and not through its maker's cloud. When it switches on is described under [The three alert levels](#the-three-alert-levels).

The device has to be reachable in Home Assistant. A smart lamp that is switched off at the wall switch stays dark; the watchdog reports that as `local_alarm`, see [the watchdog](#the-watchdog).

### Wall displays and tablets

A wall panel or a tablet that shows a Home Assistant dashboard can show alerts as well:

- **On the dashboard:** a conditional card on the binary sensor "Unanswered alert" is visible only while a warning or critical alert is unanswered. The [example dashboard](../examples/dashboard.yaml) has such a card with the button "Seen".
- **As a local alarm:** if the panel has a relay, a light or a siren that Home Assistant can switch (an entity of the type switch, light or siren), you can choose it under "Local alarm".
- **A tone or a flashing light:** use the event entity "Alert" in an automation of your own, or the blueprint [`alert_light.yaml`](../../blueprints/automation/checkbaby/alert_light.yaml), which gives a light one colour for a warning and another for a critical alert.

None of this has been tried with a particular product. Whether a panel wakes its screen or can play a tone depends on the panel.

## Acknowledge and snooze

**Seen** (button on the notification, button entity, or action `checkbaby.acknowledge`) acknowledges all active warnings and critical alerts of the child at once.

- The notifications are removed from all phones and from Home Assistant's notifications, and the local alarm is switched off.
- Repeats and escalation stop.
- Monitoring goes on. The alert stays active for as long as its cause lasts. If it gets worse, for example an acknowledged AI warning that becomes critical, it notifies again.
- An acknowledged crying warning does not become critical.
- A test alert and "Monitoring was interrupted" end with the acknowledgement.

**Quiet for 5 min** (button on the notification, button entity, or action `checkbaby.snooze` with 1 to 120 minutes) holds warnings back.

- Warnings that are showing are removed from the phones and from Home Assistant's notifications; new warnings are not sent.
- A local alarm that is on because of a warning is switched off. The binary sensor "Unanswered alert" stays on, because the warning is still unanswered.
- When the time is over, warnings that are still active and unanswered are sent again, to the phone on duty. If the warning is older than 180 seconds by then, the repeat to all phones follows within seconds. The local alarm for crying and "left the bed" comes on 60 seconds after the warning was sent again, if nobody reacts.
- **A crying warning does not turn critical during the quiet time.** Snoozing counts as an answer: the 180 seconds of "nobody reacts" start when the quiet time ends. If the child still cries then and nobody acknowledges, the alert becomes critical 180 seconds later.
- **Other critical alerts come through regardless.** Snooze never holds back an alert that is critical, for example smoke, a monitoring failure that has lasted five minutes, or a crying alert that was already critical. A local alarm that is on because of a critical alert stays on.

## On duty

The select **On duty** lists "Everyone" and each configured phone. It decides who gets a warning first. Critical alerts, the repeat after 180 seconds, and the removal of notifications always go to all phones. The results of the quick check, the night report and "AI check now" also go to whoever is on duty.

## Modes and sensitivity

**Mode** has three values:

| Mode | Effect |
|---|---|
| Night | The normal case. |
| Nap | Behaves like "Night". The mode is stored with each sleep in the sleep log. |
| Babysitter | Every warning goes to all phones at once. The phones ticked under "Babysitters' phones" (options page "Who is told") are told in addition to the parents' phones; in the other modes they receive nothing. The crying time before a warning is halved. |

There is no "Off" mode; use the switch **Monitoring**.

**Sensitivity** scales the crying time before a warning: "Low" doubles it, "Medium" leaves it, "High" halves it. With the default of 15 seconds that is 30, 15 or 7.5 seconds, and half of that in babysitter mode.

## The watchdog

A monitor that fails silently is worse than none. Every source that the active sleep place uses is watched, and each one that fails becomes a named problem.

| Problem | Watched when | It means |
|---|---|---|
| `mqtt` | Frigate camera or vital engine | MQTT is not set up or not connected. |
| `frigate` | Frigate camera | Frigate does not report `online`. |
| `audio_level` | Frigate camera, or a sound level sensor without Frigate | No sound level for more than 60 seconds, or the level sensor has no value. |
| `microphone` | Frigate camera | The level from Frigate has not changed at all for 10 minutes. A sound level read from a sensor entity is exempt, because such a value may legitimately stay constant. |
| `cry_sensor` | Crying sensor without Frigate | The crying sensor is unavailable. |
| `camera` | Camera entity set | The camera entity is missing or unavailable. |
| `engine` | Vital engine ID set | The vital engine is offline or silent for more than 30 seconds. |
| `vital_sensor` | Breathing rate sensor set | The sensor has no numeric value. |
| `notify` | Always | A configured notify service does not exist, or nobody could be alerted at all: no phone is configured, and no local alarm device is set or reachable. |
| `local_alarm` | Local alarm set | A local alarm entity is missing or `unavailable` in Home Assistant, for example a smart lamp that is switched off at the wall switch. |
| `sleep_place` | Always | No sleep place is active. |

Every problem is shown: the binary sensor **Monitoring problem** turns on and the sensor **Monitoring problems** lists the names. This also happens while Monitoring is off. What else follows depends on the grade of the problem.

**Minor problems** cost an extra, not the monitoring itself:

- `camera`: the picture in notifications and the AI assessment are missing. Crying is still detected.
- `engine` and `vital_sensor`, as long as the switch "Breathing-movement alert" is off: no alert depends on these sources then.
- `local_alarm`: a local alarm device would stay silent. The phones are still told. If no phone is configured and none of the local alarm devices can be reached, nobody could be alerted; that is reported as `notify`, which is serious.

A minor problem sends no notification and does not change the child's state. While Monitoring is on, the alert level shows "Hint" with the reason "Monitoring failure".

**All other problems are serious.** `engine` and `vital_sensor` also become serious as soon as the switch "Breathing-movement alert" is on, because an alert then depends on them.

- While Monitoring is on: a **warning** "Monitoring failure" with the reasons in the text, and a **critical alert** if the problem lasts 5 minutes.
- If the problem is in a **core source** (`mqtt` with a Frigate camera, `frigate`, `audio_level`, `cry_sensor`, `sleep_place`), the state also becomes "Unknown".

If you use an outage buzzer (see below): its sign of life stops only while a serious problem exists. A minor problem, for example a lost camera picture, does not make the buzzer sound.

After a start and after switching the sleep place there is a grace period of two minutes in which a source that has not reported yet is not a problem. A source that actively reports "offline" or "unavailable" counts at once.

Two more things guard against a silent failure:

- **When Home Assistant shuts down** while Monitoring is on, the phone on duty receives "Home Assistant is stopping. (name) is not monitored until it is back." A warning before an update is planned, but not implemented.
- **An outage buzzer** (also called a dead-man buzzer) is an optional small device of your own that beeps when Home Assistant falls silent: after a crash, or when the power or the Wi-Fi fails. An example with an ESP32 is in [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml). Such a device needs a regular sign of life. Choose its button under "Sign of life for an outage buzzer (optional)" on the options page "Who is told": CheckBaby presses it every 30 seconds while Monitoring is on and no serious problem exists. When the presses stop, the buzzer sounds. If you have no such device, leave the field empty.

If you configured an internet connectivity sensor, its "off" raises the hint "No internet" and makes the local alarm fire at once instead of after a minute, because the push notifications normally depend on the internet.

## The learned noise floor

A white-noise machine or a humidifier raises the sound level for hours. A fixed threshold would then count the whole night as loud. CheckBaby therefore learns the level of the room and counts as "noise" only what is above it by more than the margin (number **Loudness above the noise floor**, default 15 dB).

- The floor starts at the first level it receives and then follows the level slowly, with a time constant of ten minutes.
- It learns only from quiet moments and never while crying or screaming is heard, so crying does not raise it.
- Noise that simply stays for five minutes without any crying is taken for the room's own sound; from then on the floor follows it upwards.
- The floor is shown in the diagnostic sensor **Learned noise floor** and survives restarts.

The noise floor and the margin decide between "Asleep", "Restless" and "Awake" and open the audio relay. They do **not** trigger the crying alert: that comes only from Frigate's crying and scream detection (or your crying sensor).

## Audio relay

If you set a speaker on the options page "Other devices and settings", an audio stream address in the sleep place and turn on the switch **Audio relay**, CheckBaby plays the stream on the speaker after two seconds of noise or crying and stops it after 60 seconds of quiet. It works only while Monitoring is on and privacy mode is off. Whether your speaker plays the stream, and with what delay, has to be tried; this is untested.

## Privacy mode

The switch **Privacy mode** is meant for moments such as nursing in front of the camera.

While it is on:

- The state shows "Unknown".
- No alerts are raised and nothing is sent by itself, with one exception: smoke and CO. A button you press yourself ("Test alert", "Quick check", "Send night report") still shows its result.
- No image is sent to an AI task: neither automatically nor with the button "AI check now" or the actions `checkbaby.assess_now` and `checkbaby.quick_check`. The button then only reports that privacy mode is on.
- The audio relay stops. "Quiet time" is off.

What privacy mode does **not** do:

- It does not switch off the camera, Frigate or Frigate's recording. CheckBaby has no control over them.
- It does not stop the sign of life for an outage buzzer.

## What survives a restart

Stored on disk in Home Assistant and restored at the start:

- every setting you make through the entities (Monitoring, privacy mode, mode, on duty, sensitivity, thresholds, the active sleep place, a running snooze),
- the active alerts including whether they were acknowledged,
- the sleep log (sleep phases, wake-ups, crying times),
- the learned noise floor,
- whether the local alarm was on, so that it can still be switched off.

Not stored: the child's state and the latest signals. After a start the state is "Unknown" until the sources have reported, and the two-minute grace period applies.

If Monitoring was on and CheckBaby was away for two minutes or longer, you get the warning "Monitoring of (name) was interrupted for N min".

The data is saved about every 15 seconds and when Home Assistant stops. Removing the entry deletes it.
