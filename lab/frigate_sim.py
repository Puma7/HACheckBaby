"""A stand-in for Frigate: publishes the MQTT topics CheckBaby reads.

It speaks to a real broker in the way the Frigate documentation describes:
`frigate/available`, and per camera `audio/dBFS`, `audio/rms`, `audio/<label>`
and `motion`. Whether a real Frigate behaves exactly like this is what the
hardware checklist is for; the lab can only be as right as this file.

Interactive use against a running lab broker:

    python lab/frigate_sim.py --port 1883

then type commands such as `cry on`, `cry off`, `scream on`, `motion on`,
`level -20`, `quiet`, `sound`, `offline`, `online`, `person 1`, `pet 1`, `exit`.
"""

from __future__ import annotations

import argparse
import math
import random
import threading
import time

import paho.mqtt.client as mqtt


class FrigateSim:
    """Publishes what Frigate would publish for one camera."""

    def __init__(
        self, host: str, port: int, *, camera: str = "nursery", prefix: str = "frigate", zone: str = "bed"
    ) -> None:
        """Prepare the client; nothing is sent before start()."""
        self.camera = camera
        self.prefix = prefix
        self.zone = zone
        self.level = -50.0
        self.rate_hz = 2.0
        self._host = host
        self._port = port
        self._sound = True
        self._online = True
        self._stop = threading.Event()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"frigate-sim-{camera}")
        self._client.will_set(f"{prefix}/available", "offline", retain=True)
        self._client.on_connect = self._on_connect
        self._client.reconnect_delay_set(min_delay=1, max_delay=3)
        self._thread = threading.Thread(target=self._levels, daemon=True)

    def _on_connect(self, client: mqtt.Client, *args: object) -> None:
        # Also after a broker restart: say again that Frigate is there.
        if self._online:
            client.publish(f"{self.prefix}/available", "online", retain=True)

    def start(self) -> None:
        """Connect and begin publishing sound levels."""
        self._client.connect(self._host, self._port, keepalive=10)
        self._client.loop_start()
        self._thread.start()

    def stop(self) -> None:
        """Say goodbye like a clean Frigate shutdown."""
        self._stop.set()
        self._client.publish(f"{self.prefix}/available", "offline", retain=True).wait_for_publish(2)
        self._client.loop_stop()
        self._client.disconnect()

    def _topic(self, suffix: str) -> str:
        return f"{self.prefix}/{self.camera}/{suffix}"

    def _levels(self) -> None:
        while not self._stop.is_set():
            if self._sound and self._online:
                dbfs = self.level + random.uniform(-0.6, 0.6)
                rms = 32768.0 * math.pow(10.0, dbfs / 20.0)
                self._client.publish(self._topic("audio/dBFS"), f"{dbfs:.2f}")
                self._client.publish(self._topic("audio/rms"), f"{rms:.2f}")
            time.sleep(1.0 / self.rate_hz)

    # -- what a scenario can do ---------------------------------------------

    def cry(self, on: bool) -> None:
        """Frigate hears (or stops hearing) crying; the level follows."""
        self.level = -18.0 if on else -50.0
        self._client.publish(self._topic("audio/crying"), "ON" if on else "OFF")

    def scream(self, on: bool) -> None:
        """Frigate hears (or stops hearing) a scream."""
        self.level = -10.0 if on else -50.0
        self._client.publish(self._topic("audio/scream"), "ON" if on else "OFF")

    def motion(self, on: bool) -> None:
        """Frigate sees (or stops seeing) motion."""
        self._client.publish(self._topic("motion"), "ON" if on else "OFF")

    def person(self, count: int) -> None:
        """Frigate counts persons in the camera view."""
        self._client.publish(self._topic("person"), str(count))

    def pet(self, count: int, label: str = "cat") -> None:
        """Frigate counts cats or dogs in the bed zone."""
        self._client.publish(f"{self.prefix}/{self.zone}/{label}", str(count))

    def sound(self, on: bool) -> None:
        """The camera delivers (or stops delivering) audio."""
        self._sound = on

    def online(self, on: bool) -> None:
        """Frigate goes down or comes back."""
        self._online = on
        self._client.publish(f"{self.prefix}/available", "online" if on else "offline", retain=True)


def _interactive() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--camera", default="nursery")
    args = parser.parse_args()
    sim = FrigateSim(args.host, args.port, camera=args.camera)
    sim.start()
    print(f"Frigate stand-in for camera '{args.camera}' on {args.host}:{args.port}. Type a command, or 'exit'.")
    switches = {"cry": sim.cry, "scream": sim.scream, "motion": sim.motion}
    try:
        while True:
            words = input("> ").split()
            if not words:
                continue
            command, value = words[0], (words[1] if len(words) > 1 else "")
            if command == "exit":
                break
            if command in switches:
                switches[command](value == "on")
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
            else:
                print("Commands: cry on|off, scream on|off, motion on|off, level <dBFS>, quiet, sound, "
                      "offline, online, person <n>, pet <n>, exit")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    _interactive()
