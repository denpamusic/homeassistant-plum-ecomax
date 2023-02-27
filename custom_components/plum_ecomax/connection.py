"""Contains the Plum ecoMAX connection."""
from __future__ import annotations

from collections.abc import Mapping
import logging
import math
from typing import Any, Final

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
import pyplumio
from pyplumio.const import FrameType, ProductType
from pyplumio.devices import Addressable

from .const import (
    ATTR_ECOMAX_PARAMETERS,
    ATTR_LOADED,
    ATTR_MIXER_PARAMETERS,
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_SENSORS,
    ATTR_THERMOSTAT_PARAMETERS,
    ATTR_THERMOSTATS,
    ATTR_WATER_HEATER,
    ATTR_WATER_HEATER_TEMP,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
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
    ECOMAX,
    MANUFACTURER,
)

DEFAULT_TIMEOUT: Final = 15

_LOGGER = logging.getLogger(__name__)


async def async_get_connection_handler(
    connection_type: str, hass: HomeAssistant, data: Mapping[str, Any]
) -> pyplumio.Connection:
    """Return connection handler object."""
    _LOGGER.debug("Getting connection handler for type: %s...", connection_type)

    if connection_type == CONNECTION_TYPE_TCP:
        public_ip = await async_get_source_ip(hass, target_ip=IPV4_BROADCAST_ADDR)
        ethernet = pyplumio.ethernet_parameters(ip=public_ip)
        return pyplumio.TcpConnection(
            data[CONF_HOST],
            data.get(CONF_PORT, DEFAULT_PORT),
            ethernet_parameters=ethernet,
        )

    return pyplumio.SerialConnection(
        data.get(CONF_DEVICE, DEFAULT_DEVICE),
        int(data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)),
    )


async def async_get_sub_devices(device: Addressable) -> list[str]:
    """Return device subdevices."""
    _LOGGER.debug("Checking connected sub-devices...")

    sub_devices: list[str] = []

    # Wait until sensors become available.
    await device.wait_for(ATTR_SENSORS, timeout=DEFAULT_TIMEOUT)

    if ATTR_MIXERS in device.data:
        mixer_count = len(device.data[ATTR_MIXERS])
        _LOGGER.info(
            "Detected %d mixer%s.", mixer_count, "s" if mixer_count > 1 else ""
        )
        sub_devices.append(ATTR_MIXERS)

    if ATTR_THERMOSTATS in device.data:
        thermostat_count = len(device.data[ATTR_THERMOSTATS])
        _LOGGER.info(
            "Detected %d thermostat%s.",
            thermostat_count,
            "s" if thermostat_count > 1 else "",
        )
        sub_devices.append(ATTR_THERMOSTATS)

    if ATTR_WATER_HEATER_TEMP in device.data and not math.isnan(
        device.data[ATTR_WATER_HEATER_TEMP]
    ):
        _LOGGER.info("Detected indirect water heater.")
        sub_devices.append(ATTR_WATER_HEATER)

    return sub_devices


class EcomaxConnection:
    """Represents the ecoMAX connection."""

    _connection: pyplumio.Connection
    _device: Addressable | None
    _hass: HomeAssistant
    entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, connection: pyplumio.Connection
    ):
        """Initialize new ecoMAX connection object."""
        self._connection = connection
        self._device = None
        self._hass = hass
        self.entry = entry

    def __getattr__(self, name: str):
        """Proxy calls to the underlying connection handler class."""
        if hasattr(self._connection, name):
            return getattr(self._connection, name)

        raise AttributeError

    async def async_setup(self) -> None:
        """Setup connection and add hass stop handler."""
        await self.connect()
        device: Addressable = await self.get(ECOMAX, timeout=DEFAULT_TIMEOUT)
        await device.wait_for(ATTR_LOADED, timeout=DEFAULT_TIMEOUT)
        await device.wait_for(ATTR_SENSORS, timeout=DEFAULT_TIMEOUT)
        await device.wait_for(ATTR_ECOMAX_PARAMETERS, timeout=DEFAULT_TIMEOUT)
        self._device = device

    async def async_setup_thermostats(self) -> bool:
        """Setup thermostats."""
        try:
            return await self.device.request(
                ATTR_THERMOSTAT_PARAMETERS,
                FrameType.REQUEST_THERMOSTAT_PARAMETERS,
                retries=5,
                timeout=DEFAULT_TIMEOUT,
            )
        except ValueError:
            _LOGGER.error("Timed out while trying to setup thermostats.")
            return False

    async def async_setup_mixers(self) -> bool:
        """Setup mixers."""
        try:
            return await self.device.request(
                ATTR_MIXER_PARAMETERS,
                FrameType.REQUEST_MIXER_PARAMETERS,
                retries=5,
                timeout=DEFAULT_TIMEOUT,
            )
        except ValueError:
            _LOGGER.error("Timed out while trying to setup mixers.")
            return False

    async def async_setup_regdata(self) -> bool:
        """Setup regdata."""
        try:
            return await self.device.request(
                ATTR_REGDATA,
                FrameType.REQUEST_DATA_SCHEMA,
                retries=5,
                timeout=DEFAULT_TIMEOUT,
            )
        except ValueError:
            _LOGGER.error("Timed out while trying to setup regulator data.")
            return False

    async def async_update_sub_devices(self) -> None:
        """Update sub-devices."""
        data = {**self.entry.data}
        data[CONF_SUB_DEVICES] = await async_get_sub_devices(self.device)
        self._hass.config_entries.async_update_entry(self.entry, data=data)
        _LOGGER.info("Updated sub-devices, reloading config entry...")
        await self._hass.config_entries.async_reload(self.entry.entry_id)

    @property
    def has_water_heater(self) -> bool:
        """Does device has attached water heater."""
        return ATTR_WATER_HEATER in self.entry.data.get(CONF_SUB_DEVICES, [])

    @property
    def has_thermostats(self) -> bool:
        """Does device has attached thermostats."""
        return ATTR_THERMOSTATS in self.entry.data.get(CONF_SUB_DEVICES, [])

    @property
    def has_mixers(self) -> bool:
        """Does device has attached mixers."""
        return ATTR_MIXERS in self.entry.data.get(CONF_SUB_DEVICES, [])

    @property
    def device(self) -> Addressable:
        """Return connection state."""
        if self._device is None:
            raise ConfigEntryNotReady("Device not ready")

        return self._device

    @property
    def model(self) -> str:
        """Return the product model."""
        return self.entry.data[CONF_MODEL]

    @property
    def product_type(self) -> ProductType:
        """Return the product type."""
        return self.entry.data[CONF_PRODUCT_TYPE]

    @property
    def product_id(self) -> int:
        """Return the product id."""
        return self.entry.data[CONF_PRODUCT_ID]

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
        """Return the connection name."""
        return self.entry.title

    @property
    def connection(self) -> pyplumio.Connection:
        """Return the connection handler instance."""
        return self._connection

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
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
