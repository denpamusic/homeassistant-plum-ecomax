"""Base ecoMAX entity class."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from .connection import EcomaxConnection


class EcomaxEntity(ABC):
    """Representation of base ecoMAX entity."""

    _connection: EcomaxConnection
    entity_description: Any

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""
        self._connection.register_callback(self.async_update)

    async def async_removed_from_hass(self):
        """Called when an entity is about to be removed."""
        self._connection.remove_callback(self.async_update)

    @property
    def available(self) -> bool:
        return self._connection.ecomax is not None

    @property
    def device_info(self) -> Optional[dict]:
        """Return device info."""
        return self._connection.device_info

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Indicate if the entity should be enabled when first added."""
        return self.entity_description.key in self._connection.capabilities

    @property
    def unique_id(self) -> str:
        """A unique identifier for this entity."""
        return f"{self._connection.uid}-{self.entity_description.key}"

    @property
    def name(self) -> str:
        """Name of the entity."""
        return f"{self._connection.name} {self.entity_description.name}"

    @property
    def should_poll(self) -> bool:
        """Should hass check with the entity for an updated state."""
        return False

    @abstractmethod
    async def async_update() -> None:
        """Retrieve latest state."""
