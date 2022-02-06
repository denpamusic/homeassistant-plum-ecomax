"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import EcoMAX

from .const import DOMAIN
from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    switches = [
        EcomaxSwitch("boiler_control", "Regulator Switch"),
        EcomaxSwitch("heating_weather_control", "Weather Control Switch"),
        EcomaxSwitch("water_heater_disinfection", "Water Heater Disinfection Switch"),
        EcomaxSwitch("water_heater_work_mode", "Water Heater Pump Switch", off=0, on=2),
        EcomaxSwitch("summer_mode", "Summer Mode Switch"),
        EcomaxSwitch("control_mode", "Fuzzy Logic Switch"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(switches, async_add_entities)


class EcomaxSwitch(EcomaxEntity, SwitchEntity):
    def __init__(self, id_: str, name: str, off: int = 0, on: int = 1):
        super().__init__(id_=id_, name=name)
        self._on = on
        self._off = off

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        self.set_attribute(self._id, self._on)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        self.set_attribute(self._id, self._off)
        self.async_write_ha_state()

    async def update_entity(self, ecomax: EcoMAX):
        """Set up ecoMAX device instance."""
        await super().update_entity(ecomax)
        attr = self.get_attribute(self._id)
        if attr is not None:
            state = attr.value == self._on
            if state != self._state:
                self._state = state
                self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return switch state."""
        attr = self.get_attribute(self._id)
        if attr is not None:
            return attr.value == self._on

        return False
