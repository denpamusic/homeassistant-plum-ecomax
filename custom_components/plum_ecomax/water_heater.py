"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .entity import EcomaxEntity

WATER_HEATER_MODES: Final = (STATE_OFF, STATE_PERFORMANCE, STATE_ECO)


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
    """Representation of ecoMAX water heater."""

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
        self._attr_current_operation: Optional[str] = None

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = int(kwargs["temperature"])
        setattr(
            self._connection.ecomax,
            f"{self.entity_description.key}_target_temp",
            temperature,
        )
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode.

        Keyword arguments:
            operation_mode -- contains new water heater operation mode
        """
        setattr(
            self._connection.ecomax,
            f"{self.entity_description.key}_work_mode",
            hass_to_ecomax_mode(operation_mode),
        )
        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update entity state."""
        target_temp = getattr(
            self._connection.ecomax, f"{self.entity_description.key}_target_temp", None
        )
        if target_temp is None:
            self._attr_min_temp = None
            self._attr_max_temp = None
            self._attr_target_temperature = None
            self._attr_target_temperature_high = None
            self._attr_target_temperature_low = None
            self._attr_current_operation = None
        else:
            self._attr_min_temp = target_temp.min_value
            self._attr_max_temp = target_temp.max_value
            self._attr_target_temperature = target_temp.value
            self._attr_target_temperature_high = target_temp.value
            self._attr_current_operation = ecomax_to_hass_mode(
                int(
                    getattr(
                        self._connection.ecomax,
                        f"{self.entity_description.key}_work_mode",
                        0,
                    )
                )
            )
            hysteresis = getattr(
                self._connection.ecomax,
                f"{self.entity_description.key}_hysteresis",
                None,
            )
            if hysteresis is None:
                self._attr_target_temperature_low = target_temp.value
            else:
                self._attr_target_temperature_low = target_temp.value - hysteresis.value

        self._attr_current_temperature = getattr(
            self._connection.ecomax, f"{self.entity_description.key}_temp", None
        )
        self.async_write_ha_state()


def ecomax_to_hass_mode(operation_mode: int) -> str:
    """Convert ecomax operation mode to hass.

    Keyword arguments:
        operation_mode -- operation mode taken from ecoMAX
    """
    return WATER_HEATER_MODES[operation_mode]


def hass_to_ecomax_mode(operation_mode) -> int:
    """Convert hass operation mode to ecomax.

    Keyword arguments:
        operation_mode -- operation mode taken from hass
    """
    return WATER_HEATER_MODES.index(operation_mode)


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
    async_add_entities(
        [
            EcomaxWaterHeater(connection, description)
            for description in WATER_HEATER_TYPES
        ],
        False,
    )
