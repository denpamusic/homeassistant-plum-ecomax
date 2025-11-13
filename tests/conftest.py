"""Fixtures for the test suite."""

import asyncio
from collections.abc import AsyncGenerator, Generator
import json
from typing import Any, Final, cast
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from pyplumio.connection import Connection
from pyplumio.const import DeviceState, ProductType, UnitOfMeasurement
from pyplumio.devices import PhysicalDevice, VirtualDevice
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.parameters import ParameterValues
from pyplumio.parameters.ecomax import (
    EcomaxNumber,
    EcomaxNumberDescription,
    EcomaxSwitch,
    EcomaxSwitchDescription,
)
from pyplumio.parameters.mixer import (
    MixerNumber,
    MixerNumberDescription,
    MixerSwitch,
    MixerSwitchDescription,
)
from pyplumio.parameters.thermostat import ThermostatNumber, ThermostatNumberDescription
from pyplumio.structures.ecomax_parameters import ATTR_ECOMAX_CONTROL
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.sensor_data import ConnectedModules
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_MIXERS,
    ATTR_PRODUCT,
    ATTR_REGDATA,
    ATTR_THERMOSTATS,
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_PRODUCT_ID,
    CONF_PRODUCT_TYPE,
    CONF_SOFTWARE,
    CONF_SUB_DEVICES,
    CONF_UID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE,
    DEFAULT_PORT,
    DOMAIN,
)

TITLE: Final = "ecoMAX"
HOST: Final = "localhost"

FLOAT_TOLERANCE: Final = 1e-6


def keys_to_int(data: dict[str, Any]) -> dict[int, Any]:
    """Cast dict keys to int."""
    return {int(k): v for k, v in data.items()}


def load_regdata_fixture(filename: str):
    """Load regdata fixture."""
    return json.loads(load_fixture(filename), object_hook=keys_to_int)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(autouse=True)
def bypass_pyplumio_events():
    """Bypass pyplumio event system."""
    with patch(
        "pyplumio.helpers.event_manager.EventManager.create_event",
        side_effect=TimeoutError,
    ):
        yield


@pytest.fixture(name="tcp_user_input")
def fixture_tcp_user_input() -> dict[str, Any]:
    """Get the TCP config data."""
    return {
        CONF_HOST: HOST,
        CONF_PORT: DEFAULT_PORT,
    }


@pytest.fixture(name="serial_user_input")
def fixture_serial_user_input() -> dict[str, Any]:
    """Get the serial config data."""
    return {
        CONF_DEVICE: DEFAULT_DEVICE,
        CONF_BAUDRATE: DEFAULT_BAUDRATE,
    }


@pytest.fixture(name="config_data")
def fixture_config_data() -> dict[str, Any]:
    """Get the data for config flow."""
    return {
        CONF_UID: "TEST",
        CONF_MODEL: "ecoMAX 850P2-C",
        CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
        CONF_PRODUCT_ID: 4,
        CONF_SOFTWARE: {
            "module_a": "6.10.32.K1",
            "module_b": None,
            "module_c": None,
            "ecolambda": "0.8.0",
            "ecoster": None,
            "panel": "6.30.36",
        },
        CONF_SUB_DEVICES: [ATTR_MIXERS],
    }


@pytest.fixture(name="tcp_config_data")
def fixture_tcp_config_data(tcp_user_input, config_data) -> dict[str, Any]:
    """Inject the TCP connection type."""
    tcp_config_data = dict(config_data)
    tcp_config_data |= tcp_user_input
    tcp_config_data.update({CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP})
    return tcp_config_data


@pytest.fixture(name="serial_config_data")
def fixture_serial_config_data(serial_user_input, config_data) -> dict[str, Any]:
    """Inject the serial connection type."""
    serial_config_data = dict(config_data)
    serial_config_data |= serial_user_input
    serial_config_data.update({CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL})
    return serial_config_data


@pytest.fixture
def setup_config_entry(hass: HomeAssistant, config_entry: MockConfigEntry):
    """Return integration setup."""

    async def _setup_config_entry_config_entry(options: dict[str, Any] | None = None):
        """Set up the config entry for integration."""
        if options:
            hass.config_entries.async_update_entry(config_entry, options=options)

        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return _setup_config_entry_config_entry


@pytest.fixture(name="config_entry")
def fixture_config_entry(
    hass: HomeAssistant, tcp_config_data: dict[str, str]
) -> MockConfigEntry:
    """Create mock config entry and add it to hass."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=tcp_config_data, title=TITLE, entry_id="test"
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture(name="connection")
def fixture_connection(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> EcomaxConnection:
    """Get ecoMAX connection."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=Connection))
    config_entry.runtime_data = Mock()
    config_entry.runtime_data.connection = connection
    return connection


class MutableEcoMAX(EcoMAX):
    """Allows to set otherwise properties readonly due to __slots__."""

    __slots__ = ("__dict__",)


@pytest.fixture(name="ecomax_base")
def fixture_ecomax_base() -> Generator[EcoMAX]:
    """Return base ecoMAX device with no data."""
    event = AsyncMock(spec=asyncio.Event)
    event.is_set = Mock(return_value=True)
    ecomax = MutableEcoMAX(write_queue=Mock(), network_info=NetworkInfo())
    with (
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.connected",
            event,
            create=True,
        ),
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.device", ecomax
        ),
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.get",
            return_value=ecomax,
            new_callable=AsyncMock,
            create=True,
        ),
    ):
        yield ecomax


@pytest.fixture(name="ecomax_common")
async def fixture_ecomax_common(ecomax_base: EcoMAX) -> EcoMAX:
    """Inject common ecomax data."""
    await ecomax_base.load(
        {
            "sensors": {},
            "heating_pump": False,
            "circulation_pump": False,
            "pending_alerts": False,
            "connected": False,
            "heating_temp": 0.0,
            "outside_temp": 0.0,
            "heating_target": 0,
            "state": DeviceState.OFF,
            "password": "0000",
            "summer_mode": EcomaxNumber(
                device=ecomax_base,
                values=ParameterValues(value=0, min_value=0, max_value=2),
                description=EcomaxNumberDescription("summer_mode"),
            ),
        }
    )
    return ecomax_base


@pytest.fixture
async def ecomax_control(ecomax_common: EcoMAX) -> EcoMAX:
    """Inject ecomax control parameter."""
    await ecomax_common.load(
        {
            ATTR_ECOMAX_CONTROL: EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxSwitchDescription(ATTR_ECOMAX_CONTROL),
            )
        }
    )
    return ecomax_common


@pytest.fixture(name="ecomax_p")
async def fixture_ecomax_p(ecomax_common: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject ecomax p data."""
    await ecomax_common.load(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_P,
                id=4,
                uid="TEST",
                logo=1024,
                image=2816,
                model="ecoMAX 850P2-C",
            ),
            "modules": ConnectedModules(
                module_a="6.10.32.K1",
                ecolambda="0.8.0",
                panel="6.30.36",
            ),
            "fan": False,
            "fan2_exhaust": False,
            "feeder": False,
            "lighter": False,
            "boiler_power": 0.0,
            "fuel_level": 0,
            "fuel_consumption": 0.0,
            "boiler_load": 0,
            "fan_power": 0.0,
            "feeder_temp": 0.0,
            "exhaust_temp": 0.0,
            "lower_buffer_temp": 0.0,
            "upper_buffer_temp": 0.0,
            "lambda_level": 0.0,
            "optical_temp": 0.0,
            "return_temp": 0.0,
            "fuel_burned": 0.0,
            "heating_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "heating_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "min_heating_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "min_heating_target_temp",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "max_heating_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "max_heating_target_temp",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "grate_heating_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "grate_heating_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "min_fuzzy_logic_power": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "min_fuzzy_logic_power",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "max_fuzzy_logic_power": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "max_fuzzy_logic_power",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "fuel_calorific_value": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription(
                    "fuel_calorific_value",
                    step=0.1,
                    unit_of_measurement=UnitOfMeasurement.KILO_WATT_HOUR_PER_KILOGRAM,
                ),
            ),
            "weather_control": EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxSwitchDescription("weather_control"),
            ),
            "heating_schedule_switch": EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxSwitchDescription("heating_schedule_switch"),
            ),
            "fuzzy_logic": EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxSwitchDescription("fuzzy_logic"),
            ),
            "schedules": [
                (
                    0,
                    [
                        [True, True, False, True],
                        [True, True, False, True],
                        [True, True, True, True],
                        [True, True, False, True],
                        [True, True, False, True],
                        [True, True, False, True],
                        [True, True, False, True],
                    ],
                )
            ],
        }
    )

    with (
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
            ProductType.ECOMAX_P,
        ),
        patch(
            "custom_components.plum_ecomax.EcomaxConnection.async_setup_mixers",
            return_value=False,
        ),
    ):
        yield ecomax_common


@pytest.fixture(name="ecomax_i")
async def fixture_ecomax_i(ecomax_common: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject ecomax i data."""
    await ecomax_common.load(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_I,
                id=1,
                uid="TEST",
                logo=1,
                image=2816,
                model="ecoMAX 850i",
            ),
            "modules": ConnectedModules(
                module_a="109.10.129.P1",
                ecolambda="0.8.0",
                panel="109.14.79",
            ),
            "solar_pump": False,
            "fireplace_pump": False,
            "lower_solar_temp": 0.0,
            "upper_solar_temp": 0.0,
            "fireplace_temp": 0.0,
            "lambda_level": 0.0,
        }
    )

    with (
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
            ProductType.ECOMAX_I,
        ),
        patch(
            "custom_components.plum_ecomax.EcomaxConnection.async_setup_mixers",
            return_value=False,
        ),
    ):
        yield ecomax_common


@pytest.fixture
async def ecomax_860p3_o(ecomax_p: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject data for ecoMAX 860P3-O.

    (product_type: 0, product_id: 51)
    """
    product_type = ProductType.ECOMAX_P
    product_model = "ecoMAX 860P3-O"

    await ecomax_p.load(
        {
            ATTR_PRODUCT: ProductInfo(
                type=product_type,
                id=51,
                uid="TEST",
                logo=13056,
                image=2816,
                model=product_model,
            ),
            ATTR_REGDATA: load_regdata_fixture("regdata__ecomax_860p3_o.json"),
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.model",
        product_model,
    ):
        yield ecomax_p


@pytest.fixture
async def water_heater(ecomax_common: EcoMAX):
    """Inject water heater data."""
    await ecomax_common.load(
        {
            "water_heater_pump": False,
            "water_heater_temp": 0.0,
            "water_heater_target": 0,
            "water_heater_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=50, min_value=10, max_value=80),
                description=EcomaxNumberDescription(
                    "water_heater_target_temp",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "water_heater_work_mode": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=2),
                description=EcomaxNumberDescription("water_heater_work_mode"),
            ),
            "water_heater_hysteresis": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=5, min_value=0, max_value=10),
                description=EcomaxNumberDescription(
                    "water_heater_hysteresis",
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "water_heater_disinfection": EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxSwitchDescription("water_heater_disinfection"),
            ),
            "water_heater_schedule_switch": EcomaxSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=EcomaxNumberDescription("water_heater_schedule_switch"),
            ),
        }
    )

    with patch("custom_components.plum_ecomax.EcomaxConnection.has_water_heater", True):
        yield ecomax_common


@pytest.fixture
async def mixers(ecomax_common: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject mixer data."""
    mixer_0 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_common)
    await mixer_0.load(
        {
            "pump": False,
            "current_temp": 0.0,
            "target_temp": 0,
            "work_mode": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=3),
                description=MixerNumberDescription("work_mode"),
            ),
            "mixer_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "mixer_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "circuit_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "circuit_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "min_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "min_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "max_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "max_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "weather_control": MixerSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerSwitchDescription("weather_control"),
            ),
            "disable_pump_on_thermostat": MixerSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerSwitchDescription("disable_pump_on_thermostat"),
            ),
            "summer_work": MixerSwitch(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerSwitchDescription("summer_work"),
            ),
            "enable_circuit": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription("enable_circuit"),
            ),
        }
    )

    mixer_1 = Mixer(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_common)
    await mixer_1.load(
        {
            "enable_circuit": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=2),
                description=MixerNumberDescription("enable_circuit"),
            ),
            "day_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "day_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "night_target_temp": MixerNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "night_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "min_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "min_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
            "max_target_temp": EcomaxNumber(
                device=ecomax_common,
                values=ParameterValues(value=0, min_value=0, max_value=1),
                description=MixerNumberDescription(
                    "max_target_temp", unit_of_measurement=UnitOfMeasurement.CELSIUS
                ),
            ),
        }
    )

    await ecomax_common.load(
        {
            "mixers_available": 2,
            "mixers_connected": 2,
            "mixers": {
                0: mixer_0,
                1: mixer_1,
            },
        }
    )

    with (
        patch(
            "custom_components.plum_ecomax.connection.EcomaxConnection.has_mixers", True
        ),
        patch(
            "custom_components.plum_ecomax.EcomaxConnection.async_setup_mixers",
            return_value=True,
        ),
    ):
        yield ecomax_common


@pytest.fixture
async def thermostats(ecomax_common: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject thermostats data."""
    thermostat = Thermostat(write_queue=Mock(spec=asyncio.Queue), parent=ecomax_common)
    await thermostat.load(
        {
            "state": 0,
            "current_temp": 0.0,
            "target_temp": 16.0,
            "contacts": False,
            "schedule": False,
            "mode": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=0, min_value=0, max_value=7),
                description=ThermostatNumberDescription("mode"),
            ),
            "hysteresis": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=5, min_value=0, max_value=50),
                description=ThermostatNumberDescription(
                    "hysteresis",
                    step=0.1,
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "party_target_temp": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=100, min_value=100, max_value=350),
                description=ThermostatNumberDescription(
                    "party_target_temp",
                    step=0.1,
                    size=2,
                    unit_of_measurement=UnitOfMeasurement.DAYS,
                ),
            ),
            "holidays_target_temp": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=70, min_value=0, max_value=600),
                description=ThermostatNumberDescription(
                    "holidays_target_temp",
                    step=0.1,
                    size=2,
                    unit_of_measurement=UnitOfMeasurement.DAYS,
                ),
            ),
            "antifreeze_target_temp": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=90, min_value=50, max_value=300),
                description=ThermostatNumberDescription(
                    "antifreeze_target_temp",
                    step=0.1,
                    size=2,
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "day_target_temp": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=160, min_value=100, max_value=350),
                description=ThermostatNumberDescription(
                    "day_target_temp",
                    step=0.1,
                    size=2,
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
            "night_target_temp": ThermostatNumber(
                offset=0,
                device=thermostat,
                values=ParameterValues(value=100, min_value=100, max_value=200),
                description=ThermostatNumberDescription(
                    "night_target_temp",
                    step=0.1,
                    size=2,
                    unit_of_measurement=UnitOfMeasurement.CELSIUS,
                ),
            ),
        }
    )

    await ecomax_common.load(
        {
            "thermostats_available": 1,
            "thermostats_connected": 1,
            "thermostats": {0: thermostat},
        }
    )

    with (
        patch("custom_components.plum_ecomax.EcomaxConnection.has_thermostats", True),
        patch(
            "custom_components.plum_ecomax.EcomaxConnection.async_setup_thermostats",
            return_value=True,
        ),
    ):
        yield ecomax_common


@pytest.fixture
async def custom_fields(ecomax_common: EcoMAX) -> AsyncGenerator[EcoMAX]:
    """Inject custom fields."""

    custom_fields = {
        "custom_binary_sensor": False,
        "custom_binary_sensor2": False,
        "custom_sensor": 50.0,
        "custom_number": EcomaxNumber(
            device=ecomax_common,
            values=ParameterValues(value=0, min_value=30, max_value=50),
            description=EcomaxNumberDescription("custom_number"),
        ),
        "custom_switch": EcomaxSwitch(
            device=ecomax_common,
            values=ParameterValues(value=0, min_value=0, max_value=1),
            description=EcomaxSwitchDescription("custom_switch"),
        ),
    }

    await ecomax_common.load(custom_fields)

    mixers: dict[int, Mixer] = ecomax_common.data.get(ATTR_MIXERS, {})
    for mixer in mixers.values():
        await mixer.load(custom_fields)

    thermostats: dict[int, Thermostat] = ecomax_common.data.get(ATTR_THERMOSTATS, {})
    for thermostat in thermostats.values():
        await thermostat.load(custom_fields)

    regdata: dict[int, Any] = ecomax_common.data.get(ATTR_REGDATA, {})
    if regdata:
        regdata.update({9000: False, 9001: 50.0})

    yield ecomax_common


async def dispatch_value(
    physical_device: PhysicalDevice,
    name: str,
    value: Any,
    source_device: str = "ecomax",
) -> None:
    """Dispatch the value."""
    if source_device == "ecomax":
        await physical_device.dispatch(name, value)
    else:
        device_type, index = source_device.rsplit("_", 1)
        vitual_devices = cast(
            dict[int, VirtualDevice], physical_device.get_nowait(f"{device_type}s")
        )
        await vitual_devices[int(index)].dispatch(name, value)
