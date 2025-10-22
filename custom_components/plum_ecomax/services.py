"""Contains Plum ecoMAX services."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import logging
from typing import (
    TYPE_CHECKING,
    Annotated,
    Final,
    Literal,
    NotRequired,
    TypedDict,
    cast,
)

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import ATTR_DEVICE_ID, ATTR_NAME, STATE_OFF, STATE_ON
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    service,
)
from pyplumio.const import State, UnitOfMeasurement
from pyplumio.devices import Device, VirtualDevice
from pyplumio.parameters import Number, Numeric, Parameter
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.schedules import Schedule, ScheduleDay
import voluptuous as vol

from .connection import DEFAULT_TIMEOUT, EcomaxConnection
from .const import ATTR_PRODUCT, ATTR_VALUE, DOMAIN, WEEKDAYS

if TYPE_CHECKING:
    from . import PlumEcomaxConfigEntry

ATTR_START: Final = "start"
ATTR_END: Final = "end"
ATTR_PRESET: Final = "preset"
ATTR_SCHEDULES: Final = "schedules"
ATTR_TYPE: Final = "type"
ATTR_WEEKDAYS: Final = "weekdays"

PRESET_DAY: Final = "day"
PRESET_NIGHT: Final = "night"
PRESETS = (PRESET_DAY, PRESET_NIGHT)

SCHEDULES: Final = ("heating", "water_heater", "circulation_pump", "boiler_work")

SERVICE_GET_PARAMETER = "get_parameter"
SERVICE_GET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_NAME): cv.string,
    }
)

SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): vol.Any(cv.positive_float, STATE_ON, STATE_OFF),
    }
)

SERVICE_GET_SCHEDULE = "get_schedule"
SERVICE_GET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_TYPE): vol.All(str, vol.In(SCHEDULES)),
        vol.Required(ATTR_WEEKDAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    }
)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_TYPE): vol.All(str, vol.In(SCHEDULES)),
        vol.Required(ATTR_WEEKDAYS): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
        vol.Required(ATTR_PRESET): vol.All(str, vol.In(PRESETS)),
        vol.Optional(ATTR_START, default="00:00:00"): vol.Datetime("%H:%M:%S"),
        vol.Optional(ATTR_END, default="00:00:00"): vol.Datetime("%H:%M:%S"),
    }
)

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"


_LOGGER = logging.getLogger(__name__)


@callback
def async_extract_connection_from_device_entry(
    hass: HomeAssistant, device_entry: dr.DeviceEntry
) -> EcomaxConnection:
    """Extract connection instance from device entry."""
    entry: PlumEcomaxConfigEntry
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if entry.entry_id in device_entry.config_entries:
            return entry.runtime_data.connection

    raise ValueError(f"No connection instance found for device id: {device_entry.id}")


@callback
def async_get_virtual_device(
    connection: EcomaxConnection, device_id: str
) -> VirtualDevice:
    """Extract virtual device."""
    hub_id, device_type, index = device_id.split("-", 3)
    if hub_id != connection.uid:
        raise ValueError(
            f"Invalid hub id for selected virtual device: {connection.uid} != {hub_id}"
        )

    device = connection.device
    devices = cast(dict[int, VirtualDevice], device.get_nowait(f"{device_type}s", {}))
    if not (virtual_device := devices.get(int(index), None)):
        raise ValueError(f"Selected virtual device not found: {device_id}")

    return virtual_device


@callback
def async_get_device_from_entry(
    hass: HomeAssistant, device_entry: dr.DeviceEntry
) -> Device:
    """Get device instance from device entry."""
    connection = async_extract_connection_from_device_entry(hass, device_entry)
    for identifier in device_entry.identifiers:
        if identifier[0] != DOMAIN:
            continue

        if identifier[1] == connection.uid:
            return connection.device

        return async_get_virtual_device(connection, device_id=identifier[1])

    raise ValueError(f"Invalid Plum ecoMAX device entry: {device_entry.id}")


@callback
def async_extract_device_from_service(
    hass: HomeAssistant, service_call: ServiceCall
) -> Device:
    """Extract a connection instance from the service call."""
    device_registry = dr.async_get(hass)
    device_id = cast(str, service_call.data.get(ATTR_DEVICE_ID))
    if not (device_entry := device_registry.async_get(device_id)):
        raise ValueError(f"Unknown Plum ecoMAX device id: {device_id}")

    return async_get_device_from_entry(hass, device_entry)


@dataclass(slots=True, kw_only=True)
class DeviceId:
    """Represents a device id.

    This class contains information that can be used to identify
    a specific device.
    """

    type: str
    index: int


@dataclass(slots=True, kw_only=True)
class ProductId:
    """Represents a product id.

    This class contains information that can be used to identify
    a product.
    """

    model: str
    uid: str


type ParameterValue = Numeric | State | bool


class ParameterResponse(TypedDict):
    """Represents a response from get/set parameter services."""

    name: str
    value: ParameterValue
    min_value: ParameterValue
    max_value: ParameterValue
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
def async_setup_get_parameter_service(hass: HomeAssistant) -> None:
    """Set up service to get a device parameter."""

    @service.verify_domain_control(DOMAIN)
    async def _async_get_parameter_service(
        service_call: ServiceCall,
    ) -> ServiceResponse:
        """Service to get a device parameter."""
        name = service_call.data[ATTR_NAME]
        device = async_extract_device_from_service(hass, service_call)
        parameter = async_validate_device_parameter(device, name)
        return cast(ServiceResponse, async_make_parameter_response(device, parameter))

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PARAMETER,
        _async_get_parameter_service,
        schema=SERVICE_GET_PARAMETER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_set_device_parameter(
    device: Device, service_call: ServiceCall
) -> ParameterResponse:
    """Set a device parameter."""
    name = service_call.data[ATTR_NAME]
    value = service_call.data[ATTR_VALUE]
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
def async_setup_set_parameter_service(hass: HomeAssistant) -> None:
    """Set up the service to set a device parameter."""

    @service.verify_domain_control(DOMAIN)
    async def _async_set_parameter_service(
        service_call: ServiceCall,
    ) -> ServiceResponse | None:
        """Service to set a device parameter."""
        device = async_extract_device_from_service(hass, service_call)
        response = async_set_device_parameter(device, service_call)
        return cast(ServiceResponse, response) if service_call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PARAMETER,
        _async_set_parameter_service,
        schema=SERVICE_SET_PARAMETER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


type Time = Annotated[str, "Time string in %H:%M format"]


class ScheduleResponse(TypedDict):
    """Represents a response from get schedule service."""

    name: str
    schedule: dict[str, dict[Time, Literal["day", "night"]]]
    product: NotRequired[ProductId]


@callback
def async_validate_schedule(device: Device, name: str) -> Schedule:
    """Validate the device parameter."""
    schedules = cast(dict[str, Schedule], device.get_nowait(ATTR_SCHEDULES, {}))
    if name not in schedules:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="schedule_not_found",
            translation_placeholders={"schedule": name},
        )

    return schedules[name]


@callback
def async_make_schedule_response(
    device: Device, schedule: Schedule, weekdays: list[str]
) -> ScheduleResponse:
    """Make a parameter response."""
    response: ScheduleResponse = {
        "name": schedule.name,
        "schedule": {
            weekday: {
                interval: PRESET_DAY if state == STATE_ON else PRESET_NIGHT
                for interval, state in getattr(schedule, weekday).items()
            }
            for weekday in weekdays
        },
    }
    if product_info := cast(ProductInfo | None, device.get_nowait(ATTR_PRODUCT)):
        response["product"] = ProductId(model=product_info.model, uid=product_info.uid)

    return response


@callback
def async_setup_get_schedule_service(hass: HomeAssistant) -> None:
    """Set up the service to get a schedule."""

    @service.verify_domain_control(DOMAIN)
    async def _async_get_schedule_service(service_call: ServiceCall) -> ServiceResponse:
        """Service to get a schedule."""
        schedule_type: str = service_call.data[ATTR_TYPE]
        weekdays: list[str] = service_call.data[ATTR_WEEKDAYS]
        device = async_extract_device_from_service(hass, service_call)
        schedule = async_validate_schedule(device, schedule_type)
        return cast(
            ServiceResponse, async_make_schedule_response(device, schedule, weekdays)
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        _async_get_schedule_service,
        schema=SERVICE_GET_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_set_device_schedule(device: Device, service_call: ServiceCall) -> None:
    """Set device schedule."""
    schedule_type = service_call.data[ATTR_TYPE]
    weekdays = service_call.data[ATTR_WEEKDAYS]
    preset = service_call.data[ATTR_PRESET]
    start_time = service_call.data[ATTR_START]
    end_time = service_call.data[ATTR_END]
    schedule = async_validate_schedule(device, schedule_type)
    for weekday in weekdays:
        schedule_day: ScheduleDay = getattr(schedule, weekday)
        try:
            schedule_day.set_state(
                True if preset == PRESET_DAY else False, start_time[:-3], end_time[:-3]
            )
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


@callback
def async_setup_set_schedule_service(hass: HomeAssistant) -> None:
    """Set up the service to set a schedule."""

    @service.verify_domain_control(DOMAIN)
    async def _async_set_schedule_service(service_call: ServiceCall) -> None:
        """Service to set a schedule."""
        device = async_extract_device_from_service(hass, service_call)
        await async_set_device_schedule(device, service_call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        _async_set_schedule_service,
        schema=SERVICE_SET_SCHEDULE_SCHEMA,
    )


@callback
def async_setup_services(hass: HomeAssistant) -> bool:
    """Set up the ecoMAX services."""
    _LOGGER.debug("Starting setup of services...")

    async_setup_get_parameter_service(hass)
    async_setup_set_parameter_service(hass)
    async_setup_get_schedule_service(hass)
    async_setup_set_schedule_service(hass)
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_RESET_METER,
        entity_domain=SENSOR_DOMAIN,
        func="async_reset_meter",
        schema={},
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_CALIBRATE_METER,
        entity_domain=SENSOR_DOMAIN,
        func="async_calibrate_meter",
        schema={vol.Required(ATTR_VALUE): cv.positive_float},
    )

    return True
