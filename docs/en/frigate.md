# Frigate

[Deutsche Fassung](../de/frigate.md) · [Back to the index](README.md)

Frigate does the listening and watching: it detects crying in the camera's audio, measures the sound level and detects motion. CheckBaby does no audio or video processing itself. It subscribes to what Frigate publishes over MQTT and decides what that means for the child.

The MQTT topics below are the ones in the code. They follow the Frigate documentation and have not been checked against a running Frigate yet. If your Frigate version publishes something different, CheckBaby reports a monitoring problem instead of staying silent, and the topic and payload you see are the most useful thing to put into a bug report.

## What CheckBaby reads

`<prefix>` is the Frigate MQTT topic prefix. The default is `frigate`; if you changed `topic_prefix` in Frigate, enter the same value in the CheckBaby options under **Frigate MQTT topic prefix**. `<camera>` is the **Frigate camera name** of the active sleep place, `<zone>` its **Frigate zone of the bed**.

| Topic | Expected payload | What CheckBaby does with it |
|---|---|---|
| `<prefix>/available` | `online`, anything else counts as offline | Watchdog: Frigate is running. |
| `<prefix>/<camera>/audio/crying` | `ON` / `OFF` | Crying is being heard. |
| `<prefix>/<camera>/audio/scream` | `ON` / `OFF` | Screaming is being heard. It counts like crying, with a shorter confirmation time. |
| `<prefix>/<camera>/audio/dBFS` | a number | Sound level. Feeds the level sensor, the learned noise floor and "loud". Also the watchdog's proof that sound is arriving. |
| `<prefix>/<camera>/motion` | `ON` / `OFF` | Movement in the picture. |
| `<prefix>/<camera>/person` | a count | Only if "A person seen by the camera counts as a caregiver" is on: a count above zero means someone is with the child. |
| `<prefix>/<zone>/cat`, `<prefix>/<zone>/dog` | a count | Only if a bed zone is set: a count above zero raises the warning "Pet in bed". |

Payloads that cannot be read (not a number where a number is expected) are ignored.

CheckBaby does **not** read: other audio labels such as `yell` or `speech`, `audio/rms`, `frigate/events`, `frigate/reviews`, snapshots or clips. The picture in a notification comes from the camera entity in Home Assistant, not from Frigate.

Only the active sleep place is subscribed. When you switch the sleep place, CheckBaby drops the old subscriptions and subscribes to the new camera.

## What Frigate has to be set up for

An example is in [`docs/examples/frigate-camera.yaml`](../examples/frigate-camera.yaml). The points that matter:

1. **MQTT is enabled in Frigate** and uses the same broker as Home Assistant.
2. **The camera stream contains audio**, and one input of the camera has the role `audio`. Many cheap cameras deliver RTSP without sound; see [Hardware](hardware.md).
3. **Audio detection is enabled for the camera** and **`listen` contains `crying` and `scream`**. According to the Frigate documentation the default list is `bark`, `fire_alarm`, `scream`, `speech`, `yell`. `crying` is not in it, so with the defaults Frigate never reports crying. You may add `yell` for your own use; CheckBaby ignores it.
4. **Motion detection runs** for the camera, so that `<camera>/motion` is published.
5. Optional, for the pet warning: Frigate tracks `cat` and `dog`, and a zone covers the bed. Enter the zone's name in the sleep place.
6. Optional, for "person counts as caregiver": Frigate tracks `person`. Leave the option off if Frigate detects the child itself as a person, otherwise the child would count as its own caregiver and the alerts would pause.

Frigate's own thresholds (`min_volume`, the per-label `threshold`, `max_not_heard`) decide when `crying` switches to `ON` and back to `OFF`. CheckBaby then applies its own durations on top, see [How it works](how-it-works.md).

Recording and retention stay with Frigate. For a camera in your own bedroom, consider recording nothing or only for a short time; see [Safety and privacy](safety-and-privacy.md).

## What the watchdog expects from Frigate

While a sleep place uses a Frigate camera, these sources are watched. Each one that fails shows up by name in the sensor **Monitoring problems**:

| Problem | Meaning |
|---|---|
| `mqtt` | The MQTT integration is not loaded or not connected to the broker. |
| `frigate` | `<prefix>/available` does not say `online`, or nothing was received on it within two minutes after the start. |
| `audio_level` | No sound level arrived on `<camera>/audio/dBFS` for more than 60 seconds. |
| `microphone` | Levels arrive, but the value has not changed at all for ten minutes. That points to a dead microphone or a muted stream. |

`mqtt`, `frigate` and `audio_level` are core sources. While one of them is a problem, CheckBaby does not know how the child is, and the state shows "Unknown" instead of "Asleep".

## Without Frigate

A sleep place can use ordinary Home Assistant entities instead. Leave **Frigate camera name** empty and fill in:

| Field | Entity | Notes |
|---|---|---|
| Crying sensor | a binary sensor | Required. On while the child cries, for example the crying detection of the camera itself. |
| Motion sensor | a binary sensor | Optional. On while there is movement. |
| Sound level sensor | a sensor with a numeric value | Optional. It is compared with the learned noise floor plus a margin in dB, so it should be a level in dB. |

CheckBaby reads these entities every two seconds and at once when the crying or motion sensor changes. The watchdog reports `cry_sensor` when the crying sensor is unavailable and `audio_level` when the level sensor has no numeric value; in both cases the state becomes "Unknown".

The sound level sensor has to move. If its value stays exactly the same for ten minutes, CheckBaby assumes a dead microphone and reports `microphone`. A sensor that rounds coarsely or updates rarely will trigger this in a quiet room; in that case leave the field empty.

Without Frigate there is no screaming signal, no pet warning and no "person counts as caregiver".

**Do not combine the two.** If a sleep place has both a Frigate camera name and a crying or motion sensor, both write the same signal and the entity overwrites Frigate's value every two seconds. The sound level sensor is ignored as soon as a Frigate camera name is set.
