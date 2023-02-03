"""Contains the Plum ecoMAX connection."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any, Final

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo

from .const import (
    ATTR_MIXERS,
    ATTR_MODULES,
    ATTR_PRODUCT,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_TCP,
    DOMAIN,
    ECOMAX,
    MANUFACTURER,
)

DEFAULT_TIMEOUT: Final = 10

_LOGGER = logging.getLogger(__name__)


async def async_get_connection_handler(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> pyplumio.Connection:
    """Return connection handler object."""
    public_ip = await async_get_source_ip(hass, target_ip=IPV4_BROADCAST_ADDR)
    ethernet = pyplumio.ethernet_parameters(ip=public_ip)
    if data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP:
        return pyplumio.TcpConnection(
            data[CONF_HOST], data[CONF_PORT], ethernet_parameters=ethernet
        )

    return pyplumio.SerialConnection(data[CONF_DEVICE], ethernet_parameters=ethernet)


async def async_check_connection(
    connection: Connection,
) -> tuple[str, ProductInfo, ConnectedModules, list[str]]:
    """Perform connection check."""
    title = (
        connection.host
        if isinstance(connection, pyplumio.TcpConnection)
        else connection.device
    )
    await connection.connect()
    device = await connection.get_device(ECOMAX, timeout=DEFAULT_TIMEOUT)
    product = await device.get_value(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
    modules = await device.get_value(ATTR_MODULES, timeout=DEFAULT_TIMEOUT)
    sub_devices = await async_get_sub_devices(device)
    await connection.close()

    return title, product, modules, sub_devices


async def async_get_sub_devices(device: Device) -> list[str]:
    """Return device subdevices."""
    sub_devices: list[str] = []
    try:
        await device.get_value(ATTR_MIXERS, timeout=DEFAULT_TIMEOUT)
        sub_devices.append(ATTR_MIXERS)
    except asyncio.TimeoutError:
        pass

    return sub_devices


class EcomaxConnection:
    """Represents the ecoMAX connection."""

    entry: ConfigEntry
    _hass: HomeAssistant
    _connection: Connection
    _device: Device | None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, connection: Connection):
        """Initialize new ecoMAX connection object."""
        self._hass = hass
        self._device = None
        self._connection = connection
        self.entry = entry

    def __getattr__(self, name: str):
        """Proxy calls to the underlying connection handler class."""
        if hasattr(self._connection, name):
            return getattr(self._connection, name)

        raise AttributeError

    async def async_setup(self) -> None:
        """Setup connection and add hass stop handler."""
        await self.connect()
        self._device = await self.get_device(ECOMAX, timeout=DEFAULT_TIMEOUT)

    async def async_update_sub_devices(self) -> None:
        """Update sub-devices."""
        data = {**self.entry.data}
        data[CONF_SUB_DEVICES] = await async_get_sub_devices(self.device)
        self._hass.config_entries.async_update_entry(self.entry, data=data)
        _LOGGER.info("Updated sub-devices, reloading config entry...")
        await self._hass.config_entries.async_reload(self.entry.entry_id)

    @property
    def has_mixers(self) -> bool:
        """Does device has attached mixers."""
        return ATTR_MIXERS in self.entry.data[CONF_SUB_DEVICES]

    @property
    def device(self) -> Device:
        """Return connection state."""
        if self._device is None:
            raise ConfigEntryNotReady("Device not found")

        return self._device

    @property
    def model(self) -> str:
        """Return the product model."""
        return self.entry.data[CONF_MODEL]

    @property
    def product_type(self) -> int:
        """Return the product type."""
        return self.entry.data[CONF_PRODUCT_TYPE]

    @property
    def uid(self) -> str:
        """Return the product UID."""
        return self.entry.data[CONF_UID]

    @property
    def software(self) -> str:
        """Return the product software version."""
        return self.entry.data[CONF_SOFTWARE]

    @property
    def name(self) -> str:
        """Return connection name."""
        if isinstance(self.connection, pyplumio.TcpConnection):
            return self.connection.host

        return self.connection.device

    @property
    def connection(self) -> Connection:
        """Returns connection handler instance."""
        return self._connection

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            name=self.name,
            identifiers={(DOMAIN, self.uid)},
            manufacturer=MANUFACTURER,
            model=self.model,
            sw_version=self.software,
            configuration_url=f"http://{self.entry.data[CONF_HOST]}"
            if self.entry.data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP
            else None,
        )
