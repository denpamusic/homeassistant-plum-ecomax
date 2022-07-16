"""Contains Plum ecoMAX services."""
from __future__ import annotations

import asyncio
import logging
from typing import Final

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import ATTR_VALUE, DOMAIN

ATTR_NAME: Final = "name"

STATE_ON: Final = "on"
STATE_OFF: Final = "off"

SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.positive_int, STATE_ON, STATE_OFF),
    }
)

SERVICE_UPDATE_CAPABILITIES = "update_capabilities"

_LOGGER = logging.getLogger(__name__)


async def _setup_set_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to set a parameter."""

    async def set_parameter_service(service_call: ServiceCall) -> None:
        """Service to set a parameter."""
        name = service_call.data["name"]
        value = service_call.data["value"]

        if name in connection.capabilities:
            try:
                return await asyncio.wait_for(
                    connection.device.set_value(name, value), timeout=5
                )
            except asyncio.TimeoutError:
                _LOGGER.error("Service timed out while waiting for %s parameter", name)

        raise HomeAssistantError(
            f"Parameter {name} is not supported by the device, check logs for more info"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        set_parameter_service,
        SERVICE_SET_PARAMETER_SCHEMA,
    )


async def _setup_update_capabilities_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to update device capability list."""

    async def update_capabilities_service(service_call: ServiceCall) -> None:
        """Service to update device capability list."""
        await connection.async_update_device_capabilities()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_CAPABILITIES,
        update_capabilities_service,
    )


async def async_setup_services(
    hass: HomeAssistant, connection: EcomaxConnection
) -> bool:
    """Setup ecoMAX services."""
    await _setup_set_parameter_service(hass, connection)
    await _setup_update_capabilities_service(hass, connection)
    return True
