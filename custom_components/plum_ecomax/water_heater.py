"""Platform for sensor integration."""
from __future__ import annotations

from typing import Any, Tuple

from homeassistant.components.water_heater import (
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterEntity,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, WATER_HEATER_MODES
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
    water_heaters = [
        EcomaxWaterHeater(connection, "water_heater", "Water Heater"),
    ]
    await connection.add_entities(water_heaters, async_add_entities)


class EcomaxWaterHeater(EcomaxEntity, WaterHeaterEntity):
    """Representation of water heater entity.

    Attributes:
        _attr_min_temp -- The minimum temperature that can be set.
        _attr_max_temp -- The maximum temperature that can be set.
        _attr_current_temperature -- The current temperature.
        _attr_target_temperature -- The temperature we are trying to reach.
        _attr_target_temperature_low -- Lower bound of the temperature we are trying to reach.
        _attr_target_temperature_high -- Upper bound of the temperature we are trying to reach.
        _attr_current_operation -- The current operation mode.
    """

    def __init__(self, *args, **kwargs):
        """Create entity instance."""
        super().__init__(*args, **kwargs)
        self._attr_min_temp = None
        self._attr_max_temp = None
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_target_temperature_low = None
        self._attr_target_temperature_high = None
        self._attr_current_operation = None

    async def async_update_state(self) -> None:
        """Set up device instance."""
        target_temp = self.get_attribute(f"{self._id}_set_temp")
        if target_temp is None:
            self._attr_min_temp = None
            self._attr_max_temp = None
            self._attr_target_temperature = None
            self._attr_target_temperature_high = None
        else:
            self._attr_min_temp = target_temp.min_
            self._attr_max_temp = target_temp.max_
            self._attr_target_temperature = target_temp.value
            self._attr_target_temperature_high = target_temp.value
            hysteresis = self.get_attribute(f"{self._id}_hysteresis")
            if hysteresis is None:
                self._attr_target_temperature_low = target_temp.value
            else:
                self._attr_target_temperature_low = target_temp.value - hysteresis.value

        self._attr_current_temperature = self.get_attribute(f"{self._id}_temp")
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = int(kwargs["temperature"])
        self.set_attribute(f"{self._id}_set_temp", temp)
        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode.

        Keyword arguments:
            operation_mode -- contains new water heater operation mode
        """
        self.set_attribute(
            f"{self._id}_work_mode", self._hass_to_ecomax_mode(operation_mode)
        )
        self.async_write_ha_state()

    @property
    def precision(self) -> float:
        """Return the precision of the system."""
        return PRECISION_WHOLE

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def current_operation(self) -> str:
        """Return current operation ie. eco, electric, performance, ..."""
        operation_mode = self.get_attribute(f"{self._id}_work_mode", default=0)
        return self._ecomax_to_hass_mode(int(operation_mode))

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return SUPPORT_TARGET_TEMPERATURE + SUPPORT_OPERATION_MODE

    @property
    def operation_list(self) -> Tuple[Any, ...]:
        """Return the list of available operation modes."""
        return WATER_HEATER_MODES

    def _ecomax_to_hass_mode(self, operation_mode: int) -> str:
        """Convert ecomax operation mode to hass.

        Keyword arguments:
            operation_mode -- operation mode taken from ecoMAX
        """
        return WATER_HEATER_MODES[operation_mode]

    def _hass_to_ecomax_mode(self, operation_mode) -> int:
        """Convert hass operation mode to ecomax.

        Keyword arguments:
            operation_mode -- operation mode taken from hass
        """
        return WATER_HEATER_MODES.index(operation_mode)
