"""Platform for select integration."""
from __future__ import annotations

from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
import logging
from typing import Any, Final

from homeassistant.components.select import (
    EntityDescription,
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.const import ProductType
from pyplumio.filters import on_change

from .connection import EcomaxConnection
from .const import DOMAIN, MODULE_A
from .entity import EcomaxEntity

STATE_AUTO: Final = "auto"

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcomaxSelectEntityAdditionalKeys:
    """Additional keys for ecoMAX select entity description."""

    product_types: set[ProductType]


@dataclass
class EcomaxSelectEntityDescription(
    SelectEntityDescription, EcomaxSelectEntityAdditionalKeys
):
    """Describes ecoMAX select entity."""

    filter_fn: Callable[[Any], Any] = on_change
    module: str = MODULE_A


SELECT_TYPES: tuple[EcomaxSelectEntityDescription, ...] = (
    EcomaxSelectEntityDescription(
        key="summer_mode",
        translation_key="summer_mode",
        options=[STATE_OFF, STATE_AUTO, STATE_ON],
        product_types={ProductType.ECOMAX_P, ProductType.ECOMAX_I},
        icon="mdi:weather-sunny",
    ),
)


class EcomaxSelect(EcomaxEntity, SelectEntity):
    """Represents ecoMAX select platform."""

    _attr_current_option: str | None
    _connection: EcomaxConnection
    entity_description: EntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxSelectEntityDescription
    ):
        self._attr_current_option = None
        self._connection = connection
        self.entity_description = description

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        options: list[str] = self.entity_description.options
        index = options.index(option)
        self.device.set_nowait(self.entity_description.key, index)
        self._attr_current_option = option
        self.async_write_ha_state()

    async def async_update(self, value) -> None:
        """Retrieve latest state."""
        self._attr_current_option = self.entity_description.options[int(value)]
        self.async_write_ha_state()


def get_by_product_type(
    product_type: ProductType,
    descriptions: Iterable[EcomaxSelectEntityDescription],
) -> Generator[EcomaxSelectEntityDescription, None, None]:
    """Filter descriptions by product type."""
    for description in descriptions:
        if product_type in description.product_types:
            yield description


def get_by_modules(
    connected_modules, descriptions: Iterable[EcomaxSelectEntityDescription]
) -> Generator[EcomaxSelectEntityDescription, None, None]:
    """Filter descriptions by modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


def async_setup_ecomax_selects(connection: EcomaxConnection) -> list[EcomaxSelect]:
    """Setup ecoMAX selects."""
    return [
        EcomaxSelect(connection, description)
        for description in get_by_modules(
            connection.device.modules,
            get_by_product_type(connection.product_type, SELECT_TYPES),
        )
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the select platform."""
    connection: EcomaxConnection = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Starting setup of select platform...")

    entities: list[EcomaxSelect] = []

    # Add ecoMAX selects.
    entities.extend(async_setup_ecomax_select(connection))

    return async_add_entities(entities)
