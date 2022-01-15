"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterEntity,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import EcoMAX

from .const import DOMAIN, ECOMAX_STATE_NORMAL, ECOMAX_STATE_OFF, ECOMAX_STATE_PRIORITY
from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    switches = [
        EcomaxWaterHeater("cwu", "Water Heater"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(switches, async_add_entities)


class EcomaxWaterHeater(EcomaxEntity, WaterHeaterEntity):

    _ecomax: EcoMAX = None
    _attr_min_temp: float = 0
    _attr_max_temp: float = 0
    _attr_current_temp: float = 0
    _attr_target_temperature: float = 0
    _attr_target_temperature_low: float = 0
    _attr_target_temperature_high: float = 0
    _attr_current_operation: str = STATE_OFF

    async def update_sensor(self, ecomax: EcoMAX):
        """Set up ecoMAX device instance."""
        if self._ecomax is None:
            self._ecomax = ecomax

        target_temp = getattr(ecomax, f"{self._id}_set_temp")
        current_temp = getattr(ecomax, f"{self._id}_temp")
        hysteresis = getattr(ecomax, f"{self._id}_hysteresis")

        for data in [target_temp, current_temp, hysteresis]:
            if data is None:
                return

        self._attr_min_temp = round(target_temp.min_, 0)
        self._attr_max_temp = round(target_temp.max_, 0)
        self._attr_current_temperature = round(current_temp, 0)
        self._attr_target_temperature = round(target_temp.value, 0)
        self._attr_target_temperature_low = round(
            target_temp.value - hysteresis.value, 0
        )
        self._attr_target_temperature_high = round(target_temp.value, 0)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if self._water_heater_ready:
            temp = int(kwargs["temperature"])
            setattr(self._ecomax, f"{self._id}_set_temp", temp)

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        if self._water_heater_ready:
            setattr(
                self._ecomax,
                f"{self._id}_work_mode",
                self._hass_to_ecomax_mode(operation_mode),
            )

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
        if self._water_heater_ready:
            operation_mode = getattr(self._ecomax, f"{self._id}_work_mode")
            return self._ecomax_to_hass_mode(operation_mode)

        return STATE_OFF

    @property
    def supported_features(self) -> int:
        """Return supported features."""
        return SUPPORT_TARGET_TEMPERATURE + SUPPORT_OPERATION_MODE

    @property
    def operation_list(self) -> list[str]:
        """Return the list of available operation modes."""
        return (STATE_OFF, STATE_ECO, STATE_PERFORMANCE)

    @property
    def _water_heater_ready(self) -> bool:
        """Check if water heater is ready and available."""
        if self._ecomax is not None:
            attr = getattr(self._ecomax, f"{self._id}_work_mode")
            if attr is not None:
                return True

        return False

    def _ecomax_to_hass_mode(self, operation_mode) -> str:
        """Convert ecomax operation mode to hass."""
        if operation_mode == ECOMAX_STATE_PRIORITY:
            return STATE_PERFORMANCE

        if operation_mode == ECOMAX_STATE_NORMAL:
            return STATE_ECO

        return STATE_OFF

    def _hass_to_ecomax_mode(self, operation_mode) -> int:
        """Convert hass operation mode to ecomax."""
        if operation_mode == STATE_PERFORMANCE:
            return ECOMAX_STATE_PRIORITY

        if operation_mode == STATE_ECO:
            return ECOMAX_STATE_NORMAL

        return ECOMAX_STATE_OFF
