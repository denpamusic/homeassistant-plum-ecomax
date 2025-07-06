"""Config flow for Plum ecoMAX integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
import logging
from typing import Any, Final, TypeVar, cast, overload

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number.const import (
    DEVICE_CLASS_UNITS as NUMBER_DEVICE_CLASS_UNITS,
    NumberDeviceClass,
    NumberMode,
)
from homeassistant.components.sensor.const import (
    CONF_STATE_CLASS,
    DEVICE_CLASS_UNITS as SENSOR_DEVICE_CLASS_UNITS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_BASE,
    CONF_DEVICE_CLASS,
    CONF_MODE,
    CONF_NAME,
    CONF_SOURCE,
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

from . import async_reload_config
from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ATTR_MIXERS,
    ATTR_MODULES,
    ATTR_PRODUCT,
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
    CONF_REMOVE_ENTITY,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
    REGDATA,
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
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
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
            return self.async_show_progress_done(next_step_id="unsupported_device")
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

    async def async_step_unsupported_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="unsupported_device")

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


VIRTUAL_DEVICES: Final = (DeviceType.MIXER, DeviceType.THERMOSTAT)

PLATFORM_TYPES: dict[Platform, tuple[type, ...]] = {
    Platform.BINARY_SENSOR: (bool,),
    Platform.SENSOR: (str, int, float),
    Platform.NUMBER: (Number,),
    Platform.SWITCH: (Switch,),
}

SensorValueT = TypeVar("SensorValueT", str, int, float)

_REMOVE_ENTITY: dict[vol.Marker, Any] = {
    vol.Optional(CONF_REMOVE_ENTITY, default=False): selector.BooleanSelector()
}


def generate_schema(
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

    if platform == Platform.SENSOR:
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

    elif platform == Platform.BINARY_SENSOR:
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

    elif platform == Platform.NUMBER:
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

    return vol.Schema(schema | _REMOVE_ENTITY if entity else schema)


class OptionsFlowHandler(OptionsFlow):
    """Represents an options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        self.connection = cast(
            EcomaxConnection, self.config_entry.runtime_data.connection
        )
        self.options = deepcopy(dict(self.config_entry.options))
        self.entities = cast(dict[str, Any], self.options.setdefault("entities", {}))
        return self.async_show_menu(
            step_id="init", menu_options=["add_entity", "edit_entity", "reload"]
        )

    async def async_step_add_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new entity."""
        if user_input is not None:
            self.source_device: str = user_input[CONF_SOURCE]
            return await self.async_step_entity_type()

        return self.async_show_form(
            step_id="add_entity",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=self._async_get_source_device_options()
                        )
                    )
                }
            ),
        )

    async def async_step_entity_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selecting entity type."""
        menu_options = ["add_sensor", "add_binary_sensor"]

        if self.source_device != REGDATA:
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
        """Handle adding a new binary sensor."""
        self.platform = Platform.BINARY_SENSOR
        return await self.async_step_entity_details()

    async def async_step_add_number(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new number."""
        self.platform = Platform.NUMBER
        return await self.async_step_entity_details()

    async def async_step_add_switch(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new switch."""
        self.platform = Platform.SWITCH
        return await self.async_step_entity_details()

    async def async_step_entity_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle new entity details."""
        entity = self.entity if hasattr(self, "entity") else {}
        if user_input is not None:
            user_input["source_device"] = self.source_device
            return self._async_step_create_entry(
                key=entity.get(CONF_KEY, user_input[CONF_KEY]), data=user_input
            )

        if not (source_options := self._async_get_source_options()):
            raise vol.Invalid(
                f"Can not add any more {str(self.platform).replace('_', ' ')}s for "
                f"the selected source. Please select a different source and try again."
            )

        return self.async_show_form(
            step_id="entity_details",
            data_schema=generate_schema(self.platform, source_options, entity),
            description_placeholders={
                "platform": self.platform.value.replace("_", " ")
            },
            last_step=True,
        )

    @callback
    def _async_step_create_entry(
        self, key: str, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Save the options."""
        entities = self.entities.setdefault(self.platform.value, {})
        removing_entity = data.get("remove_entity", False)
        renaming_entity = True if key != data[CONF_KEY] else False

        if removing_entity or renaming_entity:
            entities.pop(key, None)

        if not removing_entity:
            key = data[CONF_KEY]
            entities[key] = data

        return self.async_create_entry(title="", data=self.options)

    async def async_step_reload(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reloading config."""
        self.hass.async_create_task(
            async_reload_config(self.hass, self.config_entry, self.connection)
        )
        return self.async_create_entry(title="Reload complete", data={})

    async def async_step_edit_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing an entity."""
        if user_input is not None:
            entity: str = user_input["entity"]
            platform, key = entity.split("-", 2)
            self.entity = self.entities[platform][key]
            self.platform = Platform(platform)
            self.source_device = self.entity["source_device"]
            return await self.async_step_entity_details()

        if not (options := self._async_get_entity_options()):
            return await self.async_step_entities_not_found()

        return self.async_show_form(
            step_id="edit_entity",
            data_schema=vol.Schema(
                {
                    vol.Required("entity"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
            last_step=False,
        )

    async def async_step_entities_not_found(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="no_entities_found")

    @callback
    def _async_get_sources(self) -> dict[str, Any]:
        """Get the entity sources."""
        device = self.connection.device
        entity_registry = er.async_get(self.hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        entity_keys = [entity.unique_id.split("-")[-1] for entity in entities]

        if self.source_device == DeviceType.ECOMAX:
            data = device.data
            existing_entities = [
                key for key in entity_keys if not key.startswith(VIRTUAL_DEVICES)
            ]

        elif self.source_device == REGDATA:
            data = device.get_nowait(REGDATA, {})
            existing_entities = [key for key in entity_keys if key.isnumeric()]

        elif self.source_device.startswith(VIRTUAL_DEVICES):
            device_type, index = self.source_device.split("_", 1)
            devices: dict[int, VirtualDevice] = device.get_nowait(f"{device_type}s", {})
            data = devices[int(index)].data
            existing_entities = [
                key for key in entity_keys if f"{device_type}-{index}" in key
            ]

        else:
            raise HomeAssistantError

        return {k: v for k, v in data.items() if k not in existing_entities}

    @callback
    def _async_get_source_device_options(self) -> list[selector.SelectOptionDict]:
        """Return the source devices."""
        model = self.connection.model
        device = self.connection.device
        sources = {DeviceType.ECOMAX.value: f"Common ({model})"}

        if device.get_nowait(REGDATA, None):
            sources[REGDATA] = f"Extended ({model})"

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

    @callback
    def _async_get_source_options(self) -> list[selector.SelectOptionDict]:
        """Return source options."""
        sources = self._async_get_sources()
        data = dict(sorted(sources.items()))

        return [
            selector.SelectOptionDict(
                value=str(k), label=f"{k} (value: {self._async_format_source_value(v)})"
            )
            for k, v in data.items()
            if self._async_is_valid_source(v, self.platform)
        ]

    @callback
    def _async_is_valid_source(self, source: Any, platform: Platform) -> bool:
        """Check if the value is a valid source for platform type."""
        platform_types = PLATFORM_TYPES[platform]
        if isinstance(source, bool):
            return True if bool in platform_types else False

        return isinstance(source, platform_types)

    @overload
    @staticmethod
    def _async_format_source_value(value: Number) -> NumericType | str: ...

    @overload
    @staticmethod
    def _async_format_source_value(value: Switch) -> State: ...

    @overload
    @staticmethod
    def _async_format_source_value(value: SensorValueT) -> SensorValueT: ...

    @callback
    @staticmethod
    def _async_format_source_value(value: Any) -> Any:
        """Format the source value."""
        if isinstance(value, Number):
            unit = value.unit_of_measurement
            unit2 = unit.value if isinstance(unit, UnitOfMeasurement) else unit
            return f"{value.value} {unit2}" if unit2 else value.value

        if isinstance(value, Switch):
            return value.value

        if isinstance(value, float):
            value = round(value, 2)

        return value

    @callback
    def _async_get_entity_options(self) -> list[selector.SelectOptionDict]:
        """Get user-added entities."""
        platforms = list(PLATFORM_TYPES)
        entities = {
            f"{platform}-{key}": entity[CONF_NAME]
            for platform, entities in self.entities.items()
            if platform in platforms
            for key, entity in entities.items()
        }
        entities = dict(sorted(entities.items(), key=lambda item: item[1]))

        return [
            selector.SelectOptionDict(value=k, label=v) for k, v in entities.items()
        ]
