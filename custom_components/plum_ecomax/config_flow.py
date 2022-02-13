"""Config flow for Plum ecoMAX integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol
from voluptuous import All, Range

from .connection import EcomaxConnection
from .const import DEFAULT_INTERVAL, DEFAULT_PORT, DOMAIN, MAX_INTERVAL, MIN_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Optional("port", default=DEFAULT_PORT): int,
        vol.Optional("interval", default=DEFAULT_INTERVAL): All(
            int, Range(min=MIN_INTERVAL, max=MAX_INTERVAL)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    connection = EcomaxConnection(hass, host=data["host"], port=data["port"])

    try:
        product, uid = await connection.check()
    except ConnectionRefusedError:
        connection.close()
        raise CannotConnect

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
