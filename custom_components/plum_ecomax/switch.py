"""Platform for switch integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import Mixer
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType
from pyplumio.helpers.typing import ParameterValueType

from .connection import EcomaxConnection
from .const import ATTR_ECOMAX_CONTROL, ATTR_MIXERS, DOMAIN
from .entity import EcomaxEntity, MixerEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxSwitchEntityDescription(SwitchEntityDescription):
    """Describes ecoMAX switch entity."""

    state_off: ParameterValueType = STATE_OFF
    state_on: ParameterValueType = STATE_ON
    filter_fn: Callable[[Any], Any] = on_change


COMMON_SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = (
    EcomaxSwitchEntityDescription(
        key=ATTR_ECOMAX_CONTROL,
        name="Controller switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_disinfection",
        name="Water heater disinfection switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_work_mode",
        name="Water heater pump switch",
        state_off=0,
        state_on=2,
    ),
    EcomaxSwitchEntityDescription(
        key="summer_mode",
        name="Summer mode switch",
        state_off=0,
        state_on=1,
    ),
)

ECOMAX_I_SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = ()

ECOMAX_P_SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = (
    EcomaxSwitchEntityDescription(
        key="heating_weather_control",
        name="Weather control switch",
    ),
    EcomaxSwitchEntityDescription(
        key="fuzzy_logic",
        name="Fuzzy logic switch",
    ),
    EcomaxSwitchEntityDescription(
        key="heating_schedule_switch",
        name="Heating schedule switch",
    ),
    EcomaxSwitchEntityDescription(
        key="water_heater_schedule_switch",
        name="Water heater schedule switch",
    ),
)

SWITCH_TYPES: dict[ProductType, tuple[EcomaxSwitchEntityDescription, ...]] = {
    ProductType.ECOMAX_I: COMMON_SWITCH_TYPES + ECOMAX_I_SWITCH_TYPES,
    ProductType.ECOMAX_P: COMMON_SWITCH_TYPES + ECOMAX_P_SWITCH_TYPES,
}


class EcomaxSwitch(EcomaxEntity, SwitchEntity):
    """Represents ecoMAX switch platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_is_on: bool | None

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxSwitchEntityDescription
    ):
        """Initialize ecoMAX switch object."""
        self._connection = connection
        self.entity_description = description
        self._attr_available = False
        self._attr_is_on = None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.device.set_value_nowait(
            self.entity_description.key, self.entity_description.state_on
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.device.set_value_nowait(
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
        self._attr_is_on = states[value.value] if value.value in states else None
        self.async_write_ha_state()


ECOMAX_I_MIXER_SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = (
    EcomaxSwitchEntityDescription(
        key="support",
        name="Enable circuit",
    ),
    EcomaxSwitchEntityDescription(
        key="summer_work",
        name="Enable in summer mode",
    ),
)

ECOMAX_P_MIXER_SWITCH_TYPES: tuple[EcomaxSwitchEntityDescription, ...] = (
    EcomaxSwitchEntityDescription(
        key="weather_control",
        name="Weather control switch",
    ),
    EcomaxSwitchEntityDescription(
        key="off_therm_pump",
        name="Disable pump on thermostat",
    ),
    EcomaxSwitchEntityDescription(
        key="summer_work",
        name="Enable in summer mode",
    ),
)

MIXER_SWITCH_TYPES: dict[ProductType, tuple[EcomaxSwitchEntityDescription, ...]] = {
    ProductType.ECOMAX_I: ECOMAX_I_MIXER_SWITCH_TYPES,
    ProductType.ECOMAX_P: ECOMAX_P_MIXER_SWITCH_TYPES,
}


class MixerSwitch(MixerEntity, EcomaxSwitch):
    """Represents mixer switch platform."""

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxSwitchEntityDescription,
        index: int,
    ):
        """Initialize mixer switch object."""
        self.index = index
        super().__init__(connection, description)


def setup_ecomax_p(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup number platform for ecoMAX P series controllers."""
    entities.extend(
        EcomaxSwitch(connection, description) for description in ECOMAX_P_SWITCH_TYPES
    )
    return async_add_entities(entities, False)


def setup_ecomax_i(
    connection: EcomaxConnection,
    entities: list[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
):
    """Setup number platform for ecoMAX I series controllers."""
    return async_add_entities(entities, False)


async def async_setup_mixer_entities(
    connection: EcomaxConnection, entities: list[EcomaxEntity]
) -> None:
    """Setup mixer number entites."""
    mixers: dict[int, Mixer] = connection.device.data[ATTR_MIXERS]
    for index in mixers.keys():
        entities.extend(
            MixerSwitch(connection, description, index)
            for description in MIXER_SWITCH_TYPES.get(connection.product_type, ())
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of switch platform...")

    async def _async_setup_entities(product_type: ProductType) -> list[EcomaxEntity]:
        """Add switch entites."""
        entities: list[EcomaxEntity] = []

        # Add ecoMAX switches.
        entities.extend(
            EcomaxSwitch(connection, description)
            for description in SWITCH_TYPES[product_type]
        )

        # Add mixer/circuit switches.
        if connection.has_mixers and await connection.setup_mixers():
            await async_setup_mixer_entities(connection, entities)

        return entities

    return async_add_entities(await _async_setup_entities(connection.product_type))
