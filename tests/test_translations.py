"""Every language carries exactly the keys of strings.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

PACKAGE = Path(__file__).parent.parent / "custom_components" / "checkbaby"


def _keys(node: Any, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return {prefix}
    keys: set[str] = set()
    for key, value in node.items():
        keys |= _keys(value, f"{prefix}.{key}" if prefix else key)
    return keys


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["en", "de"])
def test_translation_matches_strings(language: str) -> None:
    reference = _keys(_load(PACKAGE / "strings.json"))
    translated = _keys(_load(PACKAGE / "translations" / f"{language}.json"))
    assert translated == reference


def test_english_is_the_source_text() -> None:
    assert _load(PACKAGE / "translations" / "en.json") == _load(PACKAGE / "strings.json")
