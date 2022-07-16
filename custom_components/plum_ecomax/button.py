"""Platform for button integration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DOMAIN
from custom_components.plum_ecomax.entity import EcomaxEntity


@dataclass
class EcomaxButtonEntityAdditionalKeys:
    """Additional keys for ecoMAX sensor entity description."""

    press_fn: str


@dataclass
class EcomaxButtonEntityDescription(
    ButtonEntityDescription, EcomaxButtonEntityAdditionalKeys
):
    """Describes ecoMAX button entity."""


BUTTON_TYPES: tuple[EcomaxButtonEntityDescription, ...] = (
    EcomaxButtonEntityDescription(
        key="update_device_capabilities",
        name="Update Capabilities",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=ButtonDeviceClass.UPDATE,
        entity_registry_enabled_default=True,
        press_fn="async_update_device_capabilities",
    ),
)


class EcomaxButton(EcomaxEntity, ButtonEntity):
    """Represents ecoMAX sensor platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxButtonEntityDescription
    ):
        """Initialize ecoMAX sensor object."""
        self._connection = connection
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        if not hasattr(self.connection, self.entity_description.press_fn):
            raise NotImplementedError()

        func = getattr(self.connection, self.entity_description.press_fn)
        if asyncio.iscoroutinefunction(func):
            await func()
        else:
            func()

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Indicate if the entity should be enabled when first added."""
        return self.entity_description.entity_registry_enabled_default

    async def async_update(self, value) -> None:
        """Retrieve latest state."""
        raise NotImplementedError()

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""

    async def async_will_remove_from_hass(self):
        """Called when an entity is about to be removed."""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]

    return async_add_entities(
        [EcomaxButton(connection, description) for description in BUTTON_TYPES], False
    )
