"""Diagnostics support for Plum ecoMAX."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__ as pyplumio_version
from pyplumio.devices import Device

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    device: Device = hass.data[DOMAIN][entry.entry_id].device
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "pyplumio": {
            "version": pyplumio_version,
        },
        "data": device.data,
    }
