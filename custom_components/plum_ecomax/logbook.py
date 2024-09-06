"""Describe Plum ecoMAX logbook events."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from homeassistant.components.logbook.const import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.const import ATTR_CODE, ATTR_NAME
from homeassistant.core import Event, HomeAssistant, callback
from pyplumio.const import AlertType

from .const import ATTR_FROM, ATTR_TO, DOMAIN, EVENT_PLUM_ECOMAX_ALERT

DEFAULT_MESSAGE: Final = "encountered alert with code"

ALERT_MESSAGES: dict[AlertType, str] = {
    AlertType.POWER_LOSS: "encountered power loss",
    AlertType.BOILER_TEMP_SENSOR_FAILURE: "encountered boiler temperature sensor failure",
    AlertType.MAX_BOILER_TEMP_EXCEEDED: "maximum boiler temperature exceeded",
    AlertType.FEEDER_TEMP_SENSOR_FAILURE: "encountered feeder temperature sensor failure",
    AlertType.MAX_FEEDER_TEMP_EXCEEDED: "maximum feeder temperature exceeded",
    AlertType.EXHAUST_TEMP_SENSOR_FAILURE: "exhaust temperature sensor failed",
    AlertType.KINDLING_FAILURE: "encountered kindling failure",
    AlertType.NO_FUEL: "fuel not detected",
    AlertType.LEAK_DETECTED: "detected leak",
    AlertType.PRESSURE_SENSOR_FAILURE: "encountered pressure sensor failure",
    AlertType.FAN_FAILURE: "encountered fan failure",
    AlertType.INSUFFICIENT_AIR_PRESSURE: "detected insufficient air pressure",
    AlertType.BURN_OFF_FAILURE: "encountered failure while burning off",
    AlertType.FLAME_SENSOR_FAILURE: "encountered flame sensor failure",
    AlertType.LINEAR_ACTUATOR_BLOCKED: "linear actuator jammed",
    AlertType.INCORRECT_PARAMETERS: "detected incorrect parameters",
    AlertType.CONDENSATION_WARNING: "detected possible condensation",
    AlertType.BOILER_STB_TRIPPED: "boiler STB tripped",
    AlertType.FEEDER_STB_TRIPPED: "feeder STB tripped",
    AlertType.MIN_WATER_PRESSURE_EXCEEDED: "minimum water pressure exceeded",
    AlertType.MAX_WATER_PRESSURE_EXCEEDED: "maximum water pressure exceeded",
    AlertType.FEEDER_JAMMED: "feeder jammed",
    AlertType.FLAMEOUT: "detected flameout",
    AlertType.EXHAUST_FAN_FAILURE: "encountered exhaust fan failure",
    AlertType.EXTERNAL_FEEDER_FAILURE: "encountered external feeder failure",
    AlertType.SOLAR_COLLECTOR_TEMP_SENSOR_FAILURE: (
        "encountered solar collector temperature sensor failure"
    ),
    AlertType.SOLAR_CIRCUIT_TEMP_SENSOR_FAILURE: (
        "encountered solar circuit temperature sensor failure"
    ),
    AlertType.H1_CIRCUIT_TEMP_SENSOR_FAILURE: (
        "encountered temperature sensor failure in H1 circuit"
    ),
    AlertType.H2_CIRCUIT_TEMP_SENSOR_FAILURE: (
        "encountered temperature sensor failure in H2 circuit"
    ),
    AlertType.H3_CIRCUIT_TEMP_SENSOR_FAILURE: (
        "encountered temperature sensor failure in H3 circuit"
    ),
    AlertType.OUTDOOR_TEMP_SENSOR_FAILURE: (
        "encountered outdoor temperature sensor failure"
    ),
    AlertType.WATER_HEATER_TEMP_SENSOR_FAILURE: (
        "encountered water heater temperature sensor failure"
    ),
    AlertType.H0_CIRCUIT_TEMP_SENSOR_FAILURE: (
        "encountered temperature sensor failure in H0 circuit"
    ),
    AlertType.FROST_PROTECTION_RUNNING_WO_HS: (
        "frost protection is running without heat source"
    ),
    AlertType.FROST_PROTECTION_RUNNING_W_HS: (
        "frost protection is running with heat source"
    ),
    AlertType.MAX_SOLAR_COLLECTOR_TEMP_EXCEEDED: (
        "max solar collector temperature exceeded"
    ),
    AlertType.MAX_HEATED_FLOOR_TEMP_EXCEEDED: (
        "maximum heated floor temperature exceeded"
    ),
    AlertType.BOILER_COOLING_RUNNING: "boiler cooling is running",
    AlertType.ECOLAMBDA_CONNECTION_FAILURE: "encountered ecoLAMBDA connection failure",
    AlertType.PRIMARY_AIR_THROTTLE_JAMMED: "primary air throttle jammed",
    AlertType.SECONDARY_AIR_THROTTLE_JAMMED: "secondary air throttle jammed",
    AlertType.FEEDER_OVERFLOW: "detected feeder overflow",
    AlertType.FURNANCE_OVERFLOW: "detected furnance overflow",
    AlertType.MODULE_B_CONNECTION_FAILURE: "encountered module B connection failure",
    AlertType.CLEANING_ACTUATOR_FAILURE: "encountered cleaning actuator failure",
    AlertType.MIN_PRESSURE_EXCEEDED: "minimum pressure exceeded",
    AlertType.MAX_PRESSURE_EXCEEDED: "maximum pressure exceeded",
    AlertType.PRESSURE_SENSOR_DAMAGED: "pressure sensor damage detected",
    AlertType.MAX_MAIN_HS_TEMP_EXCEEDED: (
        "maximum main heat source temperature exceeded"
    ),
    AlertType.MAX_ADDITIONAL_HS_TEMP_EXCEEDED: (
        "maximum additional heat source temperature exceeded"
    ),
    AlertType.SOLAR_PANEL_OFFLINE: "solar panel overheated",
    AlertType.FEEDER_CONTROL_FAILURE: "encountered feeder control system failure",
    AlertType.FEEDER_BLOCKED: "feeder blocked",
    AlertType.MAX_THERMOCOPLE_TEMP_EXCEEDED: (
        "maximum thermocouple temperature exceeded"
    ),
    AlertType.THERMOCOUPLE_WIRING_FAILURE: "detected incorrect thermocouple wiring",
    AlertType.UNKNOWN_ERROR: "encountered unknown error",
}


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe logbook events."""

    @callback
    def _async_describe_alert_event(event: Event) -> dict[str, str]:
        """Describe an ecoMAX alert logbook event."""
        alert_code = event.data[ATTR_CODE]
        start_time = event.data[ATTR_FROM]
        time_string = f"from {start_time}"

        try:
            end_time = event.data[ATTR_TO]
            time_string += f" to {end_time}"
        except KeyError:
            pass

        alert_string = ALERT_MESSAGES.get(
            alert_code, f'{DEFAULT_MESSAGE} "{alert_code}"'
        )

        return {
            LOGBOOK_ENTRY_NAME: event.data[ATTR_NAME],
            LOGBOOK_ENTRY_MESSAGE: f"{alert_string} {time_string}",
        }

    async_describe_event(DOMAIN, EVENT_PLUM_ECOMAX_ALERT, _async_describe_alert_event)
