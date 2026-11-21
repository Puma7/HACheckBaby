# Installation

[Deutsche Fassung](../de/installation.md) · [Back to the index](README.md)

CheckBaby is not a medical device. Keep a simple baby monitor as a fallback, at least until you have seen CheckBaby work in your home for a few weeks.

The steps below follow the code. They have not been walked through on a real installation with a camera and a phone yet, so treat the first evening as a test.

## What you need

| Requirement | Why |
|---|---|
| Home Assistant 2026.2 or newer | Older versions are not tested and HACS refuses the installation. |
| An MQTT broker and the MQTT integration in Home Assistant | Frigate publishes crying, sound level and motion over MQTT, and CheckBaby reads them there. |
| Frigate with audio detection for the camera at the bed | It recognises crying and reports the sound level. See [Frigate](frigate.md). |
| The Home Assistant companion app on each parent's phone | Alerts are sent as notifications of the companion app. |
| HACS | CheckBaby is installed as a custom repository. |

Optional, and each can be added later: a siren, light or switch as a local alarm in your bedroom; a door contact; a presence sensor for the bed; a temperature and humidity sensor; a radar sensor that reports a breathing rate; an AI task entity; smoke and CO detectors; a sensor that shows whether the internet connection is up.

You can run CheckBaby without Frigate if another device gives you a binary sensor that turns on while the child cries. See [Frigate](frigate.md#without-frigate).

## Install through HACS

1. Open HACS in Home Assistant.
2. Open the menu at the top right and choose **Custom repositories**.
3. Enter `https://github.com/Puma7/HACheckBaby`, choose the type **Integration** and add it.
4. Search for **CheckBaby** in HACS, open it and choose **Download**.
5. Restart Home Assistant.

## The setup dialog

Go to **Settings → Devices & services → Add integration** and choose **CheckBaby**. The dialog has four steps. Nothing is created until you confirm the last one.

### Step 1: the child

| Field | What to enter |
|---|---|
| Name of the child | Used for the device, the entity names and the notification texts. Each child is one entry; a second entry with the same name is refused. |
| Birth date or expected due date | Selects the age profile (newborn until about three months, infant until one year, toddler after that). You can set CheckBaby up before the birth with the due date. |

The age profile currently changes two things: how a prone position reported by the AI assessment is treated, and whether a child that leaves the bed on its own raises a warning (toddlers only). The other thresholds start with the same values for every age and you adjust them yourself.

### Step 2: the sleep place

A sleep place is one bed with its camera and sensors. You need a name and a sound source: either the Frigate camera name or a crying sensor. Everything else is optional.

| Field | What to enter |
|---|---|
| Name of the sleep place | For example "Bedside crib". |
| Frigate camera name | The camera's name in the Frigate configuration, for example `nursery`. Crying, sound level and motion come from Frigate over MQTT. |
| Camera entity | The camera entity in Home Assistant. It provides the picture in notifications and the image for the AI assessment. |
| Frigate zone of the bed | If set, a cat or dog that Frigate sees in this zone raises a warning. |
| Door contact | While the door is open, someone is assumed to be with the child and the child-related alerts pause. |
| A person seen by the camera counts as a caregiver | Turn on only if Frigate does not detect the child itself as a person. |
| Presence sensor for the bed | A binary sensor that is on while the child is in bed. |
| Room temperature, Room humidity | Shown on the device; the temperature is also checked against the range you set. The sensor may report degrees Celsius or Fahrenheit; Fahrenheit is converted before the comparison. |
| Breathing rate sensor (radar), Heart rate sensor (radar) | See [Vital sources](vital-sources.md). |
| Vital engine ID | Only with the CheckBaby vital engine, see [Vital sources](vital-sources.md). |
| Audio stream address | Played on a speaker by the audio relay, for example an audio stream from go2rtc. |
| Crying sensor, Motion sensor, Sound level sensor | The alternative to Frigate. They are ignored while a Frigate camera name is set. |

### Step 3: who is told

| Field | What to enter |
|---|---|
| Phones | The notify services of the companion app, for example `mobile_app_annas_iphone`. The list offers every service that starts with `mobile_app_`; you can type another notify service name. |
| Local alarm (siren, light, switch) | Switched on when an alert stays unanswered for a minute, or at once while the internet is down. Put it where you sleep, never in the child's room. |

You must choose at least one phone or one local alarm. Without either, no alert could reach anyone.

### Step 4: the intended-use notice

The last step shows what CheckBaby is and what it is not. You have to tick "I have read and understood this" to finish.

## After the setup

The device of the child appears with its entities. **Monitoring is off at first.** Turn on the switch **Monitoring** when you want alerts.

More settings are in the options of the entry (**Configure**): the babysitter's phone, heartbeat buttons for a dead-man buzzer, smoke and CO detectors, the internet connectivity sensor, the speaker for the audio relay, the AI tasks with the consent to send images, the AI calls per hour, the Frigate MQTT topic prefix (default `frigate`) and the dashboard that a notification opens (default `/lovelace`).

Further sleep places are added on the entry with **Add sleep place**. Exactly one sleep place is monitored at a time; you choose it with the select **Active sleep place**.

Changing the options or a sleep place reloads the entry. Settings, active alerts and the sleep log survive that.

## First function test

Do this before you rely on anything.

1. **Wait two minutes** after the setup. In that time sources that have not reported yet do not count as a problem.
2. **Check the watchdog.** The binary sensor **Monitoring problem** must be off. If it is on, the sensor **Monitoring problems** lists the reasons in its attribute `problems`; [Troubleshooting](troubleshooting.md) explains each one.
3. **Silence your phone** and switch on Do Not Disturb. This is the case that matters at night.
4. **Press the button "Test alert"** on the device page (it is listed under Diagnostic). The test works even while Monitoring is off.
5. **Check what arrives.** Every configured phone should receive a notification with the title "ALARM · (name)" and the text "Test alert. Tap “Seen” to end it." It should sound although the phone is silent. If you set a camera entity, it carries a picture.
6. **Wait.** The notification repeats every 30 seconds. After 60 seconds without a reaction the local alarm switches on.
7. **Tap "Seen"** in the notification. The notification disappears from all phones and the local alarm switches off. If nobody taps it, the test ends by itself after ten minutes.

If the critical alert does not sound, see [Troubleshooting](troubleshooting.md#a-critical-alert-does-not-sound).

Then test the real chain:

1. Turn on **Monitoring**.
2. Play a recording of a crying baby next to the camera at a realistic volume.
3. With the default settings the state changes to "Crying" after about 8 seconds of detected crying and a warning arrives after 15 seconds. Frigate's own detection delay comes on top.

Repeat the test alert from time to time, and after every update of Home Assistant, Frigate or the companion app. A guided function test with a monthly reminder is planned but not implemented yet.

## Dashboard and automations

- An example dashboard is in [`docs/examples/dashboard.yaml`](../examples/dashboard.yaml).
- The two blueprints are in [`blueprints/automation/checkbaby/`](../../blueprints/automation/checkbaby/). Copy them to `config/blueprints/automation/checkbaby/` on your Home Assistant, or use **Settings → Automations & scenes → Blueprints → Import blueprint** with the address of the file on GitHub. HACS does not install blueprints.
