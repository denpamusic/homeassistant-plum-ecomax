"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, FLOW_KGH
from .entity import EcomaxEntity


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
        key="mode",
        name="Mode",
        icon="mdi:eye",
        value_fn=lambda x: x,
    ),
    EcomaxSensorEntityDescription(
        key="module_a",
        name="Software Version",
        icon="mdi:package-down",
        value_fn=lambda x: x,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=POWER_KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda x: x,
    ),
)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """Representation of ecoMAX sensor."""

    def __init__(self, connection, description: EcomaxSensorEntityDescription):
        self._connection = connection
        self.entity_description = description
        self._attr_native_value = None

    async def async_update(self) -> None:
        """Retrieve latest state."""
        value = getattr(self._connection.ecomax, self.entity_description.key, None)
        self._attr_native_value = (
            self.entity_description.value_fn(value) if value is not None else value
        )
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    connection = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [EcomaxSensor(connection, description) for description in SENSOR_TYPES], False
    )
