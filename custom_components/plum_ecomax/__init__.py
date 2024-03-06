"""The Plum ecoMAX integration."""
from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import asdict
from functools import cached_property
import logging
from typing import Any, Final, cast, final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CODE,
    ATTR_DEVICE_ID,
    ATTR_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from pyplumio.const import ProductType
from pyplumio.devices import Device
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import custom, delta
from pyplumio.structures.alerts import ATTR_ALERTS, Alert

from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ATTR_FROM,
    ATTR_MIXERS,
    ATTR_MODULES,
    ATTR_PRODUCT,
    ATTR_THERMOSTATS,
    ATTR_TO,
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONNECTION_TYPE_TCP,
    DEFAULT_CONNECTION_TYPE,
    DOMAIN,
    EVENT_PLUM_ECOMAX_ALERT,
    MANUFACTURER,
    DeviceType,
    ModuleType,
)
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]

DATE_STR_FORMAT: Final = "%Y-%m-%d %H:%M:%S"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Plum ecoMAX from a config entry."""
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)
    connection = EcomaxConnection(
        hass,
        entry,
        await async_get_connection_handler(connection_type, hass, entry.data),
    )

    try:
        await connection.async_setup()
    except TimeoutError as e:
        await connection.close()
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="connection_timeout",
            translation_placeholders={"connection": connection.name},
        ) from e

    async_setup_services(hass, connection)
    async_setup_events(hass, connection)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = connection

    async def _async_close_connection(event: Event | None = None) -> None:
        """Close the ecoMAX connection on HA Stop."""
        await connection.close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_close_connection)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def async_setup_events(hass: HomeAssistant, connection: EcomaxConnection) -> bool:
    """Set up the ecoMAX events."""

    device_registry = dr.async_get(hass)

    async def _async_dispatch_alert_events(alerts: list[Alert]) -> None:
        """Handle ecoMAX alert events."""
        if (
            device := device_registry.async_get_device({(DOMAIN, connection.uid)})
        ) is None:
            _LOGGER.error("Device not found. uid: %s", connection.uid)
            return

        for alert in alerts:
            event_data = {
                ATTR_NAME: connection.name,
                ATTR_DEVICE_ID: device.id,
                ATTR_CODE: alert.code,
                ATTR_FROM: alert.from_dt.strftime(DATE_STR_FORMAT),
            }
            if alert.to_dt is not None:
                event_data[ATTR_TO] = alert.to_dt.strftime(DATE_STR_FORMAT)

            hass.bus.async_fire(EVENT_PLUM_ECOMAX_ALERT, event_data)

    connection.device.subscribe(
        ATTR_ALERTS, custom(delta(_async_dispatch_alert_events), bool)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        try:
            connection: EcomaxConnection = hass.data[DOMAIN][entry.entry_id]
            await connection.close()
            hass.data[DOMAIN].pop(entry.entry_id)
        except KeyError:
            pass

    return cast(bool, unload_ok)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    connection_type = config_entry.data.get(
        CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE
    )
    connection = EcomaxConnection(
        hass,
        config_entry,
        await async_get_connection_handler(connection_type, hass, config_entry.data),
    )
    await connection.connect()
    data = {**config_entry.data}

    try:
        device = await connection.get(DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT)

        if config_entry.version in (1, 2):
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_TYPE] = product.type
            config_entry.version = 3

        if config_entry.version in (3, 4, 5):
            with suppress(KeyError):
                del data[CONF_CAPABILITIES]

            data[CONF_SUB_DEVICES] = await async_get_sub_devices(device)
            config_entry.version = 6

        if config_entry.version == 6:
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_ID] = product.id
            config_entry.version = 7

        if config_entry.version == 7:
            modules = await device.get(ATTR_MODULES, timeout=DEFAULT_TIMEOUT)
            data[CONF_SOFTWARE] = asdict(modules)
            config_entry.version = 8

        hass.config_entries.async_update_entry(config_entry, data=data)
        await connection.close()
        _LOGGER.info("Migration to version %s successful", config_entry.version)
    except TimeoutError:
        _LOGGER.error("Migration failed, device has failed to respond in time")
        return False

    return True


class EcomaxEntity(ABC):
    """Represents an ecoMAX entity."""

    _attr_available = False
    _attr_entity_registry_enabled_default: bool
    _attr_should_poll = False
    _attr_has_entity_name = True
    connection: EcomaxConnection
    entity_description: EntityDescription

    async def async_added_to_hass(self) -> None:
        """Subscribe to events."""

        async def _async_set_available(value: Any = None) -> None:
            """Mark entity as available."""
            self._attr_available = True

        func = self.entity_description.filter_fn(self.async_update)
        self.device.subscribe_once(self.entity_description.key, _async_set_available)
        self.device.subscribe(self.entity_description.key, func)

        if self.entity_description.key in self.device.data:
            await _async_set_available()
            await func(self.device.get_nowait(self.entity_description.key, None))

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from events."""
        self.device.unsubscribe(self.entity_description.key, self.async_update)

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

    @cached_property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            configuration_url=(
                f"http://{self.connection.entry.data[CONF_HOST]}"
                if self.connection.entry.data[CONF_CONNECTION_TYPE]
                == CONNECTION_TYPE_TCP
                else None
            ),
            identifiers={(DOMAIN, self.connection.uid)},
            manufacturer=MANUFACTURER,
            model=self.connection.model,
            name=self.connection.name,
            serial_number=self.connection.uid,
            sw_version=self.connection.software[ModuleType.A],
        )

    @cached_property
    def device(self) -> Device:
        """Return the device handler."""
        return self.connection.device

    @abstractmethod
    async def async_update(self, value: Any) -> None:
        """Update entity state."""


class ThermostatEntity(EcomaxEntity):
    """Represents a thermostat entity."""

    index: int

    @cached_property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.THERMOSTAT}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.THERMOSTAT}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            name=f"{self.connection.name} Thermostat {self.index + 1}",
            sw_version=self.connection.software[ModuleType.ECOSTER],
            via_device=(DOMAIN, self.connection.uid),
        )

    @final
    @cached_property
    def device(self) -> Thermostat:
        """Return the mixer handler."""
        return cast(
            Thermostat, self.connection.device.data[ATTR_THERMOSTATS][self.index]
        )


class MixerEntity(EcomaxEntity):
    """Represents a mixer entity."""

    index: int

    @cached_property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.MIXER}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    def device_name(self) -> str:
        """Return the device name."""
        return (
            "Circuit"
            if self.connection.product_type == ProductType.ECOMAX_I
            else "Mixer"
        )

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.MIXER}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            name=f"{self.connection.name} {self.device_name} {self.index + 1}",
            via_device=(DOMAIN, self.connection.uid),
        )

    @final
    @cached_property
    def device(self) -> Mixer:
        """Return the mixer handler."""
        return cast(Mixer, self.connection.device.data[ATTR_MIXERS][self.index])
