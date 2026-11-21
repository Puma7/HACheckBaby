"""One schema library for every supported Home Assistant version.

Newer Home Assistant releases validate with probatio, older ones with
voluptuous; the two share an API. Typed as Any so that the type checkers
accept the same source on both.
"""

from __future__ import annotations

import importlib
from typing import Any


def _load() -> Any:
    try:
        return importlib.import_module("probatio")
    except ImportError:  # pragma: no cover - only one of the two branches exists per version
        return importlib.import_module("voluptuous")


vol: Any = _load()
