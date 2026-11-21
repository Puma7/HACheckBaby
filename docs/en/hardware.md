# Hardware

[Deutsche Fassung](../de/hardware.md) · [Back to the index](README.md)

This page collects what the project's research found. **None of the devices named here has been tested with CheckBaby yet.** The statements about cameras come from manufacturer pages, the Frigate documentation and forum reports. Treat the tables as a starting point for your own check, not as a list of tested hardware; a tested list will follow once it exists.

## What the camera must be able to do

- **RTSP and audio in the same stream.** Frigate detects crying from the camera's sound. Many cheap cameras no longer offer RTSP, or offer RTSP without sound.
- **A usable infrared night picture** from about one metre, without the bed being washed out.
- **A stable connection for weeks.** A monitor that drops out once a night is of little use.

## Camera candidates

All candidates are inexpensive Wi-Fi indoor cameras with a power supply. Not every model of a brand offers RTSP; the exact model decides.

| Candidate | RTSP and sound | Two-way talk | Notes |
|---|---|---|---|
| UniFi G3 Instant | Through the UniFi Protect console, not directly from the camera; in go2rtc as `rtspx://` | Only in the Protect app | 1080p, 111° wide angle, infrared up to 6 m. The console becomes part of the alarm chain. CheckBaby does not watch the console itself; if it fails, you see it as missing sound (`audio_level`) or an unavailable camera. |
| Reolink E1 Pro / E1 Zoom (pan-tilt) | Directly, sound as AAC | Through go2rtc, depending on the model | See the buying trap below. |
| TP-Link Tapo C200 / C210 / C120 | Directly, after enabling it in the app | Through go2rtc (`tapo://`), depending on the firmware | Inexpensive. The app pushes you towards the cloud, which you can ignore. |
| Eufy indoor camera with pan-tilt | Unclear | Unclear | No reliable reports with Frigate found. Do not buy without your own test. |

### The buying trap: the base Reolink E1

**The plain Reolink E1 (without "Pro" or "Zoom") does not offer RTSP or ONVIF directly.** It only works through a Reolink hub or NVR. The E1 Pro and E1 Zoom do offer RTSP. The names differ by one word and the boxes look alike, so check the exact model before you order.

### How to choose

If you can, compare two cameras side by side on four points:

1. Is there sound in the stream, and can Frigate evaluate it?
2. What does the infrared picture look like from about one metre: washed out, sharp, noisy?
3. How large is the delay of picture and sound?
4. Does it run for 14 days without dropping out?

### Pan-tilt cameras

A pan-tilt head is handy with several sleep places. But after each move, the bed zone in Frigate and the region of the vital engine no longer match the picture. Use a fixed preset "bed" and return to it. CheckBaby does not detect a moved camera by itself; only the AI assessment can notice that the picture no longer shows a bed ("Camera view blocked"), and only if you use it.

## Bill of materials

Only the camera is required. Everything else adds a function.

| Part | What CheckBaby uses it for |
|---|---|
| Indoor camera with RTSP and sound | Picture, sound, Frigate detection |
| Door contact | "Someone is with the child": pauses the child-related alerts while the door is open |
| Siren, or a light or smart plug, in the parents' bedroom | Local alarm that works without the internet |
| Temperature and humidity sensor | Room climate display, temperature range alert, sleeping bag suggestion |
| Seeed MR60BHA2 | Local radar source for the breathing-movement hint, see [Vital sources](vital-sources.md) |
| Aqara FP2 | Local presence sensor for the bed; its vital data only through the cloud |
| ESP32 with a buzzer | Outage buzzer (dead-man buzzer): it sounds when Home Assistant falls silent, see [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml) |
| Smoke and CO detectors that Home Assistant can read | Passed through as a critical alert |
| A sensor that shows whether the internet is reachable | Makes the local alarm fire at once while the internet is down |
| UPS for server, switch and router (optional) | Bridges short power cuts |

Without a local alarm, every alert depends on the push notification, and that normally travels through Apple's or Google's servers. If your internet connection fails, a siren or light in your bedroom is the channel that still works.

## Mounting and cable safety

**Cables are the real danger near a cot.** A child can pull a cable into the bed and get caught in it.

- Keep every cable, power supply and device **at least one metre away from the bed and out of the child's reach**. Remember that the reach grows: a child that cannot stand today will stand in a few months.
- Run cables along the wall in a cable duct, not loosely and not along the cot.
- Do not attach anything to the cot itself, and put nothing into the bed. This also applies to sensors.
- Mount the camera so that it cannot fall into the bed: screwed to the wall or ceiling, not on a shelf edge above the cot.

For the picture:

- Mount the camera **as vertically above the bed as you can**. A flat angle weakens the AI assessment and the vital engine.
- Check the night picture with the room dark. If the infrared light washes out the mattress, increase the distance or change the angle.
- If the camera hangs in your own bedroom in the first months, think about privacy mode and about what Frigate records; see [Safety and privacy](safety-and-privacy.md).

For the local alarm:

- Put the siren or light **where you sleep, never in the child's room**.

For radar sensors:

- All available modules are designed for adults at up to 1.5 m. Research on premature infants worked with its own evaluation of raw data from about 45 cm. Which distance and angle work for an infant with a ready-made module is not known and has to be measured. The same cable rules apply.
