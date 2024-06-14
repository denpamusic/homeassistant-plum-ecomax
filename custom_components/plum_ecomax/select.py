"""Platform for select integration."""

from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any, Final

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType
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

STATE_SUMMER: Final = "summer"
STATE_WINTER: Final = "winter"
STATE_AUTO: Final = "auto"
STATE_HEATING: Final = "heating"
STATE_HEATED_FLOOR: Final = "heated_floor"
STATE_PUMP_ONLY: Final = "pump_only"

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcomaxSelectEntityDescription(EcomaxEntityDescription, SelectEntityDescription):
    """Describes an ecoMAX select."""


SELECT_TYPES: tuple[EcomaxSelectEntityDescription, ...] = (
    EcomaxSelectEntityDescription(
        key="summer_mode",
        icon="mdi:weather-sunny",
        options=[STATE_WINTER, STATE_SUMMER, STATE_AUTO],
        translation_key="summer_mode",
    ),
)


class EcomaxSelect(EcomaxEntity, SelectEntity):
    """Represents an ecoMAX select."""

    entity_description: EcomaxSelectEntityDescription

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if options := self.entity_description.options:
            self.device.set_nowait(self.entity_description.key, options.index(option))
            self._attr_current_option = option
            self.async_write_ha_state()

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        if self.entity_description.options:
            self._attr_current_option = self.entity_description.options[int(value)]
            self.async_write_ha_state()


@dataclass(frozen=True, kw_only=True)
class EcomaxMixerSelectEntityDescription(
    EcomaxSelectEntityDescription, SubdeviceEntityDescription
):
    """Describes a mixer select."""


MIXER_SELECT_TYPES: tuple[EcomaxMixerSelectEntityDescription, ...] = (
    EcomaxMixerSelectEntityDescription(
        key="work_mode",
        options=[STATE_OFF, STATE_HEATING, STATE_HEATED_FLOOR, STATE_PUMP_ONLY],
        product_types={ProductType.ECOMAX_P},
        translation_key="mixer_work_mode",
    ),
    EcomaxMixerSelectEntityDescription(
        key="enable_circuit",
        indexes={2, 3},
        options=[STATE_OFF, STATE_HEATING, STATE_HEATED_FLOOR],
        product_types={ProductType.ECOMAX_I},
        translation_key="mixer_work_mode",
    ),
)


class MixerSelect(MixerEntity, EcomaxSelect):
    """Represents a mixer select."""

    entity_description: EcomaxMixerSelectEntityDescription

    def __init__(
        self,
        connection: EcomaxConnection,
        description: EcomaxMixerSelectEntityDescription,
        index: int,
    ):
        """Initialize a new mixer select."""
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


def async_setup_ecomax_selects(connection: EcomaxConnection) -> list[EcomaxSelect]:
    """Set up the ecoMAX selects."""
    return [
        EcomaxSelect(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SELECT_TYPES),
        )
    ]


def async_setup_mixer_selects(connection: EcomaxConnection) -> list[MixerSelect]:
    """Set up the mixer selects."""
    entities: list[MixerSelect] = []
    for index in connection.device.mixers:
        entities.extend(
            MixerSelect(connection, description, index)
            for description in get_by_index(
                index,
                get_by_modules(
                    connection.device.modules,
                    get_by_product_type(connection.product_type, MIXER_SELECT_TYPES),
                ),
            )
        )

    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the select platform."""
    connection = entry.runtime_data.connection
    _LOGGER.debug("Starting setup of select platform...")

    entities: list[EcomaxSelect] = []

    # Add ecoMAX selects.
    entities.extend(async_setup_ecomax_selects(connection))

    # Add mixer/circuit selects.
    if connection.has_mixers and await connection.async_setup_mixers():
        entities.extend(async_setup_mixer_selects(connection))

    async_add_entities(entities)
    return True
