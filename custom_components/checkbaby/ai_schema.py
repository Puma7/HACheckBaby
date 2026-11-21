"""What the AI is asked and how its answer is read. Pure, no Home Assistant imports.

The answer is untrusted: anything missing or out of range becomes "unknown",
and an answer without the required fields is rejected as a whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRESENCE = ("in_bed", "not_visible", "caregiver_present")
POSITION = ("supine", "prone", "side", "sitting", "standing", "unknown")
AIRWAY = ("none", "possible", "likely")
CHILD = ("asleep", "awake_calm", "awake_restless", "crying", "unknown")
VERDICT = ("ok", "attention", "warning", "critical")

INSTRUCTIONS = (
    "You assess one still image from a camera above a baby's sleeping place for a "
    "parent. Report only what is visible. If something cannot be judged from the "
    "image (darkness, infrared noise, the child turned away, an empty or covered "
    "bed), answer 'unknown' or 'not_visible' and lower the confidence; never guess. "
    "airway_risk is 'likely' only if the nose and mouth are clearly covered or "
    "pressed into bedding. List loose objects in the bed (blanket, pillow, toy, "
    "cord) under hazards. view_ok is false if the image is too dark, blocked, or "
    "does not show a bed at all. Write 'reason' as one short sentence in {language}."
)

# The structure passed to ai_task.generate_data.
STRUCTURE: dict[str, Any] = {
    "presence": {
        "description": "Who is visible in the bed area",
        "required": True,
        "selector": {"select": {"options": list(PRESENCE)}},
    },
    "position": {
        "description": "Body position of the child",
        "required": True,
        "selector": {"select": {"options": list(POSITION)}},
    },
    "face_visible": {
        "description": "The child's nose and mouth are visible and uncovered",
        "required": True,
        "selector": {"boolean": {}},
    },
    "airway_risk": {
        "description": "Risk that the airway is covered or blocked",
        "required": True,
        "selector": {"select": {"options": list(AIRWAY)}},
    },
    "state": {
        "description": "What the child is doing",
        "required": True,
        "selector": {"select": {"options": list(CHILD)}},
    },
    "hazards": {
        "description": "Loose objects in the bed, comma separated; empty if none",
        "required": False,
        "selector": {"text": {}},
    },
    "view_ok": {
        "description": "The image shows the bed clearly enough to judge",
        "required": True,
        "selector": {"boolean": {}},
    },
    "assessment": {
        "description": "Overall verdict",
        "required": True,
        "selector": {"select": {"options": list(VERDICT)}},
    },
    "confidence": {
        "description": "Confidence from 0 to 1",
        "required": True,
        "selector": {"number": {"min": 0, "max": 1, "step": 0.05}},
    },
    "reason": {
        "description": "One short sentence for the parent",
        "required": True,
        "selector": {"text": {}},
    },
}

REQUIRED = tuple(key for key, spec in STRUCTURE.items() if spec["required"])


@dataclass(frozen=True)
class Assessment:
    """A validated answer."""

    presence: str
    position: str
    face_visible: bool | None
    airway_risk: str
    state: str
    view_ok: bool
    verdict: str
    confidence: float
    reason: str
    hazards: tuple[str, ...] = field(default_factory=tuple[str, ...])
    at: float = 0.0


def _choice(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    text = str(value).strip().lower() if value is not None else ""
    return text if text in allowed else fallback


def _boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "yes", "1"):
            return True
        if text in ("false", "no", "0"):
            return False
    return None


def parse_assessment(data: Any, now: float) -> Assessment | None:
    """Read the AI answer. Returns None unless every required field is present."""
    if not isinstance(data, dict) or any(key not in data for key in REQUIRED):
        return None
    try:
        confidence = float(data["confidence"])
    except (TypeError, ValueError):
        return None
    if confidence != confidence:  # NaN
        return None
    raw_hazards = data.get("hazards") or ""
    if isinstance(raw_hazards, (list, tuple)):
        parts = [str(part) for part in raw_hazards]
    else:
        parts = str(raw_hazards).split(",")
    hazards = tuple(part.strip() for part in parts if part.strip() and part.strip().lower() != "none")
    view_ok = _boolean(data["view_ok"])
    return Assessment(
        presence=_choice(data["presence"], PRESENCE, "not_visible"),
        position=_choice(data["position"], POSITION, "unknown"),
        face_visible=_boolean(data["face_visible"]),
        # An unreadable airway value must not read as "none".
        airway_risk=_choice(data["airway_risk"], AIRWAY, "possible"),
        state=_choice(data["state"], CHILD, "unknown"),
        view_ok=True if view_ok is None else view_ok,
        verdict=_choice(data["assessment"], VERDICT, "attention"),
        confidence=min(1.0, max(0.0, confidence)),
        reason=str(data["reason"]).strip()[:300],
        hazards=hazards[:10],
        at=now,
    )
