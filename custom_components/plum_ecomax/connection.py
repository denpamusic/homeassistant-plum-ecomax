"""Connection handler for Plum ecoMAX."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from functools import cached_property
import logging
import math
from typing import Any, Final, cast

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import pyplumio
from pyplumio.connection import Connection
from pyplumio.const import FrameType, ProductType
from pyplumio.devices import PhysicalDevice
from pyplumio.structures.mixer_parameters import ATTR_MIXER_PARAMETERS
from pyplumio.structures.mixer_sensors import ATTR_MIXERS_CONNECTED
from pyplumio.structures.temperatures import ATTR_WATER_HEATER_TEMP
from pyplumio.structures.thermostat_parameters import ATTR_THERMOSTAT_PARAMETERS
from pyplumio.structures.thermostat_sensors import ATTR_THERMOSTATS_CONNECTED

from .const import (
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_SENSORS,
    ATTR_SETUP,
    ATTR_THERMOSTATS,
    ATTR_WATER_HEATER,
    CONF_BAUDRATE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
    DeviceType,
)

DEFAULT_TIMEOUT: Final = 15
DEFAULT_RETRIES: Final = 5

_LOGGER = logging.getLogger(__name__)


async def async_get_connection_handler(
    connection_type: str, hass: HomeAssistant, data: Mapping[str, Any]
) -> Connection:
    """Return the connection handler."""
    _LOGGER.debug("Getting connection handler for type: %s...", connection_type)

    public_ip = await async_get_source_ip(hass, target_ip=IPV4_BROADCAST_ADDR)
    protocol = pyplumio.AsyncProtocol(
        ethernet_parameters=pyplumio.EthernetParameters(ip=public_ip)
    )

    if connection_type == CONNECTION_TYPE_TCP:
        return pyplumio.TcpConnection(
            data[CONF_HOST],
            data.get(CONF_PORT, DEFAULT_PORT),
            protocol=protocol,
        )

    return pyplumio.SerialConnection(
        data.get(CONF_DEVICE, DEFAULT_DEVICE),
        int(data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)),
        protocol=protocol,
    )


async def async_get_sub_devices(device: PhysicalDevice) -> list[str]:
    """Return the sub-devices."""
    _LOGGER.debug("Checking connected sub-devices...")

    sub_devices: list[str] = []

    # Wait until sensors are available.
    await device.wait_for(ATTR_SENSORS, timeout=DEFAULT_TIMEOUT)

    if (mixers_connected := device.get_nowait(ATTR_MIXERS_CONNECTED, 0)) > 0:
        _LOGGER.info(
            "Detected %d mixer%s.",
            mixers_connected,
            "s" if mixers_connected > 1 else "",
        )
        sub_devices.append(ATTR_MIXERS)

    if (thermostats_connected := device.get_nowait(ATTR_THERMOSTATS_CONNECTED, 0)) > 0:
        _LOGGER.info(
            "Detected %d thermostat%s.",
            thermostats_connected,
            "s" if thermostats_connected > 1 else "",
        )
        sub_devices.append(ATTR_THERMOSTATS)

    if ATTR_WATER_HEATER_TEMP in device.data and not math.isnan(
        device.data[ATTR_WATER_HEATER_TEMP]
    ):
        _LOGGER.info("Detected indirect water heater.")
        sub_devices.append(ATTR_WATER_HEATER)

    return sub_devices


class EcomaxConnection:
    """Represents an ecoMAX connection."""

    _connection: Connection
    _device: PhysicalDevice | None
    _hass: HomeAssistant
    entry: ConfigEntry

    _request_cache: dict[str, bool]
    _request_locks: dict[str, asyncio.Lock]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, connection: Connection):
        """Initialize a new ecoMAX connection."""
        self._connection = connection
        self._device = None
        self._hass = hass
        self.entry = entry

        self._request_cache = {}
        self._request_locks = {}

    def __getattr__(self, name: str) -> Any:
        """Proxy calls to the underlying connection handler class."""
        if hasattr(self._connection, name):
            return getattr(self._connection, name)

        raise AttributeError

    async def async_setup(self) -> None:
        """Set up ecoMAX connection."""
        await self._connection.connect()
        device: PhysicalDevice = await self.get(
            DeviceType.ECOMAX, timeout=DEFAULT_TIMEOUT
        )
        await device.wait_for(ATTR_SETUP, timeout=DEFAULT_TIMEOUT)
        self._device = device

    async def _request_with_cache(self, name: str, frame_type: FrameType) -> bool:
        """Make request and cache the result."""
        lock = self._request_locks.setdefault(name, asyncio.Lock())
        async with lock:
            if name not in self._request_cache:
                try:
                    await self.device.request(
                        name,
                        frame_type,
                        retries=DEFAULT_RETRIES,
                        timeout=DEFAULT_TIMEOUT,
                    )
                    self._request_cache[name] = True
                except pyplumio.RequestError:
                    _LOGGER.exception("Request failed")
                    self._request_cache[name] = False

        return self._request_cache[name]

    async def async_setup_thermostats(self) -> bool:
        """Set up thermostats."""
        return await self._request_with_cache(
            ATTR_THERMOSTAT_PARAMETERS, FrameType.REQUEST_THERMOSTAT_PARAMETERS
        )

    async def async_setup_mixers(self) -> bool:
        """Set up mixers."""
        return await self._request_with_cache(
            ATTR_MIXER_PARAMETERS, FrameType.REQUEST_MIXER_PARAMETERS
        )

    async def async_setup_regdata(self) -> bool:
        """Set up regulator data."""
        return await self._request_with_cache(
            ATTR_REGDATA, FrameType.REQUEST_REGULATOR_DATA_SCHEMA
        )

    async def async_update_sub_devices(self) -> None:
        """Update sub-devices."""
        data = dict(self.entry.data)
        data[CONF_SUB_DEVICES] = await async_get_sub_devices(self.device)
        self._hass.config_entries.async_update_entry(self.entry, data=data)
        _LOGGER.info("Updated sub-devices, reloading config entry...")
        await self._hass.config_entries.async_reload(self.entry.entry_id)

    async def async_close(self) -> None:
        """Close ecoMAX connection."""
        await self._connection.close()

    @property
    def device(self) -> PhysicalDevice:
        """Return the device handler."""
        if self._device is None:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="device_not_ready",
                translation_placeholders={"device": self.model},
            )

        return self._device

    @cached_property
    def has_water_heater(self) -> bool:
        """Return if device has attached water heater."""
        return ATTR_WATER_HEATER in self.entry.data.get(CONF_SUB_DEVICES, [])

    @cached_property
    def has_thermostats(self) -> bool:
        """Return if device has attached thermostats."""
        return ATTR_THERMOSTATS in self.entry.data.get(CONF_SUB_DEVICES, [])

    @cached_property
    def has_mixers(self) -> bool:
        """Return if device has attached mixers."""
        return ATTR_MIXERS in self.entry.data.get(CONF_SUB_DEVICES, [])

    @cached_property
    def model(self) -> str:
        """Return the product model."""
        return cast(str, self.entry.data[CONF_MODEL])

    @cached_property
    def product_type(self) -> ProductType:
        """Return the product type."""
        return cast(ProductType, self.entry.data[CONF_PRODUCT_TYPE])

    @cached_property
    def product_id(self) -> int:
        """Return the product id."""
        return cast(int, self.entry.data[CONF_PRODUCT_ID])

    @cached_property
    def uid(self) -> str:
        """Return the product UID."""
        return cast(str, self.entry.data[CONF_UID])

    @cached_property
    def software(self) -> dict[str, str | None]:
        """Return the product software version."""
        return cast(dict[str, str | None], self.entry.data[CONF_SOFTWARE])

    @cached_property
    def name(self) -> str:
        """Return the connection name."""
        return self.entry.title
