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
from pyplumio.const import ProductType
from pyplumio.exceptions import ConnectionFailedError
import voluptuous as vol

from . import format_model_name
from .connection import async_check_connection, async_get_connection_handler
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_TITLE,
    CONF_UID,
    CONNECTION_TYPES,
    DEFAULT_CONNECTION_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE, default=DEFAULT_CONNECTION_TYPE): vol.In(
            CONNECTION_TYPES
        ),
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)


async def validate_input(
    hass: HomeAssistant, data: MutableMapping[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        title, product, modules, sub_devices = await async_check_connection(
            await async_get_connection_handler(hass, data)
        )
    except ConnectionFailedError as connection_failure:
        raise CannotConnect from connection_failure
    except asyncio.TimeoutError as connection_timeout:
        raise TimeoutConnect from connection_timeout

    try:
        product_type = ProductType(product.type)
    except ValueError as validation_failure:
        raise UnsupportedProduct from validation_failure

    return {
        CONF_TITLE: title,
        CONF_UID: product.uid,
        CONF_MODEL: format_model_name(product.model),
        CONF_PRODUCT_TYPE: product_type,
        CONF_SOFTWARE: modules.module_a,
        CONF_SUB_DEVICES: sub_devices,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plum ecoMAX integration."""

    VERSION = 6

    async def async_step_user(
        self, user_input: MutableMapping[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors[CONF_BASE] = "cannot_connect"
        except TimeoutConnect:
            errors[CONF_BASE] = "timeout_connect"
        except UnsupportedProduct:
            errors[CONF_BASE] = "unsupported_product"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors[CONF_BASE] = "unknown"
        else:
            for field in (
                CONF_UID,
                CONF_MODEL,
                CONF_PRODUCT_TYPE,
                CONF_SOFTWARE,
                CONF_SUB_DEVICES,
            ):
                user_input[field] = info[field]

            await self.async_set_unique_id(info[CONF_UID])
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TimeoutConnect(HomeAssistantError):
    """Error to indicate that we established connection but
    failed to see expected response in time.
    """


class UnsupportedProduct(HomeAssistantError):
    """Error to indicate that product is not supported."""
