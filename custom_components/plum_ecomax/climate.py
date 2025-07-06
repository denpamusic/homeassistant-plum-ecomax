"""Platform for climate integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final, cast, overload

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.filters import Filter, on_change, throttle
from pyplumio.parameters.thermostat import ThermostatNumber

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .entity import EcomaxEntityDescription, ThermostatEntity

TEMPERATURE_STEP: Final = 0.1

PRESET_SCHEDULE: Final = "schedule"
PRESET_AIRING: Final = "airing"
PRESET_PARTY: Final = "party"
PRESET_HOLIDAYS: Final = "holidays"
PRESET_ANTIFREEZE: Final = "antifreeze"
PRESET_UNKNOWN: Final = "unknown"

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

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxClimateEntityDescription(EcomaxEntityDescription, ClimateEntityDescription):
    """Describes an ecoMAX climate entity."""


ENTITY_DESCRIPTION = EcomaxClimateEntityDescription(
    key="thermostat",
    always_available=True,
    entity_registry_enabled_default=True,
    translation_key="thermostat",
)


class EcomaxClimate(ThermostatEntity, ClimateEntity):
    """Represents an ecoMAX climate entity."""

    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_precision = PRECISION_TENTHS
    _attr_preset_modes = list(HA_TO_EM_MODE)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_target_temperature_name: str | None = None
    _attr_target_temperature_step = TEMPERATURE_STEP
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _callbacks: dict[str, Filter]
    entity_description: EcomaxClimateEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxClimateEntityDescription,
        index: int,
    ):
        """Initialize a new ecoMAX climate entity."""
        self._callbacks = {
            "mode": on_change(self.async_update_preset_mode),
            "state": on_change(self.async_update_preset_mode),
            "contacts": on_change(self.async_update_hvac_action),
            "current_temp": throttle(on_change(self.async_update), seconds=10),
            "target_temp": on_change(self.async_update_target_temperature),
        }
        self.index = index
        super().__init__(connection, description)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = round(kwargs[ATTR_TEMPERATURE], 1)
        target_temperature_name = cast(str, self.target_temperature_name)
        self.device.set_nowait(target_temperature_name, temperature)
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        mode = HA_TO_EM_MODE[preset_mode]
        self.device.set_nowait(ATTR_MODE, mode)
        self._attr_preset_mode = preset_mode
        await self._async_update_target_temperature_attributes()
        self.async_write_ha_state()

    async def async_update(self, value: float) -> None:
        """Update entity state."""
        self._attr_current_temperature = value
        self.async_write_ha_state()

    async def async_update_target_temperature(self, value: float) -> None:
        """Update target temperature."""
        self._attr_target_temperature = value
        await self._async_update_target_temperature_attributes(value)
        self.async_write_ha_state()

    @overload
    async def async_update_preset_mode(self, mode: int) -> None: ...

    @overload
    async def async_update_preset_mode(self, mode: ThermostatNumber) -> None: ...

    async def async_update_preset_mode(self, mode: Any) -> None:
        """Update preset mode."""
        if isinstance(mode, ThermostatNumber):
            mode = int(mode.value)

        try:
            preset_mode = EM_TO_HA_MODE[mode]
        except KeyError:
            # Ignore unknown preset and warn about it in the log.
            _LOGGER.error("Unknown climate preset %d.", mode)
            return

        self._attr_preset_mode = preset_mode
        await self._async_update_target_temperature_attributes()
        self.async_write_ha_state()

    async def async_update_hvac_action(self, value: bool) -> None:
        """Update HVAC action."""
        self._attr_hvac_action = HVACAction.HEATING if value else HVACAction.IDLE
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to thermostat events."""
        for name, handler in self._callbacks.items():
            if name in self.device.data:
                await handler(self.device.data[name])

            self.device.subscribe(name, handler)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from thermostat events."""
        for name, handler in self._callbacks.items():
            self.device.unsubscribe(name, handler)

    async def _async_update_target_temperature_attributes(
        self, target_temp: float | None = None
    ) -> None:
        """Update target temperature parameter name and boundaries."""
        preset_mode = self.preset_mode

        if preset_mode == PRESET_SCHEDULE:
            preset_mode = await self._async_get_current_schedule_preset(target_temp)

        if not preset_mode or preset_mode in (PRESET_AIRING, PRESET_UNKNOWN):
            # Couldn't identify preset in schedule mode or
            # preset is airing.
            return

        target_temperature_name = HA_PRESET_TO_EM_TEMP[preset_mode]
        if self.target_temperature_name == target_temperature_name:
            # Target temperature parameter name is unchanged.
            return

        target_temperature_parameter: ThermostatNumber = await self.device.get(
            target_temperature_name
        )
        self._attr_target_temperature_name = target_temperature_name
        self._attr_max_temp = float(target_temperature_parameter.max_value)
        self._attr_min_temp = float(target_temperature_parameter.min_value)

    async def _async_get_current_schedule_preset(
        self, target_temp: float | None = None
    ) -> str:
        """Get current preset for the schedule mode."""
        if target_temp is None:
            target_temp = await self.device.get("target_temp")

        comfort_temp: ThermostatNumber = await self.device.get(
            HA_PRESET_TO_EM_TEMP[PRESET_COMFORT]
        )
        eco_temp: ThermostatNumber = await self.device.get(
            HA_PRESET_TO_EM_TEMP[PRESET_ECO]
        )

        schedule_preset = PRESET_UNKNOWN
        if target_temp == comfort_temp.value and target_temp != eco_temp.value:
            schedule_preset = PRESET_COMFORT

        if target_temp == eco_temp.value and target_temp != comfort_temp.value:
            schedule_preset = PRESET_ECO

        return schedule_preset

    @property
    def target_temperature_name(self) -> str | None:
        """Return the target temperature name."""
        return self._attr_target_temperature_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the climate platform."""
    _LOGGER.debug("Starting setup of climate platform...")

    connection = entry.runtime_data.connection

    if connection.has_thermostats and await connection.async_setup_thermostats():
        async_add_entities(
            EcomaxClimate(connection, description=ENTITY_DESCRIPTION, index=index)
            for index in connection.device.thermostats
        )
        return True

    return False
