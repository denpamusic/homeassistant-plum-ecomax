"""Base ecoMAX entity for all platforms."""

from pyplumio.devices import EcoMAX

from .connection import EcomaxConnection


class EcomaxEntity:
    """Base ecoMAX entity representation."""

    _ecomax: EcoMAX = None

    def __init__(self, id_: str, name: str):
        self._state = None
        self._id = id_
        self._name = name
        self._connection = None

    def set_connection(self, connection: EcomaxConnection):
        """Set ecoMAX connection instance."""
        self._connection = connection

    async def update_entity(self, ecomax: EcoMAX):
        if self._ecomax is None:
            self._ecomax = ecomax

    def get_attribute(self, name: str):
        if self.has_parameters:
            return getattr(self._ecomax, name)

        return None

    def set_attribute(self, name: str, value):
        if self.has_parameters:
            setattr(self._ecomax, name, value)

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

    @property
    def has_parameters(self):
        if self._ecomax is not None and self._ecomax.parameters is not None:
            return True

        return False

    @property
    def has_data(self):
        if self._ecomax is not None and self._ecomax.data is not None:
            return True

        return False
