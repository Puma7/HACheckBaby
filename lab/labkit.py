"""Shared parts of the lab: a real broker, a real Home Assistant, and an HTTP client.

Nothing in Home Assistant is mocked. The broker is a real Mosquitto, the
config flows and actions go over the same HTTP API the frontend uses, and the
integration is the unmodified one from this checkout. What is simulated lives
in `custom_components/checkbaby_lab` (phones, sensors, camera, AI model) and in
`frigate_sim.py` (Frigate's MQTT messages).
"""

from __future__ import annotations

from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import traceback
from typing import Any

import aiohttp

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
RUNTIME = LAB / "runtime"
DASHBOARD = "checkbaby_dashboard.yaml"


def free_port() -> int:
    """Return a TCP port that is free right now."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class Broker:
    """A Mosquitto process on a local port."""

    def __init__(self, port: int, directory: Path) -> None:
        """Write the broker config; start() launches it."""
        self.port = port
        binary = shutil.which("mosquitto") or "/usr/sbin/mosquitto"
        if not Path(binary).exists():
            raise SystemExit("Mosquitto is not installed. On Debian/Ubuntu: apt-get install mosquitto")
        self._binary = binary
        self._config = directory / "mosquitto.conf"
        directory.mkdir(parents=True, exist_ok=True)
        self._config.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n")
        self._process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        """Launch the broker and wait until it accepts connections."""
        self._process = subprocess.Popen(
            [self._binary, "-c", str(self._config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", self.port)) == 0:
                    return
            time.sleep(0.1)
        raise RuntimeError("Mosquitto did not start")

    def stop(self) -> None:
        """Kill the broker, as in a crash."""
        if self._process is not None:
            self._process.kill()
            self._process.wait()
            self._process = None


def prepare_config(config_dir: Path) -> None:
    """Copy the integration and the lab simulator into a Home Assistant config directory."""
    components = config_dir / "custom_components"
    for domain, source in (
        ("checkbaby", ROOT / "custom_components" / "checkbaby"),
        ("checkbaby_lab", LAB / "custom_components" / "checkbaby_lab"),
    ):
        target = components / domain
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # The example dashboard, pointed at the lab camera. The lab child is called "Baby",
    # which is the name the example's entity ids assume.
    example = (ROOT / "docs" / "examples" / "dashboard.yaml").read_text(encoding="utf-8")
    (config_dir / DASHBOARD).write_text(example.replace("camera.nursery", "camera.lab_nursery"), encoding="utf-8")
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))


async def boot(config_dir: Path, http_port: int, *, frontend: bool = False) -> Any:
    """Start a real Home Assistant on the config directory and return it."""
    from homeassistant import bootstrap, core, loader  # noqa: PLC0415 - only with the lab environment

    # Drop modules of a previous instance so that the new one loads fresh code.
    for name in [name for name in sys.modules if name.startswith("custom_components")]:
        del sys.modules[name]
    _trace_stops(core)
    hass = core.HomeAssistant(str(config_dir))
    loader.async_setup(hass)
    config: dict[str, Any] = {
        "http": {"server_host": "127.0.0.1", "server_port": http_port},
        "homeassistant": {
            "name": "CheckBaby Lab",
            "time_zone": "Europe/Berlin",
            "latitude": 52.52,
            "longitude": 13.405,
            "elevation": 35,
            "unit_system": "metric",
            "country": "DE",
        },
        "config": {},
        "diagnostics": {},
        "checkbaby_lab": {},
        "logger": {"default": "warning", "logs": {"custom_components.checkbaby": "info"}},
    }
    if frontend:
        config.update(
            {
                "frontend": {},
                "history": {},
                "logbook": {},
                "recorder": {},
                "lovelace": {
                    "dashboards": {
                        "checkbaby-lab": {
                            "mode": "yaml",
                            "filename": DASHBOARD,
                            "title": "CheckBaby",
                            "icon": "mdi:baby-face-outline",
                            "show_in_sidebar": True,
                        }
                    }
                },
            }
        )
    # Written to disk as well: integrations such as MQTT read configuration.yaml themselves.
    (config_dir / "configuration.yaml").write_text(json.dumps(config, indent=2) + "\n")
    if await bootstrap.async_from_config_dict(config, hass) is None:
        raise RuntimeError("Home Assistant did not boot")
    await hass.async_start()
    await hass.async_block_till_done()
    await _confirm_http_config(hass)
    return hass


async def _confirm_http_config(hass: Any) -> None:
    """Tell Home Assistant that the lab's HTTP settings work.

    Newer Home Assistant versions take an `http:` block from YAML as a trial:
    unless it is confirmed, Home Assistant restarts itself five minutes after
    the start to go back to the previous settings. In the lab that looked like
    Home Assistant dying in the middle of a run.
    """
    try:
        from homeassistant.components.http.config import async_get_and_load_store  # noqa: PLC0415
    except ImportError:
        return  # this version has no such trial
    store = await async_get_and_load_store(hass)
    if store.pending is not None:
        await store.async_promote_pending()


def _trace_stops(core: Any) -> None:
    """If anything but the lab stops Home Assistant, say who it was.

    Patched on the class and before the instance exists, so that references to
    the method taken during start-up (the stop and restart actions) are traced too.
    """
    if getattr(core.HomeAssistant, "lab_traced", False):
        return
    original_stop = core.HomeAssistant.async_stop

    def traced_stop(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Not a coroutine function: the stack is printed where the stop is requested,
        # not where the event loop later runs it.
        if not getattr(self, "lab_stopping", False):
            print("Home Assistant is being stopped by:", flush=True)
            traceback.print_stack()
        return original_stop(self, *args, **kwargs)

    core.HomeAssistant.async_stop = traced_stop
    core.HomeAssistant.lab_traced = True


async def admin_token(hass: Any) -> str:
    """Create an admin user and a long-lived token for the HTTP API."""
    from homeassistant.auth.const import GROUP_ID_ADMIN  # noqa: PLC0415
    from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN  # noqa: PLC0415

    user = await hass.auth.async_create_user(f"Lab {time.time_ns()}", group_ids=[GROUP_ID_ADMIN])
    refresh = await hass.auth.async_create_refresh_token(
        user,
        client_name=f"lab-{time.time_ns()}",
        token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        access_token_expiration=timedelta(days=1),
    )
    return str(hass.auth.async_create_access_token(refresh))


class Api:
    """Home Assistant's HTTP API, as the frontend and the companion app use it."""

    def __init__(self, port: int, token: str) -> None:
        """Remember where Home Assistant listens."""
        self._base = f"http://127.0.0.1:{port}"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Api:
        self._session = aiohttp.ClientSession(headers=self._headers)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._session is not None:
            await self._session.close()

    async def request(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        """Send a request and return the status and the decoded JSON (or the raw bytes)."""
        assert self._session is not None
        async with self._session.request(method, self._base + path, json=body) as response:
            if response.content_type == "application/json":
                return response.status, await response.json()
            return response.status, await response.read()

    async def call(self, domain: str, service: str, data: dict[str, Any] | None = None, *, response: bool = False) -> Any:
        """Call an action; with response=True return what it answers."""
        path = f"/api/services/{domain}/{service}" + ("?return_response" if response else "")
        status, body = await self.request("POST", path, data or {})
        if status >= 400:
            raise RuntimeError(f"{domain}.{service} failed with {status}: {body!r}")
        return body.get("service_response") if response else body

    async def flow(self, kind: str, handler: Any, steps: list[dict[str, Any]], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run a config, options or sub-entry flow and return every result the frontend would get."""
        base = {
            "config": "/api/config/config_entries/flow",
            "options": "/api/config/config_entries/options/flow",
            "subentry": "/api/config/config_entries/subentries/flow",
        }[kind]
        start: dict[str, Any] = {"handler": handler, "show_advanced_options": False}
        if context:
            start.update(context)
        status, result = await self.request("POST", base, start)
        if status >= 400:
            raise RuntimeError(f"starting the {kind} flow failed with {status}: {result!r}")
        results = [result]
        for user_input in steps:
            status, result = await self.request("POST", f"{base}/{result['flow_id']}", user_input)
            if status >= 400:
                raise RuntimeError(f"{kind} flow step failed with {status}: {result!r}")
            results.append(result)
        return results


def engine_command(broker_port: int, engine_id: str, bpm: int = 40) -> tuple[list[str], dict[str, str]]:
    """Command and environment that run the vital engine on its synthetic test pattern."""
    env = {
        **os.environ,
        "CHECKBABY_RTSP_URL": f"synthetic://{bpm}",
        "CHECKBABY_ENGINE_ID": engine_id,
        "CHECKBABY_MQTT_HOST": "127.0.0.1",
        "CHECKBABY_MQTT_PORT": str(broker_port),
        "PYTHONPATH": str(ROOT / "engine"),
    }
    return [sys.executable, "-m", "checkbaby_engine"], env
