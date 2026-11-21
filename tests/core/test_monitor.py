"""Whole-monitor scenarios, including the rules that must never break."""

from __future__ import annotations

import pytest

from custom_components.checkbaby.ai_schema import Assessment
from custom_components.checkbaby.profiles import AgeProfile
from custom_components.checkbaby.types import (
    AI_KINDS,
    AlertKind,
    AlertLevel,
    Audience,
    ChildState,
    Mode,
    Sensitivity,
    Stage,
    VitalFusion,
)
from custom_components.checkbaby.vox import VoxAction

from .helpers import AUDIO, Night


def _assessment(night: Night, **changes: object) -> Assessment:
    values: dict[str, object] = {
        "presence": "in_bed",
        "position": "supine",
        "face_visible": True,
        "airway_risk": "none",
        "state": "asleep",
        "view_ok": True,
        "verdict": "ok",
        "confidence": 0.9,
        "reason": "Sleeping on the back.",
        "at": night.now,
    }
    values.update(changes)
    return Assessment(**values)  # type: ignore[arg-type]


# -- state ---------------------------------------------------------------


def test_calm_night_is_asleep_without_alerts() -> None:
    night = Night()
    night.advance(600)
    assert night.monitor.state is ChildState.ASLEEP
    assert night.sent == []
    assert night.monitor.alerts.level is AlertLevel.NONE


def test_short_movement_does_not_change_the_state() -> None:
    night = Night()
    night.monitor.set_motion(True, night.now)
    night.advance(10)
    night.monitor.set_motion(False, night.now)
    night.advance(30)
    assert night.monitor.state is ChildState.ASLEEP


def test_restless_then_awake_then_asleep_again() -> None:
    night = Night()
    night.monitor.set_motion(True, night.now)
    night.advance(20)
    assert night.monitor.state is ChildState.RESTLESS
    night.advance(180)
    assert night.monitor.state is ChildState.AWAKE

    night.monitor.set_motion(False, night.now)
    night.advance(299)
    assert night.monitor.state is ChildState.AWAKE
    night.advance(2)
    assert night.monitor.state is ChildState.ASLEEP
    assert night.sent == []  # awake and calm is not an alert


def test_restless_settles_back_to_asleep() -> None:
    night = Night()
    night.monitor.set_motion(True, night.now)
    night.advance(30)
    night.monitor.set_motion(False, night.now)
    night.advance(119)
    assert night.monitor.state is ChildState.RESTLESS
    night.advance(2)
    assert night.monitor.state is ChildState.ASLEEP


def test_door_open_means_attended_and_pauses_crying_alerts() -> None:
    night = Night()
    night.monitor.signals.door_open.set(True, night.now)
    night.cry()
    night.advance(300)

    assert night.monitor.state is ChildState.ATTENDED
    assert night.pushes(AlertKind.CRYING) == []

    night.monitor.signals.door_open.set(False, night.now)
    night.cry(False)
    night.advance(21)
    assert night.monitor.state is ChildState.AWAKE


def test_absent_child_is_empty() -> None:
    night = Night()
    night.monitor.set_presence(False, night.now)
    night.advance(5)
    assert night.monitor.state is ChildState.EMPTY


# -- crying --------------------------------------------------------------


def test_brief_crying_is_no_alert() -> None:
    night = Night()
    night.cry()
    night.advance(10)
    night.cry(False)
    night.advance(120)
    assert night.pushes(AlertKind.CRYING) == []


def test_sustained_crying_warns_once_then_becomes_critical() -> None:
    night = Night()
    night.cry()
    night.advance(14)
    assert night.pushes(AlertKind.CRYING) == []
    night.advance(1)
    first = night.pushes(AlertKind.CRYING)
    assert [(n.stage, n.level, n.audience) for n in first] == [
        (Stage.FIRST, AlertLevel.WARNING, Audience.ON_DUTY)
    ]
    assert night.monitor.state is ChildState.CRYING

    night.advance(60)
    assert Stage.LOCAL in night.stages(AlertKind.CRYING)
    night.advance(120)
    upgrades = [n for n in night.sent if n.stage is Stage.UPGRADE]
    assert [(n.kind, n.level, n.audience) for n in upgrades] == [
        (AlertKind.CRYING, AlertLevel.CRITICAL, Audience.ALL)
    ]
    night.advance(60)
    assert night.stages(AlertKind.CRYING).count(Stage.REPEAT) == 2


def test_acknowledged_crying_never_becomes_critical() -> None:
    night = Night()
    night.cry()
    night.advance(20)
    night.monitor.acknowledge(night.now)
    night.advance(600)

    levels = {note.level for note in night.pushes(AlertKind.CRYING)}
    assert levels == {AlertLevel.WARNING}
    assert len(night.pushes(AlertKind.CRYING)) == 1


def test_crying_alert_ends_after_a_minute_of_quiet() -> None:
    night = Night()
    night.cry()
    night.advance(20)
    night.cry(False)
    night.advance(59)
    assert AlertKind.CRYING in night.monitor.alerts.active
    night.advance(2)
    assert AlertKind.CRYING not in night.monitor.alerts.active
    assert night.stages(AlertKind.CRYING)[-1] is Stage.CLEARED
    assert night.monitor.state is ChildState.AWAKE


def test_state_says_crying_no_later_than_the_warning() -> None:
    night = Night(cry_warning_s=5.0)
    night.cry()
    night.advance(5)
    assert len(night.pushes(AlertKind.CRYING)) == 1
    assert night.monitor.state is ChildState.CRYING


def test_scream_counts_as_distress() -> None:
    night = Night()
    night.monitor.signals.scream.set(True, night.now)
    night.advance(15)
    assert len(night.pushes(AlertKind.CRYING)) == 1


@pytest.mark.parametrize(
    ("sensitivity", "mode", "expected"),
    [
        (Sensitivity.HIGH, Mode.NIGHT, 7.5),
        (Sensitivity.LOW, Mode.NIGHT, 30.0),
        (Sensitivity.MEDIUM, Mode.BABYSITTER, 7.5),
    ],
)
def test_sensitivity_and_mode_scale_the_delay(sensitivity: Sensitivity, mode: Mode, expected: float) -> None:
    night = Night(sensitivity=sensitivity, mode=mode)
    assert night.monitor.settings.cry_warning_delay() == expected


def test_snoozed_crying_does_not_turn_critical_until_the_snooze_is_over() -> None:
    night = Night()
    night.cry()
    night.advance(20)
    night.monitor.snooze(300, night.now)
    night.advance(299)
    assert night.monitor.alerts.active[AlertKind.CRYING].level is AlertLevel.WARNING

    night.advance(2)  # snooze over: the warning comes back
    assert night.stages(AlertKind.CRYING).count(Stage.FIRST) == 2
    night.advance(178)
    assert night.monitor.alerts.active[AlertKind.CRYING].level is AlertLevel.WARNING
    night.advance(3)
    assert night.monitor.alerts.active[AlertKind.CRYING].level is AlertLevel.CRITICAL


def test_snooze_delays_the_crying_warning() -> None:
    night = Night()
    night.monitor.snooze(300, night.now)
    night.cry()
    night.advance(100)
    assert night.pushes(AlertKind.CRYING) == []
    night.advance(200)
    # The snooze has run out and the crying has lasted past the critical limit.
    assert night.pushes(AlertKind.CRYING)


# -- disarmed, privacy ---------------------------------------------------


@pytest.mark.parametrize("settings", [{"armed": False}, {"armed": True, "privacy": True}])
def test_nothing_but_smoke_alerts_when_not_monitoring(settings: dict[str, bool]) -> None:
    night = Night(**settings)
    night.cry()
    night.audio_alive = False
    night.advance(900)
    assert night.sent == []

    night.monitor.signals.smoke.set(True, night.now)
    night.advance(1)
    assert [(n.kind, n.level) for n in night.sent] == [(AlertKind.SMOKE, AlertLevel.CRITICAL)]


def test_privacy_reports_unknown_not_asleep() -> None:
    night = Night(privacy=True)
    night.advance(60)
    assert night.monitor.state is ChildState.UNKNOWN


# -- monitoring failure --------------------------------------------------


def test_lost_source_is_unknown_and_alerts_then_becomes_critical() -> None:
    night = Night()
    night.advance(200)
    night.audio_alive = False
    night.advance(60)
    assert night.monitor.alerts.level is AlertLevel.NONE
    night.advance(1)

    assert night.monitor.state is ChildState.UNKNOWN
    assert night.monitor.problems == [AUDIO]
    first = night.pushes(AlertKind.MONITORING_FAILURE)
    assert [(n.level, n.detail) for n in first] == [(AlertLevel.WARNING, {"problems": [AUDIO]})]

    night.advance(300)
    assert night.monitor.alerts.active[AlertKind.MONITORING_FAILURE].level is AlertLevel.CRITICAL

    night.audio_alive = True
    night.advance(2)
    assert AlertKind.MONITORING_FAILURE not in night.monitor.alerts.active
    assert night.monitor.state is not ChildState.UNKNOWN


def test_source_that_never_reports_is_a_problem_after_the_grace_period() -> None:
    night = Night()
    night.monitor.watchdog.expect("frigate", core=True)
    night.advance(117)
    assert night.monitor.problems == []
    night.advance(2)
    assert night.monitor.problems == ["frigate"]
    assert night.monitor.state is ChildState.UNKNOWN


def test_lost_vital_source_is_a_hint_until_an_alert_depends_on_it() -> None:
    night = Night()
    night.advance(130)
    night.monitor.watchdog.set_healthy("vital_sensor", False, night.now)
    night.advance(400)

    assert night.monitor.problems == ["vital_sensor"]
    assert night.monitor.alerts.active[AlertKind.MONITORING_FAILURE].level is AlertLevel.INFO
    assert night.sent == []
    assert night.monitor.state is ChildState.ASLEEP  # the child's state is still known

    night.monitor.settings.breathing_alert = True
    night.advance(2)
    assert [n.level for n in night.pushes(AlertKind.MONITORING_FAILURE)] == [AlertLevel.WARNING]
    night.advance(300)
    assert night.monitor.alerts.active[AlertKind.MONITORING_FAILURE].level is AlertLevel.CRITICAL


def test_dead_microphone_is_reported() -> None:
    night = Night()
    night.flat_microphone = True
    night.advance(601)
    assert "microphone" in night.monitor.problems
    assert AlertKind.MONITORING_FAILURE in night.monitor.alerts.active


# -- breathing movement --------------------------------------------------


def _vital(night: Night, source: str = "radar", *, valid: bool = True, breathing: bool, moving: bool = False) -> None:
    night.monitor.signals.set_vital(
        source, valid=valid, breathing=breathing, moving=moving, rate=40.0 if breathing else None, now=night.now
    )


def _run_vital(night: Night, seconds: int, **reading: bool) -> None:
    for _ in range(seconds):
        _vital(night, **reading)
        night.advance(1)


def test_no_breathing_movement_alerts_after_the_delay() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    # The last breath was seen one second before the first silent reading.
    _run_vital(night, 18, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active
    _run_vital(night, 2, breathing=False)

    first = night.pushes(AlertKind.NO_BREATHING)
    assert [(n.level, n.audience, n.detail) for n in first] == [
        (AlertLevel.CRITICAL, Audience.ALL, {"sources": ["radar"]})
    ]
    _run_vital(night, 2, breathing=True)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_breathing_alert_is_shadow_only_while_switched_off() -> None:
    night = Night(breathing_alert=False)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 60, breathing=False)

    alert = night.monitor.alerts.active[AlertKind.NO_BREATHING]
    assert alert.shadow is True
    assert night.sent == []
    assert night.monitor.alerts.level is AlertLevel.NONE
    assert any(event["type"] == "alert" and event.get("shadow") for event in night.monitor.events)


def test_unusable_signal_never_counts_as_no_breathing() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 120, valid=False, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_stale_signal_never_counts_as_no_breathing() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _vital(night, breathing=False)
    night.advance(120)  # the source went silent after one reading
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_source_that_never_saw_the_child_cannot_alert() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 120, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_signal_that_was_unusable_restarts_the_count() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 60, valid=False, breathing=False)
    _run_vital(night, 19, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active
    _run_vital(night, 2, breathing=False)
    assert AlertKind.NO_BREATHING in night.monitor.alerts.active


def test_silence_after_a_large_movement_is_not_counted() -> None:
    """Lifting the child out looks like this: movement, then nothing."""
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 4, breathing=False, moving=True)
    _run_vital(night, 120, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active

    # Back in bed and breathing for a while: the hint is live again.
    _run_vital(night, 15, breathing=True)
    _run_vital(night, 22, breathing=False)
    assert AlertKind.NO_BREATHING in night.monitor.alerts.active


def test_a_rate_that_lingers_after_the_movement_is_not_breathing_seen_again() -> None:
    """A radar keeps showing its last rate for a few seconds after the child is lifted out."""
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 4, breathing=False, moving=True)
    _run_vital(night, 8, breathing=True)  # stale rate, less than ten seconds after the movement
    _run_vital(night, 120, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_room_temperature_in_the_alert_is_rounded() -> None:
    night = Night()
    night.monitor.signals.temperature = 26.88888888888889
    night.advance(601)
    assert night.monitor.alerts.active[AlertKind.CLIMATE].detail == {"temperature": 26.9}


def test_camera_movement_before_the_silence_is_not_counted_either() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    night.monitor.set_motion(True, night.now)
    _run_vital(night, 4, breathing=False)
    night.monitor.set_motion(False, night.now)
    _run_vital(night, 120, breathing=False)
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


def test_after_someone_was_with_the_child_breathing_must_be_seen_again() -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    night.monitor.signals.door_open.set(True, night.now)
    _run_vital(night, 5, breathing=True)
    night.monitor.signals.door_open.set(False, night.now)
    _run_vital(night, 120, breathing=False)  # the bed is empty now
    assert night.monitor.state is not ChildState.ATTENDED
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


@pytest.mark.parametrize("sign", ["moving", "camera_motion", "crying", "absent"])
def test_other_signs_of_life_rule_out_the_breathing_alert(sign: str) -> None:
    night = Night(breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    if sign == "camera_motion":
        night.monitor.set_motion(True, night.now)
    elif sign == "crying":
        night.cry()
    elif sign == "absent":
        night.monitor.set_presence(False, night.now)
    _run_vital(night, 60, breathing=False, moving=sign == "moving")
    assert AlertKind.NO_BREATHING not in night.monitor.alerts.active


@pytest.mark.parametrize(("fusion", "alerts"), [(VitalFusion.ALL, False), (VitalFusion.ANY, True)])
def test_fusion_of_two_sources(fusion: VitalFusion, alerts: bool) -> None:
    night = Night(breathing_alert=True, vital_fusion=fusion)
    for _ in range(30):
        _vital(night, "radar", breathing=True)
        _vital(night, "video", breathing=True)
        night.advance(1)
    for _ in range(30):
        _vital(night, "radar", breathing=False)
        _vital(night, "video", breathing=True)
        night.advance(1)
    assert (AlertKind.NO_BREATHING in night.monitor.alerts.active) is alerts


def test_snapshot_breathing_is_none_without_a_usable_source() -> None:
    night = Night()
    snap = night.monitor.snapshot(night.now, night.now - 100, night.now - 100)
    assert snap.breathing is None
    _run_vital(night, 2, breathing=True)
    snap = night.monitor.snapshot(night.now, night.now - 100, night.now - 100)
    assert (snap.breathing, snap.breathing_rate) == (True, 40.0)


# -- AI guard rails ------------------------------------------------------


def test_ai_saying_all_fine_cannot_clear_or_lower_deterministic_alerts() -> None:
    night = Night(ai_enabled=True)
    night.cry()
    night.advance(20)
    night.audio_alive = False
    night.advance(62)
    before = {kind: alert.level for kind, alert in night.monitor.alerts.active.items()}
    assert before == {
        AlertKind.CRYING: AlertLevel.WARNING,
        AlertKind.MONITORING_FAILURE: AlertLevel.WARNING,
    }

    night.monitor.apply_assessment(_assessment(night), night.now, night.profile, "routine")
    night.advance(1)

    after = {kind: alert.level for kind, alert in night.monitor.alerts.active.items()}
    assert after == before


def test_ai_saying_all_fine_cannot_clear_the_breathing_alert() -> None:
    night = Night(ai_enabled=True, breathing_alert=True)
    _run_vital(night, 30, breathing=True)
    _run_vital(night, 25, breathing=False)
    assert night.monitor.alerts.active[AlertKind.NO_BREATHING].level is AlertLevel.CRITICAL

    night.monitor.apply_assessment(_assessment(night), night.now, night.profile, "no_breathing")
    _run_vital(night, 2, breathing=False)

    alert = night.monitor.alerts.active[AlertKind.NO_BREATHING]
    assert (alert.level, alert.acked, alert.shadow) == (AlertLevel.CRITICAL, False, False)


def test_ai_warning_needs_a_second_look_to_become_critical() -> None:
    night = Night(ai_enabled=True)
    risky = {"airway_risk": "likely", "face_visible": False, "verdict": "critical"}
    night.monitor.apply_assessment(_assessment(night, **risky), night.now, night.profile, "routine")

    assert night.monitor.alerts.active[AlertKind.AIRWAY_RISK].level is AlertLevel.WARNING
    night.advance(14)
    assert night.monitor.take_ai_request(night.now) is None
    night.advance(2)
    assert night.monitor.take_ai_request(night.now) == "recheck"

    night.monitor.apply_assessment(_assessment(night, **risky), night.now, night.profile, "recheck")
    assert night.monitor.alerts.active[AlertKind.AIRWAY_RISK].level is AlertLevel.CRITICAL


def test_second_look_that_is_fine_clears_the_ai_warning() -> None:
    night = Night(ai_enabled=True)
    night.monitor.apply_assessment(
        _assessment(night, airway_risk="likely"), night.now, night.profile, "routine"
    )
    night.advance(16)
    night.monitor.apply_assessment(_assessment(night), night.now, night.profile, "recheck")
    assert AlertKind.AIRWAY_RISK not in night.monitor.alerts.active


def test_unsure_all_fine_does_not_take_back_an_ai_warning() -> None:
    night = Night(ai_enabled=True)
    night.monitor.apply_assessment(
        _assessment(night, airway_risk="likely"), night.now, night.profile, "routine"
    )
    night.advance(16)

    night.monitor.apply_assessment(_assessment(night, confidence=0.2), night.now, night.profile, "recheck")
    assert night.monitor.alerts.active[AlertKind.AIRWAY_RISK].level is AlertLevel.WARNING

    night.advance(5)
    night.monitor.apply_assessment(_assessment(night, confidence=0.9), night.now, night.profile, "routine")
    assert AlertKind.AIRWAY_RISK not in night.monitor.alerts.active


def test_unsure_look_does_not_lower_an_ai_warning_but_a_sure_one_does() -> None:
    night = Night(ai_enabled=True)
    night.monitor.apply_assessment(
        _assessment(night, airway_risk="likely"), night.now, night.profile, "routine"
    )
    night.advance(16)

    unsure = _assessment(night, airway_risk="possible", confidence=0.2)
    night.monitor.apply_assessment(unsure, night.now, night.profile, "recheck")
    assert night.monitor.alerts.active[AlertKind.AIRWAY_RISK].level is AlertLevel.WARNING

    night.advance(5)
    sure = _assessment(night, airway_risk="possible", confidence=0.9)
    night.monitor.apply_assessment(sure, night.now, night.profile, "routine")
    assert night.monitor.alerts.active[AlertKind.AIRWAY_RISK].level is AlertLevel.INFO
    night.advance(1)
    assert night.stages(AlertKind.AIRWAY_RISK)[-1] is Stage.CLEARED  # taken off the phones


def test_recheck_never_schedules_another_recheck() -> None:
    night = Night(ai_enabled=True, profile=AgeProfile.INFANT, ai_interval_min=600.0)
    prone = {"position": "prone"}
    night.monitor.apply_assessment(_assessment(night, **prone), night.now, night.profile, "routine")
    night.advance(16)
    assert night.monitor.take_ai_request(night.now) == "recheck"
    night.monitor.apply_assessment(_assessment(night, **prone), night.now, night.profile, "recheck")
    night.advance(300)
    assert night.monitor.take_ai_request(night.now) is None
    # An infant may roll over on its own: prone stays a warning.
    assert night.monitor.alerts.active[AlertKind.PRONE_POSITION].level is AlertLevel.WARNING


def test_failed_ai_changes_nothing_but_its_availability() -> None:
    night = Night(ai_enabled=True)
    night.cry()
    night.advance(20)
    before = dict(night.monitor.alerts.active)
    night.monitor.ai_failed(night.now, "timeout")
    night.advance(1)
    assert night.monitor.ai_available is False
    assert set(night.monitor.alerts.active) == set(before)


def test_ai_alerts_pause_while_someone_is_with_the_child() -> None:
    night = Night(ai_enabled=True)
    night.monitor.apply_assessment(
        _assessment(night, airway_risk="likely"), night.now, night.profile, "routine"
    )
    night.monitor.signals.door_open.set(True, night.now)
    night.advance(2)
    assert not AI_KINDS & set(night.monitor.alerts.active)
    assert night.monitor.take_ai_request(night.now) is None


def test_assessment_is_recorded_but_raises_nothing_when_disarmed() -> None:
    night = Night(armed=False)
    night.monitor.apply_assessment(
        _assessment(night, airway_risk="likely"), night.now, night.profile, "manual"
    )
    assert night.monitor.alerts.active == {}
    assert night.monitor.assessment is not None


def test_routine_assessment_is_requested_on_the_interval() -> None:
    night = Night(ai_enabled=True, ai_interval_min=10.0)
    night.advance(590)
    assert night.monitor.take_ai_request(night.now) is None
    night.advance(10)
    assert night.monitor.take_ai_request(night.now) == "routine"
    assert night.monitor.take_ai_request(night.now) is None


def test_waking_requests_an_assessment() -> None:
    night = Night(ai_enabled=True)
    night.cry()
    night.advance(10)
    assert night.monitor.take_ai_request(night.now) == "state_change"


def test_no_assessment_requests_without_ai() -> None:
    night = Night(ai_enabled=False)
    night.cry()
    night.advance(700)
    assert night.monitor.take_ai_request(night.now) is None


# -- toddler, pets, climate, internet -------------------------------------


def test_toddler_leaving_the_bed_alone_warns() -> None:
    night = Night(profile=AgeProfile.TODDLER)
    night.monitor.set_presence(True, night.now)
    night.advance(5)
    night.monitor.set_presence(False, night.now)
    night.advance(2)
    assert len(night.pushes(AlertKind.LEFT_BED)) == 1

    night.monitor.signals.door_open.set(True, night.now)
    night.advance(2)
    assert AlertKind.LEFT_BED not in night.monitor.alerts.active


def test_lifting_a_child_out_is_not_leaving_the_bed() -> None:
    night = Night(profile=AgeProfile.TODDLER)
    night.monitor.set_presence(True, night.now)
    night.monitor.signals.door_open.set(True, night.now)
    night.advance(5)
    night.monitor.set_presence(False, night.now)
    night.monitor.signals.door_open.set(False, night.now)
    night.advance(60)
    assert night.pushes(AlertKind.LEFT_BED) == []


def test_newborn_profile_has_no_left_bed_alert() -> None:
    night = Night(profile=AgeProfile.NEWBORN)
    night.monitor.set_presence(True, night.now)
    night.advance(5)
    night.monitor.set_presence(False, night.now)
    night.advance(5)
    assert night.pushes(AlertKind.LEFT_BED) == []


def test_pet_in_bed_warns() -> None:
    night = Night()
    night.monitor.signals.pet_in_bed.set(True, night.now)
    night.advance(1)
    assert len(night.pushes(AlertKind.PET_IN_BED)) == 1


def test_room_too_warm_is_a_hint_after_ten_minutes_and_a_warning_when_far_off() -> None:
    night = Night()
    night.monitor.signals.temperature = 23.5
    night.advance(599)
    assert AlertKind.CLIMATE not in night.monitor.alerts.active
    night.advance(2)
    assert night.monitor.alerts.active[AlertKind.CLIMATE].level is AlertLevel.INFO
    assert night.pushes(AlertKind.CLIMATE) == []

    night.monitor.signals.temperature = 26.0
    night.advance(1)
    assert [n.level for n in night.pushes(AlertKind.CLIMATE)] == [AlertLevel.WARNING]


def test_internet_down_is_noted_and_makes_the_local_channel_immediate() -> None:
    night = Night()
    night.monitor.signals.internet = False
    night.cry()
    night.advance(16)
    assert night.monitor.alerts.active[AlertKind.INTERNET_DOWN].level is AlertLevel.INFO
    assert Stage.LOCAL in night.stages(AlertKind.CRYING)


# -- user actions, vox, persistence ---------------------------------------


def test_test_alert_works_while_disarmed_and_ends_on_acknowledgement() -> None:
    night = Night(armed=False)
    night.monitor.test_alert(night.now)
    night.advance(31)
    assert night.stages(AlertKind.TEST) == [Stage.FIRST, Stage.REPEAT]
    night.monitor.acknowledge(night.now)
    night.advance(1)
    assert AlertKind.TEST not in night.monitor.alerts.active


def test_a_second_test_alert_right_after_the_first_notifies_again() -> None:
    night = Night(armed=False)
    for _ in range(2):
        night.monitor.test_alert(night.now, AlertLevel.WARNING)
        night.advance(2)
        night.monitor.acknowledge(night.now)
        night.advance(2)
    # The cooldown that keeps a flapping warning quiet does not apply to a test.
    assert night.stages(AlertKind.TEST).count(Stage.FIRST) == 2


def test_interruption_is_reported_as_a_warning() -> None:
    night = Night()
    night.monitor.report_interruption(240.4, night.now)
    night.advance(1)
    assert [n.detail for n in night.pushes(AlertKind.INTERRUPTION)] == [{"seconds": 240}]


def test_manual_sleep_and_wake() -> None:
    night = Night()
    night.advance(10)
    night.monitor.force_state(ChildState.AWAKE, night.now)
    assert night.monitor.sleep_log.current is None
    night.monitor.force_state(ChildState.ASLEEP, night.now)
    assert night.monitor.sleep_log.current is not None


def test_vox_opens_on_noise_and_closes_after_quiet() -> None:
    night = Night(vox_enabled=True)
    night.advance(60)
    night.level_db = -20.0
    night.advance(3)
    assert night.monitor.take_vox_action() is VoxAction.START
    assert night.monitor.take_vox_action() is None
    night.level_db = -50.0
    night.advance(59)
    assert night.monitor.take_vox_action() is None
    night.advance(2)
    assert night.monitor.take_vox_action() is VoxAction.STOP


def test_vox_stops_when_disarmed() -> None:
    night = Night(vox_enabled=True)
    night.level_db = -20.0
    night.advance(5)
    assert night.monitor.take_vox_action() is VoxAction.START
    night.monitor.settings.armed = False
    night.advance(1)
    assert night.monitor.take_vox_action() is VoxAction.STOP


def test_changing_the_sleep_place_forgets_old_signals() -> None:
    night = Night()
    night.cry()
    night.monitor.signals.temperature = 30.0
    night.monitor.change_place(night.now)
    assert night.monitor.signals.crying.active is False
    assert night.monitor.signals.temperature is None
    assert night.monitor.watchdog.in_grace(night.now)


def test_state_survives_a_restart() -> None:
    night = Night()
    night.advance(300)
    night.cry()
    night.advance(20)
    night.monitor.acknowledge(night.now)
    stored = night.monitor.to_dict()

    fresh = Night()
    fresh.monitor.restore(stored)

    assert fresh.monitor.alerts.active[AlertKind.CRYING].acked is True
    assert fresh.monitor.sleep_log.sessions
    assert fresh.monitor.signals.baseline_db == pytest.approx(-50.0, abs=0.3)
    fresh.monitor.restore(None)


def test_snapshot_reports_the_night() -> None:
    night = Night()
    start = night.now
    night.advance(600)
    night.cry()
    night.advance(30)
    snap = night.monitor.snapshot(night.now, start, start)

    assert snap.state is ChildState.CRYING
    assert (snap.level, snap.alert_kind, snap.needs_attention) == (AlertLevel.WARNING, AlertKind.CRYING, True)
    assert snap.crying is True
    assert snap.wakeups_tonight == 1
    assert snap.slept_today_s == pytest.approx(608, abs=2)
    assert snap.cried_today_s == pytest.approx(22, abs=2)
    assert snap.alerts[0]["kind"] == "crying"
    assert snap.level_db == pytest.approx(-50.0, abs=0.3)
