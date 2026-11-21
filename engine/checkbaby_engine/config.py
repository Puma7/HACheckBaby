"""Configuration from a YAML/JSON file and environment variables.

File, environment and the Home Assistant add-on options all use the same flat
keys (see ``DEFAULTS``). Environment variables are the key in upper case with
the prefix ``CHECKBABY_`` and win over the file.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .signal import SignalConfig

ENV_PREFIX = "CHECKBABY_"
ADDON_OPTIONS = Path("/data/options.json")  # written by the Home Assistant Supervisor

_SIGNAL_KEYS = tuple(f.name for f in dataclasses.fields(SignalConfig))

DEFAULTS: dict[str, str | int | float] = {
    "rtsp_url": "",
    "engine_id": "nursery",
    "roi_x": 0.0,
    "roi_y": 0.0,
    "roi_w": 1.0,
    "roi_h": 1.0,
    "fps": 8.0,
    "frame_width": 64,
    "mqtt_host": "localhost",
    "mqtt_port": 1883,
    "mqtt_username": "",
    "mqtt_password": "",
    "topic_prefix": "checkbaby/engine",
    "publish_interval_s": 2.0,
    "log_level": "INFO",
    **{key: getattr(SignalConfig(), key) for key in _SIGNAL_KEYS},
}


class ConfigError(ValueError):
    """The configuration is missing something or does not make sense."""


@dataclass(frozen=True)
class Roi:
    """Region of interest as fractions of the picture, origin top left."""

    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0


@dataclass(frozen=True)
class MqttConfig:
    host: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = field(default="", repr=False)
    topic_prefix: str = "checkbaby/engine"
    publish_interval_s: float = 2.0


@dataclass(frozen=True)
class Config:
    rtsp_url: str = field(repr=False)
    engine_id: str = "nursery"
    roi: Roi = Roi()
    fps: float = 8.0
    frame_width: int = 64
    mqtt: MqttConfig = MqttConfig()
    signal: SignalConfig = SignalConfig()
    log_level: str = "INFO"

    def describe(self) -> str:
        """One line for the start-up log, without credentials."""
        user = self.mqtt.username or "-"
        return (
            f"engine_id={self.engine_id} source={mask_url(self.rtsp_url)} roi={self.roi} "
            f"fps={self.fps:g} frame_width={self.frame_width} "
            f"mqtt={self.mqtt.host}:{self.mqtt.port} user={user} prefix={self.mqtt.topic_prefix}"
        )


def mask_url(url: str) -> str:
    """Hide the password (and any query string) of a URL for logging.

    Errs on the side of hiding too much: everything up to the last ``@`` counts
    as credentials, so passwords containing ``@`` or ``/`` are covered too.
    """
    head, sep, rest = url.partition("://")
    if not sep:
        head, rest = "", url
    rest, query, _ = rest.partition("?")
    creds, at, location = rest.rpartition("@")
    if at:
        user, colon, _ = creds.partition(":")
        rest = f"{user}:***@{location}" if colon else f"***@{location}"
    return head + sep + rest + ("?***" if query else "")


def load_config(path: str | None = None, env: Mapping[str, str] | None = None) -> Config:
    """Build the configuration from an optional file plus the environment."""
    environ = os.environ if env is None else env
    file_path = path or environ.get(ENV_PREFIX + "CONFIG")
    if file_path is None and ADDON_OPTIONS.is_file():
        file_path = str(ADDON_OPTIONS)
    raw: dict[str, object] = dict(DEFAULTS)
    if file_path:
        raw.update(_read_file(Path(file_path)))
    for key in DEFAULTS:
        if (value := environ.get(ENV_PREFIX + key.upper())) is not None:
            raw[key] = value
    values = {key: _coerce(key, raw[key]) for key in DEFAULTS}
    signal = SignalConfig(**{key: values[key] for key in _SIGNAL_KEYS})  # type: ignore[arg-type]
    config = Config(
        rtsp_url=str(values["rtsp_url"]),
        engine_id=str(values["engine_id"]),
        roi=Roi(*(float(values[key]) for key in ("roi_x", "roi_y", "roi_w", "roi_h"))),
        fps=float(values["fps"]),
        frame_width=int(values["frame_width"]),
        mqtt=MqttConfig(
            host=str(values["mqtt_host"]),
            port=int(values["mqtt_port"]),
            username=str(values["mqtt_username"]),
            password=str(values["mqtt_password"]),
            topic_prefix=str(values["topic_prefix"]),
            publish_interval_s=float(values["publish_interval_s"]),
        ),
        signal=signal,
        log_level=str(values["log_level"]).upper(),
    )
    _validate(config)
    return config


def _read_file(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (OSError, ValueError, yaml.YAMLError) as err:
        # Only the error type: a parser message may quote the offending line.
        raise ConfigError(f"cannot read config file {path}: {type(err).__name__}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"config file {path} must contain a mapping of keys to values")
    unknown = sorted(str(key) for key in data if key not in DEFAULTS)
    if unknown:
        raise ConfigError(f"unknown config keys in {path}: {', '.join(unknown)}")
    return {str(key): value for key, value in data.items() if value is not None}


def _coerce(key: str, value: object) -> str | int | float:
    """Convert a file or environment value to the type of the key's default."""
    kind = type(DEFAULTS[key])
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError
        if kind is str:
            return str(value)
        number = float(value)
        if kind is int:
            if number != int(number):
                raise ValueError
            return int(number)
        return number
    except ValueError:
        # The value itself is not shown: it could be a secret in the wrong field.
        raise ConfigError(f"{key}: expected {kind.__name__}") from None


def _validate(config: Config) -> None:
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ConfigError(message)

    roi, mqtt, signal = config.roi, config.mqtt, config.signal
    require(bool(config.rtsp_url), "rtsp_url is required (set CHECKBABY_RTSP_URL)")
    require(
        re.fullmatch(r"[A-Za-z0-9_-]{1,64}", config.engine_id) is not None,
        "engine_id may only contain letters, digits, '_' and '-'",
    )
    require(
        0.0 <= roi.x < 1.0 and 0.0 <= roi.y < 1.0 and roi.w > 0.0 and roi.h > 0.0,
        "roi must lie inside the picture and have a size",
    )
    require(
        roi.x + roi.w <= 1.0 + 1e-9 and roi.y + roi.h <= 1.0 + 1e-9,
        "roi must not reach beyond the picture (x + w <= 1, y + h <= 1)",
    )
    require(5.0 <= config.fps <= 30.0, "fps must be between 5 and 30")
    require(16 <= config.frame_width <= 320, "frame_width must be between 16 and 320")
    require(bool(mqtt.host), "mqtt_host is required")
    require(1 <= mqtt.port <= 65535, "mqtt_port must be between 1 and 65535")
    require(
        re.fullmatch(r"[^/+#\s]+(/[^/+#\s]+)*", mqtt.topic_prefix) is not None,
        "topic_prefix must be a plain topic without wildcards or outer slashes",
    )
    require(0.5 <= mqtt.publish_interval_s <= 60.0, "publish_interval_s must be 0.5..60")
    require(
        config.log_level in ("DEBUG", "INFO", "WARNING", "ERROR"),
        "log_level must be DEBUG, INFO, WARNING or ERROR",
    )
    require(0.0 < signal.band_low_hz < signal.band_high_hz, "band_low_hz must be below band_high_hz")
    require(
        signal.min_fps > 2.0 * signal.band_high_hz,
        "min_fps must be more than twice band_high_hz",
    )
    require(
        3.0 / signal.band_low_hz <= signal.min_window_s <= signal.window_s,
        "min_window_s must cover three of the slowest breaths and not exceed window_s",
    )
    require(0.0 < signal.periodic_confidence <= 1.0, "periodic_confidence must be in (0, 1]")
    require(signal.grid >= 2, "grid must be at least 2")
    require(
        min(signal.max_gap_s, signal.stale_after_s, signal.frozen_after_s, signal.motion_lag_s) > 0.0,
        "max_gap_s, stale_after_s, frozen_after_s and motion_lag_s must be positive",
    )
