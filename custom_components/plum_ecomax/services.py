"""Contains Plum ecoMAX services."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Final, Literal

from homeassistant.const import ATTR_NAME, STATE_OFF, STATE_ON
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.service import (
    SelectedEntities,
    async_extract_referenced_entity_ids,
)
from pyplumio.const import UnitOfMeasurement
from pyplumio.devices import Device
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.schedule import (
    START_OF_DAY,
    STATE_DAY,
    STATE_NIGHT,
    TIME_FORMAT,
    ScheduleDay,
)
import voluptuous as vol

from .connection import DEFAULT_TIMEOUT, EcomaxConnection
from .const import (
    ATTR_END,
    ATTR_MIXERS,
    ATTR_PRESET,
    ATTR_PRODUCT,
    ATTR_SCHEDULES,
    ATTR_START,
    ATTR_TYPE,
    ATTR_VALUE,
    ATTR_WEEKDAYS,
    DOMAIN,
    WEEKDAYS,
)

SCHEDULES: Final = (
    "heating",
    "water_heater",
)

PRESETS: Final = (
    STATE_DAY,
    STATE_NIGHT,
)

SERVICE_GET_PARAMETER = "get_parameter"
SERVICE_GET_PARAMETER_SCHEMA = make_entity_service_schema(
    {
        vol.Required(ATTR_NAME): cv.string,
    }
)

SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = make_entity_service_schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.positive_float, STATE_ON, STATE_OFF),
    }
)

SERVICE_GET_SCHEDULE = "get_schedule"
SERVICE_GET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TYPE): vol.All(str, vol.In(SCHEDULES)),
        vol.Required(ATTR_WEEKDAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    }
)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TYPE): vol.All(str, vol.In(SCHEDULES)),
        vol.Required(ATTR_WEEKDAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
        vol.Required(ATTR_PRESET): vol.All(str, vol.In(PRESETS)),
        vol.Optional(ATTR_START, default="00:00:00"): vol.Datetime("%H:%M:%S"),
        vol.Optional(ATTR_END, default="00:00:00"): vol.Datetime("%H:%M:%S"),
    }
)

START_OF_DAY_DT = dt.datetime.strptime(START_OF_DAY, TIME_FORMAT)

_LOGGER = logging.getLogger(__name__)


@callback
def async_extract_target_device(
    device_id: str, hass: HomeAssistant, connection: EcomaxConnection
) -> Device:
    """Get target device by the device id."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if not device:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device": device_id},
        )

    identifier = list(device.identifiers)[0][1]
    if "-mixer-" in identifier:
        index = int(identifier.split("-", 3).pop())
        mixers: dict[int, Device] = connection.device.data.get(ATTR_MIXERS, {})
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
    entity_registry = er.async_get(hass)
    referenced = selected.referenced | selected.indirectly_referenced
    for entity_id in referenced:
        entity = entity_registry.async_get(entity_id)
        if entity.device_id not in extracted:
            devices.add(async_extract_target_device(entity.device_id, hass, connection))
            extracted.add(entity.device_id)

    return devices


async def async_get_device_parameter(
    device: Device, name: str
) -> dict[str, Any] | None:
    """Get device parameter."""
    try:
        parameter = await device.get(name, timeout=DEFAULT_TIMEOUT)
    except TimeoutError as e:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="get_parameter_timeout",
            translation_placeholders={"parameter": name},
        ) from e

    if not isinstance(parameter, Parameter):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_parameter",
            translation_placeholders={"parameter": name},
        )

    ecomax = device.parent if hasattr(device, "parent") else device
    product = ecomax.get_nowait(ATTR_PRODUCT, default=None)
    device_uid = product.uid if product is not None else "unknown"

    return {
        "name": name,
        "value": parameter.value,
        "min_value": parameter.min_value,
        "max_value": parameter.max_value,
        "unit_of_measurement": parameter.unit_of_measurement.value
        if isinstance(parameter.unit_of_measurement, UnitOfMeasurement)
        else parameter.unit_of_measurement,
        "device_type": device.__class__.__name__.lower(),
        "device_uid": device_uid,
        "device_index": device.index + 1 if hasattr(device, "index") else 0,
    }


@callback
def async_setup_get_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up service to get a device parameter."""

    async def async_get_parameter_service(service_call: ServiceCall) -> ServiceResponse:
        """Service to get a device parameter."""
        name = service_call.data[ATTR_NAME]
        selected = async_extract_referenced_entity_ids(hass, service_call)
        devices = async_extract_referenced_devices(hass, connection, selected)

        return {
            "parameters": [
                parameter
                for parameter in [
                    await async_get_device_parameter(device, name) for device in devices
                ]
                if parameter is not None
            ]
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        async_get_parameter_service,
        schema=SERVICE_GET_PARAMETER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_set_device_parameter(device: Device, name: str, value: float) -> bool:
    """Set device parameter."""
    try:
        return await device.set(name, value, timeout=DEFAULT_TIMEOUT)
    except TypeError as e:
        raise ServiceValidationError(
            str(e),
            translation_domain=DOMAIN,
            translation_key="invalid_parameter",
            translation_placeholders={"parameter": name},
        ) from e
    except ValueError as e:
        raise ServiceValidationError(
            str(e),
            translation_domain=DOMAIN,
            translation_key="invalid_parameter_value",
            translation_placeholders={"parameter": name, "value": value},
        ) from e
    except TimeoutError as e:
        raise HomeAssistantError(
            str(e),
            translation_domain=DOMAIN,
            translation_key="set_parameter_timeout",
            translation_placeholders={"parameter": name},
        ) from e


@callback
def async_setup_set_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to set a device parameter."""

    async def async_set_parameter_service(service_call: ServiceCall) -> None:
        """Service to set a device parameter."""
        name = service_call.data[ATTR_NAME]
        value = service_call.data[ATTR_VALUE]
        selected = async_extract_referenced_entity_ids(hass, service_call)
        devices = async_extract_referenced_devices(hass, connection, selected)

        if not any(
            {
                await async_set_device_parameter(device, name, value)
                for device in devices
            }
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_parameter_failed",
                translation_placeholders={"parameter": name},
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        async_set_parameter_service,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
    )


def async_schedule_day_to_dict(
    schedule_day: ScheduleDay,
) -> dict[str, Literal["day", "night"]]:
    """Format the schedule day as a dictionary."""
    return {
        (START_OF_DAY_DT + dt.timedelta(minutes=30 * index)).strftime(TIME_FORMAT): (
            STATE_DAY if value else STATE_NIGHT
        )
        for index, value in enumerate(schedule_day.intervals)
    }


@callback
def async_setup_get_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to get a schedule."""

    async def async_get_schedule_service(service_call: ServiceCall) -> ServiceResponse:
        """Service to get a schedule."""
        schedule_type = service_call.data[ATTR_TYPE]
        weekdays = service_call.data[ATTR_WEEKDAYS]

        schedules = connection.device.get_nowait(ATTR_SCHEDULES, {})
        if schedule_type not in schedules:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="schedule_not_found",
                translation_placeholders={"schedule": schedule_type},
            )

        schedule = schedules[schedule_type]
        return {
            "schedule": {
                weekday: async_schedule_day_to_dict(getattr(schedule, weekday))
                for weekday in weekdays
            }
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        async_get_schedule_service,
        schema=SERVICE_GET_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_setup_set_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to set a schedule."""

    async def async_set_schedule_service(service_call: ServiceCall) -> None:
        """Service to set a schedule."""
        schedule_type = service_call.data[ATTR_TYPE]
        weekdays = service_call.data[ATTR_WEEKDAYS]
        preset = service_call.data[ATTR_PRESET]
        start_time = service_call.data[ATTR_START]
        end_time = service_call.data[ATTR_END]

        schedules = connection.device.get_nowait(ATTR_SCHEDULES, {})
        if schedule_type not in schedules:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="schedule_not_found",
                translation_placeholders={"schedule": schedule_type},
            )

        schedule = schedules[schedule_type]
        for weekday in weekdays:
            schedule_day: ScheduleDay = getattr(schedule, weekday)
            try:
                schedule_day.set_state(preset, start_time[:-3], end_time[:-3])
            except ValueError as e:
                raise ServiceValidationError(
                    str(e),
                    translation_domain=DOMAIN,
                    translation_key="invalid_schedule_interval",
                    translation_placeholders={
                        "schedule": schedule_type,
                        "start": start_time[:-3],
                        "end": end_time[:-3],
                    },
                ) from e

        schedule.commit()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_set_schedule_service,
        schema=SERVICE_SET_SCHEDULE_SCHEMA,
    )


@callback
def async_setup_services(hass: HomeAssistant, connection: EcomaxConnection) -> bool:
    """Set up the ecoMAX services."""
    _LOGGER.debug("Starting setup of services...")

    async_setup_get_parameter_service(hass, connection)
    async_setup_set_parameter_service(hass, connection)
    async_setup_get_schedule_service(hass, connection)
    async_setup_set_schedule_service(hass, connection)
    return True
