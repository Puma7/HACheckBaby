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
4. **Crying** once crying has been heard without a break for 8 seconds, or screaming for 3 seconds. The state stays "Crying" until neither has been heard for 60 seconds; then it becomes "Awake".
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
| Monitoring failure | Warning, then critical | At least one monitoring problem exists. Critical after 5 minutes. |
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

If the same warning ends and comes back within 120 seconds, it becomes active again without a new notification. This keeps a signal that flickers from buzzing your phone every few seconds.

### Critical

1. **At once:** a notification to all phones, whoever is on duty. On iOS it is sent as a critical alert at full volume, on Android on the channel `alarm_stream`, so that it sounds through silent mode and Do Not Disturb. This needs a permission on the phone, see [Troubleshooting](troubleshooting.md#a-critical-alert-does-not-sound).
2. **Every 30 seconds:** the notification is repeated until someone acknowledges it or the cause ends.
3. **After 60 seconds without a reaction:** the local alarm is switched on (at once while the internet is down).

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

## Acknowledge and snooze

**Seen** (button on the notification, button entity, or action `checkbaby.acknowledge`) acknowledges all active warnings and critical alerts of the child at once.

- The notifications are removed from all phones and the local alarm is switched off.
- Repeats and escalation stop.
- Monitoring goes on. The alert stays active for as long as its cause lasts. If it gets worse, for example an acknowledged AI warning that becomes critical, it notifies again.
- An acknowledged crying warning does not become critical.
- A test alert and "Monitoring was interrupted" end with the acknowledgement.

**Quiet for 5 min** (button on the notification, button entity, or action `checkbaby.snooze` with 1 to 120 minutes) holds warnings back.

- Warnings that are showing are removed from the phones; new warnings are not sent.
- A local alarm that is on because of a warning is switched off. The binary sensor "Unanswered alert" stays on, because the warning is still unanswered.
- When the time is over, warnings that are still active and unanswered are sent again, to the phone on duty. The steps whose time has already passed follow within seconds: the repeat to all phones if the warning is older than 180 seconds, and the local alarm for crying and "left the bed" if it is older than 60 seconds.
- **A crying warning does not turn critical during the quiet time.** Snoozing counts as an answer: the 180 seconds of "nobody reacts" start when the quiet time ends. If the child still cries then and nobody acknowledges, the alert becomes critical 180 seconds later.
- **Other critical alerts come through regardless.** Snooze never holds back an alert that is critical, for example smoke, a monitoring failure that has lasted five minutes, or a crying alert that was already critical. A local alarm that is on because of a critical alert stays on.

## On duty

The select **On duty** lists "Everyone" and each configured phone. It decides who gets a warning first. Critical alerts, the repeat after 180 seconds, and the removal of notifications always go to all phones. The quick check and the night report, when sent as a notification, also go to whoever is on duty.

## Modes and sensitivity

**Mode** has three values:

| Mode | Effect |
|---|---|
| Night | The normal case. |
| Nap | Behaves like "Night". The mode is stored with each sleep in the sleep log. |
| Babysitter | Every warning goes to all phones at once. The babysitter's phone from the options is added to the phones. The crying time before a warning is halved. |

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
| `notify` | Always | No alert target at all, or a configured notify service does not exist. |
| `sleep_place` | Always | No sleep place is active. |

What follows from a problem:

- The binary sensor **Monitoring problem** turns on and the sensor **Monitoring problems** lists the names. This also happens while Monitoring is off.
- If the problem is in a **core source** (`mqtt` with a Frigate camera, `frigate`, `audio_level`, `cry_sensor`, `sleep_place`), the state becomes "Unknown".
- While Monitoring is on: a **warning** "Monitoring failure" with the reasons in the text, and a **critical alert** if the problem lasts 5 minutes.
- The heartbeat buttons are no longer pressed, so a dead-man buzzer sounds too.

After a start and after switching the sleep place there is a grace period of two minutes in which a source that has not reported yet is not a problem. A source that actively reports "offline" or "unavailable" counts at once.

Two more things guard against a silent failure:

- **When Home Assistant shuts down** while Monitoring is on, the phone on duty receives "Home Assistant is stopping. (name) is not monitored until it is back." A warning before an update is planned, but not implemented.
- **Heartbeat buttons** (option "Dead-man heartbeat buttons"): CheckBaby presses the chosen button entities every 30 seconds while Monitoring is on and there is no problem. A separate device can sound when the presses stop. An example is in [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml).

If you configured an internet connectivity sensor, its "off" raises the hint "No internet" and makes the local alarm fire at once instead of after a minute, because the push notifications depend on the internet.

## The learned noise floor

A white-noise machine or a humidifier raises the sound level for hours. A fixed threshold would then count the whole night as loud. CheckBaby therefore learns the level of the room and counts as "noise" only what is above it by more than the margin (number **Loudness above the noise floor**, default 15 dB).

- The floor starts at the first level it receives and then follows the level slowly, with a time constant of ten minutes.
- It learns only from quiet moments and never while crying or screaming is heard, so crying does not raise it.
- Noise that simply stays for five minutes without any crying is taken for the room's own sound; from then on the floor follows it upwards.
- The floor is shown in the diagnostic sensor **Learned noise floor** and survives restarts.

The noise floor and the margin decide between "Asleep", "Restless" and "Awake" and open the audio relay. They do **not** trigger the crying alert: that comes only from Frigate's crying and scream detection (or your crying sensor).

## Audio relay

If you set a speaker in the options, an audio stream address in the sleep place and turn on the switch **Audio relay**, CheckBaby plays the stream on the speaker after two seconds of noise or crying and stops it after 60 seconds of quiet. It works only while Monitoring is on and privacy mode is off. Whether your speaker plays the stream, and with what delay, has to be tried; this is untested.

## Privacy mode

The switch **Privacy mode** is meant for moments such as nursing in front of the camera.

While it is on:

- The state shows "Unknown".
- No alerts are raised and nothing is sent, with one exception: smoke and CO.
- No image is sent to an AI task: neither automatically nor with the button "AI check now" or the actions `checkbaby.assess_now` and `checkbaby.quick_check`.
- The audio relay stops. "Quiet time" is off.

What privacy mode does **not** do:

- It does not switch off the camera, Frigate or Frigate's recording. CheckBaby has no control over them.
- It does not stop the heartbeat for a dead-man buzzer.

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
