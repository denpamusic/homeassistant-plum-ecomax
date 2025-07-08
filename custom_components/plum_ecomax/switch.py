"""Platform for switch integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType, State
from pyplumio.parameters import NumericType, Parameter

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import DeviceType
from .entity import (
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    SubdeviceEntityDescription,
    async_get_by_index,
    async_get_by_modules,
    async_get_by_product_type,
    async_get_custom_entities,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxSwitchEntityDescription(EcomaxEntityDescription, SwitchEntityDescription):
    """Describes an ecoMAX switch."""

    state_off: State | NumericType = STATE_OFF
    state_on: State | NumericType = STATE_ON
    extra_states: dict[State | NumericType, bool] = field(default_factory=dict)


SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = (
    EcomaxSwitchEntityDescription(
        key="ecomax_control",
        translation_key="controller_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_disinfection",
        translation_key="water_heater_disinfection_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_work_mode",
        state_off=0,
        state_on=2,
        extra_states={1: True},
        translation_key="water_heater_pump_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="weather_control",
        product_types={ProductType.ECOMAX_P},
        translation_key="weather_control_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="fuzzy_logic",
        product_types={ProductType.ECOMAX_P},
        translation_key="fuzzy_logic_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="heating_schedule_switch",
        product_types={ProductType.ECOMAX_P},
        translation_key="heating_schedule_switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_schedule_switch",
        product_types={ProductType.ECOMAX_P},
        translation_key="water_heater_schedule_switch",
    ),
)


class EcomaxSwitch(EcomaxEntity, SwitchEntity):
    """Represents an ecoMAX switch."""

    _attr_is_on: bool | None = None
    entity_description: EcomaxSwitchEntityDescription

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.device.set_nowait(
            self.entity_description.key, self.entity_description.state_on
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.device.set_nowait(
            self.entity_description.key, self.entity_description.state_off
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        states = {
            self.entity_description.state_on: True,
            self.entity_description.state_off: False,
        }
        states |= self.entity_description.extra_states
        self._attr_is_on = states.get(value.value, None)
        self.async_write_ha_state()


@dataclass(frozen=True, kw_only=True)
class MixerSwitchEntityDescription(
    EcomaxSwitchEntityDescription, SubdeviceEntityDescription
):
    """Describes a mixer switch entity."""


MIXER_SWITCH_TYPES: tuple[MixerSwitchEntityDescription, ...] = (
    MixerSwitchEntityDescription(
        key="summer_work",
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        translation_key="enable_in_summer_mode",
    ),
    MixerSwitchEntityDescription(
        key="weather_control",
        product_types={ProductType.ECOMAX_P},
        translation_key="weather_control_switch",
    ),
    MixerSwitchEntityDescription(
        key="disable_pump_on_thermostat",
        product_types={ProductType.ECOMAX_P},
        translation_key="disable_pump_on_thermostat",
    ),
    MixerSwitchEntityDescription(
        key="enable_circuit",
        indexes={1},
        product_types={ProductType.ECOMAX_I},
        state_off=0,
        state_on=1,
        translation_key="enable_circuit",
    ),
)


class MixerSwitch(MixerEntity, EcomaxSwitch):
    """Represents a mixer switch."""

    entity_description: EcomaxSwitchEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxSwitchEntityDescription,
        index: int,
    ):
        """Initialize a new mixer switch."""
        self.index = index
        super().__init__(connection, description)


@callback
def async_setup_ecomax_switches(connection: EcomaxConnection) -> list[EcomaxSwitch]:
    """Set up the ecoMAX switches."""
    return [
        EcomaxSwitch(connection, description)
        for description in async_get_by_modules(
            connection.device.modules,
            async_get_by_product_type(connection.product_type, SWITCH_TYPES),
        )
    ]


@callback
def async_setup_custom_ecomax_switches(
    connection: EcomaxConnection, config_entry: PlumEcomaxConfigEntry
) -> list[EcomaxSwitch]:
    """Set up the custom ecoMAX switches."""
    return [
        EcomaxSwitch(connection, description)
        for description in async_get_custom_entities(
            platform=Platform.SWITCH,
            source_device=DeviceType.ECOMAX,
            config_entry=config_entry,
            description_factory=EcomaxSwitchEntityDescription,
        )
    ]


@callback
def async_setup_mixer_switches(connection: EcomaxConnection) -> list[MixerSwitch]:
    """Set up the mixers switches."""
    return [
        MixerSwitch(connection, description, index)
        for index in cast(dict[int, Any], connection.device.mixers)
        for description in async_get_by_index(
            index,
            async_get_by_modules(
                connection.device.modules,
                async_get_by_product_type(connection.product_type, MIXER_SWITCH_TYPES),
            ),
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the switch platform."""
    _LOGGER.debug("Starting setup of switch platform...")

    connection = entry.runtime_data.connection
    entities = async_setup_ecomax_switches(connection)

    # Add custom ecoMAX switches.
    entities += async_setup_custom_ecomax_switches(connection, entry)

    # Add mixer/circuit switches.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities += async_setup_mixer_switches(connection)

    async_add_entities(entities)
    return True
