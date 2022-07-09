"""Config flow for Plum ecoMAX integration."""
from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from pyplumio.exceptions import ConnectionFailedError
import voluptuous as vol

from .connection import check_connection, get_connection_handler
from .const import (
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SOFTWARE,
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
        title, product, modules, capabilities = await check_connection(
            await get_connection_handler(hass, data)
        )
    except ConnectionFailedError as connection_failure:
        raise CannotConnect from connection_failure
    except asyncio.TimeoutError as device_timeout:
        raise TimeoutConnect from device_timeout

    return {
        CONF_TITLE: title,
        CONF_UID: product.uid,
        CONF_MODEL: product.model,
        CONF_SOFTWARE: modules.module_a,
        CONF_CAPABILITIES: capabilities,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plum ecoMAX integration."""

    VERSION = 1

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
            errors["base"] = "cannot_connect"
        except TimeoutConnect:
            errors["base"] = "timeout_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            for field in (CONF_UID, CONF_MODEL, CONF_SOFTWARE, CONF_CAPABILITIES):
                user_input[field] = info[field]

            await self.async_set_unique_id(info[CONF_UID])
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TimeoutConnect(HomeAssistantError):
    """Error to indicate that we estableshed connection but
    failed to see expected response in time.
    """
