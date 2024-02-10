"""Base ecoMAX entity for Plum ecoMAX."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast, final

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from pyplumio.const import ProductType
from pyplumio.devices import Device as BaseDevice
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat

from .connection import EcomaxConnection
from .const import ATTR_MIXERS, ATTR_THERMOSTATS, DOMAIN, MANUFACTURER, Device


class EcomaxEntity(ABC):
    """Represents an ecoMAX entity."""

    _attr_available: bool = False
    _attr_entity_registry_enabled_default: bool
    connection: EcomaxConnection
    entity_description: EntityDescription

    async def async_added_to_hass(self) -> None:
        """Subscribe to events."""

        async def async_set_available(value: Any = None) -> None:
            """Mark entity as available."""
            self._attr_available = True

        func = self.entity_description.filter_fn(self.async_update)
        self.device.subscribe_once(self.entity_description.key, async_set_available)
        self.device.subscribe(self.entity_description.key, func)

        if self.entity_description.key in self.device.data:
            await async_set_available()
            await func(self.device.get_nowait(self.entity_description.key, None))

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from events."""
        self.device.unsubscribe(self.entity_description.key, self.async_update)

    @property
    def device(self) -> BaseDevice:
        """Return the device handler."""
        return self.connection.device

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.connection.device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if getattr(self.entity_description, "always_available", False):
            return True

        return self.connection.connected.is_set() and self._attr_available

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if hasattr(self, "_attr_entity_registry_enabled_default"):
            return self._attr_entity_registry_enabled_default

        return self.entity_description.key in self.device.data

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def has_entity_name(self) -> bool:
        """Return if the name of the entity is describing only the entity itself."""
        return True

    @abstractmethod
    async def async_update(self, value: Any) -> None:
        """Update entity state."""


class ThermostatEntity(EcomaxEntity):
    """Represents a thermostat entity."""

    index: int

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return (
            f"{self.connection.uid}-thermostat-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=f"{self.connection.name} Thermostat {self.index + 1}",
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{Device.THERMOSTAT}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            model=f"{self.connection.model} (Thermostat {self.index + 1})",
            sw_version=self.connection.software,
            via_device=(DOMAIN, self.connection.uid),
        )

    @final
    @property
    def device(self) -> Thermostat:
        """Return the mixer handler."""
        return self.connection.device.data[ATTR_THERMOSTATS][self.index]


class MixerEntity(EcomaxEntity):
    """Represents a mixer entity."""

    index: int

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return (
            f"{self.connection.uid}-mixer-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @property
    def device_name(self) -> str:
        """Return the device name."""
        return (
            "Circuit"
            if self.connection.product_type == ProductType.ECOMAX_I
            else "Mixer"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=f"{self.connection.name} {self.device_name} {self.index + 1}",
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{Device.MIXER}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            model=f"{self.connection.model} ({self.device_name} {self.index + 1})",
            sw_version=self.connection.software,
            via_device=(DOMAIN, self.connection.uid),
        )

    @final
    @property
    def device(self) -> Mixer:
        """Return the mixer handler."""
        return cast(Mixer, self.connection.device.data[ATTR_MIXERS][self.index])
