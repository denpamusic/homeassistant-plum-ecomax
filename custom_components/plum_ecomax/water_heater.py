"""Platform for water heater integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final, cast

from homeassistant.components.climate import ATTR_TARGET_TEMP_STEP
from homeassistant.components.sensor import RestoreEntity
from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from pyplumio.filters import Filter, on_change, throttle
from pyplumio.parameters import Parameter

from custom_components.plum_ecomax.const import ATTR_ENABLED

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import ATTR_ELECTRIC_WATER_HEATER
from .entity import EcomaxEntity, EcomaxEntityDescription

TEMPERATURE_STEP: Final = 1

EM_TO_HA_STATE: Final = {0: STATE_OFF, 1: STATE_PERFORMANCE, 2: STATE_ECO}
HA_TO_EM_STATE: Final = {v: k for k, v in EM_TO_HA_STATE.items()}

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxWaterHeaterEntityDescription(
    EcomaxEntityDescription, WaterHeaterEntityDescription
):
    """Describes an ecoMAX water heater."""


ENTITY_DESCRIPTION = EcomaxWaterHeaterEntityDescription(
    key="water_heater",
    always_available=True,
    entity_registry_enabled_default=True,
    translation_key="indirect_water_heater",
)

ATTR_WATER_HEATER_WORK_MODE: Final = "water_heater_work_mode"
ATTR_WATER_HEATER_TEMP: Final = "water_heater_temp"
ATTR_WATER_HEATER_TARGET_TEMP: Final = "water_heater_target_temp"
ATTR_WATER_HEATER_HYSTERESIS: Final = "water_heater_hysteresis"


class ElectricWaterHeaterHelper:
    """Represents a helper class to manage electric water heater."""

    hass: HomeAssistant
    water_heater: EcomaxWaterHeater

    options: dict[str, Any]

    def __init__(self, hass: HomeAssistant, water_heater: EcomaxWaterHeater) -> None:
        """Initialize a new electric water heater helper."""
        self.hass = hass
        self.water_heater = water_heater
        self.options = water_heater.config_entry.options.get(
            ATTR_ELECTRIC_WATER_HEATER, {}
        )

    async def async_update(self, temperature: float) -> None:
        """Control electric heater switch."""
        if not self.available:
            return

        if temperature >= self.water_heater.target_temperature_high and self.is_on:
            await self.async_turn_off()

        elif temperature <= self.water_heater.target_temperature_low and not self.is_on:
            await self.async_turn_on()

    async def async_turn_on(self) -> None:
        """Turn on electric water heater switch."""
        await self.hass.services.async_call(
            Platform.SWITCH, SERVICE_TURN_ON, {ATTR_ENTITY_ID: self.entity_id}
        )

    async def async_turn_off(self) -> None:
        """Turn off electric water heater switch."""
        await self.hass.services.async_call(
            Platform.SWITCH, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: self.entity_id}
        )

    async def async_enable(self) -> None:
        """Enable electric water heater."""
        device = self.water_heater.connection.device
        handler = throttle(on_change(self.async_update), seconds=10)
        device.subscribe(ATTR_WATER_HEATER_TEMP, handler)
        await handler(self.water_heater.current_temperature)
        state_off = HA_TO_EM_STATE[STATE_OFF]
        if device.get_nowait(ATTR_WATER_HEATER_WORK_MODE, False) != state_off:
            device.set_nowait(ATTR_WATER_HEATER_WORK_MODE, state_off)

    async def async_disable(self) -> None:
        """Disable electric water heater."""
        device = self.water_heater.connection.device
        device.unsubscribe(ATTR_WATER_HEATER_TEMP, self.async_update)
        if self.is_on:
            await self.async_turn_off()

    @property
    def is_on(self) -> bool:
        """Return True if electric water heater is on, else False."""
        if not self.entity_id:
            return False

        state = self.hass.states.get(self.entity_id)
        return True if state.state == STATE_ON else False

    @property
    def enabled(self) -> bool:
        """Return True if electric water heater support is enabled."""
        return True if self.options.get(ATTR_ENABLED, False) else False

    @property
    def available(self) -> bool:
        """Return True if electric water heater is available."""
        if not self.entity_id:
            return False

        state = self.hass.states.get(self.entity_id)
        return True if state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else False

    @property
    def entity_id(self) -> str:
        """Return electric water heater switch entity id."""
        return self.options.get(ATTR_ENTITY_ID, "")


class EcomaxWaterHeater(EcomaxEntity, RestoreEntity, WaterHeaterEntity):
    """Represents an ecoMAX water heater."""

    _attr_extra_state_attributes = {ATTR_TARGET_TEMP_STEP: TEMPERATURE_STEP}
    _attr_hysteresis = 0
    _attr_precision = PRECISION_TENTHS
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _callbacks: dict[str, Filter]
    _electric_water_heater: ElectricWaterHeaterHelper
    config_entry: PlumEcomaxConfigEntry
    entity_description: EcomaxWaterHeaterEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        config_entry: PlumEcomaxConfigEntry,
        description: EcomaxWaterHeaterEntityDescription,
    ):
        """Initialize a new ecoMAX water heater entity."""
        self._callbacks = {
            ATTR_WATER_HEATER_TEMP: throttle(on_change(self.async_update), seconds=10),
            ATTR_WATER_HEATER_TARGET_TEMP: on_change(self.async_update_target_temp),
            ATTR_WATER_HEATER_HYSTERESIS: on_change(self.async_update_hysteresis),
            ATTR_WATER_HEATER_WORK_MODE: on_change(self.async_update_work_mode),
        }
        self.config_entry = config_entry
        self._attr_operation_list = list(HA_TO_EM_STATE)
        super().__init__(connection, description)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs[ATTR_TEMPERATURE]
        self.device.set_nowait(ATTR_WATER_HEATER_TARGET_TEMP, int(temperature))
        self._attr_target_temperature = temperature
        self._attr_target_temperature_high = temperature
        self._attr_target_temperature_low = temperature - self.hysteresis
        if self.current_operation == STATE_ELECTRIC:
            await self._electric_water_heater.async_update(self.current_temperature)

        self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if operation_mode == STATE_ELECTRIC:
            await self._electric_water_heater.async_enable()
        else:
            if self.current_operation == STATE_ELECTRIC:
                await self._electric_water_heater.async_disable()

            self.device.set_nowait(
                ATTR_WATER_HEATER_WORK_MODE, HA_TO_EM_STATE[operation_mode]
            )

        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_update_target_temp(self, value: Parameter) -> None:
        """Update target temperature."""
        self._attr_min_temp = float(value.min_value)
        self._attr_max_temp = float(value.max_value)
        target_temperature = float(value.value)
        self._attr_target_temperature = target_temperature
        self._attr_target_temperature_high = target_temperature
        self._attr_target_temperature_low = target_temperature - self.hysteresis
        if self.current_operation == STATE_ELECTRIC:
            await self._electric_water_heater.async_update(self.current_temperature)

        self.async_write_ha_state()

    async def async_update_hysteresis(self, value: Parameter) -> None:
        """Update lower target temperature bound."""
        self._attr_hysteresis = int(value.value)
        if self.target_temperature is not None:
            self._attr_target_temperature_low = (
                int(self.target_temperature) - self.hysteresis
            )
            self.async_write_ha_state()

    async def async_update_work_mode(self, value: Parameter) -> None:
        """Update current operation."""
        operation_mode = EM_TO_HA_STATE[int(value.value)]
        if self.current_operation == STATE_ELECTRIC and operation_mode == STATE_OFF:
            # Skip remote off state when in electric mode.
            return
        elif self.current_operation == STATE_ELECTRIC and operation_mode != STATE_OFF:
            # Sync work modes with remote, overriding electric mode.
            await self._electric_water_heater.async_disable()

        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_update(self, value: float) -> None:
        """Update entity state."""
        self._attr_current_temperature = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to water heater events."""
        for name, handler in self._callbacks.items():
            self.device.subscribe(name, handler)
            if name in self.device.data:
                await handler(self.device.data[name])

        electric_water_heater = ElectricWaterHeaterHelper(
            hass=self.hass, water_heater=self
        )
        if not electric_water_heater.enabled or not electric_water_heater.available:
            return

        self._electric_water_heater = electric_water_heater
        self._attr_operation_list.append(STATE_ELECTRIC)

        if (last_state := await self.async_get_last_state()) is not None:
            last_operation_mode = cast(str, last_state.attributes.get("operation_mode"))
            if last_operation_mode == STATE_ELECTRIC:
                await self.async_set_operation_mode(STATE_ELECTRIC)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [electric_water_heater.entity_id],
                self.async_state_changed_listener,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe to water heater events."""
        for name, handler in self._callbacks.items():
            self.device.unsubscribe(name, handler)

    @callback
    def async_state_changed_listener(
        self, event: Event[EventStateChangedData] | None = None
    ) -> None:
        """Handle electric water switch state changes."""
        if (
            self.current_operation == STATE_ELECTRIC
            and not self._electric_water_heater.available
        ):
            self._attr_available = False
            return

        self._attr_available = True

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
        async_add_entities(
            [EcomaxWaterHeater(connection, entry, description=ENTITY_DESCRIPTION)]
        )
        return True

    return False
