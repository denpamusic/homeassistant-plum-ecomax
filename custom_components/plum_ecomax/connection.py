"""Implement async Plum ecoMAX connection."""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, List, Optional

from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pyplumio
from pyplumio.connection import Connection
from pyplumio.devices import DevicesCollection

from .const import (
    CONF_MODEL,
    CONF_SW_VERSION,
    CONF_UID,
    CONNECTION_CHECK_TRIES,
    DEFAULT_DEVICE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


class EcomaxConnection(ABC):
    """Represent base ecoMAX connection.

    Attributes:
        ecomax -- instance of ecoMAX device
        _name -- connection name
        _hass -- instance of Home Assistant core
        _entities -- list of entities
        _check_tries -- how much connection check tries was performed
        _task -- connection task
        _update_interval -- data update interval in seconds
        _connection -- instance of current connection
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
        self._sw_version = None

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
            devices.ecomax
            and devices.ecomax.uid
            and devices.ecomax.product
            and devices.ecomax.module_a
        ):
            self._uid = devices.ecomax.uid
            self._model = devices.ecomax.product
            self._sw_version = devices.ecomax.module_a
            connection.close()

        self._check_tries += 1

    async def check(self) -> None:
        """Perform connection check."""
        await self._connection.task(
            self._check_callback, interval=1, reconnect_on_failure=False
        )

    async def async_setup(self, entry: ConfigEntry) -> None:
        """Setup connection and add hass stop handler."""
        self._connection.set_eth(ip=await async_get_source_ip(self._hass))
        self._task = self._hass.loop.create_task(
            self._connection.task(self.update_entities, self._update_interval)
        )
        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.close)
        self._model = entry.data[CONF_MODEL]
        self._uid = entry.data[CONF_UID]
        self._sw_version = entry.data[CONF_SW_VERSION]

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
            entity.set_connection(self)
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
        if devices.ecomax and devices.ecomax.data is not None:
            self.ecomax = devices.ecomax
            for entity in self._entities:
                await entity.async_update_state()

    @property
    def model(self) -> Optional[str]:
        """Return the product model."""
        return self._model

    @property
    def uid(self) -> Optional[str]:
        """Return the product UID."""
        return self._uid

    @property
    def sw_version(self) -> Optional[str]:
        """Return the product software version."""
        return self._sw_version

    def close(self, event=None) -> None:
        """Close connection and cancel connection coroutine."""
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
    """Represent ecoMAX TCP connection.

    Attributes:
        _host -- serial server ip or hostname
        _port -- serial server port
    """

    def __init__(
        self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, *args, **kwargs
    ):
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
    """Represent ecoMAX serial connection.

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
