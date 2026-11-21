"""The smaller pure modules."""

from __future__ import annotations

import itertools

import pytest

from custom_components.checkbaby.ai_policy import Budget, evaluate_assessment, needs_recheck
from custom_components.checkbaby.ai_schema import (
    AIRWAY,
    POSITION,
    PRESENCE,
    REQUIRED,
    STRUCTURE,
    Assessment,
    parse_assessment,
)
from custom_components.checkbaby.climate import TOG_OPTIONS, climate_level, tog_recommendation
from custom_components.checkbaby.profiles import AgeProfile
from custom_components.checkbaby.settings import Settings
from custom_components.checkbaby.signals import Flag, Signals
from custom_components.checkbaby.sleep_log import SleepLog
from custom_components.checkbaby.state_machine import next_state
from custom_components.checkbaby.types import (
    AI_KINDS,
    AlertKind,
    AlertLevel,
    ChildState,
    Mode,
    Sensitivity,
    VitalFusion,
)
from custom_components.checkbaby.watchdog import Watchdog

GOOD = {
    "presence": "in_bed",
    "position": "Supine",
    "face_visible": True,
    "airway_risk": "none",
    "state": "asleep",
    "hazards": "blanket, soft toy",
    "view_ok": True,
    "assessment": "ok",
    "confidence": 0.8,
    "reason": "  Sleeping calmly.  ",
}


def _assessment(at: float = 100.0, **changes: object) -> Assessment:
    parsed = parse_assessment({**GOOD, **changes}, at)
    assert parsed is not None
    return parsed


# -- AI answer parsing -----------------------------------------------------


def test_parse_reads_a_complete_answer() -> None:
    parsed = _assessment()
    assert parsed.position == "supine"
    assert parsed.hazards == ("blanket", "soft toy")
    assert parsed.reason == "Sleeping calmly."
    assert parsed.at == 100.0


@pytest.mark.parametrize("missing", REQUIRED)
def test_parse_rejects_an_answer_missing_a_required_field(missing: str) -> None:
    data = {key: value for key, value in GOOD.items() if key != missing}
    assert parse_assessment(data, 1.0) is None


@pytest.mark.parametrize("bad", [None, "text", [], 5, {"confidence": "high", **{k: 1 for k in REQUIRED if k != "confidence"}}])
def test_parse_rejects_garbage(bad: object) -> None:
    assert parse_assessment(bad, 1.0) is None


def test_parse_rejects_nan_confidence() -> None:
    assert parse_assessment({**GOOD, "confidence": float("nan")}, 1.0) is None


def test_unreadable_values_never_read_as_harmless() -> None:
    parsed = _assessment(airway_risk="???", position="floating", face_visible="maybe", confidence=7)
    assert parsed.airway_risk == "possible"
    assert parsed.position == "unknown"
    assert parsed.face_visible is None
    assert parsed.confidence == 1.0


def test_parse_accepts_text_booleans_and_hazard_lists() -> None:
    parsed = _assessment(face_visible="false", view_ok="no", hazards=["pillow", " ", "none"])
    assert parsed.face_visible is False
    assert parsed.view_ok is False
    assert parsed.hazards == ("pillow",)
    assert _assessment(hazards=None).hazards == ()
    assert _assessment(face_visible="Yes").face_visible is True


def test_structure_marks_required_fields() -> None:
    assert set(REQUIRED) == set(STRUCTURE) - {"hazards"}


# -- AI policy -------------------------------------------------------------


def test_ai_can_only_produce_its_own_alert_kinds() -> None:
    """The structural guarantee behind "the AI cannot suppress an alert"."""
    combos = itertools.product(PRESENCE, POSITION, AIRWAY, (True, False), (0.2, 0.9), ("", "toy"), AgeProfile)
    seen: set[AlertKind] = set()
    for presence, position, airway, view_ok, confidence, hazards, profile in combos:
        current = _assessment(
            presence=presence, position=position, airway_risk=airway, view_ok=view_ok,
            confidence=confidence, hazards=hazards,
        )  # fmt: skip
        for previous in (None, current):
            seen |= {item.kind for item in evaluate_assessment(current, previous, profile)}
    assert seen == AI_KINDS


def test_single_assessment_never_reaches_critical() -> None:
    worst = _assessment(airway_risk="likely", position="prone", view_ok=False, assessment="critical", confidence=1.0)
    levels = {item.level for item in evaluate_assessment(worst, None, AgeProfile.NEWBORN)}
    assert AlertLevel.CRITICAL not in levels
    assert AlertLevel.WARNING in levels
    assert needs_recheck(evaluate_assessment(worst, None, AgeProfile.NEWBORN))


def test_confirmation_must_be_recent() -> None:
    first = _assessment(at=100.0, airway_risk="likely")
    late = _assessment(at=100.0 + 181, airway_risk="likely")
    soon = _assessment(at=100.0 + 20, airway_risk="likely")

    assert evaluate_assessment(late, first, AgeProfile.NEWBORN)[0].level is AlertLevel.WARNING
    assert evaluate_assessment(soon, first, AgeProfile.NEWBORN)[0].level is AlertLevel.CRITICAL


def test_low_confidence_stays_a_hint() -> None:
    unsure = _assessment(airway_risk="likely", position="prone", confidence=0.3)
    levels = {item.level for item in evaluate_assessment(unsure, unsure, AgeProfile.NEWBORN)}
    assert levels == {AlertLevel.INFO}


def test_possible_airway_risk_is_a_hint() -> None:
    result = evaluate_assessment(_assessment(airway_risk="possible"), None, AgeProfile.NEWBORN)
    assert [(item.kind, item.level) for item in result] == [
        (AlertKind.AIRWAY_RISK, AlertLevel.INFO),
        (AlertKind.HAZARD, AlertLevel.INFO),
    ]


@pytest.mark.parametrize(
    ("profile", "single", "confirmed"),
    [
        (AgeProfile.NEWBORN, AlertLevel.WARNING, AlertLevel.CRITICAL),
        (AgeProfile.INFANT, AlertLevel.WARNING, AlertLevel.WARNING),
        (AgeProfile.TODDLER, None, None),
    ],
)
def test_prone_position_by_age(profile: AgeProfile, single: AlertLevel | None, confirmed: AlertLevel | None) -> None:
    prone = _assessment(position="prone", hazards="")

    def level(previous: Assessment | None) -> AlertLevel | None:
        found = [i.level for i in evaluate_assessment(prone, previous, profile) if i.kind is AlertKind.PRONE_POSITION]
        return found[0] if found else None

    assert level(None) is single
    assert level(prone) is confirmed


def test_nothing_is_raised_for_a_child_that_is_not_in_bed() -> None:
    away = _assessment(presence="not_visible", airway_risk="likely", position="prone", hazards="")
    assert evaluate_assessment(away, away, AgeProfile.NEWBORN) == []


def test_blocked_camera_view_warns_once_confirmed() -> None:
    blocked = _assessment(view_ok=False, hazards="")
    assert evaluate_assessment(blocked, None, AgeProfile.NEWBORN)[0].level is AlertLevel.INFO
    assert needs_recheck(evaluate_assessment(blocked, None, AgeProfile.NEWBORN))
    assert evaluate_assessment(blocked, blocked, AgeProfile.NEWBORN)[0].level is AlertLevel.WARNING


def test_fine_assessment_needs_no_recheck() -> None:
    assert not needs_recheck(evaluate_assessment(_assessment(hazards=""), None, AgeProfile.NEWBORN))


def test_budget_is_a_sliding_hour() -> None:
    budget = Budget(per_hour=2)
    assert budget.allow(0.0)
    budget.record(0.0)
    budget.record(10.0)
    assert not budget.allow(3599.0)
    assert budget.used(3599.0) == 2
    assert budget.allow(3600.0)
    assert budget.used(3611.0) == 0


# -- signals ---------------------------------------------------------------


def test_flag_tracks_since_only_on_change() -> None:
    flag = Flag()
    assert flag.inactive_for(5.0) == float("inf")
    flag.set(True, 10.0)
    flag.set(True, 15.0)
    assert flag.active_for(20.0) == 10.0
    assert flag.inactive_for(20.0) == 0.0
    flag.set(False, 21.0)
    assert (flag.active_for(30.0), flag.inactive_for(30.0)) == (0.0, 9.0)


def test_noise_floor_follows_a_constant_hum_but_not_crying() -> None:
    signals = Signals()
    for second in range(3600):
        signals.set_level(-30.0 if second > 10 else -50.0, 15.0, float(second))
    # A white-noise machine switched on: the floor has moved up to it.
    assert signals.baseline_db == pytest.approx(-30.0, abs=0.5)
    assert signals.loud.active is False

    floor = signals.baseline_db
    signals.crying.set(True, 3600.0)
    for second in range(3600, 3900):
        signals.set_level(-5.0, 15.0, float(second))
    assert signals.loud.active is True
    assert signals.baseline_db == floor


def test_loud_noise_alone_does_not_raise_the_floor() -> None:
    signals = Signals()
    signals.set_level(-50.0, 15.0, 0.0)
    for second in range(1, 300):
        signals.set_level(-20.0, 15.0, float(second))
    # A few minutes of noise are an event, not the room.
    assert signals.baseline_db == pytest.approx(-50.0)
    assert signals.loud.active is True


def test_microphone_flat_needs_fresh_but_unchanging_levels() -> None:
    signals = Signals()
    assert signals.microphone_flat(0.0) is False
    signals.set_level(-40.0, 15.0, 0.0)
    signals.set_level(-40.0, 15.0, 599.0)
    assert signals.microphone_flat(599.0) is False
    signals.set_level(-40.0, 15.0, 600.0)
    assert signals.microphone_flat(600.0) is True
    # No levels at all for a long time is staleness, which the watchdog reports.
    assert signals.microphone_flat(5000.0) is False


def test_caregiver_lingers_after_the_door_closes() -> None:
    signals = Signals()
    assert signals.caregiver_present(0.0) is False
    signals.door_open.set(True, 10.0)
    assert signals.caregiver_present(11.0) is True
    signals.door_open.set(False, 20.0)
    assert signals.caregiver_present(39.0) is True
    assert signals.caregiver_present(40.0) is False
    signals.person.set(True, 50.0)
    assert signals.caregiver_present(51.0) is True


# -- state machine edge cases ----------------------------------------------


def test_unusable_sources_give_unknown_even_while_crying() -> None:
    signals = Signals()
    signals.crying.set(True, 0.0)
    assert next_state(ChildState.ASLEEP, 0.0, signals, usable=False, now=100.0) is ChildState.UNKNOWN


def test_recovering_from_unknown() -> None:
    signals = Signals()
    assert next_state(ChildState.UNKNOWN, 0.0, signals, usable=True, now=10.0) is ChildState.ASLEEP
    signals.motion.set(True, 10.0)
    assert next_state(ChildState.UNKNOWN, 0.0, signals, usable=True, now=11.0) is ChildState.AWAKE


# -- sleep log ---------------------------------------------------------------


def test_sleep_log_sessions_wakeups_and_crying() -> None:
    log = SleepLog()
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 1000.0, mode="night", place="crib")
    log.on_state(ChildState.ASLEEP, ChildState.RESTLESS, 2000.0, mode="night", place="crib")
    assert log.current is not None  # restless is still asleep
    log.on_state(ChildState.RESTLESS, ChildState.CRYING, 3000.0, mode="night", place="crib")
    assert log.current is None
    log.on_state(ChildState.CRYING, ChildState.AWAKE, 3120.0, mode="night", place="crib")
    # Back asleep within the merge gap: the same session continues.
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 3600.0, mode="night", place="crib")

    assert len(log.sessions) == 1
    assert log.asleep_since() == 1000.0
    assert log.wakeups_between(0.0, 5000.0) == 1
    assert log.cried_between(0.0, 5000.0) == 120.0
    assert log.cried_between(3060.0, 5000.0) == 60.0
    assert log.slept_between(0.0, 4000.0) == 3000.0

    log.on_state(ChildState.ASLEEP, ChildState.ATTENDED, 5000.0, mode="night", place="crib")
    assert log.last_session_seconds() == 4000.0
    assert log.wakeups_between(0.0, 6000.0) == 1  # being picked up is not a wake-up
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 5000.0 + 1201, mode="nap", place="pram")
    assert [session.mode for session in log.sessions] == ["night", "nap"]


def test_sleep_log_counts_open_crying_and_survives_a_round_trip() -> None:
    log = SleepLog()
    log.on_state(ChildState.AWAKE, ChildState.ASLEEP, 100.0, mode="night", place=None)
    log.on_state(ChildState.ASLEEP, ChildState.CRYING, 200.0, mode="night", place=None)
    assert log.cried_between(0.0, 260.0) == 60.0
    assert log.last_session_seconds() == 100.0

    restored = SleepLog()
    restored.restore(log.to_dict())
    assert restored.to_dict() == log.to_dict()

    broken = SleepLog()
    broken.restore({"sessions": [{"end": 5}, "x"], "wakeups": ["a", 3], "crying": [[1], ["a", 2], [5, None]]})
    assert broken.sessions == []
    assert broken.wakeups == [3.0]
    assert [(i.start, i.end) for i in broken.crying] == [(5.0, None)]
    broken.restore(None)
    assert SleepLog().last_session_seconds() is None


# -- settings ---------------------------------------------------------------


def test_settings_round_trip_and_tolerate_bad_data() -> None:
    settings = Settings(armed=True, mode=Mode.NAP, sensitivity=Sensitivity.HIGH, vital_fusion=VitalFusion.ANY)
    settings.active_place = "abc"
    settings.cry_warning_s = 25.0
    assert Settings.from_dict(settings.to_dict()) == settings

    loaded = Settings.from_dict(
        {"mode": "party", "cry_warning_s": "soon", "armed": 1, "active_place": None, "on_duty": 5, "extra": 1}
    )
    assert loaded.mode is Mode.NIGHT
    assert loaded.cry_warning_s == 15.0
    assert loaded.armed is True
    assert loaded.on_duty == "5"
    assert Settings.from_dict(None) == Settings()


# -- watchdog ---------------------------------------------------------------


def test_watchdog_health_freshness_and_grace() -> None:
    dog = Watchdog(started=0.0, grace_s=100.0)
    dog.expect("frigate", core=True)
    dog.expect("level", max_age_s=60.0, core=True)
    dog.expect("radar", max_age_s=30.0)
    dog.seen("unknown-source", 1.0)
    dog.set_healthy("unknown-source", False, 1.0)

    assert dog.problems(50.0) == []
    assert dog.problems(100.0) == ["frigate", "level", "radar"]

    dog.set_healthy("frigate", True, 100.0)
    dog.seen("level", 100.0)
    assert dog.problems(120.0) == ["radar"]
    assert dog.usable(120.0) is True  # radar is not a core source

    dog.set_healthy("frigate", False, 130.0)
    assert dog.usable(130.0) is False
    dog.set_healthy("frigate", True, 131.0)
    assert dog.problems(161.0) == ["level", "radar"]

    dog.forget("radar")
    dog.expect("level", max_age_s=600.0, core=True)
    assert dog.problems(161.0) == []
    dog.restart_grace(200.0)
    assert dog.in_grace(250.0)
    assert dog.problems(250.0) == []


def test_unhealthy_source_is_a_problem_even_during_grace() -> None:
    dog = Watchdog(started=0.0)
    dog.expect("frigate", core=True)
    dog.set_healthy("frigate", False, 1.0)
    assert dog.problems(2.0) == ["frigate"]


# -- climate ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [(None, None), (15.0, "tog_3_5"), (17.0, "tog_2_5_plus_layer"), (20.0, "tog_2_5"),
     (22.0, "tog_1_0"), (25.0, "tog_0_5"), (28.0, "tog_0_2")],
)  # fmt: skip
def test_sleeping_bag_suggestion(temperature: float | None, expected: str | None) -> None:
    assert tog_recommendation(temperature) == expected
    assert expected is None or expected in TOG_OPTIONS


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [(None, AlertLevel.NONE), (16.0, AlertLevel.NONE), (22.0, AlertLevel.NONE), (15.0, AlertLevel.INFO),
     (25.0, AlertLevel.INFO), (25.1, AlertLevel.WARNING), (12.0, AlertLevel.WARNING)],
)  # fmt: skip
def test_climate_level(temperature: float | None, expected: AlertLevel) -> None:
    assert climate_level(temperature, 16.0, 22.0) is expected
