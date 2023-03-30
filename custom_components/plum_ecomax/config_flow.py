"""Config flow for Plum ecoMAX integration."""
from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_BASE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from pyplumio.connection import Connection
from pyplumio.const import ProductType
from pyplumio.devices import Addressable
from pyplumio.exceptions import ConnectionFailedError
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.product_info import ProductInfo
import voluptuous as vol

from . import format_model_name
from .connection import (
    DEFAULT_TIMEOUT,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ATTR_MODULES,
    ATTR_PRODUCT,
    BAUDRATES,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
    ECOMAX,
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
    connection_type: str, hass: HomeAssistant, data: MutableMapping[str, Any]
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
    except asyncio.TimeoutError as connection_timeout:
        raise TimeoutConnect from connection_timeout

    return connection


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plum ecoMAX integration."""

    VERSION = 7

    def __init__(self) -> None:
        self.connection: Connection | None = None
        self.device: Addressable | None = None
        self.device_task: asyncio.Task | None = None
        self.identify_task: asyncio.Task | None = None
        self.modules_task: asyncio.Task | None = None
        self.init_info: MutableMapping[str, Any] = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["tcp", "serial"],
        )

    async def async_step_tcp(
        self, user_input: MutableMapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle the TCP connection setup."""
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
            return await self.async_step_device()
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except TimeoutConnect:
            errors[CONF_BASE] = "timeout_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"

        return self.async_show_form(
            step_id="tcp", data_schema=STEP_TCP_DATA_SCHEMA, errors=errors
        )

    async def async_step_serial(
        self, user_input: MutableMapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle the serial connection setup."""
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
            return await self.async_step_device()
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except TimeoutConnect:
            errors[CONF_BASE] = "timeout_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"

        return self.async_show_form(
            step_id="serial", data_schema=STEP_SERIAL_DATA_SCHEMA, errors=errors
        )

    async def async_step_device(self, user_input=None) -> FlowResult:
        """Wait until the device is available."""

        async def _wait_for_device():
            try:
                self.device: Addressable = await self.connection.get(
                    ECOMAX, timeout=DEFAULT_TIMEOUT
                )
            finally:
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
                )

        if not self.device_task:
            self.device_task = self.hass.async_create_task(_wait_for_device())
            return self.async_show_progress(
                step_id="device",
                progress_action="wait_for_device",
            )

        try:
            await self.device_task
        except asyncio.TimeoutError as device_not_found:
            _LOGGER.exception(device_not_found)
            return self.async_show_progress_done(next_step_id="device_not_found")
        finally:
            self.device_task = None

        return self.async_show_progress_done(next_step_id="identify")

    async def async_step_identify(self, user_input=None) -> FlowResult:
        """Identify the device."""

        async def _identify_device():
            try:
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
                        CONF_MODEL: format_model_name(product.model),
                        CONF_PRODUCT_TYPE: product_type,
                        CONF_PRODUCT_ID: product.id,
                    }
                )

            finally:
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
                )

        if not self.identify_task:
            self.identify_task = self.hass.async_create_task(_identify_device())
            return self.async_show_progress(
                step_id="identify",
                progress_action="identify_device",
            )

        try:
            await self.identify_task
        except (UnsupportedProduct, asyncio.TimeoutError) as device_not_supported:
            _LOGGER.exception(device_not_supported)
            return self.async_show_progress_done(next_step_id="unsupported_device")
        finally:
            self.identify_task = None

        return self.async_show_progress_done(next_step_id="discover")

    async def async_step_discover(self, user_input=None) -> FlowResult:
        """Detect modules connected to the device."""

        async def _discover_modules():
            try:
                modules: ConnectedModules = await self.device.get(
                    ATTR_MODULES, timeout=DEFAULT_TIMEOUT
                )
                sub_devices = await async_get_sub_devices(self.device)

                self.init_info.update(
                    {
                        CONF_SOFTWARE: modules.module_a,
                        CONF_SUB_DEVICES: sub_devices,
                    }
                )
            finally:
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
                )

        await self._async_set_unique_id(self.init_info[CONF_UID])

        if not self.modules_task:
            self.modules_task = self.hass.async_create_task(_discover_modules())
            return self.async_show_progress(
                step_id="discover",
                progress_action="discover_modules",
                description_placeholders={"model": self.init_info[CONF_MODEL]},
            )

        try:
            await self.modules_task
        except asyncio.TimeoutError as discovery_failed:
            _LOGGER.exception(discovery_failed)
            return self.async_show_progress_done(next_step_id="discovery_failed")
        finally:
            self.modules_task = None

        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_finish(self, user_input=None) -> FlowResult:
        """Finish integration config."""
        if self.connection:
            await self.connection.close()

        return self.async_create_entry(
            title=self.init_info[CONF_MODEL], data=self.init_info
        )

    async def async_step_device_not_found(self, user_input=None) -> FlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="no_devices_found")

    async def async_step_unsupported_device(self, user_input=None) -> FlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="unsupported_device")

    async def async_step_discovery_failed(self, user_input=None) -> FlowResult:
        """Handle issues that need transition await from progress step."""
        return self.async_abort(reason="discovery_failed")

    async def _async_set_unique_id(self, uid: str) -> None:
        """Set the config entry's unique ID (based on UID)."""
        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TimeoutConnect(HomeAssistantError):
    """Error to indicate that we established connection but
    failed to see expected response in time.
    """


class UnsupportedProduct(HomeAssistantError):
    """Error to indicate that product is not supported."""
