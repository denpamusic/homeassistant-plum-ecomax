"""Contains Plum ecoMAX services."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry
import homeassistant.helpers.config_validation as cv
from pyplumio.devices import Device
from pyplumio.exceptions import ParameterNotFoundError
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_DEVICE_ID,
    ATTR_MIXERS,
    ATTR_SCHEDULES,
    ATTR_VALUE,
    DOMAIN,
    STATE_OFF,
    STATE_ON,
)

ATTR_NAME: Final = "name"
ATTR_WEEKDAY: Final = "weekday"
ATTR_STATE: Final = "state"
ATTR_START: Final = "start"
ATTR_END: Final = "end"

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


def _get_target_device(
    device_id: str, hass: HomeAssistant, connection: EcomaxConnection
) -> Device:
    """Get target device by device id."""
    dr = device_registry.async_get(hass)
    device = dr.async_get(device_id)
    if not device:
        raise HomeAssistantError(
            f"Selected device '{device_id}' was not found, plese try again"
        )

    identifier = list(device.identifiers)[0][1]
    if "-mixer-" in identifier:
        index = int(identifier.split("-", 3).pop())
        mixers = connection.device.data.get(ATTR_MIXERS, [])
        if index < len(mixers):
            return connection.device.data[ATTR_MIXERS][index]

    return connection.device


async def _setup_set_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to set a parameter."""

    async def set_parameter_service(service_call: ServiceCall) -> None:
        """Service to set a parameter."""
        name = service_call.data[ATTR_NAME]
        value = service_call.data[ATTR_VALUE]
        device_id = service_call.data.get(ATTR_DEVICE_ID)
        target_device = (
            connection.device
            if device_id is None
            else _get_target_device(device_id, hass, connection)
        )

        if target_device is not None:
            try:
                if result := await target_device.set_value(
                    name, value, await_confirmation=True
                ):
                    return result
            except ParameterNotFoundError as e:
                _LOGGER.exception(e)

        raise HomeAssistantError(
            f"Couldn't set parameter '{name}', please check logs for more info"
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

        name = name.lower().replace(" ", "_")
        if name in connection.device.data.get(ATTR_SCHEDULES, {}):
            schedule = connection.device.data[ATTR_SCHEDULES][name]
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
