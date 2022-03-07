"""Base ecoMAX entity for all platforms."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from pyplumio.devices import EcoMAX

from .const import DOMAIN

if TYPE_CHECKING:
    from .connection import EcomaxConnection


class EcomaxEntity(ABC):
    """Base ecomax entity representation.

    Attributes:
        _state -- entity state
        _id -- entity id
        _name -- human-readable entity name
        _connection -- current connection instance
    """

    def __init__(self, connection: EcomaxConnection, id_: str, name: str):
        """Create entity instance.

        Keyword arguments:
            connection -- the ecomax connection
            id_ -- entity id
            name -- human-readable entity name
        """
        self._state = None
        self._id = id_
        self._name = name
        self._connection = connection

    def get_attribute(self, name: str, default=None):
        """Return device attribute.

        Keyword arguments:
            name -- attribute name
            default -- default attribute value
        """
        return getattr(self.ecomax, name, default)

    def set_attribute(self, name: str, value) -> None:
        """Set device attribute.

        Keyword arguments:
            name -- attribute name
            value -- new attribute value
        """
        if hasattr(self.ecomax, name):
            setattr(self.ecomax, name, value)

    @property
    def ecomax(self) -> Optional[EcoMAX]:
        """Return the ecomax device instance."""
        return self._connection.ecomax

    @property
    def unique_id(self) -> Optional[str]:
        """Return unique id of sensor."""
        return f"{self._connection.uid}-{self._id}"

    @property
    def name(self) -> Optional[str]:
        """Return the name of the sensor."""
        return f"{self._connection.name} {self._name}"

    @property
    def should_poll(self) -> bool:
        """Sensor shouldn't use polling."""
        return False

    @property
    def device_info(self) -> Optional[dict]:
        """Return device info."""
        return {
            "name": self._connection.name,
            "identifiers": {(DOMAIN, self._connection.uid)},
            "manufacturer": "Plum",
            "model": f"{self._connection.model} (uid: {self._connection.uid})",
            "sw_version": self._connection.software,
        }

    @abstractmethod
    async def async_update_state(self) -> None:
        """Update entity state."""
