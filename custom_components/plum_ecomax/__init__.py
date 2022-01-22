"""The Plum ecoMAX integration."""
from __future__ import annotations

from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection import EcomaxConnection
from .const import DOMAIN

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch", "number", "water_heater"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plum ecoMAX from a config entry."""

    connection = EcomaxConnection(
        hass,
        host=entry.data["host"],
        port=entry.data["port"],
        interval=entry.data["interval"],
    )
    connection.econet.set_eth(ip=await async_get_source_ip(hass))
    await connection.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = connection
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        connection = hass.data[DOMAIN][entry.entry_id]
        await connection.async_unload()
    except KeyError:
        pass

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
