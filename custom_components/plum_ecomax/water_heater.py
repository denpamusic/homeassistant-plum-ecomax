"""Platform for water heater integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final, cast

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    STATE_OFF,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.filters import on_change, throttle
from pyplumio.helpers.parameter import Parameter

from . import EcomaxEntity, EcomaxEntityDescription, PlumEcomaxConfigEntry
from .connection import EcomaxConnection

EM_TO_HA_STATE: Final = {0: STATE_OFF, 1: STATE_PERFORMANCE, 2: STATE_ECO}
HA_TO_EM_STATE: Final = {v: k for k, v in EM_TO_HA_STATE.items()}

WATER_HEATER_MODES: Final = [STATE_OFF, STATE_PERFORMANCE, STATE_ECO]

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True, slots=True)
class EcomaxWaterHeaterEntityDescription(
    WaterHeaterEntityEntityDescription, EcomaxEntityDescription
):
    """Describes an ecoMAX water heater."""


class EcomaxWaterHeater(EcomaxEntity, WaterHeaterEntity):
    """Represents an ecoMAX water heater."""

    _attr_available = True
    _attr_entity_registry_enabled_default = True
    _attr_hysteresis: int = 0
    _attr_max_temp: float | None = None
    _attr_min_temp: float | None = None
    _attr_operation_list = WATER_HEATER_MODES
    _attr_precision = PRECISION_WHOLE
    _attr_supported_features: WaterHeaterEntityFeature = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, connection: EcomaxConnection):
        """Initialize a new ecoMAX water heater."""
        self.connection = connection
        self.entity_description = EcomaxWaterHeaterEntityDescription(
            key="water_heater",
            translation_key="indirect_water_heater",
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs[ATTR_TEMPERATURE]
        self.device.set_nowait(
            f"{self.entity_description.key}_target_temp", int(temperature)
        )
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        self.device.set_nowait(
            f"{self.entity_description.key}_work_mode", HA_TO_EM_STATE[operation_mode]
        )
        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_update_target_temp(self, value: Parameter) -> None:
        """Update target temperature."""
        self._attr_min_temp = cast(float, value.min_value)
        self._attr_max_temp = cast(float, value.max_value)
        target_temperature = cast(float, value.value)
        self._attr_target_temperature = target_temperature
        self._attr_target_temperature_high = target_temperature
        self._attr_target_temperature_low = target_temperature - self.hysteresis
        self.async_write_ha_state()

    async def async_update_hysteresis(self, value: Parameter) -> None:
        """Update lower target temperature bound."""
        self._attr_hysteresis = cast(int, value.value)
        if self.target_temperature is not None:
            self._attr_target_temperature_low = (
                int(self.target_temperature) - self.hysteresis
            )
            self.async_write_ha_state()

    async def async_update_work_mode(self, value: Parameter) -> None:
        """Update current operation."""
        self._attr_current_operation = EM_TO_HA_STATE[int(value.value)]
        self.async_write_ha_state()

    async def async_update(self, value: float) -> None:
        """Update entity state."""
        self._attr_current_temperature = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to water heater events."""
        key = self.entity_description.key
        callbacks = {
            f"{key}_temp": throttle(on_change(self.async_update), seconds=10),
            f"{key}_target_temp": on_change(self.async_update_target_temp),
            f"{key}_work_mode": on_change(self.async_update_work_mode),
            f"{key}_hysteresis": on_change(self.async_update_hysteresis),
        }

        for name, func in callbacks.items():
            # Feed initial value to the callback function.
            if name in self.device.data:
                await func(self.device.data[name])

            self.device.subscribe(name, func)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe to water heater events."""
        key = self.entity_description.key
        self.device.unsubscribe(f"{key}_temp", self.async_update)
        self.device.unsubscribe(f"{key}_target_temp", self.async_update_target_temp)
        self.device.unsubscribe(f"{key}_work_mode", self.async_update_work_mode)
        self.device.unsubscribe(f"{key}_hysteresis", self.async_update_hysteresis)

    @property
    def hysteresis(self) -> int:
        """Return the temperature hysteresis."""
        return self._attr_hysteresis


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the water heater platform."""
    connection = entry.runtime_data.connection
    _LOGGER.debug("Starting setup of water heater platform...")

    if connection.has_water_heater:
        async_add_entities([EcomaxWaterHeater(connection)])
        return True

    return False
