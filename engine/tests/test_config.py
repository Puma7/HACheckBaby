"""Configuration loading and the rule that credentials never reach a log line."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import yaml

from checkbaby_engine import config as config_module
from checkbaby_engine.config import DEFAULTS, Config, ConfigError, Roi, load_config, mask_url, redact
from checkbaby_engine.signal import SignalConfig

ENGINE_DIR = Path(__file__).resolve().parent.parent
SECRET_URL = "rtsp://viewer:c4m-s3cr3t@192.168.1.20:554/stream2"
ENV = {"CHECKBABY_RTSP_URL": SECRET_URL, "CHECKBABY_MQTT_PASSWORD": "mqtt-s3cr3t"}


@pytest.fixture(autouse=True)
def no_addon_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config_module, "ADDON_OPTIONS", tmp_path / "no-options.json")


def test_defaults_with_only_the_url_set() -> None:
    config = load_config(env={"CHECKBABY_RTSP_URL": "rtsp://cam/sub"})
    assert config.rtsp_url == "rtsp://cam/sub"
    assert (config.engine_id, config.fps, config.frame_width) == ("nursery", 8.0, 64)
    assert config.roi == Roi(0.0, 0.0, 1.0, 1.0)
    assert (config.mqtt.host, config.mqtt.port) == ("localhost", 1883)
    assert (config.mqtt.topic_prefix, config.mqtt.publish_interval_s) == ("checkbaby/engine", 2.0)
    assert config.signal == SignalConfig()
    assert (config.signal.band_low_hz, config.signal.band_high_hz) == (0.3, 1.5)
    assert 20.0 <= config.signal.window_s <= 30.0


def test_environment_values_are_converted() -> None:
    config = load_config(
        env={
            **ENV,
            "CHECKBABY_ENGINE_ID": "bed_2",
            "CHECKBABY_ROI_X": "0.25", "CHECKBABY_ROI_Y": "0.3", "CHECKBABY_ROI_W": "0.5", "CHECKBABY_ROI_H": "0.4",
            "CHECKBABY_FPS": "10",
            "CHECKBABY_MQTT_HOST": "broker", "CHECKBABY_MQTT_PORT": "8883", "CHECKBABY_MQTT_USERNAME": "cb",
            "CHECKBABY_TOPIC_PREFIX": "home/checkbaby",
            "CHECKBABY_PERIODIC_CONFIDENCE": "0.45", "CHECKBABY_GRID": "6", "CHECKBABY_LOG_LEVEL": "debug",
        }
    )
    assert config.engine_id == "bed_2" and config.roi == Roi(0.25, 0.3, 0.5, 0.4) and config.fps == 10.0
    assert (config.mqtt.host, config.mqtt.port, config.mqtt.username) == ("broker", 8883, "cb")
    assert config.mqtt.password == "mqtt-s3cr3t" and config.mqtt.topic_prefix == "home/checkbaby"
    assert config.signal.periodic_confidence == 0.45 and config.signal.grid == 6
    assert isinstance(config.signal.grid, int) and isinstance(config.mqtt.port, int)
    assert config.log_level == "DEBUG"


@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_file_is_read_and_environment_wins(tmp_path: Path, suffix: str) -> None:
    data = {"rtsp_url": "rtsp://file/sub", "engine_id": "from_file", "fps": 6, "roi_w": 0.5, "mqtt_port": 1884}
    path = tmp_path / f"engine{suffix}"
    path.write_text(json.dumps(data) if suffix == ".json" else yaml.safe_dump(data))
    config = load_config(str(path), env={})
    assert (config.rtsp_url, config.engine_id, config.fps, config.roi.w, config.mqtt.port) == (
        "rtsp://file/sub", "from_file", 6.0, 0.5, 1884,
    )
    # The same file through $CHECKBABY_CONFIG, with one value overridden.
    config = load_config(env={"CHECKBABY_CONFIG": str(path), "CHECKBABY_ENGINE_ID": "from_env"})
    assert (config.engine_id, config.fps) == ("from_env", 6.0)


def test_addon_options_file_is_used_when_nothing_else_is_given(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    options = tmp_path / "options.json"
    options.write_text(json.dumps({"rtsp_url": "rtsp://addon/sub", "mqtt_host": "core-mosquitto"}))
    monkeypatch.setattr(config_module, "ADDON_OPTIONS", options)
    config = load_config(env={})
    assert (config.rtsp_url, config.mqtt.host) == ("rtsp://addon/sub", "core-mosquitto")


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({}, "rtsp_url is required"),
        ({"CHECKBABY_ENGINE_ID": "a/b"}, "engine_id"),
        ({"CHECKBABY_ENGINE_ID": "a+#"}, "engine_id"),
        ({"CHECKBABY_ROI_X": "0.8", "CHECKBABY_ROI_W": "0.5"}, "roi"),
        ({"CHECKBABY_ROI_H": "0"}, "roi"),
        ({"CHECKBABY_ROI_Y": "-0.1"}, "roi"),
        ({"CHECKBABY_FPS": "2"}, "fps"),
        ({"CHECKBABY_FPS": "fast"}, "fps: expected float"),
        ({"CHECKBABY_MQTT_PORT": "70000"}, "mqtt_port"),
        ({"CHECKBABY_MQTT_PORT": "18.5"}, "mqtt_port: expected int"),
        ({"CHECKBABY_TOPIC_PREFIX": "checkbaby/#"}, "topic_prefix"),
        ({"CHECKBABY_TOPIC_PREFIX": "/checkbaby"}, "topic_prefix"),
        ({"CHECKBABY_MIN_WINDOW_S": "40"}, "min_window_s"),
        ({"CHECKBABY_MIN_WINDOW_S": "5"}, "min_window_s"),
        ({"CHECKBABY_MIN_FPS": "2.5"}, "min_fps"),
        ({"CHECKBABY_LOG_LEVEL": "LOUD"}, "log_level"),
    ],
)
def test_invalid_settings_are_rejected(env: dict[str, str], message: str) -> None:
    base = {} if not env else {"CHECKBABY_RTSP_URL": "rtsp://cam/sub"}
    with pytest.raises(ConfigError, match=message):
        load_config(env={**base, **env})


def test_file_problems_are_reported(tmp_path: Path) -> None:
    typo = tmp_path / "typo.yaml"
    typo.write_text("rtsp_url: rtsp://cam/sub\nmqtt_pasword: hunter2\n")
    with pytest.raises(ConfigError, match="unknown config keys.*mqtt_pasword") as caught:
        load_config(str(typo), env={})
    assert "hunter2" not in str(caught.value)
    broken = tmp_path / "broken.yaml"
    broken.write_text("mqtt_password: [hunter2\n")
    with pytest.raises(ConfigError, match="cannot read config file") as caught:
        load_config(str(broken), env={})
    assert "hunter2" not in str(caught.value)
    with pytest.raises(ConfigError, match="cannot read config file"):
        load_config(str(tmp_path / "missing.yaml"), env={})
    listing = tmp_path / "list.yaml"
    listing.write_text("- a\n- b\n")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(str(listing), env={})


def test_a_secret_in_the_wrong_field_is_not_echoed() -> None:
    with pytest.raises(ConfigError) as caught:
        load_config(env={"CHECKBABY_RTSP_URL": "rtsp://cam/sub", "CHECKBABY_MQTT_PORT": "hunter2"})
    assert "hunter2" not in str(caught.value)


# --- credentials --------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "masked"),
    [
        ("rtsp://viewer:c4m-s3cr3t@192.168.1.20:554/stream2", "rtsp://viewer:***@192.168.1.20:554/stream2"),
        ("rtsp://admin:p@ss/w:rd@cam.local/live", "rtsp://admin:***@cam.local/live"),
        ("rtsp://t0ken-only@cam.local/live", "rtsp://***@cam.local/live"),
        ("rtsp://cam.local:8554/nursery_sub", "rtsp://cam.local:8554/nursery_sub"),
        ("rtsp://cam.local/live?user=admin&password=hunter2", "rtsp://cam.local/live?***"),
        ("rtsp://u:pw@cam/live?token=abc", "rtsp://u:***@cam/live?***"),
        ("u:pw@cam/live", "u:***@cam/live"),
        ("synthetic://40", "synthetic://40"),
        ("", ""),
    ],
)
def test_mask_url(url: str, masked: str) -> None:
    assert mask_url(url) == masked
    for secret in ("c4m-s3cr3t", "p@ss/w:rd", "t0ken-only", "hunter2", "pw", "abc"):
        assert secret not in mask_url(url)


def test_redact_removes_a_urls_secrets_from_other_text() -> None:
    url = "rtsp://viewer:c4m-s3cr3t@cam/live?token=abc123"
    text = f"open '{url}' failed: bad password c4m-s3cr3t, query token=abc123"
    assert redact(text, url) == "open 'rtsp://viewer:***@cam/live?***' failed: bad password ***, query ***"
    assert redact("401 for t0ken", "rtsp://t0ken@cam/live") == "401 for ***"
    assert redact("nothing secret here", "rtsp://cam/live") == "nothing secret here"


def test_config_never_shows_credentials() -> None:
    config = load_config(env={**ENV, "CHECKBABY_MQTT_USERNAME": "cb"})
    for text in (repr(config), str(config), repr(config.mqtt), config.describe(), f"{config}"):
        assert "c4m-s3cr3t" not in text and "mqtt-s3cr3t" not in text
    assert "rtsp://viewer:***@192.168.1.20:554/stream2" in config.describe()
    assert "user=cb" in config.describe()
    # The values themselves are intact for the code that needs them.
    assert config.rtsp_url == SECRET_URL and config.mqtt.password == "mqtt-s3cr3t"


def test_startup_log_line_is_free_of_credentials(caplog: pytest.LogCaptureFixture) -> None:
    config = load_config(env=ENV)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("checkbaby_engine").info("starting: %s", config.describe())
        logging.getLogger("checkbaby_engine").debug("config: %r", config)
    assert "starting: engine_id=nursery" in caplog.text
    assert "c4m-s3cr3t" not in caplog.text and "mqtt-s3cr3t" not in caplog.text


# --- the packaging files agree with the loader --------------------------------


def test_addon_manifest_matches_the_loader() -> None:
    manifest = yaml.safe_load((ENGINE_DIR / "config.yaml").read_text())
    assert (manifest["name"], manifest["slug"]) == ("CheckBaby Vital Engine", "checkbaby_engine")
    assert manifest["arch"] and set(manifest["arch"]) <= {"amd64", "aarch64", "armv7", "armhf", "i386"}
    options, schema = manifest["options"], manifest["schema"]
    assert set(options) <= set(schema) <= set(DEFAULTS)
    assert {"rtsp_url", "engine_id", "roi_x", "roi_y", "roi_w", "roi_h", "fps"} <= set(options)
    assert {"mqtt_host", "mqtt_port", "mqtt_username", "mqtt_password"} <= set(options)
    assert schema["mqtt_password"].startswith("password")
    # The add-on defaults are a configuration the engine accepts as it stands.
    assert isinstance(load_config_from(options), Config)


def load_config_from(options: dict[str, object]) -> Config:
    return load_config(env={f"CHECKBABY_{key.upper()}": str(value) for key, value in options.items()})


def test_compose_example_uses_known_settings_and_no_inline_password() -> None:
    compose = yaml.safe_load((ENGINE_DIR / "compose.example.yaml").read_text())
    (service,) = compose["services"].values()
    env: dict[str, str] = service["environment"]
    assert env and all(key.removeprefix("CHECKBABY_").lower() in DEFAULTS for key in env)
    assert env["CHECKBABY_MQTT_PASSWORD"].startswith("${")  # taken from .env, not written down
    usable = {**env, "CHECKBABY_MQTT_PASSWORD": "x"}
    assert load_config(env=usable).roi == Roi(0.30, 0.35, 0.40, 0.30)


def test_requirements_name_the_runtime_dependencies() -> None:
    lines = (ENGINE_DIR / "requirements.txt").read_text().splitlines()
    names = {line.split(">=")[0].split("<")[0].strip().lower() for line in lines if line and not line.startswith("#")}
    assert names == {"numpy", "av", "paho-mqtt", "pyyaml"}
