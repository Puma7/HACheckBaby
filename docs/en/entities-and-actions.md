# Entities and actions

[Deutsche Fassung](../de/entities-and-actions.md) · [Back to the index](README.md)

Each child is one device. All entities below belong to it. The entity IDs in the tables are those of a child named "baby" on a Home Assistant set to English.

## Entity IDs depend on the language

Home Assistant builds an entity ID from the device name and the entity name when the entity is first created. A child named "Emma" gets `sensor.emma_state`.

The entity name is taken in the language that is set under **Settings → System → General** at that moment. On a Home Assistant set to German the same sensor is created as `sensor.emma_zustand`. The German IDs are listed in the [German version of this page](../de/entities-and-actions.md). IDs do not change when you switch the language later; you can rename them by hand in the entity settings.

In automations and dashboards, check the real IDs on the device page before you copy an example.

## Sensors

| Name | Entity ID | Meaning |
|---|---|---|
| State | `sensor.baby_state` | The child's state: `empty` (Not in bed), `asleep`, `restless`, `awake`, `crying`, `attended`, `unknown`. Attribute `since`: when the state began. |
| Alert level | `sensor.baby_alert_level` | Highest level among the active alerts: `none`, `info` (Hint), `warning`, `critical`. Attribute `alerts`: every active alert with `kind`, `level`, `acknowledged`, `shadow` and `since`. Alerts that are only recorded (`shadow: true`) appear here and nowhere else. |
| Alert reason | `sensor.baby_alert_reason` | Which alert sets the level, or `none`. The attributes carry the details of that alert, for example `seconds`, `problems`, `sources`, `reason`, `hazards` or `temperature`. |
| Sound level | `sensor.baby_sound_level` | Latest sound level in dBFS. |
| Learned noise floor | `sensor.baby_learned_noise_floor` | Diagnostic. The learned level of the room in dBFS. |
| Last movement | `sensor.baby_last_movement` | Time of the last movement reported. |
| Asleep since | `sensor.baby_asleep_since` | Start of the current sleep. The sleep ends when the state becomes "Awake", "Crying", "Attended" or "Not in bed"; it keeps running while the state is "Unknown", so sleep times include stretches without a usable signal. |
| Last sleep | `sensor.baby_last_sleep` | Length of the last finished sleep in minutes. |
| Sleep today | `sensor.baby_sleep_today` | Hours asleep since midnight. |
| Crying today | `sensor.baby_crying_today` | Minutes in the state "Crying" since midnight. |
| Wake-ups tonight | `sensor.baby_wake_ups_tonight` | How often the child went from asleep or restless to awake or crying since the most recent 18:00. |
| Breathing rate (estimate) | `sensor.baby_breathing_rate_estimate` | Breaths per minute as reported by a vital source that currently sees breathing movement. An estimate from an unvalidated source, not a measurement. |
| Heart rate (estimate) | `sensor.baby_heart_rate_estimate` | The value of the configured heart rate sensor. Display only; it never raises an alert. |
| Sleeping bag suggestion | `sensor.baby_sleeping_bag_suggestion` | A TOG value for the current room temperature, following the usual manufacturer guidance: below 16 °C 3.5 TOG, below 18 °C 2.5 TOG plus an extra layer, below 21 °C 2.5 TOG, below 24 °C 1.0 TOG, below 27 °C 0.5 TOG, above that 0.2 TOG or less. A guideline, not a rule. |
| AI assessment | `sensor.baby_ai_assessment` | Overall verdict of the last AI assessment: `ok`, `attention`, `warning`, `critical`. Attributes: `reason`, `position`, `airway_risk`, `face_visible`, `hazards`, `confidence`, `assessed_at`. The verdict is shown only; alerts follow from the individual fields. |
| Position | `sensor.baby_position` | Body position from the last AI assessment: `supine`, `prone`, `side`, `sitting`, `standing`, `unknown`. |
| Monitoring problems | `sensor.baby_monitoring_problems` | Diagnostic. Number of monitoring problems. Attribute `problems`: their names. |
| AI calls in the last hour | `sensor.baby_ai_calls_in_the_last_hour` | Diagnostic. How much of the hourly AI budget is used. |
| Age profile | `sensor.baby_age_profile` | Diagnostic. `newborn`, `infant` or `toddler`, from the birth date. |

## Binary sensors

| Name | Entity ID | Meaning |
|---|---|---|
| Crying | `binary_sensor.baby_crying` | Crying or screaming is being heard right now, before any duration is applied. |
| Movement | `binary_sensor.baby_movement` | Movement is being reported right now. |
| In bed | `binary_sensor.baby_in_bed` | The presence sensor of the bed. Unknown if none is configured. |
| Someone is with the child | `binary_sensor.baby_someone_is_with_the_child` | On while the state is "Attended". |
| Breathing movement | `binary_sensor.baby_breathing_movement` | On while a usable vital source sees breathing movement, off while the usable sources see none, **unknown while no source is usable**. Unknown is not "all fine". |
| Unanswered alert | `binary_sensor.baby_unanswered_alert` | On while a warning or critical alert has not been acknowledged. |
| Monitoring problem | `binary_sensor.baby_monitoring_problem` | Diagnostic. On while at least one monitoring problem exists. |
| AI assessment available | `binary_sensor.baby_ai_assessment_available` | Diagnostic. On after an AI answer that could be used, off after a failed attempt, unknown before the first attempt. |
| Quiet time | `binary_sensor.baby_quiet_time` | On while Monitoring is on, privacy mode is off and the child is asleep or restless. Made for your own automations. |
| Audio relay playing | `binary_sensor.baby_audio_relay_playing` | On while the audio relay has opened the stream on the speaker. |

## Switches

| Name | Entity ID | Default | Meaning |
|---|---|---|---|
| Monitoring | `switch.baby_monitoring` | off | Arms the monitor. While off, only smoke/CO and the test alert notify. |
| Privacy mode | `switch.baby_privacy_mode` | off | Pauses detection and notifications, see [How it works](how-it-works.md#privacy-mode). |
| AI assessment | `switch.baby_ai_assessment` | on | A pause button: switch it off to stop the automatic AI assessments. Being on does nothing by itself; the assessment runs once an AI task is chosen and the consent is given, in the setup or under Configure → AI assessment. |
| Breathing-movement alert | `switch.baby_breathing_movement_alert` | off | Off: "no breathing movement" is only recorded (shadow mode). On: it raises a critical alert. Read [Vital sources](vital-sources.md) before you turn it on. |
| Audio relay | `switch.baby_audio_relay` | off | Plays the room's audio stream on the speaker while there is noise. |

## Numbers

| Name | Entity ID | Range | Default | Meaning |
|---|---|---|---|---|
| Crying before a warning | `number.baby_crying_before_a_warning` | 5 to 120 s | 15 s | Uninterrupted crying before the warning. Scaled by sensitivity and babysitter mode. |
| Unanswered crying before critical | `number.baby_unanswered_crying_before_critical` | 60 to 900 s | 180 s | How long a crying warning may stay unacknowledged before it becomes critical. |
| Loudness above the noise floor | `number.baby_loudness_above_the_noise_floor` | 3 to 40 dB | 15 dB | How far above the learned noise floor a level must be to count as noise. |
| No breathing movement before an alert | `number.baby_no_breathing_movement_before_an_alert` | 20 to 60 s | 20 s | Cannot be set below 20 seconds, see [Vital sources](vital-sources.md#why-20-seconds-is-the-floor). |
| AI routine check interval | `number.baby_ai_routine_check_interval` | 2 to 60 min | 10 min | Time between routine AI assessments. |
| Lowest room temperature | `number.baby_lowest_room_temperature` | 10 to 22 °C | 16 °C | Lower end of the range for the climate alert. |
| Highest room temperature | `number.baby_highest_room_temperature` | 18 to 30 °C | 22 °C | Upper end of the range. |

## Selects

| Name | Entity ID | Options | Meaning |
|---|---|---|---|
| Mode | `select.baby_mode` | `night`, `nap`, `babysitter` | See [How it works](how-it-works.md#modes-and-sensitivity). |
| Sensitivity | `select.baby_sensitivity` | `low`, `medium`, `high` | Doubles, keeps or halves the crying time before a warning. |
| Vital sources must agree | `select.baby_vital_sources_must_agree` | `any` (One source is enough), `all` (All sources) | How several vital sources combine. Default `all`. |
| On duty | `select.baby_on_duty` | `all` (Everyone) and each configured phone | Who gets warnings first. |
| Active sleep place | `select.baby_active_sleep_place` | The names of your sleep places | Which sleep place is monitored. |

## Buttons

| Name | Entity ID | What it does | Where the result appears |
|---|---|---|---|
| Seen | `button.baby_seen` | Acknowledges all active alerts. | Their notifications disappear from the phones and from Home Assistant's notifications. |
| Quiet for 5 minutes | `button.baby_quiet_for_5_minutes` | Holds warnings back for five minutes. | Warnings that are showing disappear from the phones and from Home Assistant's notifications. |
| Quick check | `button.baby_quick_check` | Sums up in one or two sentences how the child is right now. | In Home Assistant's notifications and on the phone on duty. |
| AI check now | `button.baby_ai_check_now` | Asks the AI about a fresh camera image, regardless of the switch "AI assessment", the budget and whether Monitoring is on. No image is sent while privacy mode is on. | In Home Assistant's notifications and on the phone on duty: the AI's verdict with confidence and reason, or the reason why no check ran. See [AI assessment](ai-assessment.md#the-result-of-ai-check-now). |
| Send night report | `button.baby_send_night_report` | Sums up the night since the most recent 18:00. | In Home Assistant's notifications and on the phone on duty. |
| Test alert | `button.baby_test_alert` | Diagnostic. Starts a critical test alert. | On all phones and in Home Assistant's notifications, where a delivery report is written as well. The report stays after the test is answered. |

"Home Assistant's notifications" are the bell in the sidebar. A result is always written there, so that pressing a button shows something even when no phone is set up or reachable. A newer result of the same button replaces the older one, there and on the phone.

The delivery report of the test alert lists which notify services accepted the message, which could not be reached, which local alarm entities are set and which of them are unreachable. If the message was sent, it also says what to check on the phone when nothing showed up: the app's notification permission and, on iOS, critical alerts.

## Event

| Name | Entity ID | Meaning |
|---|---|---|
| Alert | `event.baby_alert` | Fires when an alert first sends a notification and when it rises to a higher level. The event type is the alert reason: `crying`, `no_breathing`, `airway_risk`, `prone_position`, `hazard`, `camera_view`, `left_bed`, `pet_in_bed`, `climate`, `smoke`, `monitoring_failure`, `internet_down`, `interruption`, `test`. The attribute `level` is `warning` or `critical`; the alert's details are further attributes. |

The event does not fire for hints, for repeats, for the repeat to all phones after 180 seconds, or for alerts that are only recorded. A warning that is held back by snooze fires when it is sent after the quiet time.

How to use this entity, the binary sensor "Unanswered alert" or the local alarm for a wall display is described under [Wall displays and tablets](how-it-works.md#wall-displays-and-tablets).

## Actions

Every action accepts the optional field `config_entry_id` (shown as "Child"). You only need it when more than one child is set up; with exactly one child it can be left out. If it is missing with several children, the action fails with "Choose the child".

| Action | Fields | What it does | Returns |
|---|---|---|---|
| `checkbaby.acknowledge` | – | Marks all active warnings and critical alerts as seen. | Nothing |
| `checkbaby.snooze` | `minutes` (1 to 120, default 5) | Holds warnings back for that long. Critical alerts still come through. | Nothing |
| `checkbaby.test_alert` | `level`: `critical` (default) or `warning` | Runs the notification chain with a test alert until it is acknowledged, at most 10 minutes. Works while Monitoring is off. Writes the delivery report into Home Assistant's notifications, like the button. | Nothing |
| `checkbaby.start_sleep` | – | Sets the state to "Asleep" now. | Nothing |
| `checkbaby.end_sleep` | – | Sets the state to "Awake" now. | Nothing |
| `checkbaby.assess_now` | – | Asks the configured AI tasks about a fresh camera image. Unlike the button, it shows nothing; it only returns the data. | `assessment` |
| `checkbaby.quick_check` | `with_ai` (default false): take a fresh AI look first (skipped while privacy mode is on). `notify` (default false): also send the summary to the phone on duty and write it into Home Assistant's notifications. | Reports how the child is right now. | See below |
| `checkbaby.night_report` | `notify` (default false): also send the summary to the phone on duty and write it into Home Assistant's notifications. | Reports the night since the most recent 18:00. | See below |

### What `assess_now` returns

`assessment` is empty (`null`) if no AI task is configured, consent is missing, the sleep place has no camera entity, privacy mode is on, another assessment is running, or no AI task gave a usable answer. Otherwise it contains:

| Key | Value |
|---|---|
| `presence` | `in_bed`, `not_visible` or `caregiver_present` |
| `position` | `supine`, `prone`, `side`, `sitting`, `standing`, `unknown` |
| `face_visible` | true, false or empty |
| `airway_risk` | `none`, `possible`, `likely` |
| `state` | `asleep`, `awake_calm`, `awake_restless`, `crying`, `unknown` |
| `view_ok` | false if the image is too dark, blocked or does not show a bed |
| `verdict` | `ok`, `attention`, `warning`, `critical` |
| `confidence` | 0 to 1 |
| `reason` | One sentence in the language of your Home Assistant |
| `hazards` | List of loose objects the AI named |
| `at` | Time of the assessment as a Unix timestamp |

### What `quick_check` returns

| Key | Value |
|---|---|
| `state` | The state as in the sensor, for example `asleep` |
| `state_text` | The state in words, in the language of your Home Assistant |
| `alert_level` | `none`, `info`, `warning`, `critical` |
| `alert` | The alert reason, or empty |
| `asleep_minutes` | Minutes since the current sleep began; empty unless the state is "Asleep" or "Restless" |
| `noise_level` | Latest sound level in dBFS, or empty |
| `breathing_movement` | true, false, or empty if no vital source is usable |
| `problems` | List of monitoring problems |
| `assessment`, `assessment_reason` | Verdict and sentence of the last AI assessment, or empty |
| `summary` | One or two sentences, for example "baby: asleep. Asleep for 42 min." The part about the sleep time only appears while the state is "Asleep" or "Restless". |

A voice command "How is the baby?" is not built in. You can call `checkbaby.quick_check` from a script and let your voice assistant speak `summary`.

### What `night_report` returns

| Key | Value |
|---|---|
| `since`, `until` | Start (the most recent 18:00) and end (now) as Unix timestamps |
| `slept_seconds` | Seconds asleep in that time |
| `cried_seconds` | Seconds in the state "Crying" |
| `wakeups` | Number of wake-ups |
| `sleep_phases` | Number of separate sleep phases |
| `longest_stretch_seconds` | Longest sleep phase in seconds |
| `summary` | One sentence with these numbers |

A new sleep that starts less than 20 minutes after the last one ended counts as a continuation of the same sleep phase.

### Example: use a return value

```yaml
action: checkbaby.quick_check
data:
  with_ai: false
response_variable: check
```

After this step `{{ check.summary }}` holds the sentence.

## Diagnostics

**Download diagnostics** on the entry gives you the settings, the sleep places, the latest snapshot and the last 300 entries of the event log, which records every state change, alert, acknowledgement and AI answer with its cause. The child's name, the birth date, the audio stream address, the names of the sleep places and the AI's sentences are removed. The names of your notify services and entities are included.
