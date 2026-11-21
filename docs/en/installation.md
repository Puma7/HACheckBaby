# Installation

[Deutsche Fassung](../de/installation.md) · [Back to the index](README.md)

CheckBaby is not a medical device. Keep a simple baby monitor as a fallback, at least until you have seen CheckBaby work in your home for a few weeks.

The setup described here is exercised in a lab: a real Home Assistant with simulated camera, phones and sensors, set up through the same interface that the dialogs use. A first installation on a real Home Assistant has taken place; what it showed led to changes in this version (phones are chosen with tick boxes, and results are visible in Home Assistant's notifications). It is not yet confirmed that a push arrives on a real phone, and nothing is known yet about a real Frigate, a real AI provider or a radar sensor. So treat the first evening as a test.

## The whole path

1. Install CheckBaby through HACS and restart Home Assistant.
2. Add the integration and answer five short pages.
3. Switch on **Monitoring** and press **Test alert** once.

That is all it takes. Everything else on this page explains these three steps. The AI assessment, a radar sensor, more sleep places and a dashboard can all be added later.

## Before you start

| You need | Why |
|---|---|
| Home Assistant 2026.2 or newer, with HACS | Older versions are not tested and HACS refuses the installation. |
| An MQTT broker and the MQTT integration in Home Assistant | Frigate publishes crying, sound level and motion over MQTT, and CheckBaby reads them there. |
| Frigate with audio detection for the camera at the bed | It recognises crying and reports the sound level. One setting matters: `crying` has to be added to Frigate's `listen` list. See [Frigate](frigate.md). |
| The Home Assistant companion app on each parent's phone, signed in to your Home Assistant | Alerts are sent as notifications of the companion app. A phone shows up in CheckBaby only after the app on it has signed in. |

Have two names ready, because the setup asks for them:

- the **name of the camera in Frigate**, for example `nursery`,
- the **camera entity in Home Assistant**, for example `camera.nursery`.

No Frigate? CheckBaby also runs with a binary sensor that turns on while the child cries. See [Frigate](frigate.md#without-frigate).

## Step 1: install through HACS

1. Open HACS in Home Assistant.
2. Open the menu at the top right and choose **Custom repositories**.
3. Enter `https://github.com/Puma7/HACheckBaby`, choose the type **Integration** and add it.
4. Search for **CheckBaby** in HACS, open it and choose **Download**.
5. Restart Home Assistant.

## Step 2: add CheckBaby

Go to **Settings → Devices & services → Add integration** and choose **CheckBaby**. Five pages follow. Nothing is created until you confirm the last one.

### Page 1: the child

| Field | What to enter |
|---|---|
| Name of the child | Used for the device, the entity names and the notification texts. Each child is one entry; a second entry with the same name is refused. |
| Birth date or expected due date | Sets the age profile (newborn until about three months, infant until one year, toddler after that). You can set CheckBaby up before the birth with the due date. |

The age profile decides which alerts apply: how a prone position reported by the AI assessment is treated, and whether a child that leaves the bed on its own raises a warning (toddlers only). It does not change any threshold.

### Page 2: the sleep place

A sleep place is one bed with its camera and sensors. **For a start, fill in three fields and leave the rest empty:**

| Field | What to enter |
|---|---|
| Name of the sleep place | For example "Bedside crib". |
| Frigate camera name | The camera's name in the Frigate configuration, for example `nursery`. Crying, sound level and motion come from Frigate over MQTT. |
| Camera entity | The camera entity in Home Assistant. It provides the picture in notifications and the image for the AI assessment. |

Only the name and a sound source (the Frigate camera name, or a crying sensor) are required. All other fields are optional and can be filled in later with **Change sleep place** on the entry:

| Optional field | What it does |
|---|---|
| Frigate zone of the bed | A cat or dog that Frigate sees in this zone raises a warning. |
| Door contact | While the door is open, someone is assumed to be with the child and the child-related alerts pause. |
| A person seen by the camera counts as a caregiver | Turn on only if Frigate does not detect the child itself as a person. |
| Presence sensor for the bed | A binary sensor that is on while the child is in bed. |
| Room temperature, Room humidity | Shown on the device; the temperature is also checked against the range you set. The sensor may report degrees Celsius or Fahrenheit; Fahrenheit is converted before the comparison. |
| Breathing rate sensor (radar), Heart rate sensor (radar), Vital engine ID | For the breathing-movement hint, see [Vital sources](vital-sources.md). |
| Audio stream address | Played on a speaker by the audio relay, for example an audio stream from go2rtc. |
| Crying sensor, Motion sensor, Sound level sensor | The alternative to Frigate. They are ignored while a Frigate camera name is set. |

### Page 3: who is told

| Field | What to enter |
|---|---|
| Phones | Every phone with the Home Assistant companion app is listed by its device name, with a tick box. Tick the parents' phones; nothing has to be typed. Other notify services, for example a notify group, are listed as `notify.<name>`. |
| Local alarm (siren, light, switch) | Optional but recommended: a device that Home Assistant switches itself. It is switched on when an alert stays unanswered for a minute, or at once while the internet is down. Put it where you sleep, never in the child's room. The device has to be reachable in Home Assistant: a lamp that is off at the wall switch stays dark. |

You must tick at least one phone or choose a local alarm. Without either, no alert could reach anyone.

**A phone is missing from the list?** Open the Home Assistant app on that phone and sign in to your Home Assistant. The list is read when the page opens, so open the page again afterwards.

**The phone is the main alarm.** A critical alert is sent so that it sounds through Do Not Disturb. A push normally travels through the servers of Apple or Google and therefore needs the internet. The local alarm is the path that works with no internet at all. More on both, and on receiving notifications over the home network, is under [Where an alert arrives](how-it-works.md#where-an-alert-arrives).

### Page 4: AI assessment (optional)

**To skip it, leave the page empty and continue.** Everything else works without it, and you can come back to it later.

An AI model can look at a camera picture and say whether the child lies on its back, whether the face is free and whether loose things are in the bed. If you want that:

1. The model itself is added once in Home Assistant, not in CheckBaby: **Settings → Devices & services → Add integration → Google Gemini** or **OpenRouter**. That is where you enter the API key. A local model through **Ollama** is added the same way. If you have not done this yet, skip this page now and do it afterwards.
2. On this page, choose the model in the field **AI model (an "AI task" of Home Assistant)**. An empty list means that no AI integration is set up yet.
3. Tick **Images of the child may be sent to these AI tasks**. With a cloud model, pictures of your child leave your home; read [AI assessment](ai-assessment.md#privacy-and-consent) first.

Nothing else is needed. From then on the assessment runs by itself while Monitoring is on.

### Page 5: the intended-use notice

The last page says what CheckBaby is and what it is not. Tick "I have read and understood this" to finish.

## Step 3: switch on and test

Home Assistant confirms the setup with a short note: "Done. Two things before the first night: switch on "Monitoring" on the device page when the child sleeps, and press "Test alert" once to check that the alert arrives on every phone, also when it is muted." These are the two things:

1. **Open the device** of the child (Settings → Devices & services → CheckBaby). **Monitoring is off at first.**
2. **Silence your phone** and switch on Do Not Disturb. This is the case that matters at night.
3. **Press "Test alert"** on the device page (it is listed under Diagnostic). The test works even while Monitoring is off.
4. **Check what arrives.** Every ticked phone should receive a notification with the title "ALARM · (name)" and the text "Test alert. Tap “Seen” to end it." It should sound although the phone is silent. If you set a camera entity, it carries a picture.
5. **Look at the bell in Home Assistant** (the notifications in the sidebar). There are two entries: the test alert itself and a delivery report. The report says where the alert went: which notify services accepted the message, which could not be reached, and which local alarm devices are set or unreachable. If nothing arrived on a phone, start here.
6. **Wait a minute** if you chose a local alarm. The notification repeats every 30 seconds, and after 60 seconds without a reaction the local alarm switches on.
7. **Tap "Seen"** in the notification. The notification disappears from all phones and from Home Assistant's notifications, and the local alarm switches off. The delivery report stays until you dismiss it. If nobody taps "Seen", the test ends by itself after ten minutes.
8. **Switch on "Monitoring"** when the child sleeps.

If no notification arrives, see [Troubleshooting](troubleshooting.md#no-notification-arrives-on-the-phone). If the critical alert arrives but does not sound, see [Troubleshooting](troubleshooting.md#a-critical-alert-does-not-sound).

Two minutes after the setup, look at the binary sensor **Monitoring problem** on the device page. It must be off. If it is on, the sensor **Monitoring problems** names the reasons, and [Troubleshooting](troubleshooting.md) explains each one.

## Step 4: test with real crying

1. Make sure **Monitoring** is on.
2. Play a recording of a crying baby next to the camera at a realistic volume.
3. With the default settings the state changes to "Crying" after about 8 seconds of detected crying and a warning arrives after 15 seconds. Frigate's own detection delay comes on top.

Repeat the test alert from time to time, and after every update of Home Assistant, Frigate or the companion app. A guided function test with a monthly reminder is planned but not implemented yet.

## Later, when you need it

### Change a setting

Go to **Settings → Devices & services → CheckBaby** and choose **Configure**. A menu with three short pages opens. Saving one page keeps the settings of the other two.

| Page | What is on it |
|---|---|
| Who is told | Phones, local alarm, babysitters' phones, sign of life for an outage buzzer |
| AI assessment | AI model (an "AI task" of Home Assistant), the consent to send images, AI calls per hour at most (default 30) |
| Other devices and settings | Smoke and CO detectors, internet connectivity sensor, speaker for the audio relay, Frigate MQTT topic prefix (default `frigate`), dashboard that a notification opens (default `/lovelace`) |

The page "Who is told" has two fields that the setup does not ask for:

- **Babysitters' phones:** tick boxes like "Phones", for example for grandparents or a babysitter. These phones receive alerts only while the mode is "Babysitter", in addition to the phones ticked under "Phones". If a phone is ticked only here and neither a phone under "Phones" nor a local alarm is chosen, the page is refused with a message of its own, because that phone would be told in babysitter mode only.
- **Sign of life for an outage buzzer (optional):** leave this empty unless you have built an outage buzzer (also called a dead-man buzzer). That is a small device of your own that beeps when Home Assistant falls silent, for example after a crash or when the power or the Wi-Fi fails. CheckBaby presses the button chosen here every 30 seconds as a sign of life while Monitoring is on and working. A build example for an ESP32 is in [`esphome-deadman-buzzer.yaml`](../examples/esphome-deadman-buzzer.yaml).

A phone or notify service that was ticked earlier and no longer exists in Home Assistant stays in the list with a "?" behind its name, so that you can untick it.

The thresholds and switches (for example how long crying lasts before a warning) are not in this menu. They are entities on the device page, see [Entities and actions](entities-and-actions.md).

### Add the AI assessment afterwards

Add the model's integration as described under page 4, then open **Configure → AI assessment**, choose the model and tick the consent. Then press "AI check now" on the device page: the result appears in Home Assistant's notifications. Details are in [AI assessment](ai-assessment.md#setting-it-up).

### More sleep places

Use **Add sleep place** on the CheckBaby entry, and **Change sleep place** to edit one. Exactly one sleep place is monitored at a time; you choose it with the select **Active sleep place** on the device page.

Changing a setting or a sleep place reloads the entry. Your settings, active alerts and the sleep log survive that.

### Dashboard and automations

- An example dashboard is in [`docs/examples/dashboard.yaml`](../examples/dashboard.yaml). The file explains at its top how to use it.
- Two blueprints are in [`blueprints/automation/checkbaby/`](../../blueprints/automation/checkbaby/). Copy them to `config/blueprints/automation/checkbaby/` on your Home Assistant, or use **Settings → Automations & scenes → Blueprints → Import blueprint** with the address of the file on GitHub. HACS does not install blueprints.

### Updates

HACS offers an update when a new release of CheckBaby is published on GitHub. Version numbers follow the release tags (0.0.1, 0.0.2, …). Repeat the test alert after each update.
