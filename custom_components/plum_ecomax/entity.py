"""Base ecoMAX entity for all platforms."""

from .connection import EcomaxConnection


class EcomaxEntity:
    """Base ecoMAX entity representation."""

    def __init__(self, id_: str, name: str):
        self._state = None
        self._id = id_
        self._name = name
        self._connection = None

    def set_connection(self, connection: EcomaxConnection):
        """Set ecoMAX connection instance."""
        self._connection = connection

    @property
    def unique_id(self) -> str:
        """Return unique id of sensor."""
        return f"{self._connection.name}{self._id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._connection.name} {self._name}"

    @property
    def should_poll(self):
        """Sensor shouldn't use polling."""
        return False
