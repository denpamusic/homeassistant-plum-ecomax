"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
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
from pyplumio.helpers.filters import aggregate, on_change, throttle
from pyplumio.helpers.product_info import ProductType
import voluptuous as vol

from .connection import EcomaxConnection
from .const import (
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_VALUE,
    DOMAIN,
    FLOW_KGH,
)
from .entity import EcomaxEntity, MixerEntity

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"

DEVICE_CLASS_METER: Final = "plum_ecomax__meter"
DEVICE_CLASS_STATE: Final = "plum_ecomax__mode"

STATE_FANNING: Final = "fanning"
STATE_KINDLING: Final = "kindling"
STATE_HEATING: Final = "heating"
STATE_BURNING_OFF: Final = "burning_off"
STATE_UNKNOWN: Final = "unknown"

STATES: tuple[str, ...] = (
    STATE_OFF,
    STATE_FANNING,
    STATE_KINDLING,
    STATE_HEATING,
    STATE_PAUSED,
    STATE_IDLE,
    STATE_STANDBY,
    STATE_BURNING_OFF,
)

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


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        name="Heating Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        name="Water Heater Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        name="Outside Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        name="Heating Target Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        name="Water Heater Target Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:eye",
        value_fn=lambda x: STATES[x] if x < len(STATES) else STATE_UNKNOWN,
        device_class=DEVICE_CLASS_STATE,
    ),
    EcomaxSensorEntityDescription(
        key=ATTR_PASSWORD,
        name="Service Password",
        icon="mdi:form-textbox-password",
        value_fn=lambda x: x,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EcomaxSensorEntityDescription(
        key="modules",
        name="Software Version",
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

ECOMAX_P_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        icon="mdi:radiator",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda x: round(x, 2),
    ),
    EcomaxSensorEntityDescription(
        key="fuel_level",
        name="Fuel Level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_consumption",
        name="Fuel Consumption",
        icon="mdi:fire",
        native_unit_of_measurement=FLOW_KGH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: round(x, 2),
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
        name="Fan Power",
        icon="mdi:fan",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="optical_temp",
        name="Flame Intensity",
        icon="mdi:fire",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="feeder_temp",
        name="Feeder Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        name="Exhaust Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)

ECOMAX_I_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="lower_solar_temp",
        name="Lower Solar Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="upper_solar_temp",
        name="Upper Solar Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="fireplace_temp",
        name="Fireplace Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
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
        self._attr_native_value = None

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_fn(value)
        self.async_write_ha_state()


MIXER_SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="mixer_temp",
        name="Mixer Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="mixer_target",
        name="Mixer Target Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
)


class MixerSensor(MixerEntity, EcomaxSensor):
    """Represents mixer sensor platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxSensorEntityDescription,
        mixer_number: int,
    ):
        """Initialize ecoMAX sensor object."""
        self.mixer_number = mixer_number
        super().__init__(connection, description)


@dataclass
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX meter entity."""

    device_class: str = DEVICE_CLASS_METER


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key=ATTR_FUEL_BURNED,
        name="Total Fuel Burned",
        icon="mdi:counter",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.WEIGHT,
        value_fn=lambda x: round(x, 2),
        filter_fn=lambda x: aggregate(x, seconds=30),
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


def setup_ecomax_p(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensor platform for ecoMAX P series controllers."""

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESET_METER,
        {},
        "async_reset_meter",
    )
    platform.async_register_entity_service(
        SERVICE_CALIBRATE_METER,
        {vol.Required(ATTR_VALUE): cv.positive_float},
        "async_calibrate_meter",
    )

    return async_add_entities(
        [
            *entities,
            *[
                EcomaxSensor(connection, description)
                for description in ECOMAX_P_SENSOR_TYPES
            ],
            *[EcomaxMeter(connection, description) for description in METER_TYPES],
        ],
        False,
    )


def setup_ecomax_i(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup sensor platform for ecoMAX I series controllers."""

    return async_add_entities(
        [
            *entities,
            *[
                EcomaxSensor(connection, description)
                for description in ECOMAX_I_SENSOR_TYPES
            ],
        ],
        False,
    )


def get_mixer_entities(
    connection: EcomaxConnection,
    sensor_types: tuple[EcomaxSensorEntityDescription, ...],
) -> list[MixerEntity]:
    """Setup mixers sensor platform."""
    entities: list[MixerEntity] = []
    for mixer in connection.device.data.get(ATTR_MIXERS, []):
        entities.extend(
            [
                MixerSensor(connection, description, mixer.mixer_number)
                for description in sensor_types
            ]
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[EcomaxEntity] = [
        *[EcomaxSensor(connection, description) for description in SENSOR_TYPES],
        *get_mixer_entities(connection, MIXER_SENSOR_TYPES),
    ]

    if connection.product_type == ProductType.ECOMAX_P:
        return setup_ecomax_p(connection, entities, async_add_entities)

    if connection.product_type == ProductType.ECOMAX_I:
        return setup_ecomax_i(connection, entities, async_add_entities)

    _LOGGER.error(
        "Couldn't setup platform due to unknown controller model '%s'", connection.model
    )
    return False
