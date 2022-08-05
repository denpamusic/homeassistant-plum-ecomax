"""Diagnostics support for Plum ecoMAX."""
from __future__ import annotations

from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__ as pyplumio_version
from pyplumio.devices import Device

from .const import DOMAIN

REDACTED: Final = "**REDACTED**"


def _redact_device_data(device_data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information in device data."""
    if "product" in device_data:
        device_data["product"].uid = REDACTED

    return device_data


def _redact_entry_data(entry_data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information in config entry data."""
    for field in ("uid", "host"):
        if field in entry_data:
            entry_data[field] = REDACTED

    return entry_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    device: Device = hass.data[DOMAIN][entry.entry_id].device
    return {
        "entry": {
            "title": entry.title,
            "data": _redact_entry_data(dict(entry.data)),
        },
        "pyplumio": {
            "version": pyplumio_version,
        },
        "data": _redact_device_data(device.data),
    }
