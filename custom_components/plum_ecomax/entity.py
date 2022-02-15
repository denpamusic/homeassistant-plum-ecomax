"""Base ecoMAX entity for all platforms."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from pyplumio.devices import EcoMAX

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .connection import EcomaxConnection


class EcomaxEntity(ABC):
    """Base ecoMAX entity representation.

    Attributes:
        _state -- entity state
        _id -- entity id
        _name -- human-readable entity name
        _connection -- current connection instance
    """

    def __init__(self, id_: str, name: str):
        """Create entity instance.

        Keyword arguments:
            id_ -- entity id
            name_ -- human-readable entity name
        """
        self._state = None
        self._id = id_
        self._name = name
        self._connection: Optional[EcomaxConnection] = None

    def set_connection(self, connection: EcomaxConnection) -> None:
        """Set ecoMAX connection instance.

        Keyword arguments:
            connection -- current connection instance
        """
        self._connection = connection

    def get_attribute(self, name: str):
        """Return device attribute.

        Keyword arguments:
            name -- attribute name
        """
        if hasattr(self.ecomax, name):
            return getattr(self.ecomax, name)

        return None

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
        """Return ecoMAX device instance."""
        if self._connection is not None:
            return self._connection.ecomax

        return None

    @property
    def unique_id(self) -> str:
        """Return unique id of sensor."""
        if self._connection is not None:
            return f"{self._connection.uid}{self._id}"

        return ""

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self._connection is not None:
            return f"{self._connection.name} {self._name}"

        return ""

    @property
    def should_poll(self) -> bool:
        """Sensor shouldn't use polling."""
        return False

    @property
    def device_info(self):
        """Return device info."""
        return {
            "name": self._connection.name,
            "identifiers": {(DOMAIN, self._connection.uid)},
            "manufacturer": MANUFACTURER,
            "model": f"{self._connection.model} (uid: {self._connection.uid})",
            "sw_version": self._connection.sw_version,
        }

    @abstractmethod
    async def async_update_state(self) -> None:
        """Update entity state."""
