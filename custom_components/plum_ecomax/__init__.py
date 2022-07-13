"""The Plum ecoMAX integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection import (
    EcomaxConnection,
    get_connection_handler,
    get_device_capabilities,
)
from .const import CONF_CAPABILITIES, DOMAIN

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number", "water_heater"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plum ecoMAX from a config entry."""
    connection = EcomaxConnection(
        hass, entry, await get_connection_handler(hass, entry.data)
    )
    load_ok = await connection.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = connection
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return load_ok


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        try:
            connection = hass.data[DOMAIN][entry.entry_id]
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
                await get_connection_handler(hass, config_entry.data),
            )
            await connection.connect()
            data[CONF_CAPABILITIES] = await get_device_capabilities(
                await connection.get_device("ecomax")
            )
            await connection.close()

            config_entry.version = 2
            hass.config_entries.async_update_entry(config_entry, data=data)

        _LOGGER.info("Migration to version %s successful", config_entry.version)
    except asyncio.TimeoutError:
        _LOGGER.error("Migration failed, device has failed to respond in time")
        return False

    return True
