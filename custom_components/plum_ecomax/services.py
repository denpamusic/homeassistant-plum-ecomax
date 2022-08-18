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
ATTR_WEEKDAY: Final = "weekday"
ATTR_STATE: Final = "state"
ATTR_START: Final = "start"
ATTR_END: Final = "end"

STATE_ON: Final = "on"
STATE_OFF: Final = "off"


SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.positive_int, STATE_ON, STATE_OFF),
    }
)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): vol.All(str, vol.In("Heating", "Water Heater")),
        vol.Required(ATTR_WEEKDAY): vol.All(
            str,
            vol.In(
                (
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                )
            ),
        ),
        vol.Required(ATTR_STATE): bool,
        vol.Optional(ATTR_START, default="00:00:00"): vol.Datetime("%H:%M:%S"),
        vol.Optional(ATTR_END, default="00:00:00"): vol.Datetime("%H:%M:%S"),
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
        name = service_call.data[ATTR_NAME]
        value = service_call.data[ATTR_VALUE]

        if connection.device is not None and name in connection.capabilities:
            try:
                return await asyncio.wait_for(
                    connection.device.set_value(name, value), timeout=5
                )
            except asyncio.TimeoutError:
                _LOGGER.error("Service timed out while waiting for %s parameter", name)

        raise HomeAssistantError(
            f"{name} parameter is not supported by the device, check logs for more info"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        set_parameter_service,
        SERVICE_SET_PARAMETER_SCHEMA,
    )


async def _setup_set_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to set a schedule."""

    async def set_schedule_service(service_call: ServiceCall) -> None:
        """Service to set a schedule."""
        name = service_call.data[ATTR_NAME]
        weekday = service_call.data[ATTR_WEEKDAY]
        state = service_call.data[ATTR_STATE]
        start_time = service_call.data[ATTR_START]
        end_time = service_call.data[ATTR_END]

        name = name.lower().replace("", "_")
        if connection.device is not None and name in connection.device.data.get(
            "schedules", {}
        ):
            schedule = connection.device.data["schedules"][name]
            schedule_day = getattr(schedule, weekday.lower())
            try:
                schedule_day.set_state(
                    (STATE_ON if state else STATE_OFF), start_time[:-3], end_time[:-3]
                )
            except ValueError as e:
                raise HomeAssistantError(
                    f"Error while trying to parse time interval for {name} schedule"
                ) from e
            else:
                schedule.commit()

            return

        raise HomeAssistantError(
            f"{name} schedule is not supported by the device, check logs for more info"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        set_schedule_service,
        SERVICE_SET_SCHEDULE_SCHEMA,
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
    await _setup_set_schedule_service(hass, connection)
    await _setup_update_capabilities_service(hass, connection)
    return True
