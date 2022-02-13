"""The Plum ecoMAX integration."""
from __future__ import annotations

from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection import EcomaxConnection, EcomaxSerialConnection, EcomaxTcpConnection
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DOMAIN,
)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number", "water_heater"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plum ecoMAX from a config entry.

    Keyword arguments:
        hass -- instance of Home Assistant core
        entry -- instance of config entry
    """
    connection: Optional[EcomaxConnection] = None

    if entry.data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP:
        connection = EcomaxTcpConnection(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            update_interval=entry.data[CONF_UPDATE_INTERVAL],
            hass=hass,
        )
    elif entry.data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_SERIAL:
        connection = EcomaxSerialConnection(
            device=entry.data[CONF_DEVICE],
            update_interval=entry.data[CONF_UPDATE_INTERVAL],
            hass=hass,
        )
    else:
        return False

    await connection.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = connection
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Keyword arguments:
        hass -- instance of Home Assistant core
        entry -- instance of config entry
    """
    try:
        connection = hass.data[DOMAIN][entry.entry_id]
        await connection.async_unload()
    except KeyError:
        pass

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
