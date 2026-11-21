"""Constants for the CheckBaby integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "checkbaby"

# Config entry data: the child.
CONF_CHILD_NAME: Final = "child_name"
CONF_BIRTH_DATE: Final = "birth_date"
CONF_ACKNOWLEDGED: Final = "acknowledged"

# Config entry options: who is told, and what else is connected.
CONF_NOTIFY_SERVICES: Final = "notify_services"
CONF_BABYSITTER_SERVICE: Final = "babysitter_service"
CONF_LOCAL_ALARM: Final = "local_alarm_entities"
CONF_HEARTBEAT_BUTTONS: Final = "heartbeat_buttons"
CONF_AI_ENTITIES: Final = "ai_task_entities"
CONF_AI_CONSENT: Final = "ai_consent"
CONF_AI_BUDGET: Final = "ai_calls_per_hour"
CONF_VOX_PLAYER: Final = "vox_media_player"
CONF_INTERNET_ENTITY: Final = "internet_entity"
CONF_SMOKE_ENTITIES: Final = "smoke_entities"
CONF_TOPIC_PREFIX: Final = "frigate_topic_prefix"
CONF_DASHBOARD_PATH: Final = "dashboard_path"

# Sub-entry data: one sleep place.
SUBENTRY_PLACE: Final = "sleep_place"
CONF_PLACE_NAME: Final = "name"
CONF_FRIGATE_CAMERA: Final = "frigate_camera"
CONF_CAMERA_ENTITY: Final = "camera_entity"
CONF_BED_ZONE: Final = "bed_zone"
CONF_PERSON_IS_CAREGIVER: Final = "person_is_caregiver"
CONF_PRESENCE_ENTITY: Final = "presence_entity"
CONF_DOOR_ENTITY: Final = "door_entity"
CONF_TEMPERATURE_ENTITY: Final = "temperature_entity"
CONF_HUMIDITY_ENTITY: Final = "humidity_entity"
CONF_BREATH_RATE_ENTITY: Final = "breath_rate_entity"
CONF_HEART_RATE_ENTITY: Final = "heart_rate_entity"
CONF_ENGINE_ID: Final = "engine_id"
CONF_AUDIO_URL: Final = "audio_stream_url"
CONF_CRY_ENTITY: Final = "cry_entity"
CONF_MOTION_ENTITY: Final = "motion_entity"
CONF_LEVEL_ENTITY: Final = "level_entity"

DEFAULT_TOPIC_PREFIX: Final = "frigate"
DEFAULT_ENGINE_PREFIX: Final = "checkbaby/engine"
DEFAULT_DASHBOARD_PATH: Final = "/lovelace"
DEFAULT_AI_BUDGET: Final = 30

TICK_SECONDS: Final = 2
HEARTBEAT_SECONDS: Final = 30
AI_TIMEOUT_SECONDS: Final = 20
SNOOZE_SECONDS: Final = 300
# A gap this long in the stored "last alive" time counts as an interruption.
INTERRUPTION_SECONDS: Final = 120

# Names of the watchdog sources.
SOURCE_MQTT: Final = "mqtt"
SOURCE_FRIGATE: Final = "frigate"
SOURCE_AUDIO: Final = "audio_level"
SOURCE_CAMERA: Final = "camera"
SOURCE_ENGINE: Final = "engine"
SOURCE_VITAL_SENSOR: Final = "vital_sensor"
SOURCE_NOTIFY: Final = "notify"

VITAL_VIDEO: Final = "video"
VITAL_RADAR: Final = "radar"

ACTION_ACK: Final = "CHECKBABY_ACK"
ACTION_SNOOZE: Final = "CHECKBABY_SNOOZE"

PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
