"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

from homeassistant.components.sensor import (
    RestoreSensor,
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
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import ConfigType, StateType
import homeassistant.util.dt as dt_util
from pyplumio.helpers.filters import aggregate, on_change, throttle
import voluptuous as vol

from .connection import EcomaxConnection
from .const import DOMAIN, FLOW_KGH
from .entity import EcomaxEntity

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"

ATTR_VALUE: Final = "value"

DEVICE_CLASS_METER: Final = "plum_ecomax__meter"
DEVICE_CLASS_STATE: Final = "plum_ecomax__mode"

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

    filter_fn: Callable[[Any], Any] = on_change


SENSOR_TYPES: tuple[EcomaxSensorEntityDescription, ...] = (
    EcomaxSensorEntityDescription(
        key="heating_temp",
        name="Heating Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="water_heater_temp",
        name="Water Heater Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="exhaust_temp",
        name="Exhaust Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="outside_temp",
        name="Outside Temperature",
        icon="mdi:thermometer",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda x: round(x, 1),
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
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
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="fuel_consumption",
        name="Fuel Consumption",
        icon="mdi:fire",
        native_unit_of_measurement=FLOW_KGH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x,
        filter_fn=lambda x: throttle(on_change(x), seconds=10),
    ),
    EcomaxSensorEntityDescription(
        key="mode",
        name="Mode",
        icon="mdi:eye",
        value_fn=lambda x: STATES[x] if x < len(STATES) else STATE_UNKNOWN,
        device_class=DEVICE_CLASS_STATE,
    ),
    EcomaxSensorEntityDescription(
        key="power",
        name="Power",
        icon="mdi:radiator",
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
    EcomaxSensorEntityDescription(
        key="modules",
        name="Software Version",
        value_fn=lambda x: x.module_a,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EcomaxSensorEntityDescription(
        key="product",
        name="UID",
        value_fn=lambda x: x.uid,
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


@dataclass
class EcomaxMeterEntityDescription(EcomaxSensorEntityDescription):
    """Describes ecoMAX meter entity."""

    device_class: str = DEVICE_CLASS_METER


METER_TYPES: tuple[EcomaxMeterEntityDescription, ...] = (
    EcomaxMeterEntityDescription(
        key="fuel_burned",
        name="Total Fuel Burned",
        icon="mdi:counter",
        native_unit_of_measurement=MASS_KILOGRAMS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda x: round(x, 1),
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
        self._attr_native_value = self.entity_description.value_fn(
            self._attr_native_value + value
        )
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]

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
            *[EcomaxSensor(connection, description) for description in SENSOR_TYPES],
            *[EcomaxMeter(connection, description) for description in METER_TYPES],
        ],
        False,
    )
