# AI assessment

[Deutsche Fassung](../de/ai-assessment.md) · [Back to the index](README.md)

The AI assessment is optional. It looks at a still image of the bed and answers a fixed list of questions: is the child there, how is it lying, is the face free, are there loose objects in the bed. Everything else, including every crying alert and the watchdog, works without it and without the internet.

**What is verified and what is not.** The call path is verified in the project's lab with a scripted model: CheckBaby calls Home Assistant's real `ai_task` action, and the camera picture reaches the model as a JPEG file. No real provider (Google Gemini, OpenRouter, Ollama) has been tried yet. Whether each of them accepts the picture attachment, and how well a model judges an infrared night image, is still open. Check the result with a doll before you give it any weight.

## What the AI is not used for

**The AI does not check breathing.** A language-and-image model sees single still images, takes seconds to answer and can be convincingly wrong. Breathing is a tiny periodic movement that needs a continuous signal. The [breathing-movement hint](vital-sources.md) therefore comes from a radar sensor or the vital engine, never from the AI. When "no breathing movement" is detected, CheckBaby does ask the AI for a look as additional information, but whatever the AI answers cannot clear or lower that alert.

The AI's own impression of whether the child is asleep or crying is stored with the answer and not used. The child's state comes from Frigate and your sensors.

## What an AI task is and where it comes from

An "AI task" is Home Assistant's connection to an AI model. CheckBaby does not talk to an AI provider itself and never asks for an API key. It hands the camera picture to an AI task, and Home Assistant passes it on to the model.

An AI task appears in CheckBaby's list once you have added an AI integration to Home Assistant under **Settings → Devices & services**, for example Google Gemini, OpenRouter or Ollama (for a local model). It is usually named after the provider. **If the list in CheckBaby is empty, no such integration is set up yet.**

## Setting it up

1. **Add the AI integration to Home Assistant.** Go to **Settings → Devices & services → Add integration**, choose **Google Gemini** or **OpenRouter** and enter the API key there. A local model through **Ollama** is added the same way. This is the one step that happens outside CheckBaby.
2. **Open the options of CheckBaby:** **Settings → Devices & services → CheckBaby → Configure → AI assessment**. While you set CheckBaby up for the first time, the same page appears as "AI assessment (optional)".
3. **Choose the model** in the field "AI model (an "AI task" of Home Assistant)".
4. **Confirm that pictures may be sent:** tick "Images of the child may be sent to these AI tasks". Without the tick the page cannot be saved while a model is chosen.
5. **Press "AI check now"** on the device page and read the result in Home Assistant's notifications (the bell in the sidebar). See [The result of "AI check now"](#the-result-of-ai-check-now).

That is all. The assessment now runs by itself whenever Monitoring is on. You do not need the developer tools, an automation or any YAML.

Good to know:

- The sleep place needs a **Camera entity**. The picture is taken from it.
- If you choose several AI tasks, they are asked in that order and the first usable answer is used.
- **AI calls per hour at most** (1 to 120, default 30) is on the same options page.
- The switch **AI assessment** on the device is on by default. It is a pause button: switch it off to stop the automatic assessments for a while without removing the AI task.

## What is sent and what is asked

Each assessment is one call of `ai_task.generate_data` with:

- **one still image** from the camera entity of the active sleep place,
- instructions in English that tell the model to report only what is visible and to answer "unknown" instead of guessing,
- the age profile and the state the monitor currently reads,
- a fixed answer structure.

The model has to fill in these fields:

| Field | Possible answers |
|---|---|
| `presence` | `in_bed`, `not_visible`, `caregiver_present` |
| `position` | `supine`, `prone`, `side`, `sitting`, `standing`, `unknown` |
| `face_visible` | yes / no: nose and mouth are visible and uncovered |
| `airway_risk` | `none`, `possible`, `likely`; "likely" only if nose and mouth are clearly covered or pressed into bedding |
| `state` | `asleep`, `awake_calm`, `awake_restless`, `crying`, `unknown` |
| `hazards` | loose objects in the bed (blanket, pillow, toy, cord); optional |
| `view_ok` | no if the image is too dark, blocked or does not show a bed |
| `assessment` | overall verdict: `ok`, `attention`, `warning`, `critical` |
| `confidence` | 0 to 1 |
| `reason` | one short sentence in the language of your Home Assistant |

The answer is treated as untrusted. If a required field is missing, the whole answer is rejected. A value that is not in the list is replaced by the cautious choice: an unreadable airway value becomes "possible", never "none".

The plan foresaw a series of three or four images. AI Task delivers one current image per camera, so the confirmation works through a second look after 15 seconds instead.

## When it runs

Automatic assessments need all of this: an AI task and the consent (from the setup or the options), a camera entity, Monitoring on, privacy mode off, the switch "AI assessment" not switched off, and the child not "Attended".

| Trigger | When |
|---|---|
| State change | The state becomes "Crying" or "Awake". |
| No breathing movement | The breathing-movement rule starts to hold, also in shadow mode. |
| Routine | Every 10 minutes (number "AI routine check interval", 2 to 60 minutes), counted from the last automatic assessment. |
| Second look | 15 seconds after an assessment that produced an airway or prone warning, or a first "camera view blocked". Only once; a second look never schedules a third. |
| Manual | The button "AI check now", the action `checkbaby.assess_now`, or `checkbaby.quick_check` with `with_ai`. |

Only one assessment runs at a time.

A manual assessment is carried out whenever AI tasks, consent and a camera entity are configured and privacy mode is off. It ignores the switch "AI assessment", the budget and whether Monitoring is on. While Monitoring is off, its result is displayed but raises no alert.

**In privacy mode no assessment is carried out at all, not even a manual one.** No image is sent; the button only reports that privacy mode is on, and the action returns an empty result.

### The result of "AI check now"

The button "AI check now" always shows what came of it: in Home Assistant's notifications (the bell in the sidebar) and as a notification on the phone on duty. A newer result replaces the older one.

- **If a check ran,** you read the AI's verdict, how sure it is and its reason in one sentence, for example "Looks fine (90 % sure). The child lies on its back and the face is free." The verdicts are "Looks fine", "Worth a look", "Please check" and "Possible danger".
- **If no check ran,** you read why: no AI task is chosen, sending pictures is not confirmed, privacy mode is on, the active sleep place has no camera entity, or a check is already running.
- **If the AI gave no usable answer,** you read that together with the error of the AI task that was tried last: a timeout, the provider's error message, or "unusable answer".

The action `checkbaby.assess_now` behaves as before: it returns the data and shows nothing.

## Budget, timeout and fallback

- **Budget:** at most the configured number of calls in any 60 minutes. When it is used up, automatic assessments are skipped until calls drop out of the hour. Manual assessments are always carried out and count towards the budget. The sensor "AI calls in the last hour" shows the count. With a routine check every 10 minutes, expect roughly 6 calls per hour plus the event-driven ones; the cost depends on your provider.
- **Fallback order:** the AI tasks are asked in the order you chose. The first usable answer wins. This is how you put a cloud model first and a local model second, or the other way round.
- **Timeout:** each AI task has 20 seconds. A timeout, an error or an unusable answer moves on to the next task.
- **If none answers:** the binary sensor "AI assessment available" turns off and nothing else changes. A check started with the button "AI check now" also says so in its result. The deterministic alerts work as before. An AI that cannot be reached never results in "all fine".

One assessment counts as one call towards the budget, however many AI tasks had to be tried.

## What the AI may do: the guard rails

The AI can only create, change and clear four alerts of its own: **Airway risk**, **Prone position**, **Loose objects in bed** and **Camera view blocked**. It has no way to touch an alert from another source. An AI answer of "all fine" during crying, a monitoring failure or "no breathing movement" changes nothing about those alerts.

"Confident" below means a confidence of at least 0.5. "Confirmed" means that the assessment before this one, at most 180 seconds earlier, said the same.

| What the AI reports | Result |
|---|---|
| Child in bed, airway risk "likely", confident | **Warning.** **Critical** once confirmed by the second look. |
| Child in bed, airway risk "possible", or "likely" but not confident | Hint |
| Child in bed, position "prone", newborn profile | **Warning** if confident, otherwise a hint. **Critical** once confirmed. |
| Child in bed, position "prone", infant profile | **Warning** if confident, otherwise a hint. Never critical: older infants may roll over on their own. |
| Position "prone", toddler profile | Nothing |
| Loose objects named | Hint, with the objects in the alert details |
| View not ok | Hint; **warning** once confirmed |

So on its own, with a single image, the AI reaches a warning at most. Critical needs two assessments in a row that see the same defined danger.

An AI alert ends when a later assessment no longer reports its cause, and it drops to a lower level when a later assessment reports the cause as less serious. For example, a confident "possible" after a "likely" lowers an airway warning to a hint, and the notification is then removed from the phones. One exception protects against an unsure look: an assessment that is not confident neither ends nor lowers an AI alert that is at warning or above. The AI alerts are also cleared when Monitoring is switched off, privacy mode is switched on or someone is with the child.

Once raised, an AI alert behaves like any other alert of its level: a critical one goes to all phones, repeats every 30 seconds and switches on the local alarm after a minute until someone taps "Seen" (see [How it works](how-it-works.md#the-three-alert-levels)). The next routine assessment may be up to the routine interval away, so acknowledge it yourself after you have checked.

## Privacy and consent

- **Cloud or local is your choice of AI task.** With a cloud provider such as Gemini or OpenRouter, an image of your child and its bed leaves your home with every assessment. With a local model, for example through Ollama on your own machine, it stays in your network.
- **Consent is required.** AI tasks cannot be saved without the tick, and without the tick no image is sent.
- **Check your provider's terms.** Depending on the plan, a provider may use submitted images to train its models. For Gemini, check whether you are on a paid plan and what it says about this.
- **CheckBaby does not store images.** It keeps the latest answer in memory (fields and the one-sentence reason) and shows it in the sensors "AI assessment" and "Position". The sentence appears in notifications. The planned debug archive for images is not implemented.
- **Home Assistant may keep the sentence in its history**, because it is an attribute of the sensor "AI assessment".
- **Privacy mode stops every assessment**, the automatic ones and the manual one. While it is on, no image is sent to an AI task.

See also [Safety and privacy](safety-and-privacy.md).
