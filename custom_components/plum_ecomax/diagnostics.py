"""Diagnostics support for Plum ecoMAX."""
from __future__ import annotations

from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__ as pyplumio_version
from pyplumio.devices import Device

from .const import ATTR_MIXERS, CONF_HOST, CONF_UID, DOMAIN
from .sensor import ATTR_PASSWORD, ATTR_PRODUCT

REDACTED: Final = "**REDACTED**"


def _redact_device_data(device_data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information in device data."""
    device_data = device_data.copy()
    if ATTR_PRODUCT in device_data:
        device_data[ATTR_PRODUCT].uid = REDACTED

    if ATTR_PASSWORD in device_data:
        device_data[ATTR_PASSWORD] = REDACTED

    if ATTR_MIXERS in device_data:
        device_data[ATTR_MIXERS] = list(map(lambda x: x.data, device_data[ATTR_MIXERS]))

    return device_data


def _redact_entry_data(entry_data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information in config entry data."""
    entry_data = entry_data.copy()
    for field in (CONF_UID, CONF_HOST):
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
