"""Config flow for Plum ecoMAX integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
from functools import cache
import logging
from typing import Any, cast, overload

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number.const import (
    DEVICE_CLASS_UNITS as NUMBER_DEVICE_CLASS_UNITS,
    NumberDeviceClass,
    NumberMode,
)
from homeassistant.components.sensor.const import (
    CONF_STATE_CLASS,
    DEVICE_CLASS_STATE_CLASSES,
    DEVICE_CLASS_UNITS as SENSOR_DEVICE_CLASS_UNITS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    CONF_BASE,
    CONF_DEVICE_CLASS,
    CONF_MODE,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, selector
import homeassistant.helpers.config_validation as cv
from pyplumio.connection import Connection
from pyplumio.const import ProductType
from pyplumio.devices import PhysicalDevice, VirtualDevice
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.parameters import Number, NumericType, State, Switch, UnitOfMeasurement
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.product_info import ProductInfo
import voluptuous as vol

from . import async_rediscover_devices
from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ATTR_ENTITIES,
    ATTR_MIXERS,
    ATTR_MODULES,
    ATTR_PRODUCT,
    ATTR_REGDATA,
    ATTR_THERMOSTATS,
    BAUDRATES,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_KEY,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SOURCE_DEVICE,
    CONF_STEP,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
    VIRTUAL_DEVICES,
    DeviceType,
)

_LOGGER = logging.getLogger(__name__)

STEP_TCP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)

STEP_SERIAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
        vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(BAUDRATES),
    }
)


async def validate_input(
    connection_type: str, hass: HomeAssistant, data: Mapping[str, Any]
) -> Connection:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_TCP_DATA_SCHEMA or
    STEP_SERIAL_DATA_SCHEMA with values provided by the user.
    """
    try:
        connection = await async_get_connection_handler(connection_type, hass, data)
        await asyncio.wait_for(connection.connect(), timeout=DEFAULT_TIMEOUT)
    except ConnectionFailedError as connection_failure:
        raise CannotConnect from connection_failure
    except TimeoutError as connection_timeout:
        raise TimeoutConnect from connection_timeout

    return connection


class PlumEcomaxFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plum ecoMAX integration."""

    VERSION = 8

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        """Create the options flow."""
        return OptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize a new config flow."""
        self.connection: Connection | None = None
        self.device: PhysicalDevice | None = None
        self.discover_task: asyncio.Task | None = None
        self.identify_task: asyncio.Task | None = None
        self.init_info: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["tcp", "serial"],
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle TCP connection setup."""
        if user_input is None:
            return self.async_show_form(step_id="tcp", data_schema=STEP_TCP_DATA_SCHEMA)

        errors = {}

        try:
            connection_type = CONNECTION_TYPE_TCP
            self.connection = await validate_input(
                connection_type, self.hass, user_input
            )
            self.init_info = user_input
            self.init_info[CONF_CONNECTION_TYPE] = connection_type
            return await self.async_step_identify()
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except TimeoutConnect:
            errors[CONF_BASE] = "timeout_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"

        return self.async_show_form(
            step_id="tcp", data_schema=STEP_TCP_DATA_SCHEMA, errors=errors
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle serial connection setup."""
        if user_input is None:
            return self.async_show_form(
                step_id="serial", data_schema=STEP_SERIAL_DATA_SCHEMA
            )

        errors = {}

        try:
            connection_type = CONNECTION_TYPE_SERIAL
            self.connection = await validate_input(
                connection_type, self.hass, user_input
            )
            self.init_info = user_input
            self.init_info[CONF_CONNECTION_TYPE] = connection_type
            return await self.async_step_identify()
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except TimeoutConnect:
            errors[CONF_BASE] = "timeout_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"

        return self.async_show_form(
            step_id="serial", data_schema=STEP_SERIAL_DATA_SCHEMA, errors=errors
        )

    async def async_step_identify(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Identify the device."""
        if not self.identify_task:
            self.identify_task = self.hass.async_create_task(
                self._async_identify_device(), eager_start=False
            )

        if not self.identify_task.done():
            return self.async_show_progress(
                step_id="identify",
                progress_action="identify_device",
                progress_task=self.identify_task,
            )

        try:
            await self.identify_task
        except TimeoutError as device_not_found:
            _LOGGER.exception(device_not_found)
            return self.async_show_progress_done(next_step_id="device_not_found")
        except UnsupportedProduct:
            return self.async_show_progress_done(next_step_id="unsupported_product")
        finally:
            self.identify_task = None

        return self.async_show_progress_done(next_step_id="discover")

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover connected modules."""
        await self._async_set_unique_id(self.init_info[CONF_UID])

        if not self.discover_task:
            self.discover_task = self.hass.async_create_task(
                self._async_discover_modules(), eager_start=False
            )

        if not self.discover_task.done():
            return self.async_show_progress(
                step_id="discover",
                progress_action="discover_modules",
                progress_task=self.discover_task,
                description_placeholders={"model": self.init_info[CONF_MODEL]},
            )

        try:
            await self.discover_task
        except TimeoutError as discovery_failed:
            _LOGGER.exception(discovery_failed)
            return self.async_show_progress_done(next_step_id="discovery_failed")
        finally:
            self.discover_task = None

        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Finish integration config."""
        if self.connection:
            await self.connection.close()

        return self.async_create_entry(
            title=self.init_info[CONF_MODEL], data=self.init_info
        )

    async def async_step_device_not_found(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="no_devices_found")

    async def async_step_unsupported_product(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="unsupported_product")

    async def async_step_discovery_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="discovery_failed")

    async def _async_identify_device(self) -> None:
        """Task to identify the device."""
        # Tell mypy that once we here, connection is not None
        connection = cast(Connection, self.connection)
        self.device = cast(
            PhysicalDevice,
            await connection.get(DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT),
        )
        product: ProductInfo = await self.device.get(
            ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT
        )

        try:
            product_type = ProductType(product.type)
        except ValueError as validation_failure:
            raise UnsupportedProduct from validation_failure

        self.init_info.update(
            {
                CONF_UID: product.uid,
                CONF_MODEL: product.model,
                CONF_PRODUCT_TYPE: product_type,
                CONF_PRODUCT_ID: product.id,
            }
        )

    async def _async_discover_modules(self) -> None:
        """Task to discover modules."""
        device = cast(PhysicalDevice, self.device)
        modules: ConnectedModules = await device.get(
            ATTR_MODULES, timeout=DEFAULT_TIMEOUT
        )
        sub_devices = await async_get_sub_devices(device)

        self.init_info.update(
            {
                CONF_SOFTWARE: asdict(modules),
                CONF_SUB_DEVICES: sub_devices,
            }
        )

    async def _async_set_unique_id(self, uid: str) -> None:
        """Set the config entry's unique ID (based on UID)."""
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TimeoutConnect(HomeAssistantError):
    """Error to indicate that connection timed out."""


class UnsupportedProduct(HomeAssistantError):
    """Error to indicate that product is not supported."""


PLATFORM_TYPES: dict[Platform, tuple[type, ...]] = {
    Platform.BINARY_SENSOR: (bool,),
    Platform.SENSOR: (str, int, float),
    Platform.NUMBER: (Number,),
    Platform.SWITCH: (Switch,),
}

PLATFORM_UNITS: dict[Platform, dict] = {
    Platform.SENSOR: SENSOR_DEVICE_CLASS_UNITS,
    Platform.NUMBER: NUMBER_DEVICE_CLASS_UNITS,
}


def _validate_unit(data: dict[str, Any], platform: Platform) -> None:
    """Validate unit of measurement.

    The following function is derived from Home Assistant Core,
    Copyright (c) 2016-present Nabu Casa, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Note: This function has been modified from its original version
    """
    if (
        (device_class := data.get(CONF_DEVICE_CLASS))
        and (units := PLATFORM_UNITS[platform].get(device_class)) is not None
        and (unit := data.get(CONF_UNIT_OF_MEASUREMENT)) not in units
    ):
        # Sort twice to make sure strings with same case-insensitive order of
        # letters are sorted consistently still.
        sorted_units = sorted(
            sorted(
                [f"'{unit!s}'" if unit else "no unit of measurement" for unit in units],
            ),
            key=str.casefold,
        )
        if len(sorted_units) == 1:
            units_string = sorted_units[0]
        else:
            units_string = f"one of {', '.join(sorted_units)}"

        raise vol.Invalid(
            f"'{unit}' is not a valid unit for device class '{device_class}'; "
            f"expected {units_string}"
        )


def _validate_state_class(data: dict[str, Any]) -> None:
    """Validate state class.

    The following function is derived from Home Assistant Core,
    Copyright (c) 2016-present Nabu Casa, Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Note: This function has been modified from its original version
    """
    if (
        (state_class := data.get(CONF_STATE_CLASS))
        and (device_class := data.get(CONF_DEVICE_CLASS))
        and (state_classes := DEVICE_CLASS_STATE_CLASSES.get(device_class)) is not None
        and state_class not in state_classes
    ):
        sorted_state_classes = sorted(
            [f"'{state_class!s}'" for state_class in state_classes],
            key=str.casefold,
        )
        if len(sorted_state_classes) == 1:
            state_classes_string = sorted_state_classes[0]
        else:
            state_classes_string = f"one of {', '.join(sorted_state_classes)}"

        raise vol.Invalid(
            f"'{state_class}' is not a valid state class for device class "
            f"'{device_class}'; expected {state_classes_string}"
        )


def _validate_entity_details(
    entity: dict[str, Any], platform: Platform
) -> dict[str, str]:
    """Validate entity details."""
    errors = {}

    if platform in PLATFORM_UNITS:
        try:
            _validate_unit(entity, platform=platform)
        except vol.Invalid as e:
            errors[CONF_UNIT_OF_MEASUREMENT] = str(e.msg)

    if platform is Platform.SENSOR:
        try:
            _validate_state_class(entity)
        except vol.Invalid as e:
            errors[CONF_STATE_CLASS] = str(e.msg)

    return errors


def _entity_keys_for_config_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> list[str]:
    """Get entity keys for config entry."""
    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    return [entity.unique_id.split("-")[-1] for entity in entities]


def _custom_entity_options(
    entities: dict[str, Any],
) -> list[selector.SelectOptionDict]:
    """Return custom entity options."""
    platforms = list(PLATFORM_TYPES)
    entities = {
        f"{platform}.{key}": entity[CONF_NAME]
        for platform, entities in entities.items()
        if platform in platforms
        for key, entity in entities.items()
    }
    entities = dict(sorted(entities.items(), key=lambda item: item[1]))

    return [selector.SelectOptionDict(value=k, label=v) for k, v in entities.items()]


def _is_valid_source(platform: Platform, value: Any) -> bool:
    """Check if value is valid source for the specific platform type."""
    platform_types = PLATFORM_TYPES[platform]
    if isinstance(value, bool):
        return True if bool in platform_types else False

    return isinstance(value, platform_types)


@overload
def _format_source_value(value: Number) -> NumericType | str: ...


@overload
def _format_source_value(value: Switch) -> State: ...


@overload
def _format_source_value[SensorValueT: str | int | float](
    value: SensorValueT,
) -> SensorValueT: ...


def _format_source_value(value: Any) -> Any:
    """Format the source value."""
    if isinstance(value, Number):
        unit = value.unit_of_measurement
        unit2 = unit.value if isinstance(unit, UnitOfMeasurement) else unit
        return f"{value.value} {unit2}" if unit2 else value.value

    elif isinstance(value, Switch):
        return value.value

    elif isinstance(value, float):
        value = round(value, 2)

        return value


def generate_select_schema(entities: dict[str, Any]) -> vol.Schema | None:
    """Generate schema for editing or deleting an entity."""

    if not (options := _custom_entity_options(entities)):
        return None

    return vol.Schema(
        {
            vol.Required("entity_id"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            )
        }
    )


def generate_edit_schema(
    platform: Platform,
    source_options: list[selector.SelectOptionDict],
    entity: dict[str, Any],
) -> vol.Schema:
    """Generate schema."""

    schema: dict[vol.Marker, Any] = {
        vol.Required(
            CONF_NAME, default=entity.get(CONF_NAME, vol.UNDEFINED)
        ): selector.TextSelector(),
        vol.Required(
            CONF_KEY, default=entity.get(CONF_KEY, vol.UNDEFINED)
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=source_options)
        ),
    }

    if platform is Platform.SENSOR:
        schema |= {
            vol.Optional(
                CONF_UNIT_OF_MEASUREMENT,
                default=entity.get(CONF_UNIT_OF_MEASUREMENT, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(
                        {
                            str(unit)
                            for units in SENSOR_DEVICE_CLASS_UNITS.values()
                            for unit in units
                            if unit is not None
                        }
                    ),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="sensor_unit_of_measurement",
                    custom_value=True,
                    sort=True,
                ),
            ),
            vol.Optional(
                CONF_DEVICE_CLASS,
                default=entity.get(CONF_DEVICE_CLASS, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        cls.value
                        for cls in SensorDeviceClass
                        if cls != SensorDeviceClass.ENUM
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="sensor_device_class",
                    sort=True,
                ),
            ),
            vol.Optional(
                CONF_STATE_CLASS,
                default=entity.get(CONF_STATE_CLASS, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[cls.value for cls in SensorStateClass],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="sensor_state_class",
                    sort=True,
                ),
            ),
            vol.Optional(
                CONF_UPDATE_INTERVAL, default=entity.get(CONF_UPDATE_INTERVAL, 10)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=60,
                    step=1,
                    unit_of_measurement=UnitOfTime.SECONDS,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }

    elif platform is Platform.BINARY_SENSOR:
        schema |= {
            vol.Optional(
                CONF_DEVICE_CLASS,
                default=entity.get(CONF_DEVICE_CLASS, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[cls.value for cls in BinarySensorDeviceClass],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="binary_sensor_device_class",
                    sort=True,
                ),
            ),
        }

    elif platform is Platform.NUMBER:
        schema |= {
            vol.Required(
                CONF_MODE, default=entity.get(CONF_MODE, vol.UNDEFINED)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[NumberMode.AUTO, NumberMode.BOX, NumberMode.SLIDER],
                    translation_key="number_mode",
                )
            ),
            vol.Optional(
                CONF_UNIT_OF_MEASUREMENT,
                default=entity.get(CONF_UNIT_OF_MEASUREMENT, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(
                        {
                            str(unit)
                            for units in NUMBER_DEVICE_CLASS_UNITS.values()
                            for unit in units
                            if unit is not None
                        }
                    ),
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="number_unit_of_measurement",
                    custom_value=True,
                    sort=True,
                ),
            ),
            vol.Optional(
                CONF_DEVICE_CLASS,
                default=entity.get(CONF_DEVICE_CLASS, vol.UNDEFINED),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[cls.value for cls in NumberDeviceClass],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="number_device_class",
                    sort=True,
                ),
            ),
        }

    return vol.Schema(schema)


class OptionsFlowHandler(OptionsFlowWithReload):
    """Represents an options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if not hasattr(self.config_entry, "runtime_data"):
            return self.async_abort(reason="entry_not_ready")

        self.connection = cast(
            EcomaxConnection, self.config_entry.runtime_data.connection
        )
        self.options = deepcopy(dict(self.config_entry.options))
        self.entities = cast(dict[str, Any], self.options.setdefault(ATTR_ENTITIES, {}))
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "add_entity",
                "edit_entity",
                "remove_entity",
                "rediscover_devices",
            ],
        )

    async def async_step_add_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding custom entity."""
        if user_input is not None:
            self.source_device: str = user_input[CONF_SOURCE_DEVICE]
            return await self.async_step_entity_type()

        return self.async_show_form(
            step_id="add_entity",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE_DEVICE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._source_device_select_options()
                        )
                    )
                }
            ),
        )

    async def async_step_entity_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selecting custom entity type."""
        menu_options = ["add_sensor", "add_binary_sensor"]

        if self.source_device != ATTR_REGDATA:
            menu_options.extend(["add_number", "add_switch"])

        return self.async_show_menu(step_id="entity_type", menu_options=menu_options)

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new sensor."""
        self.platform = Platform.SENSOR
        return await self.async_step_entity_details()

    async def async_step_add_binary_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a custom binary sensor entity."""
        self.platform = Platform.BINARY_SENSOR
        return await self.async_step_entity_details()

    async def async_step_add_number(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a custom number entity."""
        self.platform = Platform.NUMBER
        return await self.async_step_entity_details()

    async def async_step_add_switch(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a custom switch entity."""
        self.platform = Platform.SWITCH
        return await self.async_step_entity_details()

    async def async_step_entity_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle custom entity details."""
        entity = self.entity if hasattr(self, "entity") else {}
        if user_input is None:
            errors = {}
        elif not (
            errors := _validate_entity_details(user_input, platform=self.platform)
        ):
            user_input[CONF_SOURCE_DEVICE] = self.source_device
            key = entity.get(CONF_KEY, user_input[CONF_KEY])
            return self._async_step_create_entry(key, data=user_input)

        if not (
            source_options := self._entity_source_select_options(
                selected=entity.get(CONF_KEY, "")
            )
        ):
            return self.async_abort(reason="no_entities_to_add")

        return self.async_show_form(
            step_id="entity_details",
            data_schema=generate_edit_schema(self.platform, source_options, entity),
            errors=errors,
            description_placeholders={
                "platform": self.platform.value.replace("_", " ")
            },
            last_step=True,
        )

    @callback
    def _async_step_create_entry(
        self, key: str, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Create custom entity."""
        entities = self.entities.setdefault(self.platform.value, {})
        key_changed = True if key != data[CONF_KEY] else False

        if key_changed:
            self._remove_entry_from_registry(key)
            entities.pop(key, None)

        if self.platform is Platform.NUMBER and not key_changed:
            data[CONF_STEP] = self._number_native_step(data[CONF_KEY])

        key = data[CONF_KEY]
        entities[key] = data
        return self.async_create_entry(title="", data=self.options)

    async def async_step_rediscover_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle rediscovering connected devices."""
        self.hass.async_create_task(
            async_rediscover_devices(self.hass, self.config_entry, self.connection)
        )
        return self.async_create_entry(data=self.options)

    async def async_step_edit_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing a custom entity."""
        if user_input is not None:
            entity_id: str = user_input["entity_id"]
            platform, key = entity_id.split(".", 2)
            self.entity = self.entities[platform][key]
            self.platform = Platform(platform)
            self.source_device = self.entity[CONF_SOURCE_DEVICE]
            return await self.async_step_entity_details()

        if not (schema := generate_select_schema(self.entities)):
            return self.async_abort(reason="no_entities_to_edit_or_remove")

        return self.async_show_form(
            step_id="edit_entity", data_schema=schema, last_step=False
        )

    async def async_step_remove_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle deleting a custom entity."""
        if user_input is not None:
            return self._async_step_remove_entity(user_input["entity_id"])

        if not (schema := generate_select_schema(self.entities)):
            return self.async_abort(reason="no_entities_to_edit_or_remove")

        return self.async_show_form(
            step_id="remove_entity", data_schema=schema, last_step=False
        )

    @callback
    def _async_step_remove_entity(self, entity_id: str) -> ConfigFlowResult:
        """Remove the entity."""
        platform, key = entity_id.split(".", 2)
        entities = self.entities.setdefault(platform, {})
        entities.pop(key, None)
        self._remove_entry_from_registry(key)
        return self.async_create_entry(title="", data=self.options)

    def _remove_entry_from_registry(self, key: str) -> None:
        """Remove entry from the entity registry."""
        entity_registry = er.async_get(self.hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        for entity in entities:
            if entity.unique_id.split("-")[-1] == key:
                entity_registry.async_remove(entity_id=entity.entity_id)

    def _ecomax_source_candidates(
        self, entity_keys: list[str], selected: str
    ) -> dict[str, Any]:
        """Return source candidates for ecoMAX."""
        existing_keys = [
            key for key in entity_keys if key.split("_", 1)[0] not in VIRTUAL_DEVICES
        ]
        return {
            k: v
            for k, v in self.connection.device.data.items()
            if k not in existing_keys or k == selected
        }

    def _regdata_source_candidates(
        self, entity_keys: list[str], selected: str
    ) -> dict[str, Any]:
        """Return source candidates for regdata."""
        existing_keys = [key for key in entity_keys if key.isnumeric()]
        regdata = cast(
            dict[str, Any], self.connection.device.get_nowait(ATTR_REGDATA, {})
        )
        return {
            k: v for k, v in regdata.items() if k not in existing_keys or k == selected
        }

    def _virtual_device_source_candidates(
        self, entity_keys: list[str], selected: str
    ) -> dict[str, Any]:
        """Return source candidates for virtual device."""
        device_type, index = self.source_device.split("_", 1)
        virtual_device = self._get_virtual_device(DeviceType(device_type), int(index))
        existing_keys = [
            key for key in entity_keys if key.startswith(f"{device_type}-{index}")
        ]
        return {
            k: v
            for k, v in virtual_device.data.items()
            if k not in existing_keys or k == selected
        }

    def _entity_source_candidates(self, selected: str) -> dict[str, Any]:
        """Return custom entity source candidates."""
        entity_keys = _entity_keys_for_config_entry(self.hass, self.config_entry)

        if self.source_device == DeviceType.ECOMAX:
            return self._ecomax_source_candidates(entity_keys, selected)

        elif self.source_device == ATTR_REGDATA:
            return self._regdata_source_candidates(entity_keys, selected)

        elif self.source_device.startswith(VIRTUAL_DEVICES):
            return self._virtual_device_source_candidates(entity_keys, selected)

        raise HomeAssistantError(
            translation_key="unsupported_device",
            translation_placeholders={"device": self.source_device},
        )

    @cache
    def _get_virtual_device(self, device_type: DeviceType, index: int) -> VirtualDevice:
        """Get the virtual device by device type and index."""
        device = self.connection.device
        virtual_devices = cast(
            dict[int, VirtualDevice], device.get_nowait(f"{device_type}s", {})
        )

        try:
            return virtual_devices[index]
        except KeyError as e:
            raise HomeAssistantError(
                translation_key="device_disconnected",
                translation_placeholders={"device": f"{device_type} {index}"},
            ) from e

    def _entity_source_select_options(
        self, selected: str = ""
    ) -> list[selector.SelectOptionDict]:
        """Return source options."""
        source_candidates = self._entity_source_candidates(selected)
        data = dict(sorted(source_candidates.items()))

        return [
            selector.SelectOptionDict(
                value=str(k), label=f"{k} (value: {_format_source_value(v)})"
            )
            for k, v in data.items()
            if _is_valid_source(self.platform, v)
        ]

    def _source_device_select_options(self) -> list[selector.SelectOptionDict]:
        """Return source device options."""
        model = self.connection.model
        device = self.connection.device
        sources = {DeviceType.ECOMAX.value: f"Common ({model})"}

        if device.get_nowait(ATTR_REGDATA, None):
            sources[ATTR_REGDATA] = f"Extended ({model})"

        if mixers := device.get_nowait(ATTR_MIXERS, None):
            sources |= {
                f"{DeviceType.MIXER}_{mixer}": f"Mixer {mixer + 1}" for mixer in mixers
            }

        if thermostats := device.get_nowait(ATTR_THERMOSTATS, None):
            sources |= {
                f"{DeviceType.THERMOSTAT}_{thermostat}": f"Thermostat {thermostat + 1}"
                for thermostat in thermostats
            }

        return [selector.SelectOptionDict(value=k, label=v) for k, v in sources.items()]

    def _number_native_step(self, key: str) -> float:
        """Return native step for the number entity."""
        device = self.connection.device

        number = None
        if self.source_device == DeviceType.ECOMAX:
            number = device.get_nowait(key, None)

        elif self.source_device.startswith(VIRTUAL_DEVICES):
            device_type, index = self.source_device.split("_", 1)
            virtual_device = self._get_virtual_device(
                DeviceType(device_type), int(index)
            )
            number = virtual_device.get_nowait(key, None)

        else:
            number = None

        number = cast(Number | None, number)
        if not number:
            raise HomeAssistantError(
                translation_key="entity_not_found",
                translation_placeholders={"entity": key, "device": self.source_device},
            )

        return number.description.step
