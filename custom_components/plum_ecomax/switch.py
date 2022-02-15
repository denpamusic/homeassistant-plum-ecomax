"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
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
    switches = [
        EcomaxSwitch(connection, "boiler_control", "Regulator Switch"),
        EcomaxSwitch(connection, "heating_weather_control", "Weather Control Switch"),
        EcomaxSwitch(
            connection, "water_heater_disinfection", "Water Heater Disinfection Switch"
        ),
        EcomaxSwitch(
            connection,
            "water_heater_work_mode",
            "Water Heater Pump Switch",
            on=2,
            off=0,
        ),
        EcomaxSwitch(connection, "summer_mode", "Summer Mode Switch"),
        EcomaxSwitch(connection, "fuzzy_logic", "Fuzzy Logic Switch"),
    ]
    await connection.add_entities(switches, async_add_entities)


class EcomaxSwitch(EcomaxEntity, SwitchEntity):
    """ecoMAX switch entity representation.

    Attributes:
        _on -- value corresponding to enabled state
        _off -- value corresponding to disabled state
    """

    def __init__(self, *args, on: int = 1, off: int = 0):
        """Create ecoMAX switch instance.

        Keyword arguments:
            on -- value corresponding to enabled state
            off -- value corresponding to disabled state
        """
        super().__init__(*args)
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

    async def async_update_state(self) -> None:
        """Set up device instance."""
        attr = self.get_attribute(self._id)
        self._state = None if attr is None else (attr.value == self._on)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return switch state."""
        attr = self.get_attribute(self._id)
        return False if attr is None else (attr.value == self._on)
