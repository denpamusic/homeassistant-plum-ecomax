"""Diagnostics support for Plum ecoMAX."""

from __future__ import annotations

from copy import copy
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pyplumio import __version__ as pyplumio_version
from pyplumio.devices import Device
from pyplumio.structures.product_info import ProductInfo

from .const import ATTR_PASSWORD, ATTR_PRODUCT, CONF_HOST, CONF_UID, DOMAIN

REDACTED: Final = "**REDACTED**"


def _value_as_dict(value: Any) -> Any:
    """Return value as a dictionary."""
    if isinstance(value, Device):
        return dict(value.data)

    if isinstance(value, ProductInfo):
        return copy(value)

    return value


def _data_as_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return data as a dictionary."""
    for key, value in data.items():
        data[key] = (
            _data_as_dict(dict(value))
            if isinstance(value, dict)
            else _value_as_dict(value)
        )

    return data


def _redact_device_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from device data."""
    sensitive: tuple[tuple[str, str | None], ...] = (
        (ATTR_PRODUCT, "uid"),
        (ATTR_PASSWORD, None),
    )

    for key, attribute in sensitive:
        if key not in data:
            continue

        if attribute is None:
            data[key] = REDACTED
            continue

        setattr(data[key], attribute, REDACTED)

    return data


def _redact_entry_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from config entry data."""
    for field in (CONF_UID, CONF_HOST):
        if field in data:
            data[field] = REDACTED

    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = entry.runtime_data
    device: Device = data.connection.device
    return {
        "entry": {
            "title": entry.title,
            "data": _redact_entry_data(dict(entry.data)),
        },
        "pyplumio": {
            "version": pyplumio_version,
        },
        "data": _redact_device_data(_data_as_dict(dict(device.data))),
    }
