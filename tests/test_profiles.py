"""Age profile rules."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from custom_components.checkbaby.profiles import AgeProfile, age_in_days, profile_for

BIRTH = date(2027, 2, 14)


@pytest.mark.parametrize(
    ("age_days", "expected"),
    [
        (-30, AgeProfile.NEWBORN),  # set up before the birth
        (0, AgeProfile.NEWBORN),
        (90, AgeProfile.NEWBORN),
        (91, AgeProfile.INFANT),
        (364, AgeProfile.INFANT),
        (365, AgeProfile.TODDLER),
        (1000, AgeProfile.TODDLER),
    ],
)
def test_profile_boundaries(age_days: int, expected: AgeProfile) -> None:
    assert profile_for(BIRTH, BIRTH + timedelta(days=age_days)) is expected


def test_age_in_days_is_negative_before_birth() -> None:
    assert age_in_days(BIRTH, BIRTH - timedelta(days=3)) == -3
    assert age_in_days(BIRTH, BIRTH + timedelta(days=10)) == 10
