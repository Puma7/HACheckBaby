# AGENTS.md

## Overview

Home Assistant custom integration (`custom_components/checkbaby/`), distributed through HACS. It turns Frigate signals, optional sensors and an optional AI assessment into a baby monitor. There is no standalone server; it runs inside Home Assistant.

Read `docs/MASTERPLAN.md` (German) before changing behaviour: it holds the architecture, the alert rules and the roadmap.

## Rules that must hold

- The AI assessment may add to an alert or raise it; it must never suppress a warning or critical alert that came from a deterministic source.
- A source that is missing or unusable is never reported as "all fine".
- Critical alerts ignore cooldowns.
- The integration does no video processing inside the Home Assistant process.
- Wording: this is not a medical device. Say "breathing-movement hint", not "breathing monitoring" or "SIDS protection".
- Never commit footage or audio of real children.

## Layout

- Logic that does not need Home Assistant lives in modules without Home Assistant imports (`profiles.py` today; `fusion.py`, `state_machine.py`, `escalation.py` to come) and is tested directly.
- The runtime data class and the `CheckBabyConfigEntry` alias live in `models.py`; import them from there, not from the package root.
- `strings.json` and `translations/en.json` are identical; `translations/de.json` carries the same keys. `tests/test_translations.py` enforces both.

## Running checks

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest
mypy custom_components/checkbaby/
pyright
```

- Tests use `pytest-homeassistant-custom-component`, which pins the Home Assistant version it was built for. Python 3.13 therefore resolves Home Assistant 2026.2 (the floor in `hacs.json`), Python 3.14 the newest release. CI runs both.
- `mypy` and `pyright` run in strict mode and must report 0 errors. The config files assume Python 3.13; on 3.14 pass `mypy --python-version 3.14` and `pyright --pythonversion 3.14`, as CI does.
- `.coveragerc` `fail_under` is a ratchet over the whole package. It may only go up.

## Documentation

User documentation is bilingual (`README.md` / `README.de.md`, later `docs/en` and `docs/de` with identical file names); change both languages together. Developer notes live in `docs/development/`.
