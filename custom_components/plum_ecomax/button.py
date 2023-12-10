"""Platform for button integration."""
from __future__ import annotations

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


@dataclass(kw_only=True, slots=True)
class EcomaxButtonEntityDescription(ButtonEntityDescription):
    """Describes an ecoMAX button."""

    press_fn: str


BUTTON_TYPES: tuple[EcomaxButtonEntityDescription, ...] = (
    EcomaxButtonEntityDescription(
        key="detect_sub_devices",
        translation_key="detect_sub_devices",
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        press_fn="async_update_sub_devices",
    ),
)


class EcomaxButton(EcomaxEntity, ButtonEntity):
    """Represents an ecoMAX button."""

    _connection: EcomaxConnection
    entity_description: EntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxButtonEntityDescription
    ):
        """Initialize a new ecoMAX button."""
        self._connection = connection
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        func = getattr(self.connection, self.entity_description.press_fn)
        await func()

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        return self.entity_description.entity_registry_enabled_default

    async def async_update(self, _) -> None:
        """Update entity state."""

    async def async_added_to_hass(self):
        """Subscribe to the events."""

    async def async_will_remove_from_hass(self):
        """Unsubscribe from the events."""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the button platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]
    return async_add_entities(
        EcomaxButton(connection, description) for description in BUTTON_TYPES
    )
