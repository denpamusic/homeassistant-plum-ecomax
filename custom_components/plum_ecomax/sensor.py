"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    MASS_KILOGRAMS,
    PERCENTAGE,
    POWER_KILO_WATT,
    TEMP_CELSIUS,
)
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
    connection = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        EcomaxTemperatureSensor(connection, "heating_temp", "Heating Temperature"),
        EcomaxTemperatureSensor(
            connection, "water_heater_temp", "Water Heater Temperature"
        ),
        EcomaxTemperatureSensor(connection, "exhaust_temp", "Exhaust Temperature"),
        EcomaxTemperatureSensor(connection, "outside_temp", "Outside Temperature"),
        EcomaxTemperatureSensor(connection, "heating_target", "Target Temperature"),
        EcomaxTemperatureSensor(
            connection, "water_heater_target", "Water Heater Target Temperature"
        ),
        EcomaxTemperatureSensor(connection, "feeder_temp", "Feeder Temperature"),
        EcomaxPercentSensor(connection, "load", "Load"),
        EcomaxPercentSensor(connection, "fan_power", "Fan Power"),
        EcomaxPercentSensor(connection, "fuel_level", "Fuel Level"),
        EcomaxFuelConsumptionSensor(connection, "fuel_consumption", "Fuel Consumption"),
        EcomaxFuelBurnedSensor(connection, "fuel_burned", "Fuel Burned"),
        EcomaxTextSensor(connection, "mode", "Mode"),
        EcomaxTextSensor(connection, "module_a", "Software Version"),
        EcomaxPowerSensor(connection, "power", "Power"),
    ]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """ecoMAX sensor entity representation."""

    async def async_update_state(self) -> None:
        """Set up device instance."""
        attr = self.get_attribute(self._id)
        self._state = None if attr is None else round(attr, 2)
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


class EcomaxFuelConsumptionSensor(EcomaxSensor):
    """Representation of fuel consumption sensor."""

    @property
    def state_class(self) -> str:
        """Return state class."""
        return "measurement"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return FLOW_KGH


class EcomaxFuelBurnedSensor(EcomaxSensor):
    """Representation of fuel burned since last update."""

    async def async_update_state(self) -> None:
        """Set up device instance."""
        self._state = self.get_attribute(self._id)
        self.async_write_ha_state()

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return MASS_KILOGRAMS


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
        self._state = self.get_attribute(self._id)
        self.async_write_ha_state()
