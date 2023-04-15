"""Contains Plum ecoMAX services."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import ATTR_NAME, ATTR_STATE, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry, entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.service import (
    SelectedEntities,
    async_extract_referenced_entity_ids,
)
from pyplumio.devices import Device
from pyplumio.exceptions import ParameterNotFoundError
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_END,
    ATTR_MIXERS,
    ATTR_SCHEDULES,
    ATTR_START,
    ATTR_VALUE,
    ATTR_WEEKDAY,
    DOMAIN,
    WEEKDAYS,
)

SCHEDULES: Final = (
    "Heating",
    "Water Heater",
)

SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = make_entity_service_schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.positive_float, STATE_ON, STATE_OFF),
    }
)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): vol.All(str, vol.In(SCHEDULES)),
        vol.Required(ATTR_WEEKDAY): vol.All(str, vol.In(WEEKDAYS)),
        vol.Required(ATTR_STATE): bool,
        vol.Optional(ATTR_START, default="00:00:00"): vol.Datetime("%H:%M:%S"),
        vol.Optional(ATTR_END, default="00:00:00"): vol.Datetime("%H:%M:%S"),
    }
)

_LOGGER = logging.getLogger(__name__)


@callback
def async_extract_target_device(
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
        mixers = connection.device.data.get(ATTR_MIXERS, {})
        try:
            return mixers[index]
        except KeyError:
            pass

    return connection.device


@callback
def async_extract_referenced_devices(
    hass: HomeAssistant, connection: EcomaxConnection, selected: SelectedEntities
) -> set[Device]:
    """Extract referenced devices from the selected entities."""
    devices: set[Device] = set()
    extracted: set[str] = set()
    ent_reg = entity_registry.async_get(hass)
    referenced = selected.referenced | selected.indirectly_referenced
    for entity_id in referenced:
        entity = ent_reg.async_get(entity_id)
        if entity.device_id not in extracted:
            devices.add(async_extract_target_device(entity.device_id, hass, connection))
            extracted.add(entity.device_id)

    return devices


@callback
def async_setup_set_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to set a parameter."""

    async def async_set_parameter_service(service_call: ServiceCall) -> None:
        """Service to set a parameter."""
        name = service_call.data[ATTR_NAME]
        value = service_call.data[ATTR_VALUE]
        selected = async_extract_referenced_entity_ids(hass, service_call)
        devices = async_extract_referenced_devices(hass, connection, selected)
        for device in devices:
            try:
                if result := await device.set(name, value):
                    return result
            except ParameterNotFoundError:
                _LOGGER.exception("Requested parameter %s not found", name)

        raise HomeAssistantError(
            f"Couldn't set parameter '{name}', please check logs for more info"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        async_set_parameter_service,
        SERVICE_SET_PARAMETER_SCHEMA,
    )


@callback
def async_setup_set_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Setup service to set a schedule."""

    async def async_set_schedule_service(service_call: ServiceCall) -> None:
        """Service to set a schedule."""
        name = service_call.data[ATTR_NAME]
        weekday = service_call.data[ATTR_WEEKDAY]
        state = service_call.data[ATTR_STATE]
        start_time = service_call.data[ATTR_START]
        end_time = service_call.data[ATTR_END]

        name = name.lower().replace(" ", "_")
        schedules = connection.device.get_nowait(ATTR_SCHEDULES, {})
        if name in schedules:
            schedule = schedules[name]
            schedule_day = getattr(schedule, weekday.lower())
            try:
                schedule_day.set_state(
                    (STATE_ON if state else STATE_OFF), start_time[:-3], end_time[:-3]
                )
            except ValueError as e:
                raise HomeAssistantError(
                    f"Error while trying to parse time interval for {name} schedule"
                ) from e

            schedule.commit()
            return

        raise HomeAssistantError(
            f"{name} schedule is not supported by the device, check logs for more info"
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_set_schedule_service,
        SERVICE_SET_SCHEDULE_SCHEMA,
    )


@callback
def async_setup_services(hass: HomeAssistant, connection: EcomaxConnection) -> bool:
    """Setup ecoMAX services."""
    async_setup_set_parameter_service(hass, connection)
    async_setup_set_schedule_service(hass, connection)
    return True
