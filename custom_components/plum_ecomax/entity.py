"""Base ecoMAX entity class."""

from abc import ABC, abstractmethod

from homeassistant.helpers.entity import DeviceInfo, EntityDescription

from .connection import MANUFACTURER, EcomaxConnection
from .const import DOMAIN


class EcomaxEntity(ABC):
    """Represents base ecoMAX entity."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_entity_registry_enabled_default: bool

    async def async_added_to_hass(self):
        """Called when an entity has their entity_id assigned."""
        func = self.entity_description.filter_fn(self.async_update)

        # Feed initial value to the callback function.
        if self.entity_description.key in self.device.data:
            await func(self.device.data[self.entity_description.key])

        self.device.subscribe(self.entity_description.key, func)

    async def async_will_remove_from_hass(self):
        """Called when an entity is about to be removed."""
        self.device.unsubscribe(self.entity_description.key, self.async_update)

    @property
    def device(self):
        """Return device object."""
        return self.connection.device

    @property
    def available(self) -> bool:
        """Indicates whether the entity is available."""
        return self.connection.connected.is_set() and self.connection.device is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self.connection.device_info

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Indicate if the entity should be enabled when first added."""
        return self.entity_description.key in self.connection.capabilities

    @property
    def unique_id(self) -> str:
        """A unique identifier for this entity."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @property
    def name(self) -> str:
        """Name of the entity."""
        return f"{self.connection.name} {self.entity_description.name}"

    @property
    def connection(self) -> EcomaxConnection:
        """Ecomax connection instance."""
        return self._connection

    @property
    def should_poll(self) -> bool:
        """Should hass check with the entity for an updated state."""
        return False

    @abstractmethod
    async def async_update(self, value) -> None:
        """Retrieve latest state."""


class MixerEntity(EcomaxEntity):
    """Represents base mixer entity."""

    mixer_number: int

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Indicate if the entity should be enabled when first added."""
        return self.entity_description.key in self.device.data.keys()

    @property
    def unique_id(self) -> str:
        """A unique identifier for this entity."""
        return (
            f"{self.connection.uid}-mixer-"
            + f"{self.mixer_number}-{self.entity_description.key}"
        )

    @property
    def name(self) -> str:
        """Name of the entity."""
        return (
            f"{self.connection.name} Mixer "
            + f"{self.mixer_number} {self.entity_description.name}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            name=f"{self.connection.name} Mixer {self.mixer_number}",
            identifiers={(DOMAIN, f"{self.connection.uid}-mixer-{self.mixer_number}")},
            manufacturer=MANUFACTURER,
            model=f"{self.connection.model}",
            sw_version=self.connection.software,
            via_device=(DOMAIN, self.connection.uid),
        )

    @property
    def device(self):
        """Return mixer object."""
        return self.connection.device.data["mixers"][self.mixer_number]
