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
from pyplumio.helpers.timeout import timeout

from .const import (
    ATTR_ECOMAX_CONTROL,
    ATTR_FUEL_BURNED,
    ATTR_MIXERS,
    ATTR_PASSWORD,
    ATTR_PRODUCT,
    ATTR_SCHEDULES,
    ATTR_WATER_HEATER,
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_UID,
    CONNECTION_TYPE_TCP,
    DOMAIN,
    ECOMAX,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final = 60
DEVICE_TIMEOUT: Final = 30
CAPABILITY_TIMEOUT: Final = 3

ATTR_MODULES: Final = "modules"
ATTR_SENSORS: Final = "sensors"
ATTR_PARAMETERS: Final = "parameters"
ATTR_WATER_HEATER_TEMP: Final = "water_heater_temp"


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


@timeout(seconds=DEFAULT_TIMEOUT)
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
    device = await connection.get_device(ECOMAX)
    product = await device.get_value(ATTR_PRODUCT)
    modules = await device.get_value(ATTR_MODULES)

    await connection.close()

    return (title, product, modules, await async_get_device_capabilities(device))


@timeout(seconds=DEFAULT_TIMEOUT)
async def async_get_device_capabilities(device: Device) -> list[str]:
    """Return device capabilities, presented as list of allowed keys."""
    await device.get_value(ATTR_SENSORS)
    await device.get_value(ATTR_PARAMETERS)
    capabilities = [ATTR_PRODUCT, ATTR_MODULES]
    capabilities += list(device.data.keys())
    for capability in (
        ATTR_FUEL_BURNED,
        ATTR_ECOMAX_CONTROL,
        ATTR_PASSWORD,
        ATTR_SCHEDULES,
        ATTR_MIXERS,
    ):
        try:
            await device.get_value(capability, timeout=CAPABILITY_TIMEOUT)
            capabilities.append(capability)
        except asyncio.TimeoutError:
            continue

    if ATTR_WATER_HEATER_TEMP in capabilities:
        capabilities.append(ATTR_WATER_HEATER)

    return capabilities


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

        raise AttributeError()

    async def async_setup(self) -> None:
        """Setup connection and add hass stop handler."""
        await self.connection.connect()
        self._device = await self.connection.get_device(ECOMAX, timeout=DEVICE_TIMEOUT)

    async def async_setup_mixers(self) -> None:
        """Setup mixers."""
        if ATTR_MIXERS in self.capabilities:
            await self.device.get_value(ATTR_MIXERS, timeout=CAPABILITY_TIMEOUT)

    async def async_update_device_capabilities(self) -> None:
        """Update device capabilities."""
        data = {**self.entry.data}
        data[CONF_CAPABILITIES] = await async_get_device_capabilities(self.device)
        self._hass.config_entries.async_update_entry(self.entry, data=data)
        _LOGGER.info("Updated device capabilities list")

    @property
    def device(self) -> Device:
        """Return connection state."""
        if self._device is None:
            raise ConfigEntryNotReady("Device not found")

        return self._device

    @property
    def model(self) -> str:
        """Return the product model."""
        return self.entry.data[CONF_MODEL].replace("EM", "ecoMAX ")

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
    def capabilities(self) -> list[str]:
        """Return the product capabilities."""
        return self.entry.data[CONF_CAPABILITIES]

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
