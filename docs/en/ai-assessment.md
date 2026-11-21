# AI assessment

[Deutsche Fassung](../de/ai-assessment.md) · [Back to the index](README.md)

The AI assessment is optional. It looks at a still image of the bed and answers a fixed list of questions: is the child there, how is it lying, is the face free, are there loose objects in the bed. Everything else, including every crying alert and the watchdog, works without it and without the internet.

The call to the AI has been tested against a simulated AI task only. Which providers accept a camera image through Home Assistant's AI Task, and how well a model judges an infrared night image, has not been tried yet. Check the result with a doll before you give it any weight.

## What the AI is not used for

**The AI does not check breathing.** A language-and-image model sees single still images, takes seconds to answer and can be convincingly wrong. Breathing is a tiny periodic movement that needs a continuous signal. The [breathing-movement hint](vital-sources.md) therefore comes from a radar sensor or the vital engine, never from the AI. When "no breathing movement" is detected, CheckBaby does ask the AI for a look as additional information, but whatever the AI answers cannot clear or lower that alert.

The AI's own impression of whether the child is asleep or crying is stored with the answer and not used. The child's state comes from Frigate and your sensors.

## Setting it up

1. Set up an integration that provides an **AI Task** entity in Home Assistant, for example Google Gemini, OpenRouter or Ollama.
2. Make sure the sleep place has a **Camera entity**. The image is taken from it.
3. Open the options of the CheckBaby entry.
4. Choose one or more entities under **AI tasks, in order of preference**.
5. Tick **Images of the child may be sent to these AI tasks**. Without this the options cannot be saved while AI tasks are chosen.
6. Set **AI calls per hour at most** (1 to 120, default 30).
7. Turn on the switch **AI assessment** on the device. It is off by default.

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

Automatic assessments need all of this: Monitoring on, privacy mode off, the switch "AI assessment" on, AI tasks and consent in the options, a camera entity, and the child not "Attended".

| Trigger | When |
|---|---|
| State change | The state becomes "Crying" or "Awake". |
| No breathing movement | The breathing-movement rule starts to hold, also in shadow mode. |
| Routine | Every 10 minutes (number "AI routine check interval", 2 to 60 minutes), counted from the last automatic assessment. |
| Second look | 15 seconds after an assessment that produced an airway or prone warning, or a first "camera view blocked". Only once; a second look never schedules a third. |
| Manual | The button "AI check now", the action `checkbaby.assess_now`, or `checkbaby.quick_check` with `with_ai`. |

Only one assessment runs at a time.

A manual assessment is carried out whenever AI tasks, consent and a camera entity are configured. It ignores the switch "AI assessment", the budget, privacy mode and whether Monitoring is on. While Monitoring is off or privacy mode is on, its result is displayed but raises no alert.

## Budget, timeout and fallback

- **Budget:** at most the configured number of calls in any 60 minutes. When it is used up, automatic assessments are skipped until calls drop out of the hour. Manual assessments are always carried out and count towards the budget. The sensor "AI calls in the last hour" shows the count. With a routine check every 10 minutes, expect roughly 6 calls per hour plus the event-driven ones; the cost depends on your provider.
- **Fallback order:** the AI tasks are asked in the order you chose. The first usable answer wins. This is how you put a cloud model first and a local model second, or the other way round.
- **Timeout:** each AI task has 20 seconds. A timeout, an error or an unusable answer moves on to the next task.
- **If none answers:** the binary sensor "AI assessment available" turns off and nothing else changes. The deterministic alerts work as before. An AI that cannot be reached never results in "all fine".

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

An AI alert ends when a later assessment no longer reports its cause, and it drops to a lower level when a later assessment reports the cause as less serious. One exception: an assessment that is not confident and reports nothing at all cannot take back an AI warning or critical alert. The AI alerts are also cleared when Monitoring is switched off, privacy mode is switched on or someone is with the child.

Once raised, an AI alert behaves like any other alert of its level: a critical one goes to all phones, repeats every 30 seconds and switches on the local alarm after a minute until someone taps "Seen" (see [How it works](how-it-works.md#the-three-alert-levels)). The next routine assessment may be up to the routine interval away, so acknowledge it yourself after you have checked.

## Privacy and consent

- **Cloud or local is your choice of AI task.** With a cloud provider such as Gemini or OpenRouter, an image of your child and its bed leaves your home with every assessment. With a local model, for example through Ollama on your own machine, it stays in your network.
- **Consent is required.** AI tasks cannot be saved without the tick, and without the tick no image is sent.
- **Check your provider's terms.** Depending on the plan, a provider may use submitted images to train its models. For Gemini, check whether you are on a paid plan and what it says about this.
- **CheckBaby does not store images.** It keeps the latest answer in memory (fields and the one-sentence reason) and shows it in the sensors "AI assessment" and "Position". The sentence appears in notifications. The planned debug archive for images is not implemented.
- **Home Assistant may keep the sentence in its history**, because it is an attribute of the sensor "AI assessment".
- **Privacy mode stops the automatic assessments**, not the manual one.

See also [Safety and privacy](safety-and-privacy.md).
