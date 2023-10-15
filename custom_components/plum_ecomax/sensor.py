"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any, Final

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_STANDBY,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import ConfigType, StateType
from pyplumio.const import DeviceState, ProductType
from pyplumio.filters import aggregate, on_change, throttle
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.regulator_data import RegulatorData
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_NUMERIC,
    ATTR_VALUE,
    DEVICE_CLASS_METER,
    DEVICE_CLASS_STATE,
    DOMAIN,
    ECOLAMBDA,
    FLOW_KGH,
    MODULE_A,
    ProductId,
)
from .entity import EcomaxEntity, MixerEntity

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"

STATE_STABILIZATION: Final = "stabilization"
STATE_KINDLING: Final = "kindling"
STATE_HEATING: Final = "heating"
STATE_BURNING_OFF: Final = "burning_off"
STATE_ALERT: Final = "alert"
STATE_UNKNOWN: Final = "unknown"

EM_TO_HA_STATE: dict[DeviceState, str] = {
    DeviceState.OFF: STATE_OFF,
    DeviceState.STABILIZATION: STATE_STABILIZATION,
    DeviceState.KINDLING: STATE_KINDLING,
    DeviceState.WORKING: STATE_HEATING,
    DeviceState.SUPERVISION: STATE_PAUSED,
    DeviceState.PAUSED: STATE_IDLE,
    DeviceState.STANDBY: STATE_STANDBY,
    DeviceState.BURNING_OFF: STATE_BURNING_OFF,
    DeviceState.ALERT: STATE_ALERT,
}

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, slots=True)
class EcomaxSensorEntityDescription(SensorEntityDescription):
    """Describes ecoMAX sensor entity."""

    product_types: set[ProductType]
    value_fn: Callable[[Any], Any]
    always_available: bool = False
    filter_fn: Callable[[Any], Any] = on_change
    module: str = MODULE_A


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        translation_key="heating_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        translation_key="water_heater_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        translation_key="outside_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        translation_key="heating_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        translation_key="water_heater_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="state",
        translation_key="ecomax_state",
        device_class=DEVICE_CLASS_STATE,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: EM_TO_HA_STATE[x] if x in EM_TO_HA_STATE else STATE_UNKNOWN,
    ),
    EcomaxSensorEntityDescription(
        key="password",
        translation_key="service_password",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:form-textbox-password",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        translation_key="software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x.module_a,
    ),
    EcomaxSensorEntityDescription(
        key="product",
        translation_key="uid",
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        value_fn=lambda x: x.uid,
    ),
    EcomaxSensorEntityDescription(
        key="lambda_level",
        translation_key="oxygen_level",
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        icon="mdi:weather-windy-variant",
        module=ECOLAMBDA,
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        icon="mdi:radiator",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_level",
        translation_key="fuel_level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_consumption",
        translation_key="fuel_consumption",
        icon="mdi:fire",
        native_unit_of_measurement=FLOW_KGH,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="load",
        translation_key="load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fan_power",
        translation_key="fan_power",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="optical_temp",
        translation_key="flame_intensity",
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        icon="mdi:fire",
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="feeder_temp",
        translation_key="feeder_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        translation_key="exhaust_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="return_temp",
        translation_key="return_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="lower_buffer_temp",
        translation_key="lower_buffer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="upper_buffer_temp",
        translation_key="upper_buffer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="lower_solar_temp",
        translation_key="lower_solar_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="upper_solar_temp",
        translation_key="upper_solar_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fireplace_temp",
        translation_key="fireplace_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """Represents ecoMAX sensor platform."""

    _attr_native_value: StateType | date | datetime
    _connection: EcomaxConnection
    entity_description: EntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxSensorEntityDescription
    ):
        """Initialize ecoMAX sensor object."""
        self._attr_available = False
        self._attr_native_value = None
        self._connection = connection
        self.entity_description = description

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(value)

        if self.entity_description.device_class == DEVICE_CLASS_STATE:
            # Include raw numeric value as an extra attribute for the
            # device state.
            self._attr_extra_state_attributes = {ATTR_NUMERIC: int(value)}

        self.async_write_ha_state()


@dataclass(slots=True)
class MixerSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX mixer sensor entity."""


MIXER_SENSOR_TYPES: tuple[MixerSensorEntityDescription, ...] = (
    MixerSensorEntityDescription(
        key="current_temp",
        translation_key="mixer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        translation_key="mixer_target_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="current_temp",
        translation_key="circuit_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        translation_key="circuit_target_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
)


class MixerSensor(MixerEntity, EcomaxSensor):
    """Represents mixer sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerSensorEntityDescription,
        index: int,
    ):
        """Initialize mixer sensor object."""
        self.index = index
        super().__init__(connection, description)


@dataclass(slots=True)
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX meter entity."""

    device_class: str = DEVICE_CLASS_METER


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key="fuel_burned",
        translation_key="total_fuel_burned",
        always_available=True,
        filter_fn=lambda x: aggregate(x, seconds=30),
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda x: x,
    ),
)


class EcomaxMeter(RestoreSensor, EcomaxSensor):
    """Represents ecoMAX sensor that restores previous value."""

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""
        await super().async_added_to_hass()
        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_sensor_data.native_value
            self._attr_native_unit_of_measurement = (
                last_sensor_data.native_unit_of_measurement
            )
        else:
            self._attr_native_value = 0.0

    async def async_calibrate_meter(self, value) -> None:
        """Calibrate meter state."""
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_reset_meter(self):
        """Reset stored value."""
        self._attr_native_value = 0.0
        self.async_write_ha_state()

    async def async_update(self, value=None) -> None:
        """Update meter state."""
        if value is not None:
            self._attr_native_value += value
            self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self.entity_description.value_fn(self._attr_native_value)


@dataclass(kw_only=True, slots=True)
class RegdataSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes RegData sensor entity."""

    key: int
    product_ids: set[int]


REGDATA_SENSOR_TYPES: tuple[RegdataSensorEntityDescription, ...] = (
    RegdataSensorEntityDescription(
        key=227,
        translation_key="ash_pan_full",
        icon="mdi:tray-alert",
        native_unit_of_measurement=PERCENTAGE,
        product_ids={ProductId.ECOMAX_860P3_O},
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
)


class RegdataSensor(EcomaxSensor):
    """Represents RegData sensor platform."""

    @property
    def device(self) -> RegulatorData:
        """Return device object."""
        return self.connection.device.regdata


def get_by_product_id(
    product_id: int, descriptions: Iterable[RegdataSensorEntityDescription]
) -> Generator[RegdataSensorEntityDescription, None, None]:
    """Get descriptions by product id."""
    for description in descriptions:
        if product_id in description.product_ids:
            yield description


def get_by_product_type(
    product_type: ProductType, descriptions: Iterable[EcomaxSensorEntityDescription]
) -> Generator[EcomaxSensorEntityDescription, None, None]:
    """Get descriptions by product type."""
    for description in descriptions:
        if product_type in description.product_types:
            yield description


def get_by_modules(
    connected_modules: ConnectedModules,
    descriptions: Iterable[EcomaxSensorEntityDescription],
) -> Generator[EcomaxSensorEntityDescription, None, None]:
    """Get descriptions by modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def async_setup_ecomax_sensors(connection: EcomaxConnection) -> list[EcomaxSensor]:
    """Setup ecoMAX sensors."""
    return [
        EcomaxSensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SENSOR_TYPES),
        )
    ]


def async_setup_ecomax_meters(connection: EcomaxConnection) -> list[EcomaxMeter]:
    """Setup ecoMAX meters."""
    return [
        EcomaxMeter(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, METER_TYPES),
        )
    ]


def async_setup_regdata_sensors(connection: EcomaxConnection) -> list[RegdataSensor]:
    """Setup RegData sensors."""
    return [
        RegdataSensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(
                connection.product_type,
                get_by_product_id(connection.product_id, REGDATA_SENSOR_TYPES),
            ),
        )
    ]


def async_setup_mixer_sensors(connection: EcomaxConnection) -> list[MixerSensor]:
    """Setup mixer sensors."""
    entities: list[MixerSensor] = []

    for index in connection.device.mixers.keys():
        entities.extend(
            MixerSensor(connection, description, index)
            for description in get_by_modules(
                connection.device.modules,
                get_by_product_type(connection.product_type, MIXER_SENSOR_TYPES),
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of sensor platform...")

    entities: list[EcomaxSensor] = []

    # Add ecoMAX sensors.
    entities.extend(async_setup_ecomax_sensors(connection))

    # Add device-specific sensors.
    if (
        regdata := async_setup_regdata_sensors(connection)
    ) and await connection.async_setup_regdata():
        # If there are device-specific sensors, setup regulator data.
        entities.extend(regdata)

    # Add mixer/circuit sensors.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_sensors(connection))

    # Add ecoMAX meters.
    if meters := async_setup_ecomax_meters(connection):
        entities.extend(meters)
        platform = async_get_current_platform()
        platform.async_register_entity_service(
            SERVICE_RESET_METER, {}, "async_reset_meter"
        )
        platform.async_register_entity_service(
            SERVICE_CALIBRATE_METER,
            {vol.Required(ATTR_VALUE): cv.positive_float},
            "async_calibrate_meter",
        )

    return async_add_entities(entities)
