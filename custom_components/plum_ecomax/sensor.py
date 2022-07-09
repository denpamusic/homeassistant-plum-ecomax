"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    MASS_KILOGRAMS,
    PERCENTAGE,
    POWER_KILO_WATT,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_STANDBY,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, StateType
from pyplumio.helpers.filters import debounce
from pyplumio.helpers.typing import ValueCallback

from .connection import EcomaxConnection
from .const import DOMAIN, FLOW_KGH
from .entity import EcomaxEntity

STATE_FANNING: Final = "fanning"
STATE_KINDLING: Final = "kindling"
STATE_HEATING: Final = "heating"
STATE_UNKNOWN: Final = "unknown"

STATES: list[str] = [
    STATE_OFF,
    STATE_FANNING,
    STATE_KINDLING,
    STATE_HEATING,
    STATE_PAUSED,
    STATE_IDLE,
    STATE_STANDBY,
]


@dataclass
class EcomaxSensorEntityAdditionalKeys:
    """Additional keys for ecoMAX sensor entity description."""

    value_fn: Callable[[Any], Any]


@dataclass
class EcomaxSensorEntityDescription(
    SensorEntityDescription, EcomaxSensorEntityAdditionalKeys
):
    """Describes ecoMAX sensor entity."""


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        name="Heating Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        name="Water Heater Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        name="Exhaust Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        name="Outside Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="heating_target",
        name="Heating Target Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_target",
        name="Water Heater Target Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
    ),
    EcomaxSensorEntityDescription(
        key="feeder_temp",
        name="Feeder Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
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
        key="fuel_level",
        name="Fuel Level",
        icon="mdi:gas-station",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="optical_temp",
        name="Flame Intensity",
        icon="mdi:fire",
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
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="fuel_burned",
        name="Fuel Burned Since Last Update",
        icon="mdi:fire",
        native_unit_of_measurement=MASS_KILOGRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:eye",
        value_fn=lambda x: STATES[x] if x < len(STATES) else STATE_UNKNOWN,
    ),
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=POWER_KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="password",
        name="Service Password",
        icon="mdi:form-textbox-password",
        value_fn=lambda x: x,
        entity_category=EntityCategory.DIAGNOSTIC,
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

    @property
    def callbacks(self) -> dict[str, ValueCallback]:
        """Return callback functions mapped with value names."""
        return {self.entity_description.key: debounce(self.async_update, min_calls=3)}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]
    return async_add_entities(
        [EcomaxSensor(connection, description) for description in SENSOR_TYPES], False
    )
