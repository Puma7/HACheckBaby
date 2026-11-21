"""Connects the monitor core to Home Assistant: sources in, actions out."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta
import json
import logging
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .ai_policy import Budget
from .ai_schema import INSTRUCTIONS, STRUCTURE, Assessment, parse_assessment
from .alerts import Notification
from .const import (
    ACTION_ACK,
    ACTION_SNOOZE,
    AI_TIMEOUT_SECONDS,
    CONF_AI_BUDGET,
    CONF_AI_CONSENT,
    CONF_AI_ENTITIES,
    CONF_HEARTBEAT_BUTTONS,
    CONF_INTERNET_ENTITY,
    CONF_SMOKE_ENTITIES,
    CONF_TOPIC_PREFIX,
    CONF_VOX_PLAYER,
    DEFAULT_AI_BUDGET,
    DEFAULT_ENGINE_PREFIX,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
    HEARTBEAT_SECONDS,
    INTERRUPTION_SECONDS,
    SNOOZE_SECONDS,
    SOURCE_AUDIO,
    SOURCE_CAMERA,
    SOURCE_CRY_SENSOR,
    SOURCE_ENGINE,
    SOURCE_FRIGATE,
    SOURCE_MQTT,
    SOURCE_NOTIFY,
    SOURCE_PLACE,
    SOURCE_VITAL_SENSOR,
    SUBENTRY_PLACE,
    TICK_SECONDS,
    VITAL_RADAR,
    VITAL_VIDEO,
)
from .models import CheckBabyConfigEntry, SleepPlace
from .monitor import Monitor, Snapshot
from .notifier import Notifier
from .profiles import AgeProfile, profile_for
from .report import night_report, night_report_text, quick_check_text
from .settings import Settings
from .texts import state_name, text
from .types import AlertLevel, ChildState, Stage
from .vox import VoxAction

_LOGGER = logging.getLogger(__name__)

_SOURCES = (
    SOURCE_MQTT,
    SOURCE_FRIGATE,
    SOURCE_AUDIO,
    SOURCE_CAMERA,
    SOURCE_CRY_SENSOR,
    SOURCE_ENGINE,
    SOURCE_PLACE,
    SOURCE_VITAL_SENSOR,
)
_ENGINE_VALID = ("periodic", "gross_motion", "no_motion")
# Entities are told about a new snapshot at least this often, even if nothing changed.
_REFRESH_SECONDS = 60.0
_SAVE_DELAY_SECONDS = 15


class CheckBabyCoordinator(DataUpdateCoordinator[Snapshot]):
    """Feeds one child's monitor and carries out what it decides."""

    config_entry: CheckBabyConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CheckBabyConfigEntry, child_name: str, birth_date: date) -> None:
        """Prepare the monitor; nothing is subscribed until async_start."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} {child_name}")
        self.child_name = child_name
        self.birth_date = birth_date
        self.places: dict[str, SleepPlace] = {
            subentry_id: SleepPlace.from_data(subentry_id, subentry.title, subentry.data)
            for subentry_id, subentry in entry.subentries.items()
            if subentry.subentry_type == SUBENTRY_PLACE
        }
        self.settings = Settings()
        self.monitor = Monitor(self.settings, self._now())
        self.notifier = Notifier(hass, self)
        self.budget = Budget(int(entry.options.get(CONF_AI_BUDGET, DEFAULT_AI_BUDGET)))
        self.heart_rate: float | None = None
        self.alert_listeners: list[Callable[[Notification], None]] = []
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._source_unsubs: list[CALLBACK_TYPE] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._mqtt_expected = False
        self._mqtt_subscribed = False
        self._save_scheduled = False
        self._assessing = False
        self._last_heartbeat = 0.0
        self._last_refresh = 0.0
        self._stopping = False

    # -- small helpers -----------------------------------------------------

    @staticmethod
    def _now() -> float:
        return dt_util.utcnow().timestamp()

    @property
    def profile(self) -> AgeProfile:
        """The age profile for today."""
        return profile_for(self.birth_date, dt_util.now().date())

    @property
    def active_place(self) -> SleepPlace | None:
        """The sleep place that is being monitored."""
        place_id = self.settings.active_place
        return self.places.get(place_id) if place_id else None

    @property
    def language(self) -> str:
        """Language for texts the integration writes itself."""
        return self.hass.config.language

    def _options(self, key: str, default: Any = None) -> Any:
        return self.config_entry.options.get(key, default)

    # -- lifecycle ---------------------------------------------------------

    async def async_start(self) -> None:
        """Load stored state, subscribe to the sources and start the clock."""
        now = self._now()
        stored = await self._store.async_load()
        if stored:
            self.settings = Settings.from_dict(stored.get("settings"))
            self.monitor = Monitor(self.settings, now)
            self.monitor.restore(stored)
            self.notifier.local_on = bool(stored.get("local_alarm_on", False))
        if self.settings.active_place not in self.places:
            self.settings.active_place = next(iter(self.places), None)

        last_alive = stored.get("last_alive") if stored else None
        if self.settings.armed and isinstance(last_alive, (int, float)):
            gap = now - float(last_alive)
            if gap >= INTERRUPTION_SECONDS:
                self.monitor.report_interruption(gap, now)

        await self._async_subscribe_sources()
        self._unsubs.append(
            async_track_time_interval(self.hass, self._handle_tick, timedelta(seconds=TICK_SECONDS))
        )
        self._unsubs.append(self.hass.bus.async_listen("mobile_app_notification_action", self._handle_action))
        self._unsubs.append(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._handle_stop))
        self._update_issues()
        self.async_refresh_now()

    async def async_stop(self) -> None:
        """Unsubscribe everything and save."""
        self._stopping = True
        for unsub in (*self._unsubs, *self._source_unsubs):
            unsub()
        self._unsubs.clear()
        self._source_unsubs.clear()
        await self._store.async_save(self._data_to_save())

    def _data_to_save(self) -> dict[str, Any]:
        self._save_scheduled = False
        return {**self.monitor.to_dict(), "last_alive": self._now(), "local_alarm_on": self.notifier.local_on}

    def _schedule_save(self) -> None:
        """Save soon. A pending save is left alone: rescheduling it on every tick would postpone it forever."""
        if not self._save_scheduled:
            self._save_scheduled = True
            self._store.async_delay_save(self._data_to_save, _SAVE_DELAY_SECONDS)

    def _update_issues(self) -> None:
        entry_id = self.config_entry.entry_id
        placeholders = {"child": self.child_name}
        checks = {
            "no_alert_target": not self.notifier.has_target(),
            "no_sleep_place": not self.places,
            "mqtt_missing": self._mqtt_expected and not self._mqtt_available(),
        }
        for key, broken in checks.items():
            issue_id = f"{key}_{entry_id}"
            if broken:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key=key,
                    translation_placeholders=placeholders,
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    # -- sources -----------------------------------------------------------

    def _mqtt_available(self) -> bool:
        return self.hass.config_entries.async_loaded_entries("mqtt") != []

    async def _async_subscribe_sources(self) -> None:
        """(Re)subscribe to everything the active sleep place provides."""
        for unsub in self._source_unsubs:
            unsub()
        self._source_unsubs.clear()
        watchdog = self.monitor.watchdog
        for name in _SOURCES:
            watchdog.forget(name)
        watchdog.expect(SOURCE_NOTIFY)
        self._mqtt_expected = False
        self._mqtt_subscribed = False
        place = self.active_place
        if place is None:
            # Nothing is being monitored, and the state must say so.
            watchdog.expect(SOURCE_PLACE, core=True)
            watchdog.set_healthy(SOURCE_PLACE, False, self._now())
            return

        watched = [
            entity_id
            for entity_id in (
                place.presence_entity,
                place.door_entity,
                place.cry_entity,
                place.motion_entity,
                self._options(CONF_INTERNET_ENTITY),
                *self._options(CONF_SMOKE_ENTITIES, []),
            )
            if entity_id
        ]
        if watched:
            self._source_unsubs.append(
                async_track_state_change_event(self.hass, watched, self._handle_entity_event)
            )
        if place.camera_entity:
            watchdog.expect(SOURCE_CAMERA)
        if place.breath_rate_entity:
            watchdog.expect(SOURCE_VITAL_SENSOR)
        if not place.frigate_camera:
            if place.level_entity:
                watchdog.expect(SOURCE_AUDIO, core=True)
            if place.cry_entity:
                watchdog.expect(SOURCE_CRY_SENSOR, core=True)

        if not (place.frigate_camera or place.engine_id):
            return
        self._mqtt_expected = True
        watchdog.expect(SOURCE_MQTT, core=bool(place.frigate_camera))
        if place.frigate_camera:
            watchdog.expect(SOURCE_FRIGATE, core=True)
            watchdog.expect(SOURCE_AUDIO, max_age_s=60.0, core=True)
        if place.engine_id:
            watchdog.expect(SOURCE_ENGINE, max_age_s=30.0)
        if not self._mqtt_available():
            return
        from homeassistant.components import mqtt  # noqa: PLC0415 - only needed with MQTT sources

        for topic, handler in self._mqtt_topics(place).items():
            self._source_unsubs.append(await mqtt.async_subscribe(self.hass, topic, self._mqtt_callback(handler)))
        self._mqtt_subscribed = True

    def _mqtt_callback(self, handler: Callable[[str, float], None]) -> Callable[[Any], None]:
        @callback
        def _received(message: Any) -> None:
            handler(str(message.payload), self._now())

        return _received

    def _mqtt_topics(self, place: SleepPlace) -> dict[str, Callable[[str, float], None]]:
        """Topic to handler for the active place."""
        monitor = self.monitor
        signals, watchdog = monitor.signals, monitor.watchdog
        topics: dict[str, Callable[[str, float], None]] = {}

        def flag(setter: Callable[[bool, float], None]) -> Callable[[str, float], None]:
            return lambda payload, now: setter(payload.strip().upper() == "ON", now)

        def count(setter: Callable[[bool, float], None]) -> Callable[[str, float], None]:
            def _handle(payload: str, now: float) -> None:
                try:
                    setter(int(float(payload)) > 0, now)
                except ValueError:
                    return

            return _handle

        def level(payload: str, now: float) -> None:
            try:
                value = float(payload)
            except ValueError:
                return
            signals.set_level(value, self.settings.noise_margin_db, now)
            watchdog.seen(SOURCE_AUDIO, now)

        def engine_state(payload: str, now: float) -> None:
            try:
                data = json.loads(payload)
                status = str(data["status"])
                rate = data.get("rate")
                rate = float(rate) if rate is not None else None
            except (ValueError, TypeError, KeyError):
                return
            signals.set_vital(
                VITAL_VIDEO,
                valid=status in _ENGINE_VALID,
                breathing=status == "periodic",
                moving=status == "gross_motion",
                rate=rate,
                now=now,
            )
            watchdog.seen(SOURCE_ENGINE, now)

        if place.frigate_camera:
            prefix = str(self._options(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)).strip("/")
            camera = f"{prefix}/{place.frigate_camera}"
            topics[f"{prefix}/available"] = lambda payload, now: watchdog.set_healthy(
                SOURCE_FRIGATE, payload.strip().lower() == "online", now
            )
            topics[f"{camera}/audio/crying"] = flag(signals.crying.set)
            topics[f"{camera}/audio/scream"] = flag(signals.scream.set)
            topics[f"{camera}/audio/dBFS"] = level
            topics[f"{camera}/motion"] = flag(monitor.set_motion)
            if place.person_is_caregiver:
                topics[f"{camera}/person"] = count(signals.person.set)
            if place.bed_zone:
                pets: dict[str, bool] = {}

                def pet(animal: str) -> Callable[[bool, float], None]:
                    def _set(present: bool, now: float) -> None:
                        pets[animal] = present
                        signals.pet_in_bed.set(any(pets.values()), now)

                    return _set

                for animal in ("cat", "dog"):
                    topics[f"{prefix}/{place.bed_zone}/{animal}"] = count(pet(animal))
        if place.engine_id:
            engine = f"{DEFAULT_ENGINE_PREFIX}/{place.engine_id}"
            topics[f"{engine}/state"] = engine_state
            topics[f"{engine}/availability"] = lambda payload, now: watchdog.set_healthy(
                SOURCE_ENGINE, payload.strip().lower() == "online", now
            )
        return topics

    def _is_on(self, entity_id: str | None) -> bool | None:
        """True/False for a binary entity, None if it is missing or unavailable."""
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state == STATE_ON

    def _number(self, entity_id: str | None) -> float | None:
        """The numeric state of an entity, None if it has none."""
        state = self.hass.states.get(entity_id) if entity_id else None
        try:
            value = float(state.state) if state is not None else float("nan")
        except ValueError:
            return None
        return value if value == value else None  # NaN is not a reading

    def _poll_entities(self, now: float) -> None:
        """Read the mapped entities into the monitor."""
        monitor = self.monitor
        signals, watchdog = monitor.signals, monitor.watchdog
        place = self.active_place

        smoke = [self._is_on(entity_id) for entity_id in self._options(CONF_SMOKE_ENTITIES, [])]
        signals.smoke.set(any(value is True for value in smoke), now)
        internet_entity = self._options(CONF_INTERNET_ENTITY)
        signals.internet = self._is_on(internet_entity) if internet_entity else None
        missing = self.notifier.missing_services()
        watchdog.set_healthy(SOURCE_NOTIFY, self.notifier.has_target() and not missing, now)
        if self._mqtt_expected:
            watchdog.set_healthy(SOURCE_MQTT, self._mqtt_connected(), now)
        if place is None:
            return

        if place.presence_entity:
            monitor.set_presence(self._is_on(place.presence_entity), now)
        if place.door_entity and (door := self._is_on(place.door_entity)) is not None:
            signals.door_open.set(door, now)
        if place.cry_entity:
            crying = self._is_on(place.cry_entity)
            if crying is not None:
                signals.crying.set(crying, now)
            if not place.frigate_camera:
                watchdog.set_healthy(SOURCE_CRY_SENSOR, crying is not None, now)
        if place.motion_entity and (motion := self._is_on(place.motion_entity)) is not None:
            monitor.set_motion(motion, now)
        if place.level_entity and not place.frigate_camera:
            value = self._number(place.level_entity)
            if value is not None:
                signals.set_level(value, self.settings.noise_margin_db, now)
            watchdog.set_healthy(SOURCE_AUDIO, value is not None, now)
        signals.temperature = self._number(place.temperature_entity)
        signals.humidity = self._number(place.humidity_entity)
        self.heart_rate = self._number(place.heart_rate_entity)
        if place.breath_rate_entity:
            rate = self._number(place.breath_rate_entity)
            signals.set_vital(
                VITAL_RADAR, valid=rate is not None, breathing=bool(rate), moving=False, rate=rate, now=now
            )
            watchdog.set_healthy(SOURCE_VITAL_SENSOR, rate is not None, now)
        if place.camera_entity:
            camera = self.hass.states.get(place.camera_entity)
            watchdog.set_healthy(SOURCE_CAMERA, camera is not None and camera.state != STATE_UNAVAILABLE, now)

    def _mqtt_connected(self) -> bool:
        if not self._mqtt_available():
            return False
        from homeassistant.components import mqtt  # noqa: PLC0415

        return bool(mqtt.is_connected(self.hass))

    # -- the clock ---------------------------------------------------------

    @callback
    def _handle_entity_event(self, event: Event[Any]) -> None:
        self.async_refresh_now()

    @callback
    def _handle_tick(self, moment: datetime) -> None:
        self.async_refresh_now()

    @callback
    def async_refresh_now(self) -> None:
        """Re-evaluate the monitor and carry out what it decided."""
        if self._stopping:
            return
        now = self._now()
        if self._mqtt_expected and not self._mqtt_subscribed and self._mqtt_available():
            # MQTT came up after this entry started: subscribe now.
            self._mqtt_subscribed = True
            self.config_entry.async_create_background_task(
                self.hass, self._async_subscribe_sources(), f"{DOMAIN} subscribe"
            )
        self._poll_entities(now)
        self.monitor.tick(now, self.profile)

        for note in self.monitor.drain_notifications():
            self.config_entry.async_create_background_task(
                self.hass, self.notifier.async_handle(note), f"{DOMAIN} notify {note.kind.value}"
            )
            if note.stage in (Stage.FIRST, Stage.UPGRADE):
                for listener in self.alert_listeners:
                    listener(note)
        vox_action = self.monitor.take_vox_action()
        if vox_action is not None:
            self.config_entry.async_create_background_task(
                self.hass, self._async_vox(vox_action), f"{DOMAIN} audio relay"
            )
        if not self._assessing and self._ai_ready():
            reason = self.monitor.take_ai_request(now)
            if reason is not None and self.budget.allow(now):
                self.config_entry.async_create_background_task(
                    self.hass, self.async_assess(reason), f"{DOMAIN} assessment"
                )
        if now - self._last_heartbeat >= HEARTBEAT_SECONDS:
            self._last_heartbeat = now
            self._heartbeat()

        snapshot = self.monitor.snapshot(now, *self._day_and_night_start())
        if snapshot != self.data or now - self._last_refresh >= _REFRESH_SECONDS:
            self._last_refresh = now
            self.async_set_updated_data(snapshot)
        self._schedule_save()

    def _day_and_night_start(self) -> tuple[float, float]:
        """Local midnight, and the most recent 18:00."""
        local = dt_util.now()
        day_start = dt_util.start_of_local_day(local)
        evening = day_start + timedelta(hours=18)
        if local < evening:
            evening -= timedelta(days=1)
        return day_start.timestamp(), evening.timestamp()

    def _heartbeat(self) -> None:
        """Press the dead-man buttons while monitoring is armed and healthy."""
        buttons = list(self._options(CONF_HEARTBEAT_BUTTONS, []))
        if not buttons or not self.settings.armed or self.monitor.problems:
            return
        self.config_entry.async_create_background_task(
            self.hass, self._async_call("button", "press", {"entity_id": buttons}), f"{DOMAIN} heartbeat"
        )

    async def _async_call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        try:
            await self.hass.services.async_call(domain, service, data, blocking=True)
        except Exception:  # noqa: BLE001 - a failing helper device must not stop monitoring
            _LOGGER.exception("Calling %s.%s failed", domain, service)

    async def _async_vox(self, action: VoxAction) -> None:
        player = self._options(CONF_VOX_PLAYER)
        place = self.active_place
        if not player:
            return
        if action is VoxAction.STOP:
            await self._async_call("media_player", "media_stop", {"entity_id": player})
        elif place is not None and place.audio_url:
            await self._async_call(
                "media_player",
                "play_media",
                {"entity_id": player, "media_content_id": place.audio_url, "media_content_type": "music"},
            )

    # -- notification actions and shutdown ---------------------------------

    @callback
    def _handle_action(self, event: Event[Any]) -> None:
        action = event.data.get("action")
        entry_id = self.config_entry.entry_id
        if action == f"{ACTION_ACK}_{entry_id}":
            self.acknowledge()
        elif action == f"{ACTION_SNOOZE}_{entry_id}":
            self.snooze(SNOOZE_SECONDS)

    async def _handle_stop(self, event: Event[Any]) -> None:
        """Home Assistant is going down: say so while armed, then save."""
        if self.settings.armed and not self.settings.privacy:
            await self.notifier.async_send_text(text(self.language, "stopping", child=self.child_name))
        await self._store.async_save(self._data_to_save())

    # -- AI ----------------------------------------------------------------

    def _ai_ready(self) -> bool:
        place = self.active_place
        return bool(
            self._options(CONF_AI_ENTITIES)
            and self._options(CONF_AI_CONSENT, False)
            and place is not None
            and place.camera_entity
        )

    async def async_assess(self, reason: str, *, manual: bool = False) -> Assessment | None:
        """Ask the configured AI tasks, in order, for an assessment of a fresh image."""
        place = self.active_place
        if not self._ai_ready() or place is None or self._assessing:
            return None
        now = self._now()
        if not manual and not self.budget.allow(now):
            return None
        self._assessing = True
        self.budget.record(now)
        profile = self.profile
        instructions = INSTRUCTIONS.format(language=self.language) + (
            f" Context: age profile {profile.value}, the monitor currently reads "
            f"'{self.monitor.state.value}'."
        )
        error = "no AI task configured"
        try:
            for entity_id in self._options(CONF_AI_ENTITIES, []):
                try:
                    async with asyncio.timeout(AI_TIMEOUT_SECONDS):
                        response = await self.hass.services.async_call(
                            "ai_task",
                            "generate_data",
                            {
                                "task_name": "CheckBaby",
                                "entity_id": entity_id,
                                "instructions": instructions,
                                "structure": STRUCTURE,
                                "attachments": [
                                    {
                                        "media_content_id": f"media-source://camera/{place.camera_entity}",
                                        "media_content_type": "image/jpeg",
                                    }
                                ],
                            },
                            blocking=True,
                            return_response=True,
                        )
                except TimeoutError:
                    error = f"{entity_id}: timeout"
                    continue
                except Exception as err:  # noqa: BLE001 - any provider error means "no answer"
                    error = f"{entity_id}: {err}"
                    continue
                data = response.get("data") if isinstance(response, dict) else None
                assessment = parse_assessment(data, self._now())
                if assessment is not None:
                    self.monitor.apply_assessment(assessment, self._now(), profile, reason)
                    return assessment
                error = f"{entity_id}: unusable answer"
            self.monitor.ai_failed(self._now(), error)
            return None
        finally:
            self._assessing = False
            self.async_refresh_now()

    # -- user actions ------------------------------------------------------

    async def async_set_setting(self, name: str, value: Any) -> None:
        """Change one setting and apply it at once."""
        setattr(self.settings, name, value)
        if name == "active_place":
            self.monitor.change_place(self._now())
            await self._async_subscribe_sources()
        self.async_refresh_now()

    def acknowledge(self) -> int:
        """Acknowledge all active alerts."""
        count = self.monitor.acknowledge(self._now())
        self.async_refresh_now()
        return count

    def snooze(self, seconds: float) -> None:
        """Hold warnings back for a while."""
        self.monitor.snooze(seconds, self._now())
        self.async_refresh_now()

    def test_alert(self, level: AlertLevel = AlertLevel.CRITICAL) -> None:
        """Run the notification chain with a test alert."""
        self.monitor.test_alert(self._now(), level)
        self.async_refresh_now()

    def force_state(self, state: ChildState) -> None:
        """Manually mark the child asleep or awake."""
        self.monitor.force_state(state, self._now())
        self.async_refresh_now()

    def quick_check(self) -> dict[str, Any]:
        """How is the child right now."""
        now = self._now()
        snapshot = self.monitor.snapshot(now, *self._day_and_night_start())
        assessment = snapshot.assessment
        return {
            "state": snapshot.state.value,
            "state_text": state_name(self.language, snapshot.state),
            "alert_level": snapshot.level.name.lower(),
            "alert": snapshot.alert_kind.value if snapshot.alert_kind else None,
            "asleep_minutes": None if snapshot.asleep_since is None else round((now - snapshot.asleep_since) / 60),
            "noise_level": snapshot.level_db,
            "breathing_movement": snapshot.breathing,
            "problems": list(snapshot.problems),
            "assessment": None if assessment is None else assessment.verdict,
            "assessment_reason": None if assessment is None else assessment.reason,
            "summary": quick_check_text(self.language, self.child_name, snapshot, now),
        }

    def night_report(self) -> dict[str, Any]:
        """Numbers and a sentence for the night so far."""
        now = self._now()
        _, night_start = self._day_and_night_start()
        report = night_report(self.monitor.sleep_log, night_start, now)
        report["summary"] = night_report_text(self.language, self.child_name, report)
        return report
