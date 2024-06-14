"""Platform for sensor integration."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import asdict, astuple, dataclass
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
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import StateType
from pyplumio.const import DeviceState, ProductType
from pyplumio.filters import aggregate, on_change, throttle
from pyplumio.structures.modules import ConnectedModules
import voluptuous as vol

from . import (
    DescriptorT,
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    PlumEcomaxConfigEntry,
)
from .connection import EcomaxConnection
from .const import (
    ALL,
    ATTR_BURNED_SINCE_LAST_UPDATE,
    ATTR_NUMERIC_STATE,
    ATTR_REGDATA,
    ATTR_VALUE,
    DEVICE_CLASS_METER,
    FLOW_KGH,
    ModuleType,
    ProductModel,
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

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxSensorEntityDescription(SensorEntityDescription, EcomaxEntityDescription):
    """Describes an ecoMAX sensor."""

    value_fn: Callable[[Any], Any]


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        translation_key="heating_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        translation_key="water_heater_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        translation_key="outside_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        translation_key="heating_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        translation_key="water_heater_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="state",
        translation_key="ecomax_state",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda x: EM_TO_HA_STATE.get(x, STATE_UNKNOWN),
    ),
    EcomaxSensorEntityDescription(
        key="password",
        translation_key="service_password",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:form-textbox-password",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        translation_key="connected_modules",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:raspberry-pi",
        value_fn=lambda x: len([value for value in astuple(x) if value is not None]),
    ),
    EcomaxSensorEntityDescription(
        key="lambda_level",
        translation_key="oxygen_level",
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        icon="mdi:weather-windy-variant",
        module=ModuleType.ECOLAMBDA,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="boiler_power",
        translation_key="boiler_power",
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
        key="boiler_load",
        translation_key="boiler_load",
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
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


@dataclass(frozen=True, kw_only=True)
class MixerSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes a mixer sensor."""


MIXER_SENSOR_TYPES: tuple[MixerSensorEntityDescription, ...] = (
    MixerSensorEntityDescription(
        key="current_temp",
        translation_key="mixer_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        product_types={ProductType.ECOMAX_I},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
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
        translation_key="total_fuel_burned",
        always_available=True,
        filter_fn=lambda x: aggregate(x, seconds=30),
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        product_types={ProductType.ECOMAX_P},
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=lambda x: x,
    ),
)


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
        if value is not None and isinstance(self._attr_native_value, float):
            self._attr_extra_state_attributes = {
                ATTR_BURNED_SINCE_LAST_UPDATE: value * 1000
            }
            self._attr_native_value += value
            self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return cast(float, self.entity_description.value_fn(self._attr_native_value))


@dataclass(frozen=True, kw_only=True)
class RegdataSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes a regulator data sensor."""

    product_models: set[ProductModel]


STATE_CLOSING: Final = "closing"
STATE_OPENING: Final = "opening"

EM_TO_HA_MIXER_VALVE_STATE: dict[int, str] = {
    0: STATE_OFF,
    1: STATE_CLOSING,
    2: STATE_OPENING,
}

REGDATA_SENSOR_TYPES: tuple[RegdataSensorEntityDescription, ...] = (
    RegdataSensorEntityDescription(
        key="227",
        translation_key="ash_pan_full",
        icon="mdi:tray-alert",
        native_unit_of_measurement=PERCENTAGE,
        product_models={ProductModel.ECOMAX_860P3_O},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
    RegdataSensorEntityDescription(
        key="215",
        translation_key="ash_pan_full",
        icon="mdi:tray-alert",
        native_unit_of_measurement=PERCENTAGE,
        product_models={ProductModel.ECOMAX_860P3_S_LITE},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
    RegdataSensorEntityDescription(
        key="223",
        translation_key="ash_pan_full",
        icon="mdi:tray-alert",
        native_unit_of_measurement=PERCENTAGE,
        product_models={ProductModel.ECOMAX_860P6_O},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
    RegdataSensorEntityDescription(
        key="134",
        translation_key="mixer_valve_opening_percentage",
        filter_fn=lambda x: throttle(on_change(x), seconds=UPDATE_INTERVAL),
        native_unit_of_measurement=PERCENTAGE,
        product_models={ProductModel.ECOMAX_860P6_O},
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda x: x,
    ),
    RegdataSensorEntityDescription(
        key="139",
        translation_key="mixer_valve_state",
        device_class=SensorDeviceClass.ENUM,
        product_models={ProductModel.ECOMAX_860P6_O},
        value_fn=lambda x: EM_TO_HA_MIXER_VALVE_STATE.get(x, STATE_UNKNOWN),
    ),
)


class RegdataSensor(EcomaxSensor):
    """Represents a regulator data sensor."""

    _regdata_key: int

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxEntityDescription
    ) -> None:
        """Initialize a new regdata entity."""
        self._regdata_key = int(description.key)
        super().__init__(connection, description)

    async def async_update(self, regdata: dict[int, Any]) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(
            regdata.get(self._regdata_key, None)
        )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to regdata event."""
        description = self.entity_description
        handler = description.filter_fn(self.async_update)

        async def async_set_available(regdata: dict[int, Any]) -> None:
            """Mark entity as available."""
            if self._regdata_key in regdata:
                self._attr_available = True

        if ATTR_REGDATA in self.device.data:
            await async_set_available(self.device.data[ATTR_REGDATA])
            await handler(self.device.data[ATTR_REGDATA])

        self.device.subscribe_once(ATTR_REGDATA, async_set_available)
        self.device.subscribe(ATTR_REGDATA, handler)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from regdata event."""
        self.device.unsubscribe(ATTR_REGDATA, self.async_update)

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        return self._regdata_key in self.device.data.get(ATTR_REGDATA, {})


def get_by_product_type(
    product_type: ProductType, descriptions: Iterable[DescriptorT]
) -> Generator[DescriptorT, None, None]:
    """Get descriptions by the product type."""
    for description in descriptions:
        if (
            description.product_types == ALL
            or product_type in description.product_types
        ):
            yield description


def get_by_modules(
    connected_modules: ConnectedModules,
    descriptions: Iterable[DescriptorT],
) -> Generator[DescriptorT, None, None]:
    """Get descriptions by connected modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def get_by_product_model(
    product_model: str, descriptions: Iterable[RegdataSensorEntityDescription]
) -> Generator[RegdataSensorEntityDescription, None, None]:
    """Get descriptions by the product model."""
    for description in descriptions:
        if product_model in description.product_models:
            yield description


def async_setup_ecomax_sensors(connection: EcomaxConnection) -> list[EcomaxSensor]:
    """Set up the ecoMAX sensors."""
    return [
        EcomaxSensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SENSOR_TYPES),
        )
    ]


def async_setup_ecomax_meters(connection: EcomaxConnection) -> list[EcomaxMeter]:
    """Set up the ecoMAX meters."""
    return [
        EcomaxMeter(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, METER_TYPES),
        )
    ]


def async_setup_regdata_sensors(connection: EcomaxConnection) -> list[RegdataSensor]:
    """Set up the regulator data sensors."""
    return [
        RegdataSensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(
                connection.product_type,
                get_by_product_model(connection.model, REGDATA_SENSOR_TYPES),
            ),
        )
    ]


def async_setup_mixer_sensors(connection: EcomaxConnection) -> list[MixerSensor]:
    """Set up the mixer sensors."""
    entities: list[MixerSensor] = []
    for index in connection.device.mixers:
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
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = entry.runtime_data.connection
    _LOGGER.debug("Starting setup of sensor platform...")

    entities: list[EcomaxSensor] = []

    # Add ecoMAX sensors.
    entities.extend(async_setup_ecomax_sensors(connection))

    # Add regulator data (device-specific) sensors.
    if (
        regdata := async_setup_regdata_sensors(connection)
    ) and await connection.async_setup_regdata():
        # Set up the regulator data sensors, if there are any.
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

    async_add_entities(entities)
    return True
