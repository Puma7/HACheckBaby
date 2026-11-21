"""Builds the payload of a push notification. Pure, no Home Assistant imports.

One payload carries the keys of both companion apps; each app ignores the keys
it does not know.
"""

from __future__ import annotations

from typing import Any

from .const import ACTION_ACK, ACTION_SNOOZE
from .texts import alert_message, alert_title, text
from .types import AlertKind, AlertLevel


def notification_tag(entry_id: str, kind: AlertKind) -> str:
    """The tag that lets a later message replace or clear this one."""
    return f"checkbaby_{entry_id}_{kind.value}"


def build_push(
    *,
    language: str,
    child: str,
    entry_id: str,
    kind: AlertKind,
    level: AlertLevel,
    detail: dict[str, Any],
    camera_entity: str | None,
    dashboard_path: str,
) -> dict[str, Any]:
    """Return the service data for notify.mobile_app_*."""
    data: dict[str, Any] = {
        "tag": notification_tag(entry_id, kind),
        "group": f"checkbaby_{entry_id}",
        "url": dashboard_path,
        "clickAction": dashboard_path,
        "actions": [
            {"action": f"{ACTION_ACK}_{entry_id}", "title": text(language, "action_ack")},
            {"action": f"{ACTION_SNOOZE}_{entry_id}", "title": text(language, "action_snooze")},
            {"action": "URI", "title": text(language, "action_live"), "uri": dashboard_path},
        ],
        # Deliver now or not at all, and wake the phone.
        "ttl": 0,
        "priority": "high",
    }
    if camera_entity:
        data["entity_id"] = camera_entity
        data["image"] = f"/api/camera_proxy/{camera_entity}"
    if level is AlertLevel.CRITICAL:
        # iOS critical alert: sounds through silent mode and Do Not Disturb.
        data["push"] = {"sound": {"name": "default", "critical": 1, "volume": 1.0}}
        # Android: the alarm stream ignores the ringer volume.
        data["channel"] = "alarm_stream"
        data["importance"] = "high"
    else:
        data["push"] = {"interruption-level": "time-sensitive"}
        data["channel"] = "CheckBaby"
        data["importance"] = "high"
    return {
        "title": alert_title(language, child, level),
        "message": alert_message(language, child, kind, level, detail),
        "data": data,
    }


def build_clear(entry_id: str, kind: AlertKind) -> dict[str, Any]:
    """Return the service data that removes the notification from the phone."""
    return {"message": "clear_notification", "data": {"tag": notification_tag(entry_id, kind)}}
