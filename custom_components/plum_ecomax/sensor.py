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
import homeassistant.util.dt as dt_util
from pyplumio.const import ProductType
from pyplumio.filters import aggregate, on_change, throttle
from pyplumio.structures.modules import ConnectedModules
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_VALUE,
    DOMAIN,
    ECOLAMBDA,
    FLOW_KGH,
    MODULE_A,
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
    product_types: set[ProductType]


@dataclass
class EcomaxSensorEntityDescription(
    SensorEntityDescription, EcomaxSensorEntityAdditionalKeys
):
    """Describes ecoMAX sensor entity."""

    filter_fn: Callable[[Any], Any] = on_change
    module: str = MODULE_A


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
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
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:eye",
        value_fn=lambda x: EM_TO_HA_STATE[x] if x in EM_TO_HA_STATE else STATE_UNKNOWN,
        translation_key="ecomax_state",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key=ATTR_PASSWORD,
        name="Service password",
        icon="mdi:form-textbox-password",
        value_fn=lambda x: x,
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        name="Software version",
        value_fn=lambda x: x.module_a,
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key=ATTR_PRODUCT,
        name="UID",
        value_fn=lambda x: x.uid,
        entity_category=EntityCategory.DIAGNOSTIC,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key="lambda_level",
        name="Oxygen level",
        icon="mdi:weather-windy-variant",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        module=ECOLAMBDA,
        native_precision=1,
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
    ),
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        icon="mdi:radiator",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_precision=2,
        value_fn=lambda x: x,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxSensorEntityDescription(
        key="fuel_level",
        name="Fuel level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxSensorEntityDescription(
        key="load",
        name="Load",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
        product_types={ProductType.ECOMAX_P},
    ),
    EcomaxSensorEntityDescription(
        key="fan_power",
        name="Fan power",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_precision=1,
        value_fn=lambda x: x,
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
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
        product_types={ProductType.ECOMAX_P},
    ),
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
        product_types={ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_I},
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
        product_types={ProductType.ECOMAX_I},
    ),
)


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


@dataclass
class MixerSensorEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX mixer sensor entity."""


MIXER_SENSOR_TYPES: tuple[MixerSensorEntityDescription, ...] = (
    MixerSensorEntityDescription(
        key="current_temp",
        name="Mixer temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        product_types={ProductType.ECOMAX_P},
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        name="Mixer target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        product_types={ProductType.ECOMAX_P},
    ),
    MixerSensorEntityDescription(
        key="current_temp",
        name="Circuit temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        product_types={ProductType.ECOMAX_I},
    ),
    MixerSensorEntityDescription(
        key="target_temp",
        name="Circuit target temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_precision=1,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
        product_types={ProductType.ECOMAX_I},
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


@dataclass
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX meter entity."""


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key="fuel_burned",
        name="Total fuel burned",
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.WEIGHT,
        native_precision=2,
        value_fn=lambda x: x,
        filter_fn=lambda x: aggregate(x, seconds=30),
        product_types={ProductType.ECOMAX_P},
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

    async def async_update(self, value=None) -> None:
        """Update meter state."""
        if value is not None:
            self._attr_native_value += value
            self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self._attr_native_value)


def has_meters(entities: Iterable[EcomaxEntity]) -> bool:
    """Determines if entities collection has meters in it."""
    return any(entity for entity in entities if isinstance(entity, EcomaxMeter))


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


def async_setup_ecomax_sensors(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup ecoMAX sensors."""
    entities.extend(
        EcomaxSensor(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SENSOR_TYPES),
        )
    )


def async_setup_ecomax_meters(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup ecoMAX meters."""
    entities.extend(
        EcomaxMeter(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, METER_TYPES),
        )
    )


def async_setup_mixer_sensors(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup mixer sensors."""
    for index in connection.device.mixers.keys():
        entities.extend(
            MixerSensor(connection, description, index)
            for description in get_by_modules(
                connection.device.modules,
                get_by_product_type(connection.product_type, MIXER_SENSOR_TYPES),
            )
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of sensor platform...")

    entities: list[EcomaxEntity] = []

    # Add ecoMAX sensors and meters.
    async_setup_ecomax_sensors(connection, entities)
    async_setup_ecomax_meters(connection, entities)

    # Add mixer/circuit sensors.
    if connection.has_mixers and await connection.setup_mixers():
        async_setup_mixer_sensors(connection, entities)

    if has_meters(entities):
        # If there's meters, setup services for them.
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
