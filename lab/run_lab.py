"""An interactive lab: a real Home Assistant with CheckBaby set up, and a console to play events.

    python lab/run_lab.py

Opens Home Assistant on http://127.0.0.1:8123 (create a user on first start),
with a child "Baby", the dashboard "CheckBaby" in the sidebar, and a console in
this terminal: `cry on`, `breath 0`, `door open`, `ai risky`, `tap seen`, `help`.
Everything is kept in lab/runtime; delete that folder to start over.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from check_lab import CHILD, OPTIONS, PLACE
from frigate_sim import FrigateSim
import labkit

HELP = """Commands
  cry on|off        scream on|off      motion on|off     level <dBFS>
  quiet | sound     the camera stops / resumes delivering audio
  offline | online  Frigate goes down / comes back
  person <n>        pet <n>            (camera view / bed zone)
  breath <n>|none   heart <n>|none     temp <°C>
  door open|closed  bed in|out         smoke on|off      internet on|off
  ai ok|risky|prone|error              what the simulated AI answers next
  tap seen|quiet    a parent taps the button on the notification
  monitor on|off    the switch "Monitoring"
  status            what CheckBaby sees right now
  pushes            the notifications the simulated phones received
  exit"""


async def _flow(hass: Any, domain: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(domain, context={"source": "user"})
    for step in steps:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], step)
    return dict(result)


async def _ensure_setup(hass: Any, broker_port: int) -> str:
    """Create the MQTT and CheckBaby entries on first start, through their real config flows."""
    if not hass.config_entries.async_entries("mqtt"):
        await _flow(
            hass,
            "mqtt",
            [{"broker": "127.0.0.1", "port": broker_port, "other_settings": {"set_client_cert": False, "set_ca_cert": "off"}}],
        )
    entries = hass.config_entries.async_entries("checkbaby")
    if not entries:
        result = await _flow(
            hass,
            "checkbaby",
            [
                {"child_name": CHILD, "birth_date": "2027-02-14"},
                PLACE,
                {"notify_services": OPTIONS["notify_services"], "local_alarm_entities": OPTIONS["local_alarm_entities"]},
                {"acknowledged": True},
            ],
        )
        entry = result["result"]
        hass.config_entries.async_update_entry(entry, options=OPTIONS)
        await hass.async_block_till_done()
        return str(entry.entry_id)
    return str(entries[0].entry_id)


async def _command(hass: Any, sim: FrigateSim, entry_id: str, line: str) -> bool:
    """Carry out one console command. Returns False to stop."""
    words = line.split()
    if not words:
        return True
    command, value = words[0], (words[1] if len(words) > 1 else "")
    on = value in ("on", "open", "in")
    world = hass.data["checkbaby_lab"]

    async def lab(service: str, data: dict[str, Any]) -> None:
        await hass.services.async_call("checkbaby_lab", service, data, blocking=True)

    def number(text: str) -> float | None:
        return None if text == "none" else float(text)

    if command == "exit":
        return False
    if command in ("cry", "scream", "motion"):
        getattr(sim, command)(value == "on")
    elif command == "level":
        sim.level = float(value)
    elif command in ("quiet", "sound"):
        sim.sound(command == "sound")
    elif command in ("offline", "online"):
        sim.online(command == "online")
    elif command == "person":
        sim.person(int(value))
    elif command == "pet":
        sim.pet(int(value))
    elif command in ("breath", "heart", "temp"):
        key = {"breath": "breath_rate", "heart": "heart_rate", "temp": "temperature"}[command]
        await lab("set", {key: number(value)})
    elif command in ("door", "bed", "smoke", "internet"):
        await lab("set", {{"bed": "presence"}.get(command, command): on})
    elif command == "ai":
        fields = {"risky": {"airway_risk": "likely", "assessment": "critical"}, "prone": {"position": "prone"}}
        mode = "error" if value == "error" else "answer"
        await lab("ai", {"mode": mode, "fields": fields.get(value, {})})
    elif command == "tap":
        await lab("tap", {"button": value, "entry_id": entry_id})
    elif command == "monitor":
        coordinator = hass.config_entries.async_get_entry(entry_id).runtime_data.coordinator
        await coordinator.async_set_setting("armed", value == "on")
    elif command == "status":
        monitor = hass.config_entries.async_get_entry(entry_id).runtime_data.coordinator.monitor
        alerts = {kind.value: alert.level.name.lower() for kind, alert in monitor.alerts.active.items()}
        print(f"state: {monitor.state.value}   alerts: {alerts or 'none'}   problems: {monitor.problems or 'none'}")
    elif command == "pushes":
        for push in world.real_pushes()[-10:]:
            print(f"  {push['phone']}: {push['title']} | {push['message']}")
    else:
        print(HELP)
    return True


async def main(http_port: int, broker_port: int) -> None:
    labkit.RUNTIME.mkdir(exist_ok=True)
    labkit.prepare_config(labkit.RUNTIME)
    broker = labkit.Broker(broker_port, labkit.RUNTIME / "broker")
    broker.start()
    hass = await labkit.boot(labkit.RUNTIME, http_port, frontend=True)
    sim = FrigateSim("127.0.0.1", broker_port)
    try:
        entry_id = await _ensure_setup(hass, broker_port)
        sim.start()
        print(f"\nHome Assistant: http://127.0.0.1:{http_port}  (first start: create a user)")
        print(f"MQTT broker:    127.0.0.1:{broker_port}")
        print('The child "Baby" is set up. Switch "Monitoring" on, then try: cry on\n')
        print(HELP)
        loop = asyncio.get_running_loop()
        while True:
            try:
                line = await loop.run_in_executor(None, input, "lab> ")
            except (EOFError, KeyboardInterrupt):
                break
            try:
                if not await _command(hass, sim, entry_id, line):
                    break
            except Exception as error:  # noqa: BLE001 - a typo must not end the lab
                print(f"{type(error).__name__}: {error}")
    finally:
        sim.stop()
        hass.lab_stopping = True
        await hass.async_stop()
        broker.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8123, help="port of Home Assistant")
    parser.add_argument("--broker-port", type=int, default=18830, help="port of the lab's MQTT broker")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.port, arguments.broker_port))
