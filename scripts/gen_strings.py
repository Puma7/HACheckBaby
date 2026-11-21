"""Writes strings.json, translations/en.json and translations/de.json from one paired source.

Run from the repository root:  python scripts/gen_strings.py custom_components/checkbaby
Edit the EN and DE tables below, never the JSON files: both languages then always carry the same keys.
"""
import json, pathlib, sys

KINDS = ["crying", "no_breathing", "airway_risk", "prone_position", "hazard", "camera_view", "left_bed",
         "pet_in_bed", "climate", "smoke", "monitoring_failure", "internet_down", "interruption", "test"]

def build(t):
    """t maps a key to text in one language."""
    place_data = {k: t[f"place.{k}"] for k in ["name", "frigate_camera", "camera_entity", "bed_zone", "door_entity",
        "person_is_caregiver", "presence_entity", "temperature_entity", "humidity_entity", "breath_rate_entity",
        "heart_rate_entity", "engine_id", "audio_stream_url", "cry_entity", "motion_entity", "level_entity"]}
    place_desc = {k: t[f"place_desc.{k}"] for k in ["frigate_camera", "camera_entity", "bed_zone", "door_entity",
        "person_is_caregiver", "presence_entity", "breath_rate_entity", "engine_id", "audio_stream_url", "cry_entity"]}
    notify_data = {k: t[f"opt.{k}"] for k in ["notify_services", "local_alarm_entities"]}
    notify_desc = {k: t[f"opt_desc.{k}"] for k in ["notify_services", "local_alarm_entities"]}
    opt_keys = ["notify_services", "local_alarm_entities", "babysitter_service", "heartbeat_buttons", "smoke_entities",
        "internet_entity", "vox_media_player", "ai_task_entities", "ai_consent", "ai_calls_per_hour",
        "frigate_topic_prefix", "dashboard_path"]
    opt_data = {k: t[f"opt.{k}"] for k in opt_keys}
    opt_desc = {k: t[f"opt_desc.{k}"] for k in opt_keys if f"opt_desc.{k}" in t}
    place_errors = {"name_required": t["err.name_required"], "no_sound_source": t["err.no_sound_source"]}
    target_errors = {"no_alert_target": t["err.no_alert_target"], "ai_consent_required": t["err.ai_consent_required"]}
    def names(domain, keys):
        return {k: {"name": t[f"{domain}.{k}"]} for k in keys}
    def with_states(domain, key, states):
        return {"name": t[f"{domain}.{key}"], "state": {s: t[f"{domain}.{key}.{s}"] for s in states}}
    sensor = names("sensor", ["noise_level", "noise_floor", "last_motion", "asleep_since", "last_sleep_duration",
        "sleep_today", "crying_today", "wakeups_tonight", "breathing_rate", "heart_rate", "monitoring_problems",
        "ai_calls_last_hour"])
    sensor["state"] = with_states("sensor", "state", ["empty", "asleep", "restless", "awake", "crying", "attended", "unknown"])
    sensor["alert_level"] = with_states("sensor", "alert_level", ["none", "info", "warning", "critical"])
    sensor["alert_reason"] = {"name": t["sensor.alert_reason"], "state": {"none": t["kind.none"], **{k: t[f"kind.{k}"] for k in KINDS}}}
    sensor["sleeping_bag"] = with_states("sensor", "sleeping_bag", ["tog_3_5", "tog_2_5_plus_layer", "tog_2_5", "tog_1_0", "tog_0_5", "tog_0_2"])
    sensor["ai_assessment"] = with_states("sensor", "ai_assessment", ["ok", "attention", "warning", "critical"])
    sensor["position"] = with_states("sensor", "position", ["supine", "prone", "side", "sitting", "standing", "unknown"])
    sensor["age_profile"] = with_states("sensor", "age_profile", ["newborn", "infant", "toddler"])
    select = {
        "mode": with_states("select", "mode", ["night", "nap", "babysitter"]),
        "sensitivity": with_states("select", "sensitivity", ["low", "medium", "high"]),
        "vital_fusion": with_states("select", "vital_fusion", ["any", "all"]),
        "on_duty": with_states("select", "on_duty", ["all"]),
        "active_place": {"name": t["select.active_place"]},
    }
    services = {}
    for name, fields in {"acknowledge": [], "snooze": ["minutes"], "test_alert": ["level"], "start_sleep": [],
                         "end_sleep": [], "assess_now": [], "quick_check": ["with_ai", "notify"], "night_report": ["notify"]}.items():
        f = {"config_entry_id": {"name": t["svc.entry"], "description": t["svc.entry.desc"]}}
        for field in fields:
            f[field] = {"name": t[f"svc.{name}.{field}"], "description": t[f"svc.{name}.{field}.desc"]}
        services[name] = {"name": t[f"svc.{name}"], "description": t[f"svc.{name}.desc"], "fields": f}
    return {
        "config": {
            "step": {
                "user": {"title": t["user.title"], "description": t["user.desc"],
                         "data": {"child_name": t["user.child_name"], "birth_date": t["user.birth_date"]},
                         "data_description": {"child_name": t["user.child_name.desc"], "birth_date": t["user.birth_date.desc"]}},
                "place": {"title": t["place.title"], "description": t["place.desc"], "data": place_data, "data_description": place_desc},
                "notify": {"title": t["notify.title"], "description": t["notify.desc"], "data": notify_data, "data_description": notify_desc},
                "disclaimer": {"title": t["disc.title"], "description": t["disc.desc"], "data": {"acknowledged": t["disc.ack"]}},
            },
            "error": {**place_errors, **target_errors, "must_acknowledge": t["err.must_acknowledge"]},
            "abort": {"already_configured": t["abort.already_configured"]},
        },
        "options": {
            "step": {"init": {"title": t["opt.title"], "description": t["opt.desc"], "data": opt_data, "data_description": opt_desc}},
            "error": target_errors,
        },
        "config_subentries": {
            "sleep_place": {
                "entry_type": t["sub.entry_type"],
                "initiate_flow": {"user": t["sub.add"], "reconfigure": t["sub.reconfigure"]},
                "step": {
                    "user": {"title": t["sub.add"], "description": t["place.desc"], "data": place_data, "data_description": place_desc},
                    "reconfigure": {"title": t["sub.reconfigure"], "description": t["place.desc"], "data": place_data, "data_description": place_desc},
                },
                "error": place_errors,
                "abort": {"reconfigure_successful": t["sub.reconfigured"]},
            }
        },
        "entity": {
            "sensor": sensor,
            "binary_sensor": names("binary_sensor", ["crying", "motion", "in_bed", "attended", "breathing_movement",
                "alert_active", "monitoring_problem", "ai_available", "quiet_time", "audio_relay"]),
            "switch": names("switch", ["monitoring", "privacy_mode", "ai_assessment_enabled", "breathing_alert", "audio_relay_enabled"]),
            "number": names("number", ["cry_warning_s", "cry_critical_s", "noise_margin_db", "no_breathing_s", "ai_interval_min", "temp_min", "temp_max"]),
            "select": select,
            "button": names("button", ["acknowledge", "snooze", "quick_check", "assess_now", "night_report", "test_alert"]),
            "event": {"alert": {"name": t["event.alert"], "state_attributes": {"event_type": {"state": {k: t[f"kind.{k}"] for k in KINDS}}}}},
        },
        "selector": {"test_level": {"options": {"warning": t["sensor.alert_level.warning"], "critical": t["sensor.alert_level.critical"]}}},
        "services": services,
        "issues": {k: {"title": t[f"issue.{k}"], "description": t[f"issue.{k}.desc"]} for k in ["no_alert_target", "no_sleep_place", "mqtt_missing"]},
        "exceptions": {"entry_required": {"message": t["exc.entry_required"]}},
    }

EN = {
 "user.title": "Set up CheckBaby", "user.desc": "One entry per child. You can set this up before the birth: enter the expected due date and correct it later.",
 "user.child_name": "Name of the child", "user.birth_date": "Birth date or expected due date",
 "user.child_name.desc": "Used for the device, its entities and the notifications.", "user.birth_date.desc": "Selects the age profile and its default thresholds.",
 "place.title": "Sleep place", "place.desc": "Where the child sleeps, with its camera and sensors. A sound source is required: a Frigate camera with audio detection, or a crying sensor. Everything else is optional. More sleep places can be added later.",
 "place.name": "Name of the sleep place", "place.frigate_camera": "Frigate camera name", "place.camera_entity": "Camera entity", "place.bed_zone": "Frigate zone of the bed",
 "place.door_entity": "Door contact", "place.person_is_caregiver": "A person seen by the camera counts as a caregiver", "place.presence_entity": "Presence sensor for the bed",
 "place.temperature_entity": "Room temperature", "place.humidity_entity": "Room humidity", "place.breath_rate_entity": "Breathing rate sensor (radar)",
 "place.heart_rate_entity": "Heart rate sensor (radar)", "place.engine_id": "Vital engine ID", "place.audio_stream_url": "Audio stream address",
 "place.cry_entity": "Crying sensor", "place.motion_entity": "Motion sensor", "place.level_entity": "Sound level sensor",
 "place_desc.frigate_camera": "The camera's name in the Frigate configuration. Crying, sound level and motion are read from Frigate over MQTT.",
 "place_desc.camera_entity": "Used for the picture in notifications and for the AI assessment.",
 "place_desc.bed_zone": "If set, a cat or dog detected in this zone raises a warning.",
 "place_desc.door_entity": "While the door is open someone is with the child and child-related alerts pause.",
 "place_desc.person_is_caregiver": "Leave off if Frigate detects the child itself as a person.",
 "place_desc.presence_entity": "On while the child is in bed, for example a zone of a presence radar.",
 "place_desc.breath_rate_entity": "Breaths per minute, for example from a 60 GHz radar sensor. Used for the breathing-movement hint.",
 "place_desc.engine_id": "Only with the CheckBaby vital engine: the ID configured there.",
 "place_desc.audio_stream_url": "Played on the parents' speaker by the audio relay, for example an audio stream from go2rtc.",
 "place_desc.cry_entity": "Alternative to Frigate, for example the crying detection of the camera itself.",
 "notify.title": "Who is told", "notify.desc": "Choose the phones that receive alerts and, if you have one, a local alarm that works without internet. At least one of the two is required.",
 "opt.title": "CheckBaby options", "opt.desc": "Who is told, and what else is connected. Sleep places are managed as separate entries of the child.",
 "opt.notify_services": "Phones", "opt.local_alarm_entities": "Local alarm (siren, light, switch)", "opt.babysitter_service": "Babysitter's phone",
 "opt.heartbeat_buttons": "Dead-man heartbeat buttons", "opt.smoke_entities": "Smoke and CO detectors", "opt.internet_entity": "Internet connectivity sensor",
 "opt.vox_media_player": "Speaker for the audio relay", "opt.ai_task_entities": "AI tasks, in order of preference", "opt.ai_consent": "Images of the child may be sent to these AI tasks",
 "opt.ai_calls_per_hour": "AI calls per hour at most", "opt.frigate_topic_prefix": "Frigate MQTT topic prefix", "opt.dashboard_path": "Dashboard opened from a notification",
 "opt_desc.notify_services": "Notify services of the Home Assistant companion app. Critical alerts go to all of them.",
 "opt_desc.local_alarm_entities": "Switched on when an alert stays unanswered for a minute, or at once if the internet is down. Put it where you sleep, never in the child's room.",
 "opt_desc.babysitter_service": "Receives alerts only while the mode is “Babysitter”.",
 "opt_desc.heartbeat_buttons": "Pressed every 30 seconds while monitoring is armed and healthy, so that a separate device can sound when Home Assistant fails.",
 "opt_desc.smoke_entities": "Passed through as critical alerts, even while monitoring is off.",
 "opt_desc.internet_entity": "While it is off, the local alarm fires at once.",
 "opt_desc.ai_task_entities": "The first one that answers is used. A cloud model receives camera images of the child; a local model keeps them at home.",
 "opt_desc.ai_consent": "Required to use the AI assessment. Check your provider's terms on how images are used.",
 "err.name_required": "Enter a name.", "err.no_sound_source": "Enter a Frigate camera or choose a crying sensor: without a sound source the monitor cannot hear the child.",
 "err.no_alert_target": "Choose at least one phone or a local alarm; otherwise no alert could reach anyone.", "err.ai_consent_required": "Confirm that images may be sent, or remove the AI tasks.",
 "err.must_acknowledge": "Confirm the notice to continue.", "abort.already_configured": "A child with this name is already set up.",
 "disc.title": "What CheckBaby is, and what it is not", "disc.desc": "CheckBaby is not a medical device. It cannot prevent sudden infant death and it can fail without warning. It supports your supervision and the rules for safe infant sleep; it does not replace either. Keep a simple baby monitor as a fallback.",
 "disc.ack": "I have read and understood this",
 "sub.entry_type": "Sleep place", "sub.add": "Add sleep place", "sub.reconfigure": "Change sleep place", "sub.reconfigured": "The sleep place was updated.",
 "sensor.state": "State", "sensor.state.empty": "Not in bed", "sensor.state.asleep": "Asleep", "sensor.state.restless": "Restless", "sensor.state.awake": "Awake",
 "sensor.state.crying": "Crying", "sensor.state.attended": "Attended", "sensor.state.unknown": "Unknown",
 "sensor.alert_level": "Alert level", "sensor.alert_level.none": "None", "sensor.alert_level.info": "Hint", "sensor.alert_level.warning": "Warning", "sensor.alert_level.critical": "Critical",
 "sensor.alert_reason": "Alert reason", "kind.none": "None", "kind.crying": "Crying", "kind.no_breathing": "No breathing movement", "kind.airway_risk": "Airway risk",
 "kind.prone_position": "Prone position", "kind.hazard": "Loose objects in bed", "kind.camera_view": "Camera view blocked", "kind.left_bed": "Left the bed",
 "kind.pet_in_bed": "Pet in bed", "kind.climate": "Room climate", "kind.smoke": "Smoke or CO", "kind.monitoring_failure": "Monitoring failure",
 "kind.internet_down": "No internet", "kind.interruption": "Monitoring was interrupted", "kind.test": "Test alert",
 "sensor.noise_level": "Sound level", "sensor.noise_floor": "Learned noise floor", "sensor.last_motion": "Last movement", "sensor.asleep_since": "Asleep since",
 "sensor.last_sleep_duration": "Last sleep", "sensor.sleep_today": "Sleep today", "sensor.crying_today": "Crying today", "sensor.wakeups_tonight": "Wake-ups tonight",
 "sensor.breathing_rate": "Breathing rate (estimate)", "sensor.heart_rate": "Heart rate (estimate)", "sensor.monitoring_problems": "Monitoring problems", "sensor.ai_calls_last_hour": "AI calls in the last hour",
 "sensor.sleeping_bag": "Sleeping bag suggestion", "sensor.sleeping_bag.tog_3_5": "3.5 TOG", "sensor.sleeping_bag.tog_2_5_plus_layer": "2.5 TOG plus an extra layer",
 "sensor.sleeping_bag.tog_2_5": "2.5 TOG", "sensor.sleeping_bag.tog_1_0": "1.0 TOG", "sensor.sleeping_bag.tog_0_5": "0.5 TOG", "sensor.sleeping_bag.tog_0_2": "0.2 TOG or less",
 "sensor.ai_assessment": "AI assessment", "sensor.ai_assessment.ok": "All fine", "sensor.ai_assessment.attention": "Take a look", "sensor.ai_assessment.warning": "Warning", "sensor.ai_assessment.critical": "Critical",
 "sensor.position": "Position", "sensor.position.supine": "On the back", "sensor.position.prone": "On the tummy", "sensor.position.side": "On the side",
 "sensor.position.sitting": "Sitting", "sensor.position.standing": "Standing", "sensor.position.unknown": "Unknown",
 "sensor.age_profile": "Age profile", "sensor.age_profile.newborn": "Newborn", "sensor.age_profile.infant": "Infant", "sensor.age_profile.toddler": "Toddler",
 "binary_sensor.crying": "Crying", "binary_sensor.motion": "Movement", "binary_sensor.in_bed": "In bed", "binary_sensor.attended": "Someone is with the child",
 "binary_sensor.breathing_movement": "Breathing movement", "binary_sensor.alert_active": "Unanswered alert", "binary_sensor.monitoring_problem": "Monitoring problem",
 "binary_sensor.ai_available": "AI assessment available", "binary_sensor.quiet_time": "Quiet time", "binary_sensor.audio_relay": "Audio relay playing",
 "switch.monitoring": "Monitoring", "switch.privacy_mode": "Privacy mode", "switch.ai_assessment_enabled": "AI assessment", "switch.breathing_alert": "Breathing-movement alert", "switch.audio_relay_enabled": "Audio relay",
 "number.cry_warning_s": "Crying before a warning", "number.cry_critical_s": "Unanswered crying before critical", "number.noise_margin_db": "Loudness above the noise floor",
 "number.no_breathing_s": "No breathing movement before an alert", "number.ai_interval_min": "AI routine check interval", "number.temp_min": "Lowest room temperature", "number.temp_max": "Highest room temperature",
 "select.mode": "Mode", "select.mode.night": "Night", "select.mode.nap": "Nap", "select.mode.babysitter": "Babysitter",
 "select.sensitivity": "Sensitivity", "select.sensitivity.low": "Low", "select.sensitivity.medium": "Medium", "select.sensitivity.high": "High",
 "select.vital_fusion": "Vital sources must agree", "select.vital_fusion.any": "One source is enough", "select.vital_fusion.all": "All sources",
 "select.on_duty": "On duty", "select.on_duty.all": "Everyone", "select.active_place": "Active sleep place",
 "button.acknowledge": "Seen", "button.snooze": "Quiet for 5 minutes", "button.quick_check": "Quick check", "button.assess_now": "AI check now", "button.night_report": "Send night report", "button.test_alert": "Test alert",
 "event.alert": "Alert",
 "svc.entry": "Child", "svc.entry.desc": "Only needed when more than one child is set up.",
 "svc.acknowledge": "Acknowledge alerts", "svc.acknowledge.desc": "Marks all active alerts as seen. Monitoring continues; an alert that gets worse notifies again.",
 "svc.snooze": "Snooze warnings", "svc.snooze.desc": "Holds warnings back for a while. Critical alerts still come through.",
 "svc.snooze.minutes": "Minutes", "svc.snooze.minutes.desc": "How long warnings are held back.",
 "svc.test_alert": "Send a test alert", "svc.test_alert.desc": "Runs the whole notification chain until it is acknowledged, at most 10 minutes.",
 "svc.test_alert.level": "Level", "svc.test_alert.level.desc": "A critical test checks that the alert sounds through Do Not Disturb.",
 "svc.start_sleep": "Start sleep", "svc.start_sleep.desc": "Marks the child as asleep now.", "svc.end_sleep": "End sleep", "svc.end_sleep.desc": "Marks the child as awake now.",
 "svc.assess_now": "AI assessment now", "svc.assess_now.desc": "Asks the configured AI task about a fresh camera image and returns the assessment.",
 "svc.quick_check": "Quick check", "svc.quick_check.desc": "Returns how the child is right now: state, alert, sleep time and a one-sentence summary.",
 "svc.quick_check.with_ai": "With AI assessment", "svc.quick_check.with_ai.desc": "Take a fresh AI look first.",
 "svc.quick_check.notify": "Send as notification", "svc.quick_check.notify.desc": "Also send the summary to whoever is on duty.",
 "svc.night_report": "Night report", "svc.night_report.desc": "Returns sleep time, wake-ups and crying since the evening.",
 "svc.night_report.notify": "Send as notification", "svc.night_report.notify.desc": "Also send the summary to whoever is on duty.",
 "issue.no_alert_target": "CheckBaby cannot alert anyone for {child}", "issue.no_alert_target.desc": "Neither a phone nor a local alarm is configured. Open the options of the CheckBaby entry and choose at least one.",
 "issue.no_sleep_place": "No sleep place is set up for {child}", "issue.no_sleep_place.desc": "Without a sleep place there is nothing to monitor. Add one to the CheckBaby entry.",
 "issue.mqtt_missing": "CheckBaby needs MQTT for {child}", "issue.mqtt_missing.desc": "The sleep place uses a Frigate camera or the vital engine, but the MQTT integration is not set up. Set up MQTT, then reload CheckBaby.",
 "exc.entry_required": "Choose the child: no CheckBaby entry is loaded, or more than one.",
}

DE = {
 "user.title": "CheckBaby einrichten", "user.desc": "Ein Eintrag pro Kind. Die Einrichtung geht schon vor der Geburt: errechneten Termin eintragen und später korrigieren.",
 "user.child_name": "Name des Kindes", "user.birth_date": "Geburtsdatum oder errechneter Termin",
 "user.child_name.desc": "Wird für das Gerät, seine Entitäten und die Benachrichtigungen verwendet.", "user.birth_date.desc": "Bestimmt das Altersprofil und dessen Startwerte.",
 "place.title": "Schlafplatz", "place.desc": "Wo das Kind schläft, mit Kamera und Sensoren. Eine Tonquelle ist nötig: eine Frigate-Kamera mit Audio-Erkennung oder ein Wein-Sensor. Alles andere ist optional. Weitere Schlafplätze lassen sich später hinzufügen.",
 "place.name": "Name des Schlafplatzes", "place.frigate_camera": "Name der Frigate-Kamera", "place.camera_entity": "Kamera-Entität", "place.bed_zone": "Frigate-Zone des Bettes",
 "place.door_entity": "Türkontakt", "place.person_is_caregiver": "Eine von der Kamera erkannte Person zählt als Betreuung", "place.presence_entity": "Präsenzsensor für das Bett",
 "place.temperature_entity": "Raumtemperatur", "place.humidity_entity": "Luftfeuchte", "place.breath_rate_entity": "Atemraten-Sensor (Radar)",
 "place.heart_rate_entity": "Herzraten-Sensor (Radar)", "place.engine_id": "ID der Vital-Engine", "place.audio_stream_url": "Adresse des Ton-Streams",
 "place.cry_entity": "Wein-Sensor", "place.motion_entity": "Bewegungssensor", "place.level_entity": "Geräuschpegel-Sensor",
 "place_desc.frigate_camera": "Der Name der Kamera in der Frigate-Konfiguration. Weinen, Geräuschpegel und Bewegung kommen per MQTT aus Frigate.",
 "place_desc.camera_entity": "Für das Bild in Benachrichtigungen und für die KI-Bewertung.",
 "place_desc.bed_zone": "Wenn gesetzt, löst eine Katze oder ein Hund in dieser Zone eine Warnung aus.",
 "place_desc.door_entity": "Solange die Tür offen ist, ist jemand beim Kind und die kindbezogenen Alarme pausieren.",
 "place_desc.person_is_caregiver": "Ausgeschaltet lassen, wenn Frigate das Kind selbst als Person erkennt.",
 "place_desc.presence_entity": "An, solange das Kind im Bett liegt, zum Beispiel eine Zone eines Präsenzradars.",
 "place_desc.breath_rate_entity": "Atemzüge pro Minute, zum Beispiel von einem 60-GHz-Radarsensor. Dient dem Atembewegungs-Hinweis.",
 "place_desc.engine_id": "Nur mit der CheckBaby-Vital-Engine: die dort eingestellte ID.",
 "place_desc.audio_stream_url": "Wird von der Ton-Weiterleitung auf dem Lautsprecher der Eltern abgespielt, zum Beispiel ein Ton-Stream aus go2rtc.",
 "place_desc.cry_entity": "Alternative zu Frigate, zum Beispiel die Wein-Erkennung der Kamera selbst.",
 "notify.title": "Wer benachrichtigt wird", "notify.desc": "Wähle die Handys, die Alarme bekommen, und falls vorhanden einen lokalen Alarm, der ohne Internet funktioniert. Mindestens eines von beiden ist nötig.",
 "opt.title": "CheckBaby-Optionen", "opt.desc": "Wer benachrichtigt wird und was sonst angeschlossen ist. Schlafplätze werden als eigene Einträge des Kindes verwaltet.",
 "opt.notify_services": "Handys", "opt.local_alarm_entities": "Lokaler Alarm (Sirene, Licht, Schalter)", "opt.babysitter_service": "Handy des Babysitters",
 "opt.heartbeat_buttons": "Herzschlag-Tasten für den Dead-Man-Summer", "opt.smoke_entities": "Rauch- und CO-Melder", "opt.internet_entity": "Sensor für die Internetverbindung",
 "opt.vox_media_player": "Lautsprecher für die Ton-Weiterleitung", "opt.ai_task_entities": "KI-Aufgaben, in bevorzugter Reihenfolge", "opt.ai_consent": "Bilder des Kindes dürfen an diese KI-Aufgaben gesendet werden",
 "opt.ai_calls_per_hour": "KI-Aufrufe pro Stunde höchstens", "opt.frigate_topic_prefix": "MQTT-Präfix von Frigate", "opt.dashboard_path": "Dashboard, das eine Benachrichtigung öffnet",
 "opt_desc.notify_services": "Benachrichtigungsdienste der Home-Assistant-App. Kritische Alarme gehen an alle.",
 "opt_desc.local_alarm_entities": "Wird eingeschaltet, wenn ein Alarm eine Minute unbeantwortet bleibt, oder sofort, wenn das Internet ausgefallen ist. Gehört ins Elternschlafzimmer, nie ins Kinderzimmer.",
 "opt_desc.babysitter_service": "Bekommt Alarme nur im Modus „Babysitter“.",
 "opt_desc.heartbeat_buttons": "Werden alle 30 Sekunden gedrückt, solange die Überwachung scharf und störungsfrei ist. So kann ein eigenes Gerät Alarm geben, wenn Home Assistant ausfällt.",
 "opt_desc.smoke_entities": "Werden als kritische Alarme durchgereicht, auch wenn die Überwachung aus ist.",
 "opt_desc.internet_entity": "Solange er aus ist, löst der lokale Alarm sofort aus.",
 "opt_desc.ai_task_entities": "Die erste, die antwortet, wird verwendet. Ein Cloud-Modell erhält Kamerabilder des Kindes; ein lokales Modell behält sie im Haus.",
 "opt_desc.ai_consent": "Nötig, um die KI-Bewertung zu nutzen. Prüfe in den Bedingungen deines Anbieters, wie Bilder verwendet werden.",
 "err.name_required": "Bitte einen Namen eingeben.", "err.no_sound_source": "Bitte eine Frigate-Kamera eintragen oder einen Wein-Sensor wählen: Ohne Tonquelle kann die Überwachung das Kind nicht hören.",
 "err.no_alert_target": "Bitte mindestens ein Handy oder einen lokalen Alarm wählen; sonst könnte kein Alarm jemanden erreichen.", "err.ai_consent_required": "Bitte bestätigen, dass Bilder gesendet werden dürfen, oder die KI-Aufgaben entfernen.",
 "err.must_acknowledge": "Bitte den Hinweis bestätigen, um fortzufahren.", "abort.already_configured": "Ein Kind mit diesem Namen ist bereits eingerichtet.",
 "disc.title": "Was CheckBaby ist und was nicht", "disc.desc": "CheckBaby ist kein Medizinprodukt. Es kann den plötzlichen Kindstod nicht verhindern und kann ohne Vorwarnung ausfallen. Es unterstützt deine Aufsicht und die Regeln für sicheren Babyschlaf, ersetzt aber beides nicht. Behalte ein einfaches Babyphone als Rückfallebene.",
 "disc.ack": "Ich habe das gelesen und verstanden",
 "sub.entry_type": "Schlafplatz", "sub.add": "Schlafplatz hinzufügen", "sub.reconfigure": "Schlafplatz ändern", "sub.reconfigured": "Der Schlafplatz wurde geändert.",
 "sensor.state": "Zustand", "sensor.state.empty": "Nicht im Bett", "sensor.state.asleep": "Schläft", "sensor.state.restless": "Unruhig", "sensor.state.awake": "Wach",
 "sensor.state.crying": "Weint", "sensor.state.attended": "Betreut", "sensor.state.unknown": "Unbekannt",
 "sensor.alert_level": "Alarmstufe", "sensor.alert_level.none": "Keine", "sensor.alert_level.info": "Hinweis", "sensor.alert_level.warning": "Warnung", "sensor.alert_level.critical": "Kritisch",
 "sensor.alert_reason": "Alarmgrund", "kind.none": "Keiner", "kind.crying": "Weinen", "kind.no_breathing": "Keine Atembewegung", "kind.airway_risk": "Risiko für die Atemwege",
 "kind.prone_position": "Bauchlage", "kind.hazard": "Lose Gegenstände im Bett", "kind.camera_view": "Kamerablick verdeckt", "kind.left_bed": "Bett verlassen",
 "kind.pet_in_bed": "Haustier im Bett", "kind.climate": "Raumklima", "kind.smoke": "Rauch oder CO", "kind.monitoring_failure": "Überwachung gestört",
 "kind.internet_down": "Kein Internet", "kind.interruption": "Überwachung war unterbrochen", "kind.test": "Testalarm",
 "sensor.noise_level": "Geräuschpegel", "sensor.noise_floor": "Gelernter Grundpegel", "sensor.last_motion": "Letzte Bewegung", "sensor.asleep_since": "Schläft seit",
 "sensor.last_sleep_duration": "Letzter Schlaf", "sensor.sleep_today": "Schlaf heute", "sensor.crying_today": "Weinen heute", "sensor.wakeups_tonight": "Aufgewacht heute Nacht",
 "sensor.breathing_rate": "Atemrate (Schätzung)", "sensor.heart_rate": "Herzrate (Schätzung)", "sensor.monitoring_problems": "Störungen der Überwachung", "sensor.ai_calls_last_hour": "KI-Aufrufe in der letzten Stunde",
 "sensor.sleeping_bag": "Schlafsack-Empfehlung", "sensor.sleeping_bag.tog_3_5": "3,5 TOG", "sensor.sleeping_bag.tog_2_5_plus_layer": "2,5 TOG plus eine Schicht",
 "sensor.sleeping_bag.tog_2_5": "2,5 TOG", "sensor.sleeping_bag.tog_1_0": "1,0 TOG", "sensor.sleeping_bag.tog_0_5": "0,5 TOG", "sensor.sleeping_bag.tog_0_2": "0,2 TOG oder weniger",
 "sensor.ai_assessment": "KI-Bewertung", "sensor.ai_assessment.ok": "Alles in Ordnung", "sensor.ai_assessment.attention": "Bitte ansehen", "sensor.ai_assessment.warning": "Warnung", "sensor.ai_assessment.critical": "Kritisch",
 "sensor.position": "Lage", "sensor.position.supine": "Rückenlage", "sensor.position.prone": "Bauchlage", "sensor.position.side": "Seitenlage",
 "sensor.position.sitting": "Sitzt", "sensor.position.standing": "Steht", "sensor.position.unknown": "Unbekannt",
 "sensor.age_profile": "Altersprofil", "sensor.age_profile.newborn": "Neugeborenes", "sensor.age_profile.infant": "Säugling", "sensor.age_profile.toddler": "Kleinkind",
 "binary_sensor.crying": "Weinen", "binary_sensor.motion": "Bewegung", "binary_sensor.in_bed": "Im Bett", "binary_sensor.attended": "Jemand ist beim Kind",
 "binary_sensor.breathing_movement": "Atembewegung", "binary_sensor.alert_active": "Unbeantworteter Alarm", "binary_sensor.monitoring_problem": "Störung der Überwachung",
 "binary_sensor.ai_available": "KI-Bewertung verfügbar", "binary_sensor.quiet_time": "Ruhezeit", "binary_sensor.audio_relay": "Ton-Weiterleitung läuft",
 "switch.monitoring": "Überwachung", "switch.privacy_mode": "Privatmodus", "switch.ai_assessment_enabled": "KI-Bewertung", "switch.breathing_alert": "Atembewegungs-Alarm", "switch.audio_relay_enabled": "Ton-Weiterleitung",
 "number.cry_warning_s": "Weinen bis zur Warnung", "number.cry_critical_s": "Unbeantwortetes Weinen bis kritisch", "number.noise_margin_db": "Lautstärke über dem Grundpegel",
 "number.no_breathing_s": "Keine Atembewegung bis zum Alarm", "number.ai_interval_min": "Abstand der KI-Routineprüfung", "number.temp_min": "Niedrigste Raumtemperatur", "number.temp_max": "Höchste Raumtemperatur",
 "select.mode": "Modus", "select.mode.night": "Nacht", "select.mode.nap": "Nickerchen", "select.mode.babysitter": "Babysitter",
 "select.sensitivity": "Empfindlichkeit", "select.sensitivity.low": "Niedrig", "select.sensitivity.medium": "Mittel", "select.sensitivity.high": "Hoch",
 "select.vital_fusion": "Vitalquellen müssen übereinstimmen", "select.vital_fusion.any": "Eine Quelle genügt", "select.vital_fusion.all": "Alle Quellen",
 "select.on_duty": "Hat Dienst", "select.on_duty.all": "Alle", "select.active_place": "Aktiver Schlafplatz",
 "button.acknowledge": "Gesehen", "button.snooze": "5 Minuten Ruhe", "button.quick_check": "Schnell-Check", "button.assess_now": "KI-Check jetzt", "button.night_report": "Nachtbericht senden", "button.test_alert": "Testalarm",
 "event.alert": "Alarm",
 "svc.entry": "Kind", "svc.entry.desc": "Nur nötig, wenn mehr als ein Kind eingerichtet ist.",
 "svc.acknowledge": "Alarme quittieren", "svc.acknowledge.desc": "Markiert alle aktiven Alarme als gesehen. Die Überwachung läuft weiter; ein Alarm, der sich verschlimmert, meldet sich erneut.",
 "svc.snooze": "Warnungen pausieren", "svc.snooze.desc": "Hält Warnungen eine Zeit lang zurück. Kritische Alarme kommen trotzdem durch.",
 "svc.snooze.minutes": "Minuten", "svc.snooze.minutes.desc": "Wie lange Warnungen zurückgehalten werden.",
 "svc.test_alert": "Testalarm senden", "svc.test_alert.desc": "Durchläuft die ganze Benachrichtigungskette, bis quittiert wird, höchstens 10 Minuten.",
 "svc.test_alert.level": "Stufe", "svc.test_alert.level.desc": "Ein kritischer Test prüft, ob der Alarm trotz „Nicht stören“ ertönt.",
 "svc.start_sleep": "Schlaf beginnen", "svc.start_sleep.desc": "Markiert das Kind ab jetzt als schlafend.", "svc.end_sleep": "Schlaf beenden", "svc.end_sleep.desc": "Markiert das Kind ab jetzt als wach.",
 "svc.assess_now": "KI-Bewertung jetzt", "svc.assess_now.desc": "Fragt die eingerichtete KI-Aufgabe zu einem frischen Kamerabild und gibt die Bewertung zurück.",
 "svc.quick_check": "Schnell-Check", "svc.quick_check.desc": "Gibt zurück, wie es dem Kind gerade geht: Zustand, Alarm, Schlafdauer und eine Zusammenfassung in einem Satz.",
 "svc.quick_check.with_ai": "Mit KI-Bewertung", "svc.quick_check.with_ai.desc": "Zuerst einen frischen KI-Blick einholen.",
 "svc.quick_check.notify": "Als Benachrichtigung senden", "svc.quick_check.notify.desc": "Die Zusammenfassung zusätzlich an die Person im Dienst senden.",
 "svc.night_report": "Nachtbericht", "svc.night_report.desc": "Gibt Schlafdauer, Aufwachen und Weinen seit dem Abend zurück.",
 "svc.night_report.notify": "Als Benachrichtigung senden", "svc.night_report.notify.desc": "Die Zusammenfassung zusätzlich an die Person im Dienst senden.",
 "issue.no_alert_target": "CheckBaby kann für {child} niemanden alarmieren", "issue.no_alert_target.desc": "Es ist weder ein Handy noch ein lokaler Alarm eingerichtet. Öffne die Optionen des CheckBaby-Eintrags und wähle mindestens eines.",
 "issue.no_sleep_place": "Für {child} ist kein Schlafplatz eingerichtet", "issue.no_sleep_place.desc": "Ohne Schlafplatz gibt es nichts zu überwachen. Füge dem CheckBaby-Eintrag einen hinzu.",
 "issue.mqtt_missing": "CheckBaby braucht MQTT für {child}", "issue.mqtt_missing.desc": "Der Schlafplatz nutzt eine Frigate-Kamera oder die Vital-Engine, aber die MQTT-Integration ist nicht eingerichtet. Richte MQTT ein und lade CheckBaby neu.",
 "exc.entry_required": "Bitte das Kind wählen: Es ist kein CheckBaby-Eintrag geladen, oder mehr als einer.",
}

missing = set(EN) ^ set(DE)
assert not missing, missing
root = pathlib.Path(sys.argv[1])
en, de = build(EN), build(DE)
for path, data in ((root / "strings.json", en), (root / "translations/en.json", en), (root / "translations/de.json", de)):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written")
