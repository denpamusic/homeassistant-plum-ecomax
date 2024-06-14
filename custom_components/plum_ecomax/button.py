"""Platform for button integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlumEcomaxConfigEntry
from .entity import EcomaxEntity, EcomaxEntityDescription


@dataclass(frozen=True, kw_only=True)
class EcomaxButtonEntityDescription(EcomaxEntityDescription, ButtonEntityDescription):
    """Describes an ecoMAX button."""

    press_fn: str


BUTTON_TYPES: tuple[EcomaxButtonEntityDescription, ...] = (
    EcomaxButtonEntityDescription(
        key="detect_sub_devices",
        always_available=True,
        device_class=ButtonDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        press_fn="async_update_sub_devices",
        translation_key="detect_sub_devices",
    ),
)


class EcomaxButton(EcomaxEntity, ButtonEntity):
    """Represents an ecoMAX button."""

    entity_description: EcomaxButtonEntityDescription

    async def async_press(self) -> None:
        """Press the button."""
        func = getattr(self.connection, self.entity_description.press_fn)
        await func()

    async def async_update(self, value: Any) -> None:
        """Update entity state."""

    async def async_added_to_hass(self) -> None:
        """Subscribe to the events."""

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the events."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlumEcomaxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the button platform."""
    async_add_entities(
        EcomaxButton(entry.runtime_data.connection, description)
        for description in BUTTON_TYPES
    )
    return True
