"""Implement async Plum ecoMAX connection."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from homeassistant.components.network import async_get_source_ip
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pyplumio
from pyplumio.devices import DevicesCollection
from pyplumio.econet import EcoNET

from .const import CONNECTION_CHECK_TRIES, DEFAULT_INTERVAL, DEFAULT_PORT

if TYPE_CHECKING:
    from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


class EcomaxConnection:
    """Representation of ecoMAX connection.

    Attributes:
        ecomax -- instance of ecoMAX device
        _host -- serial server ip or hostname
        _port -- serial server port
        _name -- connection name
        _hass -- instance of Home Assistant core
        _entities -- list of entities
        _check_tries -- how much connection check tries was performed
        _uid -- device UID
        _task -- connection task
        _interval -- data update interval in seconds
        _connection -- instance of current connection
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = DEFAULT_PORT,
        interval: int = DEFAULT_INTERVAL,
    ):
        """Construct new connection.

        Keyword arguments:
            hass -- instance of Home Assistant core
            host -- serial server ip or hostname
            port -- serial server port
            interval -- data update interval in seconds
        """
        self.ecomax = None
        self._host = host
        self._port = port
        self._name = host
        self._hass = hass
        self._entities: List[EcomaxEntity] = []
        self._check_tries = 0
        self._uid = None
        self._task = None
        self._interval = interval
        self._connection = pyplumio.TcpConnection(host, port)

    async def _check_callback(
        self, devices: DevicesCollection, connection: EcoNET
    ) -> None:
        """Called when connection check succeeds.

        Keyword arguments:
            devices -- collection of available devices
            connection -- instance of current connection
        """
        if self._check_tries > CONNECTION_CHECK_TRIES:
            _LOGGER.exception("Connection succeeded, but device failed to respond.")
            connection.close()

        if devices.ecomax and devices.ecomax.uid and devices.ecomax.product:
            self.ecomax = devices.ecomax
            connection.close()

        self._check_tries += 1

    async def check(self) -> Tuple[Union[str, None], Union[str, None]]:
        """Perform connection check."""
        await self._connection.task(self._check_callback, 1)
        return self.product, self.uid

    async def async_setup(self) -> None:
        """Setup connection and add hass stop handler."""
        self._connection.set_eth(ip=await async_get_source_ip(self._hass))
        self._task = self._hass.loop.create_task(
            self._connection.task(self.update_entities, self._interval)
        )
        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.close)

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
        self, devices: DevicesCollection, connection: EcoNET
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
    def product(self) -> Optional[str]:
        """Return currently connected product type."""
        if self.ecomax is not None and self.ecomax.product is not None:
            return self.ecomax.product

        return None

    @property
    def uid(self) -> Optional[str]:
        """Return currently connected product UID."""
        if self.ecomax is not None and self.ecomax.uid is not None:
            return self.ecomax.uid

        return None

    @property
    def name(self) -> str:
        """Return connection name."""
        return self._name

    @property
    def host(self) -> str:
        """Return connection host."""
        return self._host

    @property
    def port(self) -> int:
        """Return connection port."""
        return self._port

    def close(self, event=None) -> None:
        """Close connection and cancel connection coroutine."""
        self._connection.close()
        if self._task:
            self._task.cancel()
