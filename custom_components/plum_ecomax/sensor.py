"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
import dataclasses
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
import homeassistant.util.dt as dt_util
from pyplumio.devices import Mixer
from pyplumio.helpers.filters import aggregate, on_change, throttle
from pyplumio.helpers.product_info import ConnectedModules, ProductType
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_FUEL_BURNED,
    ATTR_LAMBDA_LEVEL,
    ATTR_MIXERS,
    ATTR_MODULE_LAMBDA,
    ATTR_MODULES,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_VALUE,
    DOMAIN,
    FLOW_KGH,
)
from .entity import EcomaxEntity, MixerEntity

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"

STATE_FANNING: Final = "fanning"
STATE_KINDLING: Final = "kindling"
STATE_HEATING: Final = "heating"
STATE_BURNING_OFF: Final = "burning_off"
STATE_ALERT: Final = "alert"
STATE_UNKNOWN: Final = "unknown"

EM_TO_HA_STATE: dict[int, str] = {
    0: STATE_OFF,
    1: STATE_FANNING,
    2: STATE_KINDLING,
    3: STATE_HEATING,
    4: STATE_PAUSED,
    5: STATE_IDLE,
    6: STATE_STANDBY,
    7: STATE_BURNING_OFF,
    8: STATE_ALERT,
    23: STATE_FANNING,
}

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxSensorEntityAdditionalKeys:
    """Additional keys for ecoMAX sensor entity description."""

    value_fn: Callable[[Any], Any]


@dataclass
class EcomaxSensorEntityDescription(
    SensorEntityDescription, EcomaxSensorEntityAdditionalKeys
):
    """Describes ecoMAX sensor entity."""

    filter_fn: Callable[[Any], Any] = on_change


COMMON_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        name="Heating temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        name="Water heater temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        name="Outside temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        name="Heating target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        name="Water heater target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:eye",
        value_fn=lambda x: EM_TO_HA_STATE[x] if x in EM_TO_HA_STATE else STATE_UNKNOWN,
        translation_key="ecomax_state",
    ),
    EcomaxSensorEntityDescription(
        key=ATTR_PASSWORD,
        name="Service password",
        icon="mdi:form-textbox-password",
        value_fn=lambda x: x,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        name="Software version",
        value_fn=lambda x: x.module_a,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EcomaxSensorEntityDescription(
        key=ATTR_PRODUCT,
        name="UID",
        value_fn=lambda x: x.uid,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

ECOMAX_I_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="lower_solar_temp",
        name="Lower solar temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="upper_solar_temp",
        name="Upper solar temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="fireplace_temp",
        name="Fireplace temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)

ECOMAX_P_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        icon="mdi:radiator",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_precision=2,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_level",
        name="Fuel level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_consumption",
        name="Fuel consumption",
        icon="mdi:fire",
        native_unit_of_measurement=FLOW_KGH,
        state_class=SensorStateClass.MEASUREMENT,
        native_precision=2,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="load",
        name="Load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fan_power",
        name="Fan power",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_precision=1,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="optical_temp",
        name="Flame intensity",
        icon="mdi:fire",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="feeder_temp",
        name="Feeder temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        name="Exhaust temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="return_temp",
        name="Return temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="lower_buffer_temp",
        name="Lower buffer temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="upper_buffer_temp",
        name="Upper buffer temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)

SENSOR_TYPES: dict[int, tuple[EcomaxMeterEntityDescription, ...]] = {
    ProductType.ECOMAX_I: COMMON_SENSOR_TYPES + ECOMAX_I_SENSOR_TYPES,
    ProductType.ECOMAX_P: COMMON_SENSOR_TYPES + ECOMAX_P_SENSOR_TYPES,
}

MODULE_LAMBDA_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key=ATTR_LAMBDA_LEVEL,
        name="Oxygen level",
        icon="mdi:weather-windy-variant",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)

MODULE_SENSOR_TYPES: dict[str, tuple[EcomaxSensorEntityDescription, ...]] = {
    ATTR_MODULE_LAMBDA: MODULE_LAMBDA_SENSOR_TYPES
}


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """Represents ecoMAX sensor platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_native_value: StateType | date | datetime

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxSensorEntityDescription
    ):
        """Initialize ecoMAX sensor object."""
        self._connection = connection
        self.entity_description = description
        self._attr_available = False
        self._attr_native_value = None

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(value)
        self.async_write_ha_state()


ECOMAX_I_MIXER_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="current_temp",
        name="Circuit temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="target_temp",
        name="Circuit target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)


ECOMAX_P_MIXER_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="current_temp",
        name="Mixer temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="target_temp",
        name="Mixer target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)

MIXER_SENSOR_TYPES: dict[ProductType, tuple[EcomaxSensorEntityDescription, ...]] = {
    ProductType.ECOMAX_I: ECOMAX_I_MIXER_SENSOR_TYPES,
    ProductType.ECOMAX_P: ECOMAX_P_MIXER_SENSOR_TYPES,
}


class MixerSensor(MixerEntity, EcomaxSensor):
    """Represents mixer sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxSensorEntityDescription,
        index: int,
    ):
        """Initialize mixer sensor object."""
        self.index = index
        super().__init__(connection, description)


@dataclass
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX meter entity."""


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key=ATTR_FUEL_BURNED,
        name="Total fuel burned",
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.WEIGHT,
        native_precision=2,
        value_fn=lambda x: x,
        filter_fn=lambda x: aggregate(x, seconds=30),
    ),
)


class EcomaxMeter(RestoreSensor, EcomaxSensor):
    """Represents ecoMAX sensor that restores previous value."""

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxSensorEntityDescription
    ):
        """Initialize ecoMAX meter object."""
        super().__init__(connection, description)
        self._attr_available = True

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
        if self.state_class == SensorStateClass.TOTAL:
            self._attr_last_reset = dt_util.utcnow()

        self._attr_native_value = 0.0
        self.async_write_ha_state()

    async def async_update(self, value) -> None:
        """Update meter state."""
        self._attr_native_value += value
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self._attr_native_value)


def setup_mixer_entities(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup mixer sensors."""
    mixers: dict[int, Mixer] = connection.device.data[ATTR_MIXERS]
    for index in mixers.keys():
        entities.extend(
            MixerSensor(connection, description, index)
            for description in MIXER_SENSOR_TYPES[connection.product_type]
        )


def setup_module_entities(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup module-dependent sensors."""
    modules: ConnectedModules = connection.device.data[ATTR_MODULES]
    for module, version in dataclasses.asdict(modules).items():
        if version is not None and module in MODULE_SENSOR_TYPES:
            entities.extend(
                EcomaxSensor(connection, description)
                for description in MODULE_SENSOR_TYPES[module]
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of sensor platform...")

    async def _async_setup_entities(product_type: ProductType) -> list[EcomaxEntity]:
        """Add sensor entites."""
        entities: list[EcomaxEntity] = []

        # Add ecoMAX sensors.
        entities.extend(
            EcomaxSensor(connection, description)
            for description in SENSOR_TYPES[product_type]
        )

        # Add module-dependent sensors.
        setup_module_entities(connection, entities)

        # Add mixer/circuit sensors.
        if connection.has_mixers and await connection.setup_mixers():
            setup_mixer_entities(connection, entities)

        # Add meter sensors.
        if product_type == ProductType.ECOMAX_P:
            entities.extend(
                EcomaxMeter(connection, description) for description in METER_TYPES
            )

            # Setup services.
            platform = async_get_current_platform()
            platform.async_register_entity_service(
                SERVICE_RESET_METER, {}, "async_reset_meter"
            )
            platform.async_register_entity_service(
                SERVICE_CALIBRATE_METER,
                {vol.Required(ATTR_VALUE): cv.positive_float},
                "async_calibrate_meter",
            )

        return entities

    return async_add_entities(await _async_setup_entities(connection.product_type))
