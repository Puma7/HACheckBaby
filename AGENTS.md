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

- `monitor.py` is the core: signals in, child state and notifications out. It and everything it uses (`signals.py`, `state_machine.py`, `rules.py`, `alerts.py`, `watchdog.py`, `sleep_log.py`, `ai_schema.py`, `ai_policy.py`, `climate.py`, `vox.py`, `texts.py`, `push.py`, `report.py`, `settings.py`, `types.py`, `profiles.py`) has no Home Assistant imports and no clock of its own: every method takes `now`. Tests in `tests/core/` replay whole nights against it.
- `coordinator.py` connects the core to Home Assistant: MQTT and entity sources in, service calls out. `notifier.py` sends pushes and drives the local alarm. The platform files only read the snapshot.
- The runtime data class, `SleepPlace` and the `CheckBabyConfigEntry` alias live in `models.py`; import them from there, not from the package root.
- Sleep places are config sub-entries of a child; options hold who is told and what else is connected; everything the entities change lives in `Settings` and is persisted with `Store`.
- Translations are generated: edit the `EN` and `DE` tables in `scripts/gen_strings.py` and run `python scripts/gen_strings.py custom_components/checkbaby`. Never edit the JSON files by hand. Notification texts live in `texts.py`.
- Use `from .schema_compat import vol` for schemas: Home Assistant validates with voluptuous up to some version and probatio after it.
- `engine/` is a separate program with its own dependencies and tests; see `engine/README.md`.

## Running checks

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest --timeout=30
mypy custom_components/checkbaby/
pyright
```

- Tests use `pytest-homeassistant-custom-component`, which pins the Home Assistant version it was built for. Python 3.13 therefore resolves Home Assistant 2026.2 (the floor in `hacs.json`), Python 3.14 the newest release. CI runs both, and so should you before pushing: `uv venv --python 3.14 .venv314 && uv pip install --python .venv314/bin/python -r requirements-dev.txt`.
- `pyright` checks against the `python` it finds on `PATH`, not the interpreter that started it. To check against the 3.14 environment run `pyright --pythonpath .venv314/bin/python --pythonversion 3.14`.
- `mypy` and `pyright` run in strict mode and must report 0 errors. Re-export checks are off in both, because Home Assistant moves names such as `BinarySensorDeviceClass` between modules across versions.
- `.coveragerc` `fail_under` is a ratchet over the whole package. It may only go up.
- A test that uses the `freezer` fixture freezes the event loop's clock too: `asyncio.timeout` and `asyncio.sleep` never finish. Tests that need real time must not use it.
- `async_block_till_done` does not wait for background tasks; advance time with `advance()` from `tests/conftest.py` instead.
- Mock a service only after the entry is set up if the integration's own platforms bring the real service (`button.press`, `switch.turn_on`), otherwise the real one replaces the mock.

## Documentation

User documentation is bilingual (`README.md` / `README.de.md`, later `docs/en` and `docs/de` with identical file names); change both languages together. Developer notes live in `docs/development/`.
