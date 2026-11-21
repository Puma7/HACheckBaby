# Safety and privacy

[Deutsche Fassung](../de/safety-and-privacy.md) · [Back to the index](README.md)

## Intended use

CheckBaby is an attention and convenience system for parents. It tells you when your child cries, when something in the bed looks wrong to an AI model, when the room is too warm or cold, and when its own monitoring has failed.

**CheckBaby is not a medical device.** It makes no diagnosis and it guarantees no detection.

- **It cannot prevent sudden infant death.** No monitoring device has been shown to do that. The American Academy of Pediatrics advises in its 2022 recommendations against using home monitors as a strategy to reduce that risk. Using one is not harmful, but it does not replace the measures that are proven to help.
- **It can fail without warning.** It depends on a camera, Wi-Fi, Frigate, an MQTT broker, Home Assistant, your phone and usually the internet. The watchdog reports many failures, but not a failure of Home Assistant itself unless you build the dead-man buzzer, and not a phone that is switched off.
- **It can be wrong in both directions.** Crying can go undetected, and alerts can be false. The AI assessment can describe a picture convincingly and incorrectly.
- **The breathing-movement hint is unvalidated on infants** and is switched off by default. See [Vital sources](vital-sources.md).
- **It has not run on real hardware yet.** The integration is covered by automated tests; the checks with a real camera, phone and sensor are still to be done.

What follows for you:

- Keep a simple baby monitor as a fallback, at least until CheckBaby has run next to it for two weeks without a missed cry and without an unnoticed failure.
- Never let a quiet phone stand in for looking in on your child.
- Repeat the test alert regularly.
- It is not a travel solution. Away from home, a simple device remains the sensible choice.

The project uses the words "breathing-movement hint" on purpose. Software that is advertised as monitoring physiological processes or preventing illness can fall under the EU Medical Device Regulation. A legal review of the intended use is planned before version 1.0 and has not happened yet.

## Safe-sleep basics

These measures are the ones with evidence behind them. No device replaces them.

- Put your baby to sleep **on the back**.
- Use a **firm, flat** surface.
- Let the baby sleep in **its own bed in your room**.
- **No loose blankets, pillows or soft toys** in the bed.
- **Do not overheat** the baby or the room.
- Keep the surroundings **smoke-free**.

This list is a short summary and not medical advice. Your midwife or paediatrician is the right person for questions about your child.

CheckBaby can support some of these points, if you use the optional parts: the AI assessment can point out a prone position, a covered face and loose objects in the bed, and the room temperature is checked against the range you set. These are hints from a system that can err. An empty hint list does not mean the bed is safe.

Cables and devices near the cot are a danger of their own; see [Hardware](hardware.md#mounting-and-cable-safety).

## Privacy

### Where the data is

Everything is processed in your home, with one exception that you have to switch on yourself: the AI assessment with a cloud provider.

| Data | Where it is |
|---|---|
| Camera picture and sound | In the camera, in Frigate and in Home Assistant. Recording and retention are Frigate's settings; CheckBaby does not record. |
| The child's name and birth date | In the configuration of Home Assistant. |
| Settings, active alerts, sleep log, learned noise floor | In a file in Home Assistant's storage folder. Deleted when you remove the entry. |
| Event log (the last 300 decisions with their cause) | In memory only; lost at a restart. Included in the diagnostics download. |
| Images for the AI assessment | Not stored by CheckBaby. Sent to the AI task you chose. |

The sensors' history is kept by Home Assistant's recorder like that of any other entity.

### No telemetry

CheckBaby sends nothing to the project or to third parties, and the code contains no network access of its own. The only data that can leave your home through CheckBaby are the notifications to your phones and, if you enable it, the images for a cloud AI.

### Keep the camera off the internet

- Give the camera **no internet access**: a firewall rule or a separate network segment.
- Open **no ports** to the camera or to Frigate.
- Keep the RTSP credentials **only in Frigate**.
- Reach the picture from outside **only through your secured Home Assistant access**.

### Pictures in notifications

If the sleep place has a camera entity, each alert notification carries a current picture. The phone loads it from your Home Assistant; away from home this needs your external address. The picture can appear on the lock screen. An option to leave the picture out is planned but not implemented: to send no pictures at all, leave the field "Camera entity" empty, which also turns off the AI assessment.

Push notifications normally travel through Apple's or Google's servers.

### Cloud AI needs your consent

With a cloud provider, an image of your child and its bed leaves your home with every assessment. CheckBaby does not send any image until you have ticked "Images of the child may be sent to these AI tasks" in the options. Depending on the plan, a provider may use images for training; read its terms. A local model keeps the images at home. Details are in [AI assessment](ai-assessment.md#privacy-and-consent).

### A camera in your own bedroom

In the first months the child usually sleeps in the parents' bedroom, and so the camera hangs there too.

- Use **privacy mode** for moments in front of the camera. Be aware of its limit: it pauses CheckBaby's detection and notifications. It does not switch off the camera or Frigate's recording.
- Set Frigate to record **nothing or only for a short time** for this camera.

### Recording other people's speech

A camera with a microphone records everyone in the room, not only the child. In Germany, secretly recording non-public conversations is a criminal offence (§ 201 StGB). Babysitters, grandparents and visitors must know that camera and microphone are running. Tell them before they are in the room.

Babysitter mode changes who is notified and how fast. It does not show such a notice by itself; telling people is up to you.

This is a pointer, not legal advice. Other countries have their own rules.

### The diagnostics download

The diagnostics download removes the child's name, the birth date, the audio stream address, the names of the sleep places and the AI's sentences. It does contain the names of your notify services and entities. Read it before you attach it to a public bug report.
