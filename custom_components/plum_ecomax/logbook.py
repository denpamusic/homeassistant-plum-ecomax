"""Describe Plum ecoMAX logbook events."""
from __future__ import annotations

from collections.abc import Callable
from typing import Final

from homeassistant.components.logbook.const import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.util import dt as dt_util

from custom_components.plum_ecomax.const import (
    ATTR_CODE,
    ATTR_FROM,
    ATTR_TO,
    DOMAIN,
    ECOMAX_ALERT_EVENT,
)

DATE_STR_FORMAT: Final = "%Y-%m-%d %H:%M:%S"


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe logbook events."""

    @callback
    def async_describe_alert_event(event: Event) -> dict[str, str]:
        """Describe ecomax logbook event."""
        alert_code = event.data[ATTR_CODE]
        start_dt = dt_util.as_local(event.data[ATTR_FROM])
        start_time = start_dt.strftime(DATE_STR_FORMAT)
        time_string = f"was generated {start_time}"
        if event.data[ATTR_TO] is not None:
            end_dt = dt_util.as_local(event.data[ATTR_TO])
            end_time = end_dt.strftime(DATE_STR_FORMAT)
            time_string += f" and resolved {end_time}"

        return {
            LOGBOOK_ENTRY_NAME: "ecoMAX alert",
            LOGBOOK_ENTRY_MESSAGE: f"The alert with code '{alert_code}' {time_string}",
        }

    async_describe_event(DOMAIN, ECOMAX_ALERT_EVENT, async_describe_alert_event)
