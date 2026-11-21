"""Config flow for CheckBaby: the child, its sleep places and who is told."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)
from homeassistant.util import slugify

from .const import (
    CONF_ACKNOWLEDGED,
    CONF_AI_BUDGET,
    CONF_AI_CONSENT,
    CONF_AI_ENTITIES,
    CONF_AUDIO_URL,
    CONF_BABYSITTER_SERVICE,
    CONF_BED_ZONE,
    CONF_BIRTH_DATE,
    CONF_BREATH_RATE_ENTITY,
    CONF_CAMERA_ENTITY,
    CONF_CHILD_NAME,
    CONF_CRY_ENTITY,
    CONF_DASHBOARD_PATH,
    CONF_DOOR_ENTITY,
    CONF_ENGINE_ID,
    CONF_FRIGATE_CAMERA,
    CONF_HEART_RATE_ENTITY,
    CONF_HEARTBEAT_BUTTONS,
    CONF_HUMIDITY_ENTITY,
    CONF_INTERNET_ENTITY,
    CONF_LEVEL_ENTITY,
    CONF_LOCAL_ALARM,
    CONF_MOTION_ENTITY,
    CONF_NOTIFY_SERVICES,
    CONF_PERSON_IS_CAREGIVER,
    CONF_PLACE_NAME,
    CONF_PRESENCE_ENTITY,
    CONF_SMOKE_ENTITIES,
    CONF_TEMPERATURE_ENTITY,
    CONF_TOPIC_PREFIX,
    CONF_VOX_PLAYER,
    DEFAULT_AI_BUDGET,
    DEFAULT_DASHBOARD_PATH,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
    SUBENTRY_PLACE,
)
from .schema_compat import vol


def _entity(domain: str | list[str], *, multiple: bool = False, device_class: str | None = None) -> Any:
    config = EntitySelectorConfig(domain=domain, multiple=multiple)
    if device_class is not None:
        config["device_class"] = device_class
    return EntitySelector(config)


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CHILD_NAME): TextSelector(),
        vol.Required(CONF_BIRTH_DATE): DateSelector(),
    }
)
DISCLAIMER_SCHEMA = vol.Schema({vol.Required(CONF_ACKNOWLEDGED, default=False): BooleanSelector()})
PLACE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLACE_NAME): TextSelector(),
        vol.Optional(CONF_FRIGATE_CAMERA): TextSelector(),
        vol.Optional(CONF_CAMERA_ENTITY): _entity("camera"),
        vol.Optional(CONF_BED_ZONE): TextSelector(),
        vol.Optional(CONF_DOOR_ENTITY): _entity("binary_sensor"),
        vol.Optional(CONF_PERSON_IS_CAREGIVER, default=False): BooleanSelector(),
        vol.Optional(CONF_PRESENCE_ENTITY): _entity("binary_sensor"),
        vol.Optional(CONF_TEMPERATURE_ENTITY): _entity("sensor", device_class="temperature"),
        vol.Optional(CONF_HUMIDITY_ENTITY): _entity("sensor", device_class="humidity"),
        vol.Optional(CONF_BREATH_RATE_ENTITY): _entity("sensor"),
        vol.Optional(CONF_HEART_RATE_ENTITY): _entity("sensor"),
        vol.Optional(CONF_ENGINE_ID): TextSelector(),
        vol.Optional(CONF_AUDIO_URL): TextSelector(),
        vol.Optional(CONF_CRY_ENTITY): _entity("binary_sensor"),
        vol.Optional(CONF_MOTION_ENTITY): _entity("binary_sensor"),
        vol.Optional(CONF_LEVEL_ENTITY): _entity("sensor"),
    }
)


def _mobile_apps(hass: HomeAssistant) -> list[str]:
    """The notify services of the companion apps."""
    return sorted(name for name in hass.services.async_services().get("notify", {}) if name.startswith("mobile_app_"))


def _notify_fields(hass: HomeAssistant) -> dict[Any, Any]:
    apps = _mobile_apps(hass)
    return {
        vol.Optional(CONF_NOTIFY_SERVICES, default=[]): SelectSelector(
            SelectSelectorConfig(options=apps, multiple=True, custom_value=True)
        ),
        vol.Optional(CONF_LOCAL_ALARM, default=[]): _entity(["siren", "light", "switch"], multiple=True),
    }


def _option_fields(hass: HomeAssistant) -> dict[Any, Any]:
    return {
        **_notify_fields(hass),
        vol.Optional(CONF_BABYSITTER_SERVICE): SelectSelector(
            SelectSelectorConfig(options=_mobile_apps(hass), custom_value=True)
        ),
        vol.Optional(CONF_HEARTBEAT_BUTTONS, default=[]): _entity(["button", "input_button"], multiple=True),
        vol.Optional(CONF_SMOKE_ENTITIES, default=[]): _entity("binary_sensor", multiple=True),
        vol.Optional(CONF_INTERNET_ENTITY): _entity("binary_sensor"),
        vol.Optional(CONF_VOX_PLAYER): _entity("media_player"),
        vol.Optional(CONF_AI_ENTITIES, default=[]): _entity("ai_task", multiple=True),
        vol.Optional(CONF_AI_CONSENT, default=False): BooleanSelector(),
        vol.Optional(CONF_AI_BUDGET, default=DEFAULT_AI_BUDGET): NumberSelector(
            NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): TextSelector(),
        vol.Optional(CONF_DASHBOARD_PATH, default=DEFAULT_DASHBOARD_PATH): TextSelector(),
    }


def validate_place(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Clean sleep place input and report what is missing."""
    data = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in user_input.items()
        if value not in (None, "")
    }
    errors: dict[str, str] = {}
    if not str(data.get(CONF_PLACE_NAME, "")).strip():
        errors[CONF_PLACE_NAME] = "name_required"
    if not data.get(CONF_FRIGATE_CAMERA) and not data.get(CONF_CRY_ENTITY):
        # Without a sound source the monitor could never hear the child.
        errors["base"] = "no_sound_source"
    return data, errors


def validate_targets(user_input: dict[str, Any]) -> dict[str, str]:
    """Report options that would leave the monitor unable to alert, or lack consent."""
    errors: dict[str, str] = {}
    if not user_input.get(CONF_NOTIFY_SERVICES) and not user_input.get(CONF_LOCAL_ALARM):
        errors["base"] = "no_alert_target"
    if user_input.get(CONF_AI_ENTITIES) and not user_input.get(CONF_AI_CONSENT):
        errors[CONF_AI_CONSENT] = "ai_consent_required"
    return errors


class CheckBabyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up one child: name, first sleep place, who is told, intended-use notice."""

    VERSION = 1

    def __init__(self) -> None:
        """Start with nothing collected."""
        self._data: dict[str, Any] = {}
        self._place: dict[str, Any] = {}
        self._options: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return CheckBabyOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        """Sleep places are sub-entries of a child."""
        return {SUBENTRY_PLACE: SleepPlaceFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the child's name and birth date (or expected due date)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_CHILD_NAME]).strip()
            if not name:
                errors[CONF_CHILD_NAME] = "name_required"
            else:
                await self.async_set_unique_id(slugify(name))
                self._abort_if_unique_id_configured()
                self._data = {CONF_CHILD_NAME: name, CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE]}
                return await self.async_step_place()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_place(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the first sleep place."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._place, errors = validate_place(user_input)
            if not errors:
                return await self.async_step_notify()

        return self.async_show_form(
            step_id="place",
            data_schema=self.add_suggested_values_to_schema(PLACE_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_notify(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask who is told and how."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_targets(user_input)
            if not errors:
                self._options = dict(user_input)
                return await self.async_step_disclaimer()

        schema = vol.Schema(_notify_fields(self.hass))
        return self.async_show_form(
            step_id="notify",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_disclaimer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the intended-use notice; the entry exists only once it is confirmed."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_ACKNOWLEDGED) is True:
                place = dict(self._place)
                place_name = str(place.pop(CONF_PLACE_NAME))
                return self.async_create_entry(
                    title=self._data[CONF_CHILD_NAME],
                    data=self._data,
                    options=self._options,
                    subentries=[
                        {
                            "subentry_type": SUBENTRY_PLACE,
                            "title": place_name,
                            "data": place,
                            "unique_id": None,
                        }
                    ],
                )
            errors[CONF_ACKNOWLEDGED] = "must_acknowledge"

        return self.async_show_form(step_id="disclaimer", data_schema=DISCLAIMER_SCHEMA, errors=errors)


class CheckBabyOptionsFlow(OptionsFlow):
    """Change who is told and what else is connected."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show all options on one page."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_targets(user_input)
            if not errors:
                return self.async_create_entry(data=user_input)

        schema = vol.Schema(_option_fields(self.hass))
        suggested = user_input if user_input is not None else dict(self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )


class SleepPlaceFlow(ConfigSubentryFlow):
    """Add or change a sleep place."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add a sleep place."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = validate_place(user_input)
            if not errors:
                return self.async_create_entry(title=str(data.pop(CONF_PLACE_NAME)), data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(PLACE_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Change a sleep place."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = validate_place(user_input)
            if not errors:
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=str(data.pop(CONF_PLACE_NAME)), data=data
                )

        suggested = user_input if user_input is not None else {CONF_PLACE_NAME: subentry.title, **subentry.data}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(PLACE_SCHEMA, suggested),
            errors=errors,
        )
