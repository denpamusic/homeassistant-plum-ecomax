"""Platform for sensor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, astuple, dataclass
from functools import partial
import logging
from typing import Any, Final, cast, override

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
    Platform,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import StateType
from pyplumio.const import DeviceState, ProductType
from pyplumio.filters import aggregate, deadband, on_change, throttle
from pyplumio.structures.modules import ConnectedModules
import voluptuous as vol

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import (
    ATTR_BURNED_SINCE_LAST_UPDATE,
    ATTR_NUMERIC_STATE,
    ATTR_VALUE,
    DEVICE_CLASS_METER,
    DeviceType,
    ModuleType,
)
from .entity import (
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    RegdataEntity,
    ThermostatEntity,
    async_get_by_modules,
    async_get_by_product_type,
    async_get_custom_entities,
)

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

UPDATE_INTERVAL: Final = 10

DEFAULT_TOLERANCE: Final = 0.1

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxSensorEntityDescription(EcomaxEntityDescription, SensorEntityDescription):
    """Describes an ecoMAX sensor."""

    value_fn: Callable[[Any], Any]


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="heating_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="water_heater_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="outside_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="heating_target",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="water_heater_target",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="state",
        device_class=SensorDeviceClass.ENUM,
        translation_key="ecomax_state",
        value_fn=lambda x: EM_TO_HA_STATE.get(x, STATE_UNKNOWN),
    ),
    EcomaxSensorEntityDescription(
        key="password",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="service_password",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        entity_category=EntityCategory.DIAGNOSTIC,
        translation_key="connected_modules",
        value_fn=lambda x: len([value for value in astuple(x) if value is not None]),
    ),
    EcomaxSensorEntityDescription(
        key="lambda_level",
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        module=ModuleType.ECOLAMBDA,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="oxygen_level",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="boiler_power",
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="boiler_power",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_level",
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        translation_key="fuel_level",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_consumption",
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=0.001), seconds=UPDATE_INTERVAL
        ),
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        translation_key="fuel_consumption",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="boiler_load",
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="boiler_load",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fan_power",
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="fan_power",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="optical_temp",
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=PERCENTAGE,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="flame_intensity",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="feeder_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="feeder_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="exhaust_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="return_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="return_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="lower_buffer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="lower_buffer_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="upper_buffer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="upper_buffer_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="lower_solar_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="lower_solar_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="upper_solar_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="upper_solar_temp",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fireplace_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="fireplace_temp",
        value_fn=lambda x: x,
    ),
)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """Represents an ecoMAX sensor."""

    entity_description: EcomaxSensorEntityDescription

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(value)

        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            # Include raw numeric value as an extra attribute for the
            # device state.
            self._attr_extra_state_attributes = {ATTR_NUMERIC_STATE: int(value)}

        if isinstance(value, ConnectedModules):
            self._attr_extra_state_attributes = {
                key: value for key, value in asdict(value).items() if value is not None
            }

        self.async_write_ha_state()


@callback
def async_setup_ecomax_sensors(connection: EcomaxConnection) -> list[EcomaxSensor]:
    """Set up the ecoMAX sensors."""
    return [
        EcomaxSensor(connection, description)
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(connection.product_type, SENSOR_TYPES),
        )
    ]


@callback
def async_setup_custom_ecomax_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[EcomaxSensor]:
    """Set up the custom ecoMAX sensors."""
    description_partial = partial(EcomaxSensorEntityDescription, value_fn=lambda x: x)
    return [
        EcomaxSensor(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.SENSOR,
            source_device=DeviceType.ECOMAX,
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


@dataclass(frozen=True, kw_only=True)
class MixerSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes a mixer sensor."""


MIXER_SENSOR_TYPES: tuple[MixerSensorEntityDescription, ...] = (
    MixerSensorEntityDescription(
        key="current_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="mixer_temp",
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="mixer_target_temp",
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="current_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(
            deadband(x, tolerance=DEFAULT_TOLERANCE), seconds=UPDATE_INTERVAL
        ),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="circuit_temp",
        value_fn=lambda x: x,
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        translation_key="circuit_target_temp",
        value_fn=lambda x: x,
    ),
)


class MixerSensor(MixerEntity, EcomaxSensor):
    """Represents a mixer sensor."""

    entity_description: MixerSensorEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: MixerSensorEntityDescription,
        index: int,
    ):
        """Initialize a new mixer sensor."""
        self.index = index
        super().__init__(connection, description)


@dataclass(frozen=True, kw_only=True)
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes an ecoMAX meter entity."""


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key="fuel_burned",
        always_available=True,
        filter_fn=lambda x: aggregate(x, seconds=30, sample_size=50),
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        translation_key="total_fuel_burned",
        value_fn=lambda x: x,
    ),
)


@callback
def async_setup_mixer_sensors(connection: EcomaxConnection) -> list[MixerSensor]:
    """Set up the mixer sensors."""
    return [
        MixerSensor(connection, description, index)
        for index in connection.device.mixers
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(connection.product_type, MIXER_SENSOR_TYPES),
        )
    ]


@callback
def async_setup_custom_mixer_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[MixerSensor]:
    """Set up the custom mixer sensors."""
    description_partial = partial(MixerSensorEntityDescription, value_fn=lambda x: x)
    return [
        MixerSensor(connection, description, index)
        for description, index in async_get_custom_entities(
            platform=Platform.SENSOR,
            source_device=DeviceType.MIXER,
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


class EcomaxMeter(EcomaxSensor, RestoreSensor):
    """Represents an ecoMAX sensor that restores previous value."""

    _attr_device_class = DEVICE_CLASS_METER  # type: ignore[assignment]
    _unrecorded_attributes = frozenset({ATTR_BURNED_SINCE_LAST_UPDATE})
    entity_description: EcomaxMeterEntityDescription

    @override
    async def async_added_to_hass(self) -> None:
        """Restore native value."""
        await super().async_added_to_hass()
        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_sensor_data.native_value
            self._attr_native_unit_of_measurement = (
                last_sensor_data.native_unit_of_measurement
            )
        else:
            self._attr_native_value = 0.0

    async def async_calibrate_meter(self, value: float) -> None:
        """Calibrate meter state."""
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_reset_meter(self) -> None:
        """Reset stored value."""
        self._attr_native_value = 0.0
        self.async_write_ha_state()

    async def async_update(self, value: float | None = None) -> None:
        """Update meter state."""
        if value is not None:
            self._attr_extra_state_attributes = {
                ATTR_BURNED_SINCE_LAST_UPDATE: value * 1000
            }
            self._attr_native_value = float(self._attr_native_value + value)
            self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return cast(float, self.entity_description.value_fn(self._attr_native_value))


@callback
def async_setup_ecomax_meters(connection: EcomaxConnection) -> list[EcomaxMeter]:
    """Set up the ecoMAX meters."""
    return [
        EcomaxMeter(connection, description)
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(connection.product_type, METER_TYPES),
        )
    ]


@dataclass(frozen=True, kw_only=True)
class RegdataSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes a regulator data sensor."""


class RegdataSensor(RegdataEntity, EcomaxSensor):
    """Represents a regulator data sensor."""

    async def async_update(self, regdata: dict[int, Any]) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(
            regdata.get(self._regdata_key, None)
        )
        self.async_write_ha_state()


@callback
def async_setup_custom_regdata_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[RegdataSensor]:
    """Set up the custom regulator data sensors."""
    description_partial = partial(RegdataSensorEntityDescription, value_fn=lambda x: x)
    return [
        RegdataSensor(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.SENSOR,
            source_device="regdata",
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


@dataclass(frozen=True, kw_only=True)
class ThermostatSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes a thermostat sensor."""


class ThermostatSensor(ThermostatEntity, EcomaxSensor):
    """Represents a thermostat sensor."""

    entity_description: ThermostatSensorEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: ThermostatSensorEntityDescription,
        index: int,
    ):
        """Initialize a new mixer sensor."""
        self.index = index
        super().__init__(connection, description)


@callback
def async_setup_custom_thermostat_sensors(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[ThermostatSensor]:
    """Set up the custom thermostat sensors."""
    description_partial = partial(
        ThermostatSensorEntityDescription, value_fn=lambda x: x
    )
    return [
        ThermostatSensor(connection, description, index)
        for description, index in async_get_custom_entities(
            platform=Platform.SENSOR,
            source_device=DeviceType.THERMOSTAT,
            config_entry=config_entry,
            description_factory=description_partial,
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Starting setup of sensor platform...")

    connection = entry.runtime_data.connection
    entities = async_setup_ecomax_sensors(connection)

    # Add custom ecoMAX sensors.
    entities += async_setup_custom_ecomax_sensors(connection, entry)

    # Add custom regulator data (device-specific) sensors.
    if (
        regdata_entities := async_setup_custom_regdata_sensors(connection, entry)
    ) and await connection.async_setup_regdata():
        entities += regdata_entities

    # Add mixer/circuit sensors.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities += async_setup_mixer_sensors(connection)
        entities += async_setup_custom_mixer_sensors(connection, entry)

    # Add thermostat sensors.
    if connection.has_thermostats and await connection.async_setup_thermostats():
        entities += async_setup_custom_thermostat_sensors(connection, entry)

    # Add ecoMAX meters.
    if meters := async_setup_ecomax_meters(connection):
        entities += meters
        platform = async_get_current_platform()
        platform.async_register_entity_service(
            SERVICE_RESET_METER, {}, "async_reset_meter"
        )
        platform.async_register_entity_service(
            SERVICE_CALIBRATE_METER,
            {vol.Required(ATTR_VALUE): cv.positive_float},
            "async_calibrate_meter",
        )

    async_add_entities(entities)
    return True
