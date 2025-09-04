"""Provide info to system health."""

from typing import Any, cast

from homeassistant.components import system_health
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from pyplumio import __version__ as pyplumio_version
from pyplumio.protocol import Statistics

from . import DOMAIN, PlumEcomaxConfigEntry
from .const import ATTR_ENTITIES


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the info page."""
    config_entry: PlumEcomaxConfigEntry = hass.config_entries.async_entries(DOMAIN)[0]

    statistics = cast(Statistics, config_entry.runtime_data.connection.statistics)
    total_frames = (
        statistics.sent_frames + statistics.received_frames + statistics.failed_frames
    )
    failure_rate = (statistics.failed_frames / total_frames) * 100.0
    if failure_rate == 0:
        failure_rate_string = "0 %"
    elif failure_rate < 0.01:
        failure_rate_string = "<0.01 %"
    else:
        failure_rate_string = f"{round(failure_rate, 2)} %"

    custom_entities: dict[Platform, dict] = config_entry.options.get(ATTR_ENTITIES, {})

    return {
        "pyplumio_version": pyplumio_version,
        "received_frames": statistics.received_frames,
        "sent_frames": statistics.sent_frames,
        "failed_frames": statistics.failed_frames,
        "failure_rate": failure_rate_string,
        "connected_since": statistics.connected_since,
        "connection_losses": statistics.connection_losses,
        "custom_entities": sum(len(entities) for entities in custom_entities.values()),
    }


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)
