"""Diagnostics support for Plum ecoMAX."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from pyplumio import __version__ as pyplumio_version
from pyplumio.helpers.event_manager import EventManager

from .connection import EcomaxConnection
from .const import ATTR_PASSWORD, CONF_HOST, CONF_UID


@callback
def _async_value_as_dict(value: Any) -> Any:
    """Return value as a dictionary."""
    if isinstance(value, EventManager):
        return {**value.data}

    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}

    return value


@callback
def _async_data_as_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return data as a dictionary."""
    items = {**data}

    for key, value in items.items():
        items[key] = (
            _async_data_as_dict(value)
            if isinstance(value, dict)
            else _async_value_as_dict(value)
        )

    return items


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    connection: EcomaxConnection = entry.runtime_data.connection
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(entry.data, to_redact={CONF_UID, CONF_HOST}),
            "options": dict(entry.options),
        },
        "pyplumio": {
            "version": pyplumio_version,
        },
        "data": async_redact_data(
            _async_data_as_dict(connection.device.data),
            to_redact={CONF_UID, ATTR_PASSWORD},
        ),
    }
