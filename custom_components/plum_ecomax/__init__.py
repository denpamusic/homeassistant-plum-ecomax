"""The Plum ecoMAX integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import dt as dt_util
from pyplumio.helpers.filters import delta
from pyplumio.structures.alerts import Alert

from custom_components.plum_ecomax.services import async_setup_services

from .connection import (
    DEFAULT_TIMEOUT,
    EcomaxConnection,
    async_get_connection_handler,
    async_get_device_capabilities,
)
from .const import (
    ATTR_CODE,
    ATTR_FROM,
    ATTR_PRODUCT,
    ATTR_TO,
    CONF_CAPABILITIES,
    CONF_PRODUCT_TYPE,
    DOMAIN,
    ECOMAX,
    ECOMAX_ALERT_EVENT,
)

PLATFORMS: list[str] = [
    "sensor",
    "binary_sensor",
    "switch",
    "number",
    "water_heater",
    "button",
]

DATE_STR_FORMAT: Final = "%Y-%m-%d %H:%M:%S"

ATTR_ALERTS: Final = "alerts"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plum ecoMAX from a config entry."""
    connection = EcomaxConnection(
        hass, entry, await async_get_connection_handler(hass, entry.data)
    )

    async def async_close_connection(event=None):
        """Close ecoMAX connection on HA Stop."""
        await connection.close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_close_connection)
    )

    try:
        await connection.async_setup()
    except asyncio.TimeoutError as e:
        raise ConfigEntryNotReady("Device not found") from e

    await async_setup_services(hass, connection)
    await async_setup_events(hass, connection)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = connection
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_setup_events(hass: HomeAssistant, connection: EcomaxConnection) -> None:
    """Setup ecoMAX events."""

    async def _alerts_event(alerts: list[Alert]):
        """Handle ecoMAX alerts."""
        for alert in alerts:
            event_data = {
                ATTR_CODE: alert.code,
                ATTR_FROM: alert.from_dt.strftime(DATE_STR_FORMAT),
            }
            if alert.to_dt is not None:
                event_data[ATTR_TO] = alert.to_dt.strftime(DATE_STR_FORMAT)

            hass.bus.async_fire(ECOMAX_ALERT_EVENT, event_data)

    connection.device.subscribe(ATTR_ALERTS, delta(_alerts_event))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        try:
            connection: EcomaxConnection = hass.data[DOMAIN][entry.entry_id]
            await connection.close()
            hass.data[DOMAIN].pop(entry.entry_id)
        except KeyError:
            pass

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    try:
        if config_entry.version == 1:
            data = {**config_entry.data}
            connection = EcomaxConnection(
                hass,
                config_entry,
                await async_get_connection_handler(hass, config_entry.data),
            )
            await connection.connect()
            data[CONF_CAPABILITIES] = await async_get_device_capabilities(
                await connection.get_device(ECOMAX.lower())
            )
            await connection.close()

            config_entry.version = 2
            hass.config_entries.async_update_entry(config_entry, data=data)

        elif config_entry.version == 2:
            data = {**config_entry.data}
            connection = EcomaxConnection(
                hass,
                config_entry,
                await async_get_connection_handler(hass, config_entry.data),
            )
            await connection.connect()
            device = await connection.get_device(ECOMAX.lower())
            product = await device.get_value(ATTR_PRODUCT, timeout=DEFAULT_TIMEOUT)
            data[CONF_CAPABILITIES] = await async_get_device_capabilities(device)
            data[CONF_PRODUCT_TYPE] = product.type
            await connection.close()

            config_entry.version = 3
            hass.config_entries.async_update_entry(config_entry, data=data)

        _LOGGER.info("Migration to version %s successful", config_entry.version)
    except asyncio.TimeoutError:
        _LOGGER.error("Migration failed, device has failed to respond in time")
        return False

    return True
