"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE, POWER_KILO_WATT, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import EcoMAX

from .const import DOMAIN, FLOW_KGH
from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    sensors = [
        EcomaxTemperatureSensor("co_temp", "CO Temperature"),
        EcomaxTemperatureSensor("cwu_temp", "CWU Temperature"),
        EcomaxTemperatureSensor("exhaust_temp", "Exhaust Temperature"),
        EcomaxTemperatureSensor("outside_temp", "Outside Temperature"),
        EcomaxTemperatureSensor("co_target", "Target Temperature"),
        EcomaxTemperatureSensor("cwu_target", "CWU Target Temperature"),
        EcomaxTemperatureSensor("feeder_temp", "Feeder Temperature"),
        EcomaxPercentSensor("fan_power", "Fan Power"),
        EcomaxPercentSensor("fuel_level", "Fuel Level"),
        EcomaxFuelFlowSensor("fuel_flow", "Fuel Flow"),
        EcomaxTextSensor("mode", "Mode"),
        EcomaxPowerSensor("power", "Power"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxSensor(EcomaxEntity, SensorEntity):
    """ecoMAX sensor entity representation."""

    async def update_sensor(self, ecomax: EcoMAX):
        """Update sensor state. Called by connection instance."""
        attr = round(getattr(ecomax, self._id), 2)

        if attr != self._state:
            self._state = attr
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

    async def update_sensor(self, ecomax):
        """Update sensor state. Called by connection instance."""
        attr = getattr(ecomax, self._id)
        if attr != self._state:
            self._state = str(attr).lower().title()
            self.async_write_ha_state()
