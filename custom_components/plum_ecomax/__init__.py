"""The Plum ecoMAX integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection import EcomaxConnection, get_connection_handler
from .const import DOMAIN

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number", "water_heater"]


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
