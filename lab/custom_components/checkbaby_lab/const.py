"""Constants of the lab simulator."""

DOMAIN = "checkbaby_lab"
PHONES = ("mobile_app_lab_parent_a", "mobile_app_lab_parent_b", "mobile_app_lab_babysitter")

# What the simulated devices report until a scenario changes it.
DEFAULTS: dict[str, float | bool | None] = {
    "breath_rate": 40.0,
    "heart_rate": 128.0,
    "temperature": 19.5,
    "humidity": 45.0,
    "door": False,
    "presence": True,
    "smoke": False,
    "internet": True,
}

GOOD_ANSWER = {
    "presence": "in_bed",
    "position": "supine",
    "face_visible": True,
    "airway_risk": "none",
    "state": "asleep",
    "hazards": "",
    "view_ok": True,
    "assessment": "ok",
    "confidence": 0.9,
    "reason": "Lab: sleeping on the back.",
}
