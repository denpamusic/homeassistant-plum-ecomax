"""Contains the Plum ecoMAX connection."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, List, Optional

from homeassistant.components.network import async_get_source_ip
from homeassistant.components.network.const import IPV4_BROADCAST_ADDR
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import DevicesCollection

from .const import (
    CONF_CAPABILITIES,
    CONF_MODEL,
    CONF_SOFTWARE,
    CONF_UID,
    CONNECTION_CHECK_TRIES,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


class EcomaxConnection(ABC):
    """Represent base ecoMAX connection.

    Attributes:
        ecomax -- instance of the ecomax device
        _name -- connection name
        _hass -- instance of Home Assistant core
        _entities -- list of entities
        _check_tries -- how much connection check tries was performed
        _task -- connection task
        _update_interval -- data update interval in seconds
        _connection -- instance of current connection
        _uid - the product uid
        _model - the product model
        _software - the product software
        _capabilities -- the product capabilities
    """

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ):
        """Construct new connection.

        Keyword arguments:
            hass -- instance of Home Assistant core
            host -- serial server ip or hostname
            port -- serial server port
            update_interval -- data update interval in seconds
        """
        self.ecomax = None
        self._entities: List[EcomaxEntity] = []
        self._check_tries = 0
        self._task = None
        self._hass = hass
        self._update_interval = update_interval
        self._connection = self.get_connection()
        self._uid = None
        self._model = None
        self._software = None
        self._capabilities: List[str] = []

    async def _check_callback(
        self, devices: DevicesCollection, connection: Connection
    ) -> None:
        """Called when connection check succeeds.

        Keyword arguments:
            devices -- collection of available devices
            connection -- instance of current connection
        """
        if self._check_tries > CONNECTION_CHECK_TRIES:
            _LOGGER.exception("Connection succeeded, but device failed to respond.")
            connection.close()

        if (
            devices.has("ecomax")
            and None
            not in [
                devices.ecomax.uid,
                devices.ecomax.product,
                devices.ecomax.software,
            ]
            and len(devices.ecomax.data) > 1
            and len(devices.ecomax.parameters) > 1
        ):
            self._uid = devices.ecomax.uid
            self._model = devices.ecomax.product
            self._software = devices.ecomax.software
            self._capabilities = ["fuel_burned"]
            self._capabilities += list(devices.ecomax.data.keys())
            self._capabilities += list(devices.ecomax.parameters.keys())
            if "water_heater_temp" in self._capabilities:
                self._capabilities.append("water_heater")

            connection.close()

        self._check_tries += 1

    async def check(self) -> None:
        """Perform connection check."""
        await self._connection.task(
            self._check_callback, interval=1, reconnect_on_failure=False
        )

    async def async_setup(self, entry: ConfigEntry) -> None:
        """Setup connection and add hass stop handler."""
        self._connection.set_eth(
            ip=await async_get_source_ip(self._hass, target_ip=IPV4_BROADCAST_ADDR)
        )
        self._connection.on_closed(self.connection_closed)
        self._task = self._hass.loop.create_task(
            self._connection.task(self.update_entities, self._update_interval)
        )
        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.close)
        self._model = entry.data[CONF_MODEL]
        self._uid = entry.data[CONF_UID]
        self._software = entry.data[CONF_SOFTWARE]
        if CONF_CAPABILITIES in entry.data:
            self._capabilities = entry.data[CONF_CAPABILITIES]

    async def async_unload(self) -> None:
        """Close connection on entry unload."""
        await self._hass.async_add_executor_job(self.close)

    async def add_entities(
        self, entities: List, add_entities_callback: AddEntitiesCallback
    ) -> None:
        """Add sensor entities to the processing queue.

        Keyword arguments:
            entities -- list of entities
            add_entities_callback -- callback to add entities to hass
        """
        for entity in entities:
            self._entities.append(entity)

        add_entities_callback(entities, True)

    async def update_entities(
        self, devices: DevicesCollection, connection: Connection
    ) -> None:
        """Call update method for sensor instance.

        Keyword arguments:
            devices -- collection of available devices
            connection -- instance of current connection
        """
        if devices.has("ecomax") and devices.ecomax.data:
            if devices.ecomax.software is not None:
                self._software = devices.ecomax.software

            self.ecomax = devices.ecomax
            for entity in self._entities:
                if entity.enabled:
                    await entity.async_update_state()

    async def connection_closed(self, connection: Connection) -> None:
        """If connection is closed, set entities state to unknown.

        Keyword arguments:
            connection -- instance of current connection
        """
        self.ecomax = None
        for entity in self._entities:
            await entity.async_update_state()

    @property
    def model(self) -> Optional[str]:
        """Return the product model."""
        return self._model.replace("EM", "ecoMAX ")

    @property
    def uid(self) -> Optional[str]:
        """Return the product UID."""
        return self._uid

    @property
    def software(self) -> Optional[str]:
        """Return the product software version."""
        return self._software

    @property
    def capabilities(self) -> List:
        """Return the product capabilities."""
        return self._capabilities

    @property
    def update_interval(self) -> Optional[int]:
        """Return update interval in seconds."""
        return self._update_interval

    def close(self, event=None) -> None:
        """Close connection and cancel connection coroutine."""
        self._connection.on_closed(callback=None)
        self._connection.close()
        if self._task:
            self._task.cancel()

    @abstractmethod
    def get_connection(self) -> Connection:
        """Return connection instance."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return connection name."""


class EcomaxTcpConnection(EcomaxConnection):
    """Represent ecomax TCP connection.

    Attributes:
        _host -- serial server ip or hostname
        _port -- serial server port
    """

    def __init__(self, host, port: int = DEFAULT_PORT, *args, **kwargs):
        """Construct new connection.

        Keyword arguments:
            host -- serial server ip or hostname
            port -- serial server port
        """
        self._host = host
        self._port = port
        super().__init__(*args, **kwargs)

    def get_connection(self) -> Connection:
        """Return connection instance."""
        if hasattr(self, "_connection") and isinstance(self._connection, Connection):
            return self._connection

        return pyplumio.TcpConnection(self._host, self._port)

    @property
    def name(self) -> str:
        """Return connection name."""
        return self._host

    @property
    def host(self) -> str:
        """Return connection host."""
        return self._host

    @property
    def port(self) -> int:
        """Return connection port."""
        return self._port


class EcomaxSerialConnection(EcomaxConnection):
    """Represent ecomax serial connection.

    Attributes:
        _device -- serial device path, e. g. /dev/ttyUSB0
    """

    def __init__(self, device: str = DEFAULT_DEVICE, *args, **kwargs):
        """Construct new connection.

        Keyword arguments:
            device -- serial device path, e. g. /dev/ttyUSB0
        """
        self._device = device
        super().__init__(*args, **kwargs)

    def get_connection(self) -> Connection:
        """Return connection instance."""
        if hasattr(self, "_connection") and isinstance(self._connection, Connection):
            return self._connection

        return pyplumio.SerialConnection(self._device)

    @property
    def name(self) -> str:
        """Return connection name."""
        return self._device

    @property
    def device(self) -> str:
        """Return connection device."""
        return self._device
