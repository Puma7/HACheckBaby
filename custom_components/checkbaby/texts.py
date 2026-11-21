"""Texts that the integration writes itself: notifications and summaries. Pure.

Entity names and the setup dialogs are translated by Home Assistant; a push
notification is composed here, in the language of the Home Assistant instance.
"""

from __future__ import annotations

from typing import Any

from .types import AlertKind, AlertLevel, ChildState

_EN: dict[str, str] = {
    "title_critical": "ALARM · {child}",
    "title_warning": "CheckBaby · {child}",
    "crying_warning": "{child} is crying ({seconds} s).",
    "crying_critical": "{child} has been crying for several minutes and nobody has responded.",
    "no_breathing": "No breathing movement detected for {child}. Check now.",
    "airway_risk": "Possible airway risk for {child}: {reason}",
    "prone_position": "{child} may be lying face down: {reason}",
    "hazard": "Loose objects in {child}'s bed: {hazards}",
    "camera_view": "The camera view of {child}'s bed is blocked or too dark.",
    "left_bed": "{child} has left the bed.",
    "pet_in_bed": "A pet is in {child}'s bed.",
    "climate": "The room is at {temperature} °C, outside the set range.",
    "smoke": "Smoke or CO alarm near {child}!",
    "monitoring_failure_warning": "Monitoring of {child} is impaired: {problems}.",
    "monitoring_failure_critical": "Monitoring of {child} has been down for over 5 minutes: {problems}.",
    "internet_down": "No internet: alerts reach you through local channels only.",
    "interruption": "Monitoring of {child} was interrupted for {minutes} min.",
    "test": "Test alert. Tap “Seen” to end it.",
    "stopping": "Home Assistant is stopping. {child} is not monitored until it is back.",
    "action_ack": "Seen",
    "action_snooze": "Quiet for 5 min",
    "action_live": "Live",
    "problem_mqtt": "MQTT disconnected",
    "problem_frigate": "Frigate offline",
    "problem_audio_level": "no sound from the camera",
    "problem_microphone": "microphone signal flat",
    "problem_camera": "camera unavailable",
    "problem_engine": "vital engine offline",
    "problem_vital_sensor": "radar sensor unavailable",
    "problem_notify": "a notification target is missing",
    "problem_sleep_place": "no sleep place is active",
    "problem_cry_sensor": "crying sensor unavailable",
    "problem_local_alarm": "local alarm unreachable",
    "delivery_sent": "Sent to: {names}.",
    "delivery_failed": "Could NOT be sent to: {names}. Open the options of CheckBaby and check “Who is told”.",
    "delivery_none": "No phone is chosen, so no push was sent.",
    "delivery_local": "Local alarm: {names}. It switches on after a minute without “Seen”.",
    "delivery_local_down": "Local alarm NOT reachable: {names}.",
    "delivery_no_local": "No local alarm is set up.",
    "delivery_hint": (
        "Nothing on the phone? Check that the Home Assistant app is allowed to notify, "
        "and on iOS that critical alerts are allowed."
    ),
    "ai_title": "AI check",
    "ai_result": "{verdict} ({confidence} % sure). {reason}",
    "ai_verdict_ok": "Looks fine",
    "ai_verdict_attention": "Worth a look",
    "ai_verdict_warning": "Please check",
    "ai_verdict_critical": "Possible danger",
    "ai_off_none": "No AI check: no AI task is chosen. Open the options of CheckBaby, “AI assessment”.",
    "ai_off_consent": "No AI check: sending pictures is not confirmed in the options, “AI assessment”.",
    "ai_off_privacy": "No AI check: privacy mode is on, so no picture leaves the house.",
    "ai_off_camera": "No AI check: the active sleep place has no camera entity.",
    "ai_off_busy": "An AI check is already running.",
    "ai_failed": "The AI gave no usable answer: {error}",
    "state_empty": "not in bed",
    "state_asleep": "asleep",
    "state_restless": "restless",
    "state_awake": "awake",
    "state_crying": "crying",
    "state_attended": "someone is with the child",
    "state_unknown": "unknown (signal unusable)",
    "quick": "{child}: {state}.",
    "quick_alert": " Active alert: {alert}.",
    "quick_asleep": " Asleep for {minutes} min.",
    "quick_ai": " {reason}",
    "quick_problems": " Monitoring problems: {problems}.",
    "report": (
        "{child}: slept {hours} h {minutes} min since the evening, woke {wakeups} time(s), "
        "cried {cried} min, longest stretch {longest} min."
    ),
    "report_none": "{child}: no sleep recorded since the evening.",
}

_DE: dict[str, str] = {
    "title_critical": "ALARM · {child}",
    "title_warning": "CheckBaby · {child}",
    "crying_warning": "{child} weint ({seconds} s).",
    "crying_critical": "{child} weint seit mehreren Minuten und niemand hat reagiert.",
    "no_breathing": "Keine Atembewegung bei {child} erkannt. Bitte sofort nachsehen.",
    "airway_risk": "Mögliches Risiko für die Atemwege bei {child}: {reason}",
    "prone_position": "{child} liegt möglicherweise auf dem Bauch: {reason}",
    "hazard": "Lose Gegenstände im Bett von {child}: {hazards}",
    "camera_view": "Der Kamerablick auf das Bett von {child} ist verdeckt oder zu dunkel.",
    "left_bed": "{child} hat das Bett verlassen.",
    "pet_in_bed": "Ein Haustier ist im Bett von {child}.",
    "climate": "Im Zimmer sind es {temperature} °C, außerhalb des eingestellten Bereichs.",
    "smoke": "Rauch- oder CO-Alarm bei {child}!",
    "monitoring_failure_warning": "Die Überwachung von {child} ist gestört: {problems}.",
    "monitoring_failure_critical": "Die Überwachung von {child} ist seit über 5 Minuten ausgefallen: {problems}.",
    "internet_down": "Kein Internet: Alarme erreichen dich nur über lokale Kanäle.",
    "interruption": "Die Überwachung von {child} war {minutes} min unterbrochen.",
    "test": "Testalarm. Mit „Gesehen“ beenden.",
    "stopping": "Home Assistant wird beendet. {child} wird nicht überwacht, bis es wieder läuft.",
    "action_ack": "Gesehen",
    "action_snooze": "5 min Ruhe",
    "action_live": "Live",
    "problem_mqtt": "MQTT getrennt",
    "problem_frigate": "Frigate offline",
    "problem_audio_level": "kein Ton von der Kamera",
    "problem_microphone": "Mikrofonsignal flach",
    "problem_camera": "Kamera nicht verfügbar",
    "problem_engine": "Vital-Engine offline",
    "problem_vital_sensor": "Radarsensor nicht verfügbar",
    "problem_notify": "ein Benachrichtigungsziel fehlt",
    "problem_sleep_place": "kein Schlafplatz aktiv",
    "problem_cry_sensor": "Wein-Sensor nicht verfügbar",
    "problem_local_alarm": "lokaler Alarm nicht erreichbar",
    "delivery_sent": "Gesendet an: {names}.",
    "delivery_failed": (
        "NICHT gesendet an: {names}. Öffne die Optionen von CheckBaby und prüfe „Wer benachrichtigt wird“."
    ),
    "delivery_none": "Es ist kein Handy gewählt, deshalb wurde kein Push gesendet.",
    "delivery_local": "Lokaler Alarm: {names}. Er schaltet nach einer Minute ohne „Gesehen“ ein.",
    "delivery_local_down": "Lokaler Alarm NICHT erreichbar: {names}.",
    "delivery_no_local": "Es ist kein lokaler Alarm eingerichtet.",
    "delivery_hint": (
        "Nichts auf dem Handy? Prüfe, ob die Home-Assistant-App Mitteilungen senden darf, "
        "und unter iOS, ob kritische Hinweise erlaubt sind."
    ),
    "ai_title": "KI-Check",
    "ai_result": "{verdict} ({confidence} % sicher). {reason}",
    "ai_verdict_ok": "Sieht gut aus",
    "ai_verdict_attention": "Einen Blick wert",
    "ai_verdict_warning": "Bitte nachsehen",
    "ai_verdict_critical": "Mögliche Gefahr",
    "ai_off_none": "Kein KI-Check: Es ist keine KI-Aufgabe gewählt. Öffne die Optionen von CheckBaby, „KI-Bewertung“.",
    "ai_off_consent": (
        "Kein KI-Check: In den Optionen unter „KI-Bewertung“ ist nicht bestätigt, dass Bilder gesendet werden dürfen."
    ),
    "ai_off_privacy": "Kein KI-Check: Der Privatmodus ist an, deshalb verlässt kein Bild das Haus.",
    "ai_off_camera": "Kein KI-Check: Der aktive Schlafplatz hat keine Kamera-Entität.",
    "ai_off_busy": "Es läuft bereits ein KI-Check.",
    "ai_failed": "Die KI hat keine brauchbare Antwort gegeben: {error}",
    "state_empty": "nicht im Bett",
    "state_asleep": "schläft",
    "state_restless": "unruhig",
    "state_awake": "wach",
    "state_crying": "weint",
    "state_attended": "jemand ist beim Kind",
    "state_unknown": "unbekannt (Signal unbrauchbar)",
    "quick": "{child}: {state}.",
    "quick_alert": " Aktiver Alarm: {alert}.",
    "quick_asleep": " Schläft seit {minutes} min.",
    "quick_ai": " {reason}",
    "quick_problems": " Störungen: {problems}.",
    "report": (
        "{child}: seit dem Abend {hours} h {minutes} min geschlafen, {wakeups}-mal aufgewacht, "
        "{cried} min geweint, längste Schlafphase {longest} min."
    ),
    "report_none": "{child}: seit dem Abend kein Schlaf aufgezeichnet.",
}

_TEXTS = {"en": _EN, "de": _DE}


def text(language: str, key: str, **values: Any) -> str:
    """Return a text in the given language, English if the language is unknown."""
    table = _TEXTS.get(language.split("-")[0].lower(), _EN)
    return table.get(key, _EN[key]).format(**values)


def problem_names(language: str, problems: list[str] | tuple[str, ...]) -> str:
    """Readable list of monitoring problems."""
    names = [text(language, f"problem_{name}") if f"problem_{name}" in _EN else name for name in problems]
    return ", ".join(names)


def state_name(language: str, state: ChildState) -> str:
    """Readable child state."""
    return text(language, f"state_{state.value}")


def alert_message(language: str, child: str, kind: AlertKind, level: AlertLevel, detail: dict[str, Any]) -> str:
    """The sentence a notification carries."""
    key = kind.value
    if kind in (AlertKind.CRYING, AlertKind.MONITORING_FAILURE):
        key += "_critical" if level is AlertLevel.CRITICAL else "_warning"
    seconds = detail.get("seconds", 0)
    return text(
        language,
        key,
        child=child,
        seconds=seconds,
        minutes=max(1, round(float(seconds) / 60)),
        reason=detail.get("reason", ""),
        hazards=", ".join(detail.get("hazards", [])),
        temperature=detail.get("temperature", "?"),
        problems=problem_names(language, detail.get("problems", [])),
    ).strip()


def alert_title(language: str, child: str, level: AlertLevel) -> str:
    """The notification title."""
    key = "title_critical" if level is AlertLevel.CRITICAL else "title_warning"
    return text(language, key, child=child)


def delivery_report(
    language: str, *, sent: list[str], failed: list[str], local: list[str], local_down: list[str]
) -> str:
    """Where a test alert went, so that a silent phone is not a riddle."""
    lines = []
    if sent:
        lines.append(text(language, "delivery_sent", names=", ".join(sent)))
    if failed:
        lines.append(text(language, "delivery_failed", names=", ".join(failed)))
    if not sent and not failed:
        lines.append(text(language, "delivery_none"))
    reachable = [name for name in local if name not in local_down]
    if reachable:
        lines.append(text(language, "delivery_local", names=", ".join(reachable)))
    if local_down:
        lines.append(text(language, "delivery_local_down", names=", ".join(local_down)))
    if not local:
        lines.append(text(language, "delivery_no_local"))
    if sent:
        lines.append(text(language, "delivery_hint"))
    return "\n".join(lines)


def assessment_text(language: str, verdict: str, confidence: float, reason: str) -> str:
    """What the AI said, in one sentence."""
    key = f"ai_verdict_{verdict}"
    return text(
        language,
        "ai_result",
        verdict=text(language, key) if key in _EN else verdict,
        confidence=round(confidence * 100),
        reason=reason,
    ).strip()
