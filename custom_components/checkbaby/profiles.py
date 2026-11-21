"""Age profiles. Pure logic, no Home Assistant imports.

The age profile selects the default thresholds for a child. It follows from
the birth date, so it moves on by itself as the child grows.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

# A newborn becomes an infant after three months, an infant a toddler after
# one year. Day counts keep the rule independent of calendar month lengths.
NEWBORN_UNTIL_DAYS = 91
INFANT_UNTIL_DAYS = 365


class AgeProfile(StrEnum):
    """Age group that selects the default thresholds."""

    NEWBORN = "newborn"
    INFANT = "infant"
    TODDLER = "toddler"


def age_in_days(birth_date: date, today: date) -> int:
    """Return the age in days; negative before the birth date."""
    return (today - birth_date).days


def profile_for(birth_date: date, today: date) -> AgeProfile:
    """Return the age profile for a child born on birth_date.

    A birth date in the future is an expected due date: the integration can be
    set up before the child is born and starts with the newborn profile.
    """
    age = age_in_days(birth_date, today)
    if age < NEWBORN_UNTIL_DAYS:
        return AgeProfile.NEWBORN
    if age < INFANT_UNTIL_DAYS:
        return AgeProfile.INFANT
    return AgeProfile.TODDLER
