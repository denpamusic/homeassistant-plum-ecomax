"""Config flow for Plum ecoMAX integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from serial import SerialException
import voluptuous as vol

from .connection import EcomaxConnection, EcomaxSerialConnection, EcomaxTcpConnection
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    CONNECTION_TYPES,
    DEFAULT_CONNECTION_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE, default=DEFAULT_CONNECTION_TYPE): vol.In(
            CONNECTION_TYPES
        ),
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    connection: Optional[EcomaxConnection] = None
    if data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP:
        connection = EcomaxTcpConnection(data[CONF_HOST], data[CONF_PORT], hass=hass)
    elif data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_SERIAL:
        connection = EcomaxSerialConnection(data[CONF_DEVICE], hass=hass)
    else:
        raise UnknownConnectionType

    try:
        product, uid = await connection.check()
    except (
        asyncio.TimeoutError,
        ConnectionRefusedError,
        ConnectionResetError,
        OSError,
        SerialException,
    ) as connection_failure:
        connection.close()
        raise CannotConnect from connection_failure

    if product is None or uid is None:
        raise UnsupportedDevice

    return {
        "title": f"{product}, uid: {uid}",
        "uid": uid,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Plum ecoMAX."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
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
        except UnsupportedDevice:
            errors["base"] = "unsupported_device"
        except UnknownConnectionType:
            errors["base"] = "unknown_connection_type"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info["uid"])
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class UnsupportedDevice(HomeAssistantError):
    """Error to indicate that we estableshed connection but
    failed to see expected response.
    """


class UnknownConnectionType(HomeAssistantError):
    """Error to indicate unknown connection type."""
