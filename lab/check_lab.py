"""Acceptance run of CheckBaby in a real Home Assistant, in real time.

    python lab/check_lab.py            # about ten minutes
    python lab/check_lab.py --long     # also waits out a two-minute outage

Starts a real Mosquitto and a real Home Assistant with the unmodified
integration, sets everything up through the HTTP API the frontend uses, and
plays scenarios against a stand-in for Frigate, simulated phones and sensors,
a scripted AI model and the real vital engine on its test pattern. See
README.md in this folder for what that does and does not prove.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import traceback
from typing import Any

from frigate_sim import FrigateSim
import labkit

CHILD = "Baby"
PARENT_A = "mobile_app_lab_parent_a"
PARENT_B = "mobile_app_lab_parent_b"
ENGINE_ID = "crib"

PLACE = {
    "name": "Crib",
    "frigate_camera": "nursery",
    "camera_entity": "camera.lab_nursery",
    "bed_zone": "bed",
    "door_entity": "binary_sensor.lab_door",
    "presence_entity": "binary_sensor.lab_in_bed",
    "temperature_entity": "sensor.lab_temperature",
    "humidity_entity": "sensor.lab_humidity",
    "breath_rate_entity": "sensor.lab_breath_rate",
    "heart_rate_entity": "sensor.lab_heart_rate",
    "audio_stream_url": "http://go2rtc.lab/api/stream.mp3?src=nursery",
}
OPTIONS = {
    "notify_services": [PARENT_A, PARENT_B],
    "local_alarm_entities": ["switch.lab_siren"],
    "babysitter_service": ["mobile_app_lab_babysitter"],
    "heartbeat_buttons": ["button.lab_dead_man_heartbeat"],
    "smoke_entities": ["binary_sensor.lab_smoke"],
    "internet_entity": "binary_sensor.lab_internet",
    "vox_media_player": "media_player.lab_speaker",
    "ai_task_entities": ["ai_task.lab_ai"],
    "ai_consent": True,
    "ai_calls_per_hour": 60,
    "frigate_topic_prefix": "frigate",
    "dashboard_path": "/lovelace",
}


OPTION_PAGES = {
    "notify": ["notify_services", "local_alarm_entities", "babysitter_service", "heartbeat_buttons"],
    "ai": ["ai_task_entities", "ai_consent", "ai_calls_per_hour"],
    "devices": ["smoke_entities", "internet_entity", "vox_media_player", "frigate_topic_prefix", "dashboard_path"],
}


class Run:
    """One lab run: the world, and the list of what was checked."""

    def __init__(self, root: Path, long: bool) -> None:
        self.root = root
        self.long = long
        self.checks: list[dict[str, Any]] = []
        self.broker = labkit.Broker(labkit.free_port(), root / "broker")
        self.http_port = labkit.free_port()
        self.hass: Any = None
        self.api: labkit.Api | None = None
        self.sim: FrigateSim | None = None
        self.entry_id = ""
        self.engine: subprocess.Popen[bytes] | None = None

    # -- bookkeeping ---------------------------------------------------------

    def check(self, label: str, passed: bool, detail: Any = "") -> bool:
        self.checks.append({"check": label, "passed": bool(passed), "detail": str(detail)})
        print(f"{'PASS' if passed else 'FAIL'}  {label}" + (f"  [{detail}]" if detail != "" else ""), flush=True)
        return bool(passed)

    async def until(self, label: str, predicate: Any, timeout: float, *, not_before: float = 0.0) -> bool:
        """Wait until the predicate holds; record how long it took."""
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            if predicate():
                elapsed = time.monotonic() - started
                return self.check(label, elapsed >= not_before, f"after {elapsed:.1f} s")
            await asyncio.sleep(0.25)
        return self.check(label, False, f"not within {timeout:.0f} s; {self.situation()}")

    async def stays(self, label: str, predicate: Any, seconds: float) -> bool:
        """Check that the predicate holds for the whole time."""
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            if not predicate():
                return self.check(label, False, f"broke after {time.monotonic() - started:.1f} s")
            await asyncio.sleep(0.25)
        return self.check(label, True, f"for {seconds:.0f} s")

    def situation(self) -> str:
        """What the monitor sees right now, for the detail of a failed check."""
        if not self.entry_id or self.hass is None:
            return "no entry"
        try:
            monitor = self.coordinator.monitor
            place = self.coordinator.active_place
            alerts = {kind.value: alert.level.name for kind, alert in monitor.alerts.active.items()}
            return (
                f"state={monitor.state.value} problems={monitor.problems} alerts={alerts} "
                f"place={place.name if place else None} pushes={[p['message'][:40] for p in self.pushes()[-3:]]}"
            )
        except Exception as error:  # noqa: BLE001 - diagnostics must not fail the run
            return f"situation unavailable: {error}"

    # -- access --------------------------------------------------------------

    @property
    def world(self) -> Any:
        return self.hass.data["checkbaby_lab"]

    @property
    def coordinator(self) -> Any:
        return self.hass.config_entries.async_get_entry(self.entry_id).runtime_data.coordinator

    def entity(self, platform: str, key: str) -> str:
        from homeassistant.helpers import entity_registry as er  # noqa: PLC0415

        found = er.async_get(self.hass).async_get_entity_id(platform, "checkbaby", f"{self.entry_id}_{key}")
        assert found, f"{platform}.{key} is not registered"
        return str(found)

    def state(self, platform: str, key: str) -> str:
        state = self.hass.states.get(self.entity(platform, key))
        return state.state if state else "missing"

    def notices(self) -> dict[str, str]:
        """The child's entries in Home Assistant's own notifications, by topic."""
        from homeassistant.components.persistent_notification import (  # noqa: PLC0415
            _async_get_or_create_notifications,
        )

        prefix = f"checkbaby_{self.entry_id}_"
        return {
            key.removeprefix(prefix): note["message"]
            for key, note in _async_get_or_create_notifications(self.hass).items()
            if key.startswith(prefix)
        }

    def pushes(self, phone: str | None = None) -> list[dict[str, Any]]:
        return list(self.world.real_pushes(phone))

    def siren(self) -> bool:
        state = self.hass.states.get("switch.lab_siren")
        return bool(state and state.state == "on")

    async def switch(self, key: str, on: bool) -> None:
        assert self.api
        await self.api.call("switch", "turn_on" if on else "turn_off", {"entity_id": self.entity("switch", key)})

    async def number(self, key: str, value: float) -> None:
        assert self.api
        await self.api.call("number", "set_value", {"entity_id": self.entity("number", key), "value": value})

    async def select(self, key: str, option: str) -> None:
        assert self.api
        await self.api.call("select", "select_option", {"entity_id": self.entity("select", key), "option": option})

    async def world_set(self, **values: Any) -> None:
        assert self.api
        await self.api.call("checkbaby_lab", "set", values)

    async def tap(self, button: str) -> None:
        assert self.api
        await self.api.call("checkbaby_lab", "tap", {"button": button, "entry_id": self.entry_id})

    async def quiet_down(self, seconds: float = 3.0) -> None:
        """Acknowledge whatever is active and forget the recordings."""
        assert self.api
        await self.api.call("checkbaby", "acknowledge", {})
        await asyncio.sleep(seconds)
        await self.api.call("checkbaby_lab", "reset", {})

    # -- start and stop --------------------------------------------------------

    async def start_home_assistant(self) -> None:
        self.hass = await labkit.boot(self.root, self.http_port)
        token = await labkit.admin_token(self.hass)
        self.api = labkit.Api(self.http_port, token)
        await self.api.__aenter__()

    async def stop_home_assistant(self) -> None:
        if self.api is not None:
            await self.api.__aexit__()
            self.api = None
        if self.hass is not None:
            self.hass.lab_stopping = True
            await self.hass.async_stop()
            self.hass = None

    def stop_engine(self, sig: int = signal.SIGKILL) -> None:
        if self.engine is not None:
            self.engine.send_signal(sig)
            self.engine.wait(timeout=10)
            self.engine = None


# -- scenarios ---------------------------------------------------------------


async def setup_through_the_frontend_api(run: Run) -> None:
    api = run.api
    assert api
    from homeassistant import const  # noqa: PLC0415

    run.check("real Home Assistant is running", run.hass.is_running, f"version {const.__version__}")
    await run.until("lab simulator entry is loaded", lambda: "checkbaby_lab" in run.hass.data, 20)

    results = await api.flow("config", "mqtt", [{"broker": "127.0.0.1", "port": run.broker.port, "other_settings": {"set_client_cert": False, "set_ca_cert": "off"}}])
    run.check("MQTT integration connects to the real broker", results[-1]["type"] == "create_entry", results[-1]["type"])

    results = await api.flow(
        "config",
        "checkbaby",
        [
            {"child_name": CHILD, "birth_date": "2027-02-14"},
            PLACE,
            {"notify_services": [PARENT_A, PARENT_B], "local_alarm_entities": ["switch.lab_siren"]},
            {"ai_task_entities": ["ai_task.lab_ai"], "ai_consent": True},
            {"acknowledged": True},
        ],
    )
    steps = [result.get("step_id") for result in results[:-1]]
    run.check("setup dialog walks child, place, notify, AI, disclaimer", steps == ["user", "place", "notify", "ai", "disclaimer"], steps)
    forms_ok = all(isinstance(result.get("data_schema"), list) and result["data_schema"] for result in results[:-1])
    fields = {result["step_id"]: [field["name"] for field in result["data_schema"]] for result in results[:-1]}
    run.check("every form reaches the frontend as a field list", forms_ok, {k: len(v) for k, v in fields.items()})
    run.check(
        "sleep place form offers the entity pickers",
        {"camera_entity", "door_entity", "breath_rate_entity"} <= set(fields["place"]),
        len(fields["place"]),
    )
    phones = next(field for field in results[2]["data_schema"] if field["name"] == "notify_services")["selector"]["select"]
    offered = {option["value"]: option["label"] for option in phones["options"]}
    run.check(
        "phones are offered as tick boxes with readable names",
        phones.get("mode") == "list" and phones["multiple"] and offered.get(PARENT_A) == "Lab Parent A" and len(offered) == 3,
        offered,
    )
    created = results[-1]
    run.check("setup creates the entry", created["type"] == "create_entry", created.get("title"))
    run.entry_id = created["result"]["entry_id"]
    await run.until("entry is loaded", lambda: "loaded" in str(run.hass.config_entries.async_get_entry(run.entry_id).state).lower(), 20)

    saved = []
    for page, keys in OPTION_PAGES.items():
        results = await api.flow("options", run.entry_id, [{"next_step_id": page}, {key: OPTIONS[key] for key in keys}])
        saved.append(results[0]["type"] == "menu" and results[-1]["type"] == "create_entry")
        await asyncio.sleep(2)  # the entry reloads
    stored = dict(run.hass.config_entries.async_get_entry(run.entry_id).options)
    run.check("the three options pages save and keep each other's settings", all(saved) and stored == OPTIONS,
              sorted(set(OPTIONS) - set(stored)))

    results = await api.flow(
        "options", run.entry_id, [{"next_step_id": "notify"}, {"notify_services": [], "babysitter_service": [PARENT_B]}]
    )
    run.check("a phone ticked only under babysitters is refused with its own message",
              results[-1].get("errors") == {"base": "only_babysitter"}, results[-1].get("errors"))

    results = await api.flow(
        "subentry", [run.entry_id, "sleep_place"], [{"name": "Pram", "cry_entity": "binary_sensor.lab_door"}]
    )
    run.check("second sleep place is added as a sub-entry", results[-1]["type"] == "create_entry", results[-1].get("title"))
    await asyncio.sleep(2)
    options = run.hass.states.get(run.entity("select", "active_place")).attributes["options"]
    run.check("active sleep place offers both places", options == ["Crib", "Pram"], options)
    count = len([s for s in run.hass.states.async_all() if s.entity_id.split(".")[1].startswith("baby_")])
    run.check("the child's entities exist", count >= 45, f"{count} entities")

    status, issues = await api.request("GET", "/api/states/" + run.entity("sensor", "monitoring_problems"))
    run.check("states are readable over REST", status == 200 and "state" in issues, status)


async def calm_baseline(run: Run) -> None:
    assert run.sim
    await run.number("cry_warning_s", 5)
    await run.number("cry_critical_s", 60)
    await run.select("on_duty", PARENT_A)
    await run.switch("audio_relay_enabled", True)
    await run.switch("monitoring", True)
    await run.until("Frigate stand-in is seen as online and delivering sound", lambda: run.coordinator.monitor.problems == [], 20)
    await run.until("state settles to asleep", lambda: run.state("sensor", "state") == "asleep", 15)
    await run.stays("a calm child raises no notification", lambda: run.pushes() == [], 6)
    level = float(run.state("sensor", "noise_level"))
    run.check("sound level arrives from MQTT", -52 <= level <= -48, f"{level} dBFS")


async def message_flood(run: Run) -> None:
    """Frigate publishes levels about ten times a second; twice that must not slow anything down."""
    assert run.sim and run.api
    run.sim.rate_hz = 20.0
    await asyncio.sleep(8)
    started = time.monotonic()
    await run.api.call("checkbaby", "quick_check", {}, response=True)
    took = time.monotonic() - started
    run.sim.rate_hz = 2.0
    run.check("actions answer quickly under 40 MQTT messages a second", took < 1.0, f"{took * 1000:.0f} ms")
    run.check("no problem and no notification from the flood", run.coordinator.monitor.problems == [] and run.pushes() == [])


async def crying_chain(run: Run) -> None:
    assert run.sim and run.api
    run.sim.cry(True)
    await run.until("crying warning reaches the phone on duty", lambda: len(run.pushes(PARENT_A)) == 1, 14, not_before=4.0)
    first = run.pushes(PARENT_A)[0]
    run.check("the other parent is not woken by a warning", run.pushes(PARENT_B) == [])
    run.check("warning is time-sensitive, with picture and buttons",
              first["data"].get("push") == {"interruption-level": "time-sensitive"}
              and first["data"].get("image") == "/api/camera_proxy/camera.lab_nursery"
              and len(first["data"].get("actions", [])) == 3, first["message"])
    status, picture = await run.api.request("GET", first["data"]["image"])
    run.check("the picture in the notification can be fetched", status == 200 and isinstance(picture, bytes) and picture[:2] == b"\xff\xd8", f"{len(picture)} bytes")
    run.check("state is crying", run.state("sensor", "state") == "crying" and run.state("binary_sensor", "crying") == "on")
    await run.until("audio relay plays the room on the speaker", lambda: any(m["action"] == "play" for m in run.world.media), 10)

    await run.until("local alarm switches on after a minute without a reaction", run.siren, 70, not_before=40.0)
    await run.until("unanswered crying becomes critical for both parents",
                    lambda: any(p["title"].startswith("ALARM") for p in run.pushes(PARENT_B)), 20)
    critical = [p for p in run.pushes(PARENT_B) if p["title"].startswith("ALARM")][0]
    run.check("critical push breaks through silent mode on iOS and Android",
              critical["data"]["push"]["sound"]["critical"] == 1 and critical["data"]["channel"] == "alarm_stream")
    run.check("local alarm stays on while the alert gets worse", run.siren())
    before = len(run.pushes(PARENT_B))
    await run.until("critical alert repeats", lambda: len(run.pushes(PARENT_B)) > before, 40)

    await run.tap("seen")
    await run.until("tapping Seen switches the local alarm off", lambda: not run.siren(), 6)
    cleared = [p for p in run.world.pushes if p["message"] == "clear_notification"]
    run.check("the notification is cleared from the phones", len(cleared) >= 2, len(cleared))
    count = len(run.pushes())
    await run.stays("no more notifications after Seen", lambda: len(run.pushes()) == count, 35)
    run.check("the alert stays visible while the child still cries", run.state("sensor", "alert_level") == "critical")

    run.sim.cry(False)
    await run.until("alert ends a minute after the crying stops", lambda: run.state("sensor", "alert_level") == "none", 80, not_before=45.0)
    run.check("state is awake afterwards", run.state("sensor", "state") == "awake")
    await run.quiet_down()


async def frigate_outage(run: Run) -> None:
    assert run.sim
    run.sim.online(False)
    await run.until("Frigate going offline is reported", lambda: any("Frigate offline" in p["message"] for p in run.pushes()), 10)
    run.check("state is unknown, not asleep", run.state("sensor", "state") == "unknown")
    run.sim.online(True)
    await run.until("monitoring recovers when Frigate is back", lambda: run.state("binary_sensor", "monitoring_problem") == "off", 15)
    await run.quiet_down()

    run.sim.sound(False)
    await run.until("a camera that goes silent is reported", lambda: "audio_level" in run.coordinator.monitor.problems, 80, not_before=50.0)
    run.sim.sound(True)
    await run.until("it recovers when sound returns", lambda: run.coordinator.monitor.problems == [], 10)
    await run.quiet_down()


async def broker_restart(run: Run) -> None:
    assert run.sim
    run.broker.stop()
    await run.until("a dead broker is reported as an MQTT problem", lambda: "mqtt" in run.coordinator.monitor.problems, 40)
    run.check("state is unknown while MQTT is down", run.state("sensor", "state") == "unknown")
    run.broker.start()
    await run.until("monitoring recovers after the broker restart", lambda: run.coordinator.monitor.problems == [], 60)
    run.sim.motion(True)
    await run.until("subscriptions survived the restart", lambda: run.state("binary_sensor", "motion") == "on", 15)
    run.sim.motion(False)
    await asyncio.sleep(2)
    await run.quiet_down()


async def ai_assessment(run: Run) -> None:
    api = run.api
    assert api
    answer = await api.call("checkbaby", "assess_now", {}, response=True)
    run.check("assessment goes through Home Assistant's real ai_task action", answer["assessment"] is not None, answer["assessment"] and answer["assessment"]["position"])
    call = run.world.ai_calls[-1]
    attachment = call["attachments"][0] if call["attachments"] else {}
    run.check("the camera picture arrives at the model as an image file",
              attachment.get("bytes", 0) > 1000 and str(attachment.get("mime_type", "")).startswith("image/"), attachment)
    run.check("the model is given the answer structure and the instructions", call["has_structure"] and "airway_risk" in call["instructions"])
    run.check("sensors show the assessment", run.state("sensor", "ai_assessment") == "ok" and run.state("sensor", "position") == "supine")

    await run.switch("ai_assessment_enabled", True)
    await api.call("checkbaby_lab", "ai", {"mode": "answer", "fields": {"airway_risk": "likely", "assessment": "critical"}})
    await api.call("checkbaby", "assess_now", {}, response=True)
    await run.until("a risky picture raises a warning, not a critical alert",
                    lambda: run.state("sensor", "alert_reason") == "airway_risk" and run.state("sensor", "alert_level") == "warning", 8)
    calls = len(run.world.ai_calls)
    await run.until("the second look happens by itself", lambda: len(run.world.ai_calls) > calls, 30, not_before=10.0)
    await run.until("the confirmed risk is critical", lambda: run.state("sensor", "alert_level") == "critical", 8)

    await api.call("checkbaby_lab", "ai", {"mode": "answer"})
    await api.call("checkbaby", "assess_now", {}, response=True)
    await run.until("a confident all-clear ends the AI alert", lambda: run.state("sensor", "alert_level") == "none", 8)

    await api.call("checkbaby_lab", "ai", {"mode": "error"})
    answer = await api.call("checkbaby", "assess_now", {}, response=True)
    run.check("a failing model gives no assessment and no alert",
              answer["assessment"] is None and run.state("binary_sensor", "ai_available") == "off" and run.state("sensor", "alert_level") == "none")
    await api.call("checkbaby_lab", "ai", {"mode": "answer"})

    await run.switch("privacy_mode", True)
    calls = len(run.world.ai_calls)
    await api.call("checkbaby", "assess_now", {}, response=True)
    run.check("privacy mode sends no picture, even on request", len(run.world.ai_calls) == calls)
    await run.switch("privacy_mode", False)
    await run.switch("ai_assessment_enabled", False)
    await run.quiet_down()


async def breathing_hint_with_radar(run: Run) -> None:
    assert run.sim
    await run.switch("breathing_alert", True)
    await run.world_set(breath_rate=40.0, heart_rate=128.0)
    await run.until("radar breathing shows up", lambda: run.state("binary_sensor", "breathing_movement") == "on", 8)
    await asyncio.sleep(13)

    # The child is lifted out: movement, then nothing.
    run.sim.motion(True)
    await asyncio.sleep(3)
    await run.world_set(breath_rate=0.0)
    run.sim.motion(False)
    await run.stays("an empty bed after lifting the child out raises nothing", lambda: run.state("sensor", "alert_level") == "none", 32)

    # Back in bed, breathing, then the radar sees no breathing movement any more.
    await run.world_set(breath_rate=38.0)
    await asyncio.sleep(14)
    await run.world_set(breath_rate=0.0)
    await run.until("no breathing movement becomes a critical alert", lambda: run.state("sensor", "alert_reason") == "no_breathing", 35, not_before=18.0)
    run.check("it is critical and goes to both parents",
              run.state("sensor", "alert_level") == "critical" and any("breathing" in p["message"] for p in run.pushes(PARENT_B)))
    await run.world_set(breath_rate=41.0)
    await run.until("it ends when breathing movement is back", lambda: run.state("sensor", "alert_level") == "none", 8)

    await run.world_set(breath_rate=None)
    await run.until("a radar without a reading is a problem, not an alarm",
                    lambda: run.coordinator.monitor.problems == ["vital_sensor"] and run.state("binary_sensor", "breathing_movement") == "unknown", 8)
    await run.world_set(breath_rate=40.0)
    await run.switch("breathing_alert", False)
    await run.quiet_down()


async def vital_engine(run: Run) -> None:
    api = run.api
    assert api
    from homeassistant.helpers import entity_registry  # noqa: F401, PLC0415

    entry = run.hass.config_entries.async_get_entry(run.entry_id)
    crib = next(sub for sub in entry.subentries.values() if sub.title == "Crib")
    results = await api.flow(
        "subentry", [run.entry_id, "sleep_place"], [{**PLACE, "engine_id": ENGINE_ID}],
        context={"subentry_id": crib.subentry_id},
    )
    run.check("the sleep place can be changed to use the vital engine", results[-1].get("reason") == "reconfigure_successful", results[-1].get("reason") or results[-1].get("type"))
    await asyncio.sleep(3)
    run.check("monitoring stays armed across the reload", run.state("switch", "monitoring") == "on")

    command, env = labkit.engine_command(run.broker.port, ENGINE_ID)
    run.engine = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    video = lambda: run.coordinator.monitor.signals.vitals.get("video")  # noqa: E731
    await run.until("the real engine process reports breathing movement over MQTT",
                    lambda: video() is not None and video().breathing, 60)
    rate = video().rate
    run.check("its rate matches the test pattern of 40 per minute", rate is not None and abs(rate - 40) <= 3, rate)
    run.check("no monitoring problem with the engine running", run.coordinator.monitor.problems == [])

    run.stop_engine()
    await run.until("a crashed engine is reported", lambda: "engine" in run.coordinator.monitor.problems, 40)
    await run.quiet_down()


async def smoke_and_internet(run: Run) -> None:
    await run.switch("monitoring", False)
    await run.world_set(smoke=True)
    await run.until("smoke is passed through although monitoring is off", lambda: any("Smoke" in p["message"] for p in run.pushes()), 6)
    await run.until("the local alarm joins after a minute", run.siren, 70, not_before=40.0)
    await run.world_set(smoke=False)
    await run.until("it switches off when the smoke alarm ends", lambda: not run.siren(), 6)
    await run.switch("monitoring", True)
    await run.quiet_down()

    await run.world_set(internet=False)
    await asyncio.sleep(3)
    alerts = {kind.value: alert.level.name for kind, alert in run.coordinator.monitor.alerts.active.items()}
    run.check("an internet outage is a hint, not a push", alerts.get("internet_down") == "INFO" and run.pushes() == [],
              f"alerts {alerts}, pushes {[p['message'][:50] for p in run.pushes()]}")
    assert run.api
    await run.api.call("checkbaby", "test_alert", {"level": "critical"})
    await run.until("without internet the local alarm fires at once", run.siren, 5)
    await run.tap("seen")
    await run.world_set(internet=True)
    await run.until("local alarm off after Seen", lambda: not run.siren(), 6)
    await run.quiet_down()


async def reports_and_diagnostics(run: Run) -> None:
    api = run.api
    assert api
    check = await api.call("checkbaby", "quick_check", {"notify": True}, response=True)
    run.check("quick check answers with a sentence", CHILD in check["summary"] and check["state"] in ("asleep", "awake", "restless"), check["summary"])
    await run.until("and sends it to the phone on duty", lambda: any(p["message"] == check["summary"] for p in run.pushes(PARENT_A)), 5)
    await run.until("and shows it in Home Assistant's notifications", lambda: run.notices().get("quick_check") == check["summary"], 5)
    await api.call("button", "press", {"entity_id": run.entity("button", "assess_now")})
    await run.until("the button 'AI check now' shows the AI's answer", lambda: "% sure" in run.notices().get("ai_check", ""), 15)

    await api.call("checkbaby", "test_alert", {"level": "critical"})
    await run.until("a test alert writes a delivery report", lambda: "test_delivery" in run.notices(), 6)
    delivery = run.notices().get("test_delivery", "")
    run.check("the report names both phones and the siren",
              all(name in delivery for name in (PARENT_A, PARENT_B, "switch.lab_siren")), delivery.replace("\n", " | "))
    await run.tap("seen")
    await run.until("after Seen the alert is gone from the notifications, the report stays",
                    lambda: "test" not in run.notices() and "test_delivery" in run.notices(), 6)

    await run.quiet_down()
    # What an unplugged siren looks like to the integration.
    run.hass.states.async_set("switch.lab_siren", "unavailable")
    await run.until("an unreachable local alarm is listed as a problem", lambda: "local_alarm" in run.coordinator.monitor.problems, 8)
    await run.stays("but wakes nobody while the phones work", lambda: run.pushes() == [] and run.state("sensor", "state") != "unknown", 8)
    run.hass.states.async_set("switch.lab_siren", "off")
    await run.until("and the problem ends when it is back", lambda: "local_alarm" not in run.coordinator.monitor.problems, 8)
    await run.quiet_down()

    report = await api.call("checkbaby", "night_report", {}, response=True)
    run.check("night report has numbers", report["slept_seconds"] > 0 and report["wakeups"] >= 1, report["summary"])
    run.check("heartbeat button was pressed regularly", run.world.heartbeats >= 5, run.world.heartbeats)
    status, diagnostics = await api.request("GET", f"/api/diagnostics/config_entry/{run.entry_id}")
    text = json.dumps(diagnostics)
    events = diagnostics["data"]["events"] if status == 200 else []
    # The name as a word of its own; "CheckBaby" in a link is not the child.
    leaks = re.findall(rf"(?<![A-Za-z]){CHILD}(?![A-Za-z])", text)[:3]
    run.check("diagnostics download works and leaves the child's name out",
              status == 200 and not leaks and "REDACTED" in text and len(events) >= 1,
              f"status {status}, {len(text)} bytes, {len(events)} events, name found in {leaks}")
    from homeassistant.helpers import issue_registry as ir  # noqa: PLC0415

    ours = [issue for issue in ir.async_get(run.hass).issues.values() if issue.domain == "checkbaby"]
    run.check("no repair issue is open", ours == [], [issue.issue_id for issue in ours])


async def restart(run: Run) -> None:
    sessions = len(run.coordinator.monitor.sleep_log.sessions)
    await run.number("noise_margin_db", 12)
    await run.stop_home_assistant()
    stored = json.loads((run.root / ".storage" / f"checkbaby.{run.entry_id}").read_text())["data"]
    run.check("state is on disk after shutdown", stored["settings"]["armed"] is True and stored["settings"]["noise_margin_db"] == 12.0)
    if run.long:
        print("      waiting out a 125 second outage ...", flush=True)
        await asyncio.sleep(125)
    await run.start_home_assistant()
    await run.until("the entry comes back after the restart", lambda: run.hass.config_entries.async_get_entry(run.entry_id) is not None
                    and hasattr(run.hass.config_entries.async_get_entry(run.entry_id), "runtime_data")
                    and "loaded" in str(run.hass.config_entries.async_get_entry(run.entry_id).state).lower(), 60)
    run.check("monitoring is still armed and settings are kept",
              run.state("switch", "monitoring") == "on" and run.coordinator.settings.cry_warning_s == 5.0
              and run.coordinator.settings.noise_margin_db == 12.0)
    run.check("the sleep log survived", len(run.coordinator.monitor.sleep_log.sessions) >= sessions, sessions)
    await run.until("monitoring is healthy again without help", lambda: run.coordinator.monitor.problems in ([], ["engine"]), 40)
    false_alarms = [p["message"][:60] for p in run.pushes() if "impaired" in p["message"] or "down for" in p["message"]]
    run.check("the restart raises no false monitoring warning", false_alarms == [], false_alarms)
    if run.long:
        await run.until("the outage is reported after the restart", lambda: any("interrupted" in p["message"] for p in run.pushes()), 10)
    else:
        await run.stays("a short restart is not reported as an outage", lambda: not any("interrupted" in p["message"] for p in run.pushes()), 5)


SCENARIOS = [
    setup_through_the_frontend_api,
    calm_baseline,
    message_flood,
    crying_chain,
    frigate_outage,
    broker_restart,
    ai_assessment,
    breathing_hint_with_radar,
    vital_engine,
    smoke_and_internet,
    reports_and_diagnostics,
    restart,
]


async def main(long: bool, only: list[str]) -> int:
    with tempfile.TemporaryDirectory(prefix="checkbaby-lab-") as temporary:
        run = Run(Path(temporary), long)
        labkit.prepare_config(run.root)
        run.broker.start()
        started = time.monotonic()
        try:
            await run.start_home_assistant()
            run.sim = FrigateSim("127.0.0.1", run.broker.port)
            for scenario in SCENARIOS:
                # Setup and the calm baseline always run; the rest can be picked.
                if only and scenario.__name__ not in only and scenario not in SCENARIOS[:2]:
                    continue
                print(f"\n== {scenario.__name__.replace('_', ' ')}", flush=True)
                if scenario is calm_baseline:
                    run.sim.start()
                try:
                    await scenario(run)
                except Exception as error:  # noqa: BLE001 - one broken scenario must not hide the others
                    run.check(f"{scenario.__name__} ran to the end", False, f"{type(error).__name__}: {error}")
                    traceback.print_exc()
                    if run.hass is not None:
                        site = getattr(run.hass.http, "site", None)
                        server = getattr(site, "_server", None)
                        print(
                            f"      Home Assistant state={run.hass.state} http site={site is not None} "
                            f"serving={server.is_serving() if server is not None else None}",
                            flush=True,
                        )
        finally:
            run.stop_engine()
            if run.sim is not None:
                run.sim.stop()
            await run.stop_home_assistant()
            run.broker.stop()

        failed = [item for item in run.checks if not item["passed"]]
        minutes = (time.monotonic() - started) / 60
        print(f"\n{len(run.checks) - len(failed)} of {len(run.checks)} checks passed in {minutes:.1f} minutes.")
        for item in failed:
            print(f"FAILED: {item['check']}  [{item['detail']}]")
        reports = labkit.LAB / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "latest.json").write_text(json.dumps({"minutes": round(minutes, 1), "checks": run.checks}, indent=2))
        return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--long", action="store_true", help="also wait out a two-minute outage before the restart")
    parser.add_argument("--only", nargs="*", default=[], help="names of scenarios to run after setup")
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(main(arguments.long, arguments.only)))
