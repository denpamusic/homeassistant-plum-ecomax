"""Platform for switch integration."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.typing import ParameterValueType
from pyplumio.structures.modules import ConnectedModules

from . import PlumEcomaxConfigEntry
from .connection import EcomaxConnection
from .const import ALL
from .entity import (
    DescriptorT,
    EcomaxEntity,
    EcomaxEntityDescription,
    MixerEntity,
    SubDescriptorT,
    SubdeviceEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxSwitchEntityDescription(EcomaxEntityDescription, SwitchEntityDescription):
    """Describes an ecoMAX switch."""

    state_off: ParameterValueType = STATE_OFF
    state_on: ParameterValueType = STATE_ON


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


def get_by_product_type(
    product_type: ProductType,
    descriptions: Iterable[DescriptorT],
) -> Generator[DescriptorT, None, None]:
    """Filter descriptions by the product type."""
    for description in descriptions:
        if (
            description.product_types == ALL
            or product_type in description.product_types
        ):
            yield description


def get_by_modules(
    connected_modules: ConnectedModules,
    descriptions: Iterable[DescriptorT],
) -> Generator[DescriptorT, None, None]:
    """Filter descriptions by connected modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def get_by_index(
    index: int, descriptions: Iterable[SubDescriptorT]
) -> Generator[SubDescriptorT, None, None]:
    """Filter mixer/circuit descriptions by the index."""
    index += 1
    for description in descriptions:
        if description.indexes == ALL or index in description.indexes:
            yield description


def async_setup_ecomax_switches(connection: EcomaxConnection) -> list[EcomaxSwitch]:
    """Set up the ecoMAX switches."""
    return [
        EcomaxSwitch(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SWITCH_TYPES),
        )
    ]


def async_setup_mixer_switches(connection: EcomaxConnection) -> list[MixerSwitch]:
    """Set up the mixers switches."""
    entities: list[MixerSwitch] = []
    for index in connection.device.mixers:
        entities.extend(
            MixerSwitch(connection, description, index)
            for description in get_by_index(
                index,
                get_by_modules(
                    connection.device.modules,
                    get_by_product_type(connection.product_type, MIXER_SWITCH_TYPES),
                ),
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = entry.runtime_data.connection
    _LOGGER.debug("Starting setup of switch platform...")

    entities: list[EcomaxSwitch] = []

    # Add ecoMAX switches.
    entities.extend(async_setup_ecomax_switches(connection))

    # Add mixer/circuit switches.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_switches(connection))

    async_add_entities(entities)
    return True
