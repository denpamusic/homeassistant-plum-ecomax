"""Contains the Plum ecoMAX connection."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any, Final, Tuple

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import Device
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo
from pyplumio.helpers.timeout import timeout

from .const import (
    CONF_CAPABILITIES,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SOFTWARE,
    CONF_UID,
    CONNECTION_TYPE_TCP,
    DOMAIN,
    ECOMAX,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final = 30
DEVICE_TIMEOUT: Final = 20

MANUFACTURER: Final = "Plum Sp. z o.o."


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
    product = await device.get_value("product")
    modules = await device.get_value("modules")

    await connection.close()

    return (title, product, modules, await async_get_device_capabilities(device))


@timeout(seconds=DEFAULT_TIMEOUT)
async def async_get_device_capabilities(device: Device) -> list[str]:
    """Return device capabilities, presented as list of allowed keys."""
    await device.get_value("sensors")
    await device.get_value("parameters")
    capabilities = ["product", "modules"]
    capabilities += list(device.data.keys())
    for capability in ("fuel_burned", "boiler_control", "password", "schedules"):
        try:
            await device.get_value(capability, timeout=5)
            capabilities.append(capability)
        except asyncio.TimeoutError:
            continue

    if "water_heater_temp" in capabilities:
        capabilities.append("water_heater")

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

    async def async_setup(self) -> Tuple[bool, str | None]:
        """Setup connection and add hass stop handler."""

        error_message = None
        await self.connection.connect()
        try:
            self._device = await self.connection.get_device(
                ECOMAX, timeout=DEVICE_TIMEOUT
            )
        except asyncio.TimeoutError:
            error_message = "Device has failed to respond in time"
            await self.connection.close()
            return False, error_message

        return True, error_message

    async def async_update_device_capabilities(self) -> None:
        """Update device capabilities."""
        if self.device is not None:
            data = {**self.entry.data}
            data[CONF_CAPABILITIES] = await async_get_device_capabilities(self.device)
            self._hass.config_entries.async_update_entry(self.entry, data=data)
            _LOGGER.info("Updated device capabilities list")

    @property
    def device(self) -> Device | None:
        """Return connection state."""
        return self._device

    @property
    def model(self) -> str:
        """Return the product model."""
        return self.entry.data[CONF_MODEL].replace("EM", "ecoMAX ")

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
            model=f"{self.model}",
            sw_version=self.software,
        )
