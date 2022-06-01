"""Diagnostics support for Plum ecoMAX."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio.devices import EcoMAX

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    ecomax: EcoMAX = hass.data[DOMAIN][entry.entry_id].ecomax
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "data": {
            "sensors": ecomax.data,
            "parameters": ecomax.parameters,
            "schema": ecomax.schema,
            "mixers": ecomax.mixers,
        },
    }
