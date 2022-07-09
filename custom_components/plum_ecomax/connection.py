"""Contains the Plum ecoMAX connection."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import EcoMAX
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
)

_LOGGER = logging.getLogger(__name__)


async def get_connection_handler(
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


@timeout(seconds=15)
async def check_connection(connection: Connection):
    """Perform connection check."""
    title = (
        connection.host
        if isinstance(connection, pyplumio.TcpConnection)
        else connection.device
    )
    await connection.connect()
    device = await connection.get_device("ecomax")
    product = await device.get_value("product")
    modules = await device.get_value("modules")
    sensors = await device.get_value("sensors")
    parameters = await device.get_value("parameters")
    capabilities = sensors.keys() + parameters.keys()
    for capability in ("fuel_burned", "boiler_control", "password"):
        try:
            await device.get_value(capability)
            capabilities.append(capability)
        except asyncio.TimeoutError:
            continue

    if "water_heater_temp" in capabilities:
        capabilities.append("water_heater")

    await connection.close()

    return (title, product, modules, capabilities)


class EcomaxConnection:
    """Represents the ecoMAX connection."""

    entry: ConfigEntry
    _hass: HomeAssistant
    _connection: Connection
    _device: EcoMAX | None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, connection: Connection):
        """Initialize new ecoMAX connection object."""
        self._hass = hass
        self._device = None
        self._connection = connection
        self.entry = entry

    async def async_setup(self) -> bool:
        """Setup connection and add hass stop handler."""

        async def _close(event=None) -> None:
            await self.connection.close()

        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close)
        await self.connection.connect()

        try:
            self._device = await self.connection.get_device("ecomax")
        except asyncio.TimeoutError:
            _LOGGER.error("DeviceNotFound: ecomax device not found")
            return False

        return True

    def __getattr__(self, name: str):
        """Proxy calls to the underlying connection handler class."""
        if hasattr(self._connection, name):
            return getattr(self._connection, name)

        return None

    @property
    def device(self):
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
            manufacturer="Plum Sp. z o.o.",
            model=f"{self.model} (uid: {self.uid})",
            sw_version=self.software,
        )
