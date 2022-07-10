"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.helpers.filters import debounce, on_change
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import ValueCallback

from .connection import EcomaxConnection
from .const import DOMAIN
from .entity import EcomaxEntity

WATER_HEATER_MODES: Final = [STATE_OFF, STATE_PERFORMANCE, STATE_ECO]


@dataclass
class EcomaxWaterHeaterEntityDescription(WaterHeaterEntityEntityDescription):
    """Describes ecoMAX water heater entity."""


WATER_HEATER_TYPES: tuple[EcomaxWaterHeaterEntityDescription, ...] = (
    EcomaxWaterHeaterEntityDescription(
        key="water_heater",
        name="Indirect Water Heater",
    ),
)


class EcomaxWaterHeater(EcomaxEntity, WaterHeaterEntity):
    """Represents ecoMAX water heater platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_temperature_unit: str
    _attr_precision: float
    _attr_supported_features: int
    _attr_operation_list: list[str] | None
    _attr_min_temp: float | None
    _attr_max_temp: float | None
    _attr_target_temperature: float | None
    _attr_target_temperature_high: float | None
    _attr_target_temperature_low: float | None
    _attr_current_temperature: float | None
    _attr_current_operation: str | None
    _attr_hysteresis: int

    def __init__(self, connection, description: WaterHeaterEntityEntityDescription):
        self._connection = connection
        self.entity_description = description
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_precision = PRECISION_WHOLE
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            + WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_operation_list = WATER_HEATER_MODES
        self._attr_min_temp = None
        self._attr_max_temp = None
        self._attr_target_temperature = None
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None
        self._attr_current_temperature = None
        self._attr_current_operation = None
        self._attr_hysteresis = 0

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs["temperature"]
        await self.device.set_value(
            f"{self.entity_description.key}_target_temp", int(temperature)
        )
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        await self.device.set_value(
            f"{self.entity_description.key}_work_mode",
            hass_to_ecomax_mode(operation_mode),
        )
        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_update_target_temp(self, value: Parameter) -> None:
        """Update target temperature."""
        self._attr_min_temp = value.min_value
        self._attr_max_temp = value.max_value
        self._attr_target_temperature = value.value
        self._attr_target_temperature_high = value.value
        self._attr_target_temperature_low = value.value - self.hysteresis
        self.async_write_ha_state()

    async def async_update_hysteresis(self, value: Parameter) -> None:
        """Update lower target temperature bound."""
        self._attr_hysteresis = value.value
        if self.target_temperature is not None:
            self._attr_target_temperature_low = (
                int(self.target_temperature) - self.hysteresis
            )
            self.async_write_ha_state()

    async def async_update_work_mode(self, value: Parameter) -> None:
        """Update current operation."""
        self._attr_current_operation = ecomax_to_hass_mode(value.value)
        self.async_write_ha_state()

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_current_temperature = value
        self.async_write_ha_state()

    @property
    def callbacks(self) -> dict[str, ValueCallback]:
        """Return callback functions mapped with value names."""
        key = self.entity_description.key
        return {
            f"{key}_temp": debounce(self.async_update, min_calls=3),
            f"{key}_target_temp": on_change(self.async_update_target_temp),
            f"{key}_work_mode": on_change(self.async_update_work_mode),
            f"{key}_hysteresis": on_change(self.async_update_hysteresis),
        }

    @property
    def hysteresis(self) -> int:
        """Return temperature hysteresis."""
        return self._attr_hysteresis


def ecomax_to_hass_mode(operation_mode: int) -> str:
    """Convert ecomax operation mode to hass."""
    return WATER_HEATER_MODES[operation_mode]


def hass_to_ecomax_mode(operation_mode) -> int:
    """Convert hass operation mode to ecomax."""
    return WATER_HEATER_MODES.index(operation_mode)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]
    return async_add_entities(
        [
            EcomaxWaterHeater(connection, description)
            for description in WATER_HEATER_TYPES
        ],
        False,
    )
