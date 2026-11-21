# Vital sources: the breathing-movement hint

[Deutsche Fassung](../de/vital-sources.md) · [Back to the index](README.md)

CheckBaby can take in sources that report whether they see breathing movement, and raise an alert when a source that saw movement before sees none for a while. This is a **breathing-movement hint**. It is not a medical measurement.

> **This is unvalidated on infants.** Nothing on this page has run on real hardware, and no radar module on the market is specified for infants. The rule is covered by automated tests with simulated readings; nobody has yet measured how often it misses a real pause or raises a false alarm. No monitor has been shown to prevent sudden infant death. Do not rely on the hint, do not let it replace looking in on your child, and keep following the [rules for safe sleep](safety-and-privacy.md#safe-sleep-basics).

The alert is switched off when you install CheckBaby. In that state the rule runs in **shadow mode**: it records, but tells nobody. Leave it that way until you have looked at its record for at least two weeks.

## The two kinds of source

A sleep place can have one of each. Both can be used together.

### A radar sensor (breathing rate entity)

Enter a sensor under **Breathing rate sensor (radar)** in the sleep place. CheckBaby reads its state every two seconds and interprets it like this:

| State of the entity | Meaning for CheckBaby |
|---|---|
| A number other than zero | Usable, breathing movement seen. The number is shown as "Breathing rate (estimate)". |
| Zero | Usable, no breathing movement seen. |
| `unavailable`, `unknown`, not a number, or the entity is missing | Not usable. The watchdog reports `vital_sensor`. |
| Any value that the sensor has not reported again for 120 seconds | Not usable, as above. A sensor that died while showing a rate would otherwise look like one that still measures it. |

Only the distinction "zero or not" enters the rule. The rate itself is displayed and not judged, because nobody knows yet whether a module built for adults reports plausible rates for a newborn.

The 120 seconds count from the last time the sensor reported, also if it reported the same value again. A sensor that only reports when its value changes, and holds a constant rate for two minutes, therefore shows up as the problem `vital_sensor`; the same goes for a filter in the sensor's own configuration that suppresses repeated values. "Breathing movement" is unknown during that time.

Any entity with a numeric breathing rate fits here, whatever its manufacturer. A radar source never reports body movement to CheckBaby; movement comes from the camera.

The field **Heart rate sensor (radar)** is displayed as "Heart rate (estimate)" and never raises an alert. A baby's heart movement is far smaller than its breathing movement, and the value has not been checked against a reference device.

### The vital engine

The vital engine is a separate program in the folder `engine/` of the repository. It reads the camera's low-resolution stream, looks at a region over the child's upper body and publishes whether it sees a periodic movement in the range of breathing. It runs outside Home Assistant on purpose: decoding video inside Home Assistant would put your whole home automation at risk if it fails.

Its signal processing has been tested with artificial signals only. It has never seen a real camera, a real room or a real child, and its thresholds are tuned on artificial data. Packaging it as a Home Assistant add-on is untested. How to run it, what exactly was tested and its own list of limits are in [`engine/README.md`](../../engine/README.md).

Enter the engine's ID under **Vital engine ID** in the sleep place. CheckBaby then subscribes to two MQTT topics. The prefix `checkbaby/engine` is fixed in the integration, so leave the engine's `topic_prefix` at its default.

| Topic | Payload |
|---|---|
| `checkbaby/engine/<id>/availability` | `online` or `offline` |
| `checkbaby/engine/<id>/state` | JSON, about every two seconds, for example `{"status": "periodic", "rate": 38.0, "confidence": 0.6, "motion": 0.4, "ts": 1800000000.0}` |

CheckBaby reads `status` and `rate` and ignores the other keys:

| `status` | Meaning for CheckBaby |
|---|---|
| `periodic` | Usable, breathing movement seen; `rate` is shown as the estimated rate. |
| `gross_motion` | Usable, the child is moving. Breathing cannot be measured, but there is a sign of life. |
| `no_motion` | Usable, neither periodic nor gross movement. |
| anything else, for example `unusable` | Not usable: covered, child not in the picture, too dark, too noisy. |

If no state message arrives for 15 seconds, the last reading no longer counts as usable. After 30 seconds, or when the engine reports `offline`, the watchdog reports `engine`.

The plan describes this contract with German names; the names above are the ones the engine and the integration actually use.

## The rule

"No breathing movement" holds when **all** of the following are true:

1. Monitoring is on and privacy mode is off.
2. The state is neither "Attended" nor "Not in bed", and the presence sensor does not say the bed is empty.
3. The camera reports no movement, and neither crying nor screaming is heard. Any of these is a sign of life and rules the alert out.
4. At least one vital source is usable right now.
5. That source **has seen breathing movement before**. A source that has never seen the child breathe cannot say that something stopped.
6. **That source has seen breathing movement at least 10 seconds after the last large movement.** A large movement is: the camera reports movement (Frigate's motion or your motion sensor; the moment it ends counts too), or a vital source reports body movement (the engine's `gross_motion`).
7. Since it last saw breathing movement, and for as long as its signal has been usable without a break, the source has seen neither breathing movement nor body movement for the configured time (number "No breathing movement before an alert", 20 to 60 seconds, default 20).

The alert is critical. It ends as soon as a source sees movement again or one of the conditions no longer holds.

While the state is "Attended", every source forgets that it has seen breathing movement. After the person has left, each source has to see breathing movement anew before its silence can count.

### Silence after a large movement is not counted

Point 6 exists because of the most common false alarm: you lift the child out of bed. That is a large movement followed by a bed in which nothing breathes, and no source can tell this apart from anything worse. CheckBaby therefore never counts silence that follows a large movement. The source has to see breathing movement again first.

**The price, stated plainly: if breathing movement stops directly after a large movement, before the source has seen breathing again, the hint does not notice it.** With the vital engine that window is at least the roughly 12 seconds it reports `gross_motion` after any larger movement, plus the time until it reports `periodic` again. A child that moves and then lies still under a thick sleeping bag, so that the source never sees breathing again, is not covered at all until breathing is seen again.

### What never counts as "no movement"

- A source that is unavailable, offline or reports "unusable".
- A reading that is older than 15 seconds.
- A source that has not yet seen the child breathe.
- Silence after a large movement, until the source has seen breathing movement again.
- Silence after someone was with the child, until the source has seen breathing movement again.
- The time while the signal was unusable: when a signal comes back, the count starts again from that moment.

In all these cases the rule stays silent. While no source is usable at all, the binary sensor "Breathing movement" shows **unknown**. That is deliberate: an unusable signal is a visible state, not an alert, and never "all fine". It also means that the hint can be blind for long stretches without telling you by a notification. Look at the sensor.

### Several sources: "any" or "all"

The select **Vital sources must agree** decides what happens with two sources:

| Option | The rule holds when | Character |
|---|---|---|
| All sources (default) | every source that is usable right now sees no movement | fewer false alarms |
| One source is enough | at least one usable source sees no movement | more sensitive |

"All sources" means all *usable* sources. A source that is unusable at that moment has no vote: if the radar is unavailable and the engine sees no movement, the rule holds on the engine alone.

### Shadow mode

The switch **Breathing-movement alert** is off by default.

- **Off:** when the rule holds, the alert is only recorded. No notification, no local alarm, no change of the alert level. You find it in the attribute `alerts` of the sensor "Alert level" with `shadow: true` while it lasts, and afterwards in the event log of the diagnostics download. If the AI assessment is on, one AI look is requested.
- **On:** the same situation raises a critical alert: all phones, repeated every 30 seconds, local alarm after a minute.

If you switch the alert on while a recorded alert is active, it notifies at once. If you switch it off while it is sounding, the notification is removed.

The switch also decides how much a lost source matters. While it is off, a radar sensor without a reading (`vital_sensor`) or a vital engine that is offline (`engine`) is shown in the list of monitoring problems and as a hint, but sends no notification. While it is on, an alert depends on these sources: losing one raises the warning "Monitoring failure", which becomes critical after five minutes.

A sensible way to use shadow mode: let it run for at least 14 nights, download the diagnostics each morning or record the sensor "Alert level" with its attributes, and count how often the rule held although everything was fine. An evaluation tool for this is not built yet.

### Why 20 seconds is the floor

Newborns breathe irregularly. Pauses of up to about ten seconds are part of normal breathing in the first weeks. A shorter delay would raise alarms on healthy children every night, and alarms that are usually wrong stop being answered. The delay can therefore not be set below 20 seconds.

## Known limits

- **Swaddling, sleeping bags and thick blankets** hide the movement from a camera.
- **Lying on the side with the back to the camera**, a flat camera angle and infrared noise at night weaken the video signal.
- **A fan or a mobile in the region** the engine looks at produces a periodic movement of its own.
- **Radar modules are designed for adults** at up to 1.5 m. A newborn has a much smaller chest, breathes 30 to 60 times a minute and has a pulse of 100 to 160. Whether a module's firmware reports plausible values for that, or cuts the range off, is not documented anywhere and has to be measured.
- **A stop of breathing movement directly after a large movement is not detected** until the source has seen breathing movement again. See [above](#silence-after-a-large-movement-is-not-counted).
- **An empty bed looks like a child that does not move.** A radar that reports zero and an engine that reports `no_motion` say the same for both. Lifting the child out normally does not raise the alert, because it is a large movement and because the sources forget what they saw while someone is with the child. This protection has gaps: it needs the movement to be seen (a sleep place with only a radar, without camera motion and without a door contact, has no such signal), and breathing movement only counts as seen again when a source reports it at least 10 seconds after the last large movement, because a radar can keep showing its last rate for a few seconds after the child is gone. A radar that holds a stale rate for longer than that can still make the rule hold. A presence sensor for the bed remains the reliable way to tell CheckBaby that the bed is empty. What the radar modules actually report for an empty bed, and how fast, has not been measured.
- **A pan-tilt camera that was moved** no longer shows the region the engine was set up for.
- **A moving pet, a curtain or a parent's arm** can count as a sign of life.
- **Every source can be late.** The rule adds its 20 seconds or more on top of whatever delay the source has. The vital engine judges a window of up to 25 seconds, so it reports `no_motion` only some time after breathing movement has stopped: 18 to 21 seconds in its tests with artificial signals. Over the camera path the hint is therefore roughly 40 seconds or more behind the event.
- **The vital engine only reports rates between 18 and 90 per minute** as breathing movement, and after any larger movement it reports `gross_motion` for about 12 seconds before it can judge again.

## Hardware notes

### Seeed MR60BHA2

A 60 GHz radar module sold as a kit with a XIAO ESP32-C6. With ESPHome it reports breathing rate, heart rate, distance and the number of targets locally, without a cloud. An example configuration is in [`esphome-mr60bha2.yaml`](../examples/esphome-mr60bha2.yaml); it is untested.

- Enter its breathing rate entity under "Breathing rate sensor (radar)" and its heart rate entity under "Heart rate sensor (radar)".
- Its target or presence entity can serve as "Presence sensor for the bed", if it turns out to be reliable.
- The plan is to use only the robust statement "target present and breathing movement seen: yes or no" at first, not the exact rate. That is how the integration treats it.
- Before use with a child: test it on an adult against a smartwatch or pulse oximeter, hold your breath for 20 seconds and note what the sensor reports, and note what it reports for an empty bed.

### Aqara FP2

The FP2 reports presence and zones locally through HomeKit. Its breathing rate, heart rate and sleep stage exist only in Aqara's cloud; a community add-on (SleepRadar) reads them from there.

- Locally it is useful as the **presence sensor for the bed** ("is lying in bed").
- Its vital data through the cloud is experimental at best: it depends on the internet, is evaluated for adults, and its delay is unknown. Do not use it as the only reason for an alert.
- A sleep place has one field for a breathing rate entity. You cannot enter the MR60BHA2 and the FP2 as two radar sources of the same sleep place.
- Whether two 60 GHz sensors at the same bed disturb each other has not been checked.

Other sensors (Aqara FP300 and FP400) report presence only and no vital data. DFRobot C1001 and HLK-LD6002 report vital data but need their own ESP32 firmware; they are alternatives if the MR60BHA2 does not work out.
