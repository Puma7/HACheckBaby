"""Alert lifecycle rules."""

from __future__ import annotations

from custom_components.checkbaby.alerts import AlertManager
from custom_components.checkbaby.types import AlertKind, AlertLevel, Audience, Stage

T0 = 1000.0


def _stages(manager: AlertManager) -> list[Stage]:
    return [note.stage for note in manager.drain()]


def test_warning_goes_to_on_duty_then_escalates_to_all() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    first = manager.drain()
    assert [(note.stage, note.audience) for note in first] == [(Stage.FIRST, Audience.ON_DUTY)]

    manager.tick(T0 + 179)
    assert Stage.ESCALATE not in _stages(manager)
    manager.tick(T0 + 180)
    escalated = [note for note in manager.drain() if note.stage is Stage.ESCALATE]
    assert [note.audience for note in escalated] == [Audience.ALL]
    manager.tick(T0 + 400)
    assert Stage.ESCALATE not in _stages(manager)  # only once


def test_critical_goes_to_all_and_repeats_until_acknowledged() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.SMOKE, AlertLevel.CRITICAL, {}, T0)
    assert [(n.stage, n.audience) for n in manager.drain()] == [(Stage.FIRST, Audience.ALL)]

    manager.tick(T0 + 29)
    assert _stages(manager) == []
    manager.tick(T0 + 30)
    assert _stages(manager) == [Stage.REPEAT]
    manager.tick(T0 + 60)
    assert _stages(manager) == [Stage.REPEAT, Stage.LOCAL]

    assert manager.acknowledge(T0 + 61) == 1
    assert _stages(manager) == [Stage.ACKNOWLEDGED]
    manager.tick(T0 + 500)
    assert _stages(manager) == []
    # Acknowledged is not cleared: the cause is still there.
    assert manager.level is AlertLevel.CRITICAL
    assert not manager.needs_attention()


def test_snooze_holds_warnings_but_never_critical() -> None:
    manager = AlertManager()
    manager.snooze(T0 + 300, T0)

    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0 + 1)
    assert _stages(manager) == []
    manager.raise_alert(AlertKind.SMOKE, AlertLevel.CRITICAL, {}, T0 + 2)
    assert _stages(manager) == [Stage.FIRST]

    manager.tick(T0 + 299)
    assert Stage.FIRST not in _stages(manager)
    manager.tick(T0 + 300)
    assert [n.kind for n in manager.drain() if n.stage is Stage.FIRST] == [AlertKind.CRYING]


def test_warning_that_becomes_critical_breaks_through_snooze() -> None:
    manager = AlertManager()
    manager.snooze(T0 + 300, T0)
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0 + 1)
    manager.drain()

    manager.raise_alert(AlertKind.CRYING, AlertLevel.CRITICAL, {}, T0 + 10)

    assert [(n.stage, n.audience) for n in manager.drain()] == [(Stage.UPGRADE, Audience.ALL)]


def test_snoozing_an_active_warning_silences_it_and_brings_it_back() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.drain()

    manager.snooze(T0 + 300, T0 + 5)
    assert _stages(manager) == [Stage.ACKNOWLEDGED]
    manager.tick(T0 + 200)
    assert _stages(manager) == []
    manager.tick(T0 + 301)
    assert Stage.FIRST in _stages(manager)


def test_acknowledging_twice_or_only_hints_counts_nothing() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.HAZARD, AlertLevel.INFO, {}, T0)
    assert manager.acknowledge(T0 + 1) == 0
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0 + 2)
    assert manager.acknowledge(T0 + 3) == 1
    assert manager.acknowledge(T0 + 4) == 0


def test_snooze_leaves_acknowledged_and_critical_alerts_alone() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.acknowledge(T0 + 1)
    manager.raise_alert(AlertKind.SMOKE, AlertLevel.CRITICAL, {}, T0 + 2)
    manager.drain()

    manager.snooze(T0 + 300, T0 + 3)

    assert manager.drain() == []
    manager.tick(T0 + 32)
    assert _stages(manager) == [Stage.REPEAT]


def test_cooldown_stops_a_flapping_warning_from_pushing_again() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.clear(AlertKind.CRYING, T0 + 10)
    manager.drain()

    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0 + 60)
    assert _stages(manager) == []
    assert manager.level is AlertLevel.WARNING

    manager.clear(AlertKind.CRYING, T0 + 70)
    manager.drain()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0 + 70 + 121)
    assert _stages(manager) == [Stage.FIRST]


def test_cooldown_never_applies_to_critical() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0)
    manager.clear(AlertKind.NO_BREATHING, T0 + 5)
    manager.drain()

    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0 + 6)

    assert _stages(manager) == [Stage.FIRST]


def test_acknowledged_alert_speaks_again_when_it_gets_worse() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.acknowledge(T0 + 5)
    manager.drain()

    manager.raise_alert(AlertKind.CRYING, AlertLevel.CRITICAL, {}, T0 + 50)

    assert _stages(manager) == [Stage.UPGRADE]
    assert manager.needs_attention()


def test_shadow_alert_is_recorded_but_silent_and_has_no_level() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0, shadow=True)
    manager.tick(T0 + 500)

    assert manager.drain() == []
    assert manager.level is AlertLevel.NONE
    assert manager.top is None
    assert AlertKind.NO_BREATHING in manager.active

    manager.clear(AlertKind.NO_BREATHING, T0 + 501)
    assert manager.drain() == []


def test_shadow_alert_switched_live_notifies() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0, shadow=True)

    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0 + 5)

    assert _stages(manager) == [Stage.FIRST]
    assert manager.level is AlertLevel.CRITICAL


def test_info_alert_never_pushes() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.HAZARD, AlertLevel.INFO, {}, T0)
    manager.tick(T0 + 1000)
    manager.clear(AlertKind.HAZARD, T0 + 1001)

    assert manager.drain() == []


def test_local_channel_fires_for_unanswered_crying_but_not_for_climate() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.raise_alert(AlertKind.CLIMATE, AlertLevel.WARNING, {}, T0)
    manager.drain()

    manager.tick(T0 + 60)

    assert [n.kind for n in manager.drain() if n.stage is Stage.LOCAL] == [AlertKind.CRYING]


def test_local_channel_is_wanted_only_while_an_alert_that_reached_it_is_unanswered() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    assert manager.local_wanted() is False
    manager.tick(T0 + 60)
    assert manager.local_wanted() is True

    manager.snooze(T0 + 400, T0 + 70)
    assert manager.local_wanted() is False  # snoozing silences it
    manager.clear(AlertKind.CRYING, T0 + 80)
    assert manager.local_wanted() is False

    manager.raise_alert(AlertKind.SMOKE, AlertLevel.CRITICAL, {}, T0 + 500)
    manager.tick(T0 + 560)
    assert manager.local_wanted() is True
    manager.acknowledge(T0 + 561)
    assert manager.local_wanted() is False


def test_internet_down_fires_local_channel_at_once() -> None:
    manager = AlertManager()
    manager.local_immediately = True
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.drain()

    manager.tick(T0 + 1)

    assert _stages(manager) == [Stage.LOCAL]


def test_babysitter_mode_sends_warnings_to_everyone() -> None:
    manager = AlertManager()
    manager.everyone = True
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)

    assert [n.audience for n in manager.drain()] == [Audience.ALL]


def test_test_alert_ends_on_acknowledgement_or_expires() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.TEST, AlertLevel.CRITICAL, {}, T0)
    manager.acknowledge(T0 + 3)
    assert AlertKind.TEST not in manager.active

    manager.raise_alert(AlertKind.TEST, AlertLevel.WARNING, {}, T0 + 10)
    manager.tick(T0 + 10 + 599)
    assert AlertKind.TEST in manager.active
    manager.tick(T0 + 10 + 600)
    assert AlertKind.TEST not in manager.active


def test_clear_tells_the_phones_only_if_they_were_told() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {}, T0)
    manager.drain()
    manager.clear(AlertKind.CRYING, T0 + 5)
    assert _stages(manager) == [Stage.CLEARED]


def test_alert_that_drops_to_a_hint_is_taken_off_the_phones() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CLIMATE, AlertLevel.WARNING, {}, T0)
    manager.drain()

    manager.raise_alert(AlertKind.CLIMATE, AlertLevel.INFO, {}, T0 + 5)

    assert _stages(manager) == [Stage.CLEARED]
    assert manager.level is AlertLevel.INFO
    manager.clear(AlertKind.CLIMATE, T0 + 6)
    assert manager.drain() == []  # nothing left to clear


def test_critical_that_drops_to_warning_stays_on_the_phones() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.MONITORING_FAILURE, AlertLevel.CRITICAL, {}, T0)
    manager.drain()
    manager.raise_alert(AlertKind.MONITORING_FAILURE, AlertLevel.WARNING, {}, T0 + 5)
    assert manager.drain() == []
    assert manager.level is AlertLevel.WARNING


def test_live_alert_switched_to_shadow_is_taken_off_the_phones() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0)
    manager.drain()

    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {}, T0 + 5, shadow=True)

    assert _stages(manager) == [Stage.CLEARED]
    assert manager.level is AlertLevel.NONE
    assert manager.active[AlertKind.NO_BREATHING].shadow is True
    manager.raise_alert(AlertKind.NO_BREATHING, AlertLevel.CRITICAL, {"sources": ["radar"]}, T0 + 6, shadow=True)
    manager.tick(T0 + 100)
    assert manager.drain() == []


def test_alerts_survive_a_round_trip() -> None:
    manager = AlertManager()
    manager.raise_alert(AlertKind.CRYING, AlertLevel.WARNING, {"seconds": 20}, T0)
    manager.acknowledge(T0 + 4)
    manager.snooze(T0 + 300, T0 + 5)
    manager.drain()

    restored = AlertManager()
    restored.restore(manager.to_dict())

    alert = restored.active[AlertKind.CRYING]
    assert (alert.level, alert.acked, alert.detail) == (AlertLevel.WARNING, True, {"seconds": 20})
    assert restored.snooze_until == T0 + 300
    restored.tick(T0 + 1000)
    assert restored.drain() == []  # still acknowledged


def test_restore_drops_malformed_alerts() -> None:
    restored = AlertManager()
    restored.restore({"snooze_until": "x", "active": [{"kind": "nonsense"}, {"kind": "crying", "level": 2}]})
    assert restored.active == {}
    assert restored.snooze_until == 0.0
    restored.restore(None)
