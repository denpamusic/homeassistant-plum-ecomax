"""Contains Plum ecoMAX services."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import logging
from typing import Final, NotRequired, TypedDict, cast

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
from pyplumio.const import State, UnitOfMeasurement
from pyplumio.devices import Device, VirtualDevice
from pyplumio.parameters import Number, NumericType, Parameter
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.schedules import Schedule, ScheduleDay
import voluptuous as vol

from .connection import DEFAULT_TIMEOUT, EcomaxConnection
from .const import ATTR_PRODUCT, ATTR_VALUE, DOMAIN, VIRTUAL_DEVICES, WEEKDAYS

ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_PRESET: Final = "preset"
ATTR_SCHEDULES: Final = "schedules"
ATTR_TYPE: Final = "type"
ATTR_WEEKDAYS: Final = "weekdays"

PRESET_DAY: Final = "day"
PRESET_NIGHT: Final = "night"
PRESETS = (PRESET_DAY, PRESET_NIGHT)

SCHEDULES: Final = ("heating", "water_heater")

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

    ecomax = connection.device
    identifier = list(device.identifiers)[0][1]
    for device_type in VIRTUAL_DEVICES:
        if f"-{device_type}-" in identifier:
            index = int(identifier.split("-", 3).pop())
            devices = cast(
                dict[int, VirtualDevice], ecomax.get_nowait(f"{device_type}s", {})
            )
            return devices.get(index, ecomax)

    return ecomax


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
        if entity and entity.device_id and entity.device_id not in extracted:
            devices.add(async_extract_target_device(entity.device_id, hass, connection))
            extracted.add(entity.device_id)

    return devices


@dataclass
class DeviceId:
    """Represents a device id.

    This class contains information that can be used to identify
    a specific device.
    """

    type: str
    index: int


@dataclass
class ProductId:
    """Represents a product id.

    This class contains information that can be used to identify
    a product.
    """

    model: str
    uid: str


class ParameterResponse(TypedDict):
    """Represents a response from get/set parameter services."""

    name: str
    value: NumericType | State | bool
    min_value: NumericType | State | bool
    max_value: NumericType | State | bool
    step: NotRequired[float]
    unit_of_measurement: NotRequired[str | None]
    device: NotRequired[DeviceId]
    product: NotRequired[ProductId]


@callback
def async_make_parameter_response(
    device: Device, parameter: Parameter
) -> ParameterResponse:
    """Make a parameter response."""
    response: ParameterResponse = {
        "name": parameter.description.name,
        "value": parameter.value,
        "min_value": parameter.min_value,
        "max_value": parameter.max_value,
    }

    if isinstance(parameter, Number):
        response["step"] = parameter.description.step
        response["unit_of_measurement"] = (
            parameter.unit_of_measurement.value
            if isinstance(parameter.unit_of_measurement, UnitOfMeasurement)
            else parameter.unit_of_measurement
        )

    if isinstance(device, VirtualDevice):
        response["device"] = DeviceId(
            type=device.__class__.__name__.lower(), index=device.index + 1
        )
        device = device.parent

    if product_info := cast(ProductInfo | None, device.get_nowait(ATTR_PRODUCT)):
        response["product"] = ProductId(model=product_info.model, uid=product_info.uid)

    return response


SUGGESTION_SCORE: Final = 0.6


@callback
def async_suggest_device_parameter_name(device: Device, name: str) -> str | None:
    """Get the parameter name suggestion."""
    parameter_names = [
        name for name, value in device.data.items() if isinstance(value, Parameter)
    ]
    matches = difflib.get_close_matches(
        name, parameter_names, n=1, cutoff=SUGGESTION_SCORE
    )
    return matches[0] if matches else None


@callback
def async_validate_device_parameter(device: Device, name: str) -> Parameter:
    """Validate the device parameter."""
    parameter = device.get_nowait(name, None)
    if not parameter:
        suggestion = async_suggest_device_parameter_name(device, name)
        if suggestion:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="parameter_not_found_with_suggestion",
                translation_placeholders={"parameter": name, "suggestion": suggestion},
            )
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="parameter_not_found",
                translation_placeholders={"parameter": name},
            )

    if not isinstance(parameter, Parameter):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="property_not_writable",
            translation_placeholders={"property": name},
        )

    return parameter


@callback
def async_get_device_parameter(device: Device, name: str) -> ParameterResponse:
    """Get device parameter."""
    parameter = async_validate_device_parameter(device, name)
    return async_make_parameter_response(device, parameter)


@callback
def async_setup_get_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up service to get a device parameter."""

    async def _async_get_parameter_service(
        service_call: ServiceCall,
    ) -> ServiceResponse:
        """Service to get a device parameter."""
        name = service_call.data[ATTR_NAME]
        selected = async_extract_referenced_entity_ids(hass, service_call)
        devices = async_extract_referenced_devices(hass, connection, selected)
        response = {
            "parameters": [
                async_get_device_parameter(device, name) for device in devices
            ]
        }
        return cast(ServiceResponse, response)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        _async_get_parameter_service,
        schema=SERVICE_GET_PARAMETER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_set_device_parameter(
    device: Device, name: str, value: float
) -> ParameterResponse:
    """Set device parameter."""
    parameter = async_validate_device_parameter(device, name)
    try:
        parameter.set_nowait(value, timeout=DEFAULT_TIMEOUT)
    except ValueError as e:
        raise ServiceValidationError(
            str(e),
            translation_domain=DOMAIN,
            translation_key="invalid_parameter_value",
            translation_placeholders={"parameter": name, "value": str(value)},
        ) from e

    return async_make_parameter_response(device, parameter)


@callback
def async_setup_set_parameter_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to set a device parameter."""

    async def _async_set_parameter_service(
        service_call: ServiceCall,
    ) -> ServiceResponse | None:
        """Service to set a device parameter."""
        name = service_call.data[ATTR_NAME]
        value = service_call.data[ATTR_VALUE]
        selected = async_extract_referenced_entity_ids(hass, service_call)
        devices = async_extract_referenced_devices(hass, connection, selected)
        response = {
            "parameters": [
                async_set_device_parameter(device, name, value) for device in devices
            ]
        }
        return cast(ServiceResponse, response) if service_call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        _async_set_parameter_service,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


@callback
def async_setup_get_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to get a schedule."""

    async def _async_get_schedule_service(service_call: ServiceCall) -> ServiceResponse:
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
                weekday: {
                    interval: PRESET_DAY if state == STATE_ON else PRESET_NIGHT
                    for interval, state in getattr(schedule, weekday).items()
                }
                for weekday in weekdays
            },
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        _async_get_schedule_service,
        schema=SERVICE_GET_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_setup_set_schedule_service(
    hass: HomeAssistant, connection: EcomaxConnection
) -> None:
    """Set up the service to set a schedule."""

    async def _async_set_schedule_service(service_call: ServiceCall) -> None:
        """Service to set a schedule."""
        schedule_type = service_call.data[ATTR_TYPE]
        weekdays = service_call.data[ATTR_WEEKDAYS]
        preset = service_call.data[ATTR_PRESET]
        start_time = service_call.data[ATTR_START]
        end_time = service_call.data[ATTR_END]
        schedules = cast(
            dict[str, Schedule], connection.device.get_nowait(ATTR_SCHEDULES, {})
        )
        if schedule_type not in schedules:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="schedule_not_found",
                translation_placeholders={"schedule": schedule_type},
            )

        schedule = schedules[schedule_type]
        state = bool(preset == "day")
        for weekday in weekdays:
            schedule_day: ScheduleDay = getattr(schedule, weekday)
            try:
                schedule_day.set_state(state, start_time[:-3], end_time[:-3])
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

        await schedule.commit()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        _async_set_schedule_service,
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
