"""Config flow for Plum ecoMAX integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
import logging
from typing import Any, TypeVar, cast, overload

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.components.number.const import (
    DEVICE_CLASS_UNITS as NUMBER_DEVICE_CLASS_UNITS,
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
from pyplumio.devices import AddressableDevice, SubDevice
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.helpers.parameter import Parameter, UnitOfMeasurement
from pyplumio.structures.ecomax_parameters import EcomaxBinaryParameter, EcomaxParameter
from pyplumio.structures.mixer_parameters import MixerBinaryParameter, MixerParameter
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.thermostat_parameters import (
    ThermostatBinaryParameter,
    ThermostatParameter,
)
import voluptuous as vol

from . import PlumEcomaxConfigEntry, async_reload_config
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
        return OptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Initialize a new config flow."""
        self.connection: Connection | None = None
        self.device: AddressableDevice | None = None
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
        assert self.connection
        self.device = cast(
            AddressableDevice,
            await self.connection.get(DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT),
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
        # Tell mypy that once we here, device is not None
        assert self.device
        modules: ConnectedModules = await self.device.get(
            ATTR_MODULES, timeout=DEFAULT_TIMEOUT
        )
        sub_devices = await async_get_sub_devices(self.device)

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


SOURCE_TYPES: dict[Platform, tuple[type, ...]] = {
    Platform.BINARY_SENSOR: (bool,),
    Platform.SENSOR: (int, float, str),
    Platform.NUMBER: (EcomaxParameter, MixerParameter, ThermostatParameter),
    Platform.SWITCH: (
        EcomaxBinaryParameter,
        MixerBinaryParameter,
        ThermostatBinaryParameter,
    ),
}

ValueT = TypeVar("ValueT", str, int, float)


class OptionsFlowHandler(OptionsFlow):
    """Represents an options flow."""

    config_entry: PlumEcomaxConfigEntry
    connection: EcomaxConnection
    options: dict[str, Any]
    entities: dict[str, list]
    platforms = list(SOURCE_TYPES)

    def __init__(self, entry: PlumEcomaxConfigEntry) -> None:
        """Initialize a new options flow."""
        self.config_entry = entry
        self.connection = entry.runtime_data.connection
        self.options = deepcopy(dict(self.config_entry.options))
        self.entities = self.options.setdefault("entities", {})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_entity", "edit_entity", "reload"],
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
        if user_input is not None:
            user_input["source_device"] = self.source_device
            platform = self.entities.setdefault(self.platform.value, [])
            platform.append(user_input)
            return self.async_create_entry(title="", data=self.options)

        if not (source_options := self._async_get_source_options()):
            raise vol.Invalid(
                f"Cannot add any more {str(self.platform).replace('_', ' ')}s for "
                f"the selected source. Please select a different source and try again"
            )

        if self.platform == Platform.SENSOR:
            schema = {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_KEY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=source_options)
                ),
                vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.SelectSelector(
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
                vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
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
                vol.Optional(CONF_STATE_CLASS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[cls.value for cls in SensorStateClass],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="sensor_state_class",
                        sort=True,
                    ),
                ),
                vol.Optional(CONF_UPDATE_INTERVAL, default=10): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=60,
                        step=1,
                        unit_of_measurement=UnitOfTime.SECONDS,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }

        elif self.platform == Platform.BINARY_SENSOR:
            schema = {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_KEY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=source_options)
                ),
                vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[cls.value for cls in BinarySensorDeviceClass],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="binary_sensor_device_class",
                        sort=True,
                    ),
                ),
            }

        elif self.platform == Platform.NUMBER:
            schema = {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_KEY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=source_options)
                ),
                vol.Required(CONF_MODE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[NumberMode.AUTO, NumberMode.BOX, NumberMode.SLIDER],
                        translation_key="number_mode",
                    )
                ),
                vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.SelectSelector(
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
                vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[cls.value for cls in NumberDeviceClass],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="number_device_class",
                        sort=True,
                    ),
                ),
            }

        elif self.platform == Platform.SWITCH:
            schema = {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_KEY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=source_options)
                ),
            }

        else:
            raise HomeAssistantError

        return self.async_show_form(
            step_id="entity_details",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "platform": self.platform.value.replace("_", " ")
            },
        )

    async def async_step_reload(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reloading config."""
        self.hass.async_create_task(
            async_reload_config(self.hass, self.config_entry, self.connection)
        )
        return self.async_create_entry(title="Reload complete", data={})

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
                key
                for key in entity_keys
                if not key.startswith((DeviceType.MIXER, DeviceType.THERMOSTAT))
            ]

        elif self.source_device == REGDATA:
            data = device.get_nowait(REGDATA, {})
            existing_entities = [key for key in entity_keys if key.isnumeric()]

        elif self.source_device.startswith((DeviceType.MIXER, DeviceType.THERMOSTAT)):
            device_type, index = self.source_device.split("_", 1)
            devices: dict[int, SubDevice] = device.get_nowait(f"{device_type}s", {})
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
        connection = self.connection
        sources = {DeviceType.ECOMAX.value: f"Common ({connection.model})"}

        if connection.device.get_nowait(REGDATA, None):
            sources[REGDATA] = f"Extended ({connection.model})"

        if mixers := connection.device.get_nowait(ATTR_MIXERS, None):
            sources |= {
                f"{DeviceType.MIXER}_{mixer}": f"Mixer {mixer + 1}" for mixer in mixers
            }

        if thermostats := connection.device.get_nowait(ATTR_THERMOSTATS, None):
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
            if type(v) in SOURCE_TYPES[self.platform]
        ]

    @overload
    @staticmethod
    def _async_format_source_value(value: Parameter) -> str: ...

    @overload
    @staticmethod
    def _async_format_source_value(value: ValueT) -> ValueT: ...

    @callback
    @staticmethod
    def _async_format_source_value(value: Any) -> Any:
        """Format the source value."""
        if isinstance(value, Parameter):
            unit = value.unit_of_measurement
            unit2 = unit.value if isinstance(unit, UnitOfMeasurement) else unit
            return f"{value.value} {'' if unit2 is None else unit2}".rstrip()

        if isinstance(value, float):
            value = round(value, 2)

        return value
