"""Platform for climate integration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Final

from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_MODE,
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import Thermostat
from pyplumio.helpers.filters import on_change, throttle

from .connection import VALUE_TIMEOUT, EcomaxConnection
from .const import DOMAIN
from .entity import EcomaxEntity

ATTR_THERMOSTATS: Final = "thermostats"

TEMPERATURE_STEP: Final = 0.1

PRESET_SCHEDULE: Final = "schedule"
PRESET_AIRING: Final = "airing"
PRESET_PARTY: Final = "party"
PRESET_HOLIDAYS: Final = "holidays"
PRESET_ANTIFREEZE: Final = "antifreeze"

EM_TO_HA_MODE: Final[dict[int, str]] = {
    0: PRESET_SCHEDULE,
    1: PRESET_ECO,
    2: PRESET_COMFORT,
    3: PRESET_AWAY,
    4: PRESET_AIRING,
    5: PRESET_PARTY,
    6: PRESET_HOLIDAYS,
    7: PRESET_ANTIFREEZE,
}
HA_TO_EM_MODE: Final = {v: k for k, v in EM_TO_HA_MODE.items()}

HA_PRESET_TO_EM_TEMP: Final[dict[str, str]] = {
    PRESET_ECO: "night_target_temp",
    PRESET_COMFORT: "day_target_temp",
    PRESET_AWAY: "night_target_temp",
    PRESET_PARTY: "party_target_temp",
    PRESET_HOLIDAYS: "holidays_target_temp",
    PRESET_ANTIFREEZE: "antifreeze_target_temp",
}

CLIMATE_MODES: Final[list[str]] = [
    PRESET_SCHEDULE,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_AWAY,
    PRESET_AIRING,
    PRESET_PARTY,
    PRESET_HOLIDAYS,
    PRESET_ANTIFREEZE,
]

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxClimateEntityAdditionalKeys:
    """Additional keys for ecoMAX climate entity description."""

    index: int


@dataclass
class EcomaxClimateEntityDescription(
    ClimateEntityDescription, EcomaxClimateEntityAdditionalKeys
):
    """Describes ecoMAX climate entity."""


class EcomaxClimate(EcomaxEntity, ClimateEntity):
    """Represents ecoMAX climate platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_supported_features: ClimateEntityFeature = ClimateEntityFeature(0)
    _attr_current_temperature: float | None = None
    _attr_hvac_action: HVACAction | str | None = None
    _attr_hvac_mode: HVACMode | str | None
    _attr_hvac_modes: list[HVACMode] | list[str]
    _attr_preset_mode: str | None
    _attr_preset_modes: list[str] | None
    _attr_precision: float
    _attr_target_temperature: float | None = None
    _attr_target_temperature_name: str | None
    _attr_target_temperature_high: float | None
    _attr_target_temperature_low: float | None
    _attr_target_temperature_step: float | None
    _attr_temperature_unit: str

    def __init__(self, connection: EcomaxConnection, thermostat: Thermostat):
        self._connection = connection
        self.entity_description = EcomaxClimateEntityDescription(
            key=f"thermostat-{thermostat.index}",
            name=f"Thermostat {thermostat.index+1}",
            translation_key="ecomax_climate",
            index=thermostat.index,
        )
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_hvac_modes = [HVACMode.HEAT]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_preset_modes = CLIMATE_MODES
        self._attr_precision = PRECISION_TENTHS
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_hvac_action = None
        self._attr_preset_mode = None
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_target_temperature_high = None
        self._attr_target_temperature_low = None
        self._attr_target_temperature_name = None
        self._attr_target_temperature_step = TEMPERATURE_STEP

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = round(kwargs[ATTR_TEMPERATURE], 1)
        self.device.set_value_nowait(self.target_temperature_name, temperature)
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        mode = HA_TO_EM_MODE[preset_mode]
        self.device.set_value_nowait(ATTR_MODE, mode)
        self._attr_preset_mode = preset_mode
        await self._async_update_target_temperature_name()
        self.async_write_ha_state()

    async def async_update(self, value) -> None:
        """Update entity state."""
        self._attr_current_temperature = value
        self.async_write_ha_state()

    async def async_update_target_temp(self, value) -> None:
        """Update target temperature."""
        target_temp = await self.device.get_parameter(self.target_temperature_name)
        self._attr_max_temp = target_temp.max_value
        self._attr_min_temp = target_temp.min_value
        self._attr_target_temperature = target_temp.value
        self.async_write_ha_state()

    async def async_update_preset_mode(self, value: int) -> None:
        """Update preset mode."""
        try:
            preset_mode = EM_TO_HA_MODE[value]
        except KeyError:
            # Ignore unknown preset and warn about them in the log.
            _LOGGER.error("Unknown climate preset %i", value)
            return

        self._attr_preset_mode = preset_mode
        await self._async_update_target_temperature_name()
        self.async_write_ha_state()

    async def async_update_hvac_action(self, value) -> None:
        """Update HVAC action."""
        self._attr_hvac_action = HVACAction.HEATING if value else HVACAction.IDLE
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""
        callbacks = {
            "state": on_change(self.async_update_preset_mode),
            "contacts": on_change(self.async_update_hvac_action),
            "current_temp": throttle(self.async_update, seconds=10),
            "target_temp": on_change(self.async_update_target_temp),
        }

        for name, func in callbacks.items():
            # Feed initial value to the callback function.
            if name in self.device.data:
                await func(self.device.data[name])

            self.device.subscribe(name, func)

    async def async_will_remove_from_hass(self):
        """Called when an entity is about to be removed."""
        self.device.unsubscribe("state", self.async_update_preset_mode)
        self.device.unsubscribe("contacts", self.async_update_hvac_action)
        self.device.unsubscribe("current_temp", self.async_update)
        self.device.unsubscribe("target_temp", self.async_update_target_temp)

    async def _async_update_target_temperature_name(self) -> None:
        """Get target temperature name."""
        if self.preset_mode == PRESET_AIRING:
            # Don't update temperature target name if mode is airing.
            return

        preset_mode = self.preset_mode
        if preset_mode == PRESET_SCHEDULE:
            schedule = await self.device.get_value("schedule")
            preset_mode = PRESET_ECO if schedule else PRESET_COMFORT

        self._attr_target_temperature_name = HA_PRESET_TO_EM_TEMP[preset_mode]

    @property
    def device(self) -> Thermostat:
        """Return thermostat object."""
        return self.connection.device.data[ATTR_THERMOSTATS][
            self.entity_description.index
        ]

    @property
    def target_temperature_name(self) -> str | None:
        """Return target temperature name."""
        return self._attr_target_temperature_name


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the climate platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    try:
        thermostats: dict[int, Thermostat] = await connection.device.get_value(
            ATTR_THERMOSTATS, timeout=VALUE_TIMEOUT
        )
    except asyncio.TimeoutError:
        _LOGGER.warning("Can't find thermostats, skipping climate platform setup...")
        return False

    entities: list[EcomaxEntity] = [
        EcomaxClimate(connection, thermostat) for thermostat in thermostats.values()
    ]
    return async_add_entities(entities, False)
