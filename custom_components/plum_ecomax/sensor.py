"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE, POWER_KILO_WATT, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, FLOW_KGH
from .entity import EcomaxEntity


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

    sensors = [
        EcomaxTemperatureSensor("heating_temp", "Heating Temperature"),
        EcomaxTemperatureSensor("water_heater_temp", "Water Heater Temperature"),
        EcomaxTemperatureSensor("exhaust_temp", "Exhaust Temperature"),
        EcomaxTemperatureSensor("outside_temp", "Outside Temperature"),
        EcomaxTemperatureSensor("heating_target", "Target Temperature"),
        EcomaxTemperatureSensor(
            "water_heater_target", "Water Heater Target Temperature"
        ),
        EcomaxTemperatureSensor("feeder_temp", "Feeder Temperature"),
        EcomaxPercentSensor("load", "Load"),
        EcomaxPercentSensor("fan_power", "Fan Power"),
        EcomaxPercentSensor("fuel_level", "Fuel Level"),
        EcomaxFuelFlowSensor("fuel_consumption", "Fuel Consumption"),
        EcomaxTextSensor("mode", "Mode"),
        EcomaxTextSensor("module_a", "Software Version"),
        EcomaxPowerSensor("power", "Power"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """ecoMAX sensor entity representation."""

    async def async_update_state(self) -> None:
        """Set up device instance."""
        attr = self.get_attribute(self._id)
        if attr is not None:
            self._state = round(attr, 2)
            self.async_write_ha_state()

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state


class EcomaxTemperatureSensor(EcomaxSensor):
    """Representation of temperature sensor."""

    @property
    def state_class(self) -> str:
        """Return state class."""
        return "measurement"

    @property
    def device_class(self) -> str:
        """Return device class."""
        return "temperature"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS


class EcomaxPercentSensor(EcomaxSensor):
    """Representation of percent sensor."""

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return PERCENTAGE


class EcomaxFuelFlowSensor(EcomaxSensor):
    """Representation of fuel flow sensor."""

    @property
    def state_class(self) -> str:
        """Return state class."""
        return "measurement"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return FLOW_KGH


class EcomaxPowerSensor(EcomaxSensor):
    """Representation of heat power sensor."""

    @property
    def icon(self) -> str:
        """Return sensor icon."""
        return "mdi:radiator"

    @property
    def state_class(self) -> str:
        """Return state class."""
        return "measurement"

    @property
    def device_class(self) -> str:
        """Return device class."""
        return "power"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return POWER_KILO_WATT


class EcomaxTextSensor(EcomaxSensor):
    """Representation of text sensor."""

    async def async_update_state(self) -> None:
        """Update sensor state. Called by connection instance."""
        attr = self.get_attribute(self._id)
        if attr is not None:
            self._state = attr
            self.async_write_ha_state()
