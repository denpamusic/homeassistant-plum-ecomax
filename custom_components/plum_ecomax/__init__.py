"""The Plum ecoMAX integration."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass
from functools import cached_property
import logging
from typing import Any, Final, Literal, TypeVar, cast, final, override

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
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from pyplumio.const import ProductType
from pyplumio.devices import Device
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import Filter, custom, delta, on_change
from pyplumio.structures.alerts import ATTR_ALERTS, Alert

from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_sub_devices,
)
from .const import (
    ALL,
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

type PlumEcomaxConfigEntry = ConfigEntry["PlumEcomaxData"]


@dataclass
class PlumEcomaxData:
    """Represents and Plum ecoMAX config data."""

    connection: EcomaxConnection


async def async_setup_entry(hass: HomeAssistant, entry: PlumEcomaxConfigEntry) -> bool:
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
    entry.runtime_data = PlumEcomaxData(connection)

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


async def async_unload_entry(hass: HomeAssistant, entry: PlumEcomaxConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.connection.close()

    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant, entry: PlumEcomaxConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    connection_type = entry.data.get(CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)
    connection = EcomaxConnection(
        hass,
        entry,
        await async_get_connection_handler(connection_type, hass, entry.data),
    )
    await connection.connect()
    data = {**entry.data}

    try:
        device = await connection.get(DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT)

        if entry.version in (1, 2):
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_TYPE] = product.type
            entry.version = 3

        if entry.version in (3, 4, 5):
            with suppress(KeyError):
                del data[CONF_CAPABILITIES]

            data[CONF_SUB_DEVICES] = await async_get_sub_devices(device)
            entry.version = 6

        if entry.version == 6:
            product = await device.get(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_PRODUCT_ID] = product.id
            entry.version = 7

        if entry.version == 7:
            modules = await device.get(ATTR_MODULES, timeout=DEFAULT_TIMEOUT)
            data[CONF_SOFTWARE] = asdict(modules)
            entry.version = 8

        hass.config_entries.async_update_entry(entry, data=data)
        await connection.close()
        _LOGGER.info("Migration to version %s successful", entry.version)
    except TimeoutError:
        _LOGGER.error("Migration failed, device has failed to respond in time")
        return False

    return True


@dataclass(frozen=True, kw_only=True)
class EcomaxEntityDescription(EntityDescription):
    """Describes an ecoMAX entity."""

    always_available: bool = False
    entity_registry_enabled_default: bool = False
    filter_fn: Callable[[Any], Filter] = on_change
    module: ModuleType = ModuleType.A
    product_types: set[ProductType] | Literal["all"] = ALL


DescriptorT = TypeVar("DescriptorT", bound=EcomaxEntityDescription)


class EcomaxEntity(Entity):
    """Represents an ecoMAX entity."""

    _always_available: bool = False
    _attr_available = False
    _attr_has_entity_name = True
    _attr_should_poll = False
    connection: EcomaxConnection
    entity_description: EcomaxEntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxEntityDescription
    ) -> None:
        """Initialize a new ecoMAX entity."""
        self.connection = connection
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Subscribe to events."""
        description = self.entity_description
        handler = description.filter_fn(self.async_update)

        async def _async_set_available(value: Any = None) -> None:
            """Mark entity as available."""
            self._attr_available = True

        if description.key in self.device.data:
            await _async_set_available()
            await handler(self.device.get_nowait(description.key, None))

        self.device.subscribe_once(description.key, _async_set_available)
        self.device.subscribe(description.key, handler)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from events."""
        self.device.unsubscribe(self.entity_description.key, self.async_update)

    @property
    @override
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity_description.always_available:
            return True

        return self.connection.connected.is_set() and self._attr_available

    @property
    @override
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added.

        This only applies when fist added to the entity registry.
        """
        if self.entity_description.entity_registry_enabled_default:
            return True

        return self.entity_description.key in self.device.data

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @cached_property
    @override
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

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        raise NotImplementedError


class ThermostatEntity(EcomaxEntity):
    """Represents a thermostat entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return the unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.THERMOSTAT}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key="thermostat",
            translation_placeholders={
                "device_name": self.connection.name,
                "thermostat_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.THERMOSTAT}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            sw_version=self.connection.software[ModuleType.ECOSTER],
            via_device=(DOMAIN, self.connection.uid),
        )

    @cached_property
    @final
    @override
    def device(self) -> Thermostat:
        """Return the mixer handler."""
        return cast(
            Thermostat, self.connection.device.data[ATTR_THERMOSTATS][self.index]
        )


class MixerEntity(EcomaxEntity):
    """Represents a mixer entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.MIXER}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key=(
                "circuit"
                if self.connection.product_type == ProductType.ECOMAX_I
                else "mixer"
            ),
            translation_placeholders={
                "device_name": self.connection.name,
                "mixer_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.MIXER}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            via_device=(DOMAIN, self.connection.uid),
        )

    @cached_property
    @final
    @override
    def device(self) -> Mixer:
        """Return the mixer handler."""
        return cast(Mixer, self.connection.device.data[ATTR_MIXERS][self.index])
