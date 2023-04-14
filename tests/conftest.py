"""Fixtures for the test suite."""

import asyncio
from typing import Final
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pyplumio import Connection
from pyplumio.const import DeviceState, ProductType
from pyplumio.devices import Mixer, Thermostat
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.structures.ecomax_parameters import (
    EcomaxBinaryParameter,
    EcomaxParameter,
    EcomaxParameterDescription,
)
from pyplumio.structures.mixer_parameters import (
    MixerBinaryParameter,
    MixerParameter,
    MixerParameterDescription,
)
from pyplumio.structures.modules import ConnectedModules
from pyplumio.structures.network_info import NetworkInfo
from pyplumio.structures.product_info import ProductInfo
from pyplumio.structures.regulator_data import RegulatorData
from pyplumio.structures.thermostat_parameters import (
    ThermostatParameter,
    ThermostatParameterDescription,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import (
    ATTR_ECOMAX_CONTROL,
    ATTR_MIXERS,
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
    ProductId,
)
from tests.common import load_regdata_fixture

TITLE: Final = "ecoMAX"
HOST: Final = "localhost"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(autouse=True)
def bypass_pyplumio_events():
    """Bypass pyplumio event system."""
    with patch(
        "pyplumio.helpers.event_manager.EventManager.create_event",
        side_effect=asyncio.TimeoutError,
    ):
        yield


@pytest.fixture(name="tcp_user_input")
def fixture_tcp_user_input():
    """Get the TCP config data."""
    yield {
        CONF_HOST: HOST,
        CONF_PORT: DEFAULT_PORT,
    }


@pytest.fixture(name="serial_user_input")
def fixture_serial_user_input():
    """Get the serial config data."""
    yield {
        CONF_DEVICE: DEFAULT_DEVICE,
        CONF_BAUDRATE: DEFAULT_BAUDRATE,
    }


@pytest.fixture(name="config_data")
def fixture_config_data():
    """Get the data for config flow."""
    return {
        CONF_UID: "TEST",
        CONF_MODEL: "ecoMAX 850P2-C",
        CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
        CONF_PRODUCT_ID: 4,
        CONF_SOFTWARE: "6.10.32.K1",
        CONF_SUB_DEVICES: [ATTR_MIXERS],
    }


@pytest.fixture(name="tcp_config_data")
def fixture_tcp_config_data(tcp_user_input, config_data):
    """Inject the TCP connection type."""
    config_data |= tcp_user_input
    config_data.update(
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
        }
    )

    yield config_data


@pytest.fixture(name="serial_config_data")
def fixture_serial_config_data(serial_user_input, config_data):
    """Inject the serial connection type."""
    config_data |= serial_user_input
    config_data.update(
        {
            CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
        }
    )

    yield config_data


@pytest.fixture
async def setup_integration():
    """Setup the integration."""

    async def setup_entry(hass: HomeAssistant, config_entry: MockConfigEntry):
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return setup_entry


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
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = connection
    return connection


@pytest.fixture
def connected():
    """Integration is connected."""
    event = AsyncMock(spec=asyncio.Event)
    event.is_set = Mock(return_value=True)
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.connected",
        event,
        create=True,
    ):
        yield


@pytest.fixture(name="ecomax_base")
def fixture_ecomax_base() -> EcoMAX:
    """Basic ecoMAX device with no data."""
    ecomax = EcoMAX(queue=Mock(), network=NetworkInfo())
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device", ecomax
    ), patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.get",
        return_value=ecomax,
        new_callable=AsyncMock,
        create=True,
    ):
        yield ecomax


@pytest.fixture(name="ecomax_common")
def fixture_ecomax_common(ecomax_base: EcoMAX):
    """Inject common ecomax data."""
    ecomax_base.data.update(
        {
            "sensors": True,
            "ecomax_parameters": True,
            "heating_pump": False,
            "circulation_pump": False,
            "pending_alerts": False,
            "connected": False,
            "heating_temp": 0.0,
            "outside_temp": 0.0,
            "heating_target": 0,
            "state": DeviceState.OFF,
            "password": "0000",
            "summer_mode": EcomaxParameter(
                device=ecomax_base,
                value=0,
                min_value=0,
                max_value=2,
                description=EcomaxParameterDescription("summer_mode"),
            ),
        }
    )
    yield ecomax_base


@pytest.fixture
def ecomax_control(ecomax_common: EcoMAX):
    """Inject ecomax control parameter"""
    ecomax_common.data.update(
        {
            ATTR_ECOMAX_CONTROL: EcomaxBinaryParameter(
                device=ecomax_common,
                value=STATE_OFF,
                min_value=STATE_OFF,
                max_value=STATE_ON,
                description=EcomaxParameterDescription(
                    ATTR_ECOMAX_CONTROL, cls=EcomaxBinaryParameter
                ),
            )
        }
    )
    yield ecomax_common


@pytest.fixture(name="ecomax_p")
def fixture_ecomax_p(ecomax_common: EcoMAX):
    """Inject ecomax p data."""
    ecomax_common.data.update(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_P,
                id=4,
                uid="TEST",
                logo=1024,
                image=2816,
                model="ecoMAX850P2-C",
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
            "power": 0.0,
            "fuel_level": 0,
            "fuel_consumption": 0.0,
            "load": 0,
            "fan_power": 0.0,
            "feeder_temp": 0.0,
            "exhaust_temp": 0.0,
            "lower_buffer_temp": 0.0,
            "upper_buffer_temp": 0.0,
            "lambda_level": 0.0,
            "optical_temp": 0.0,
            "return_temp": 0.0,
            "fuel_burned": 0.0,
            "heating_target_temp": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("heating_target_temp"),
            ),
            "min_heating_target_temp": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("min_heating_target_temp"),
            ),
            "max_heating_target_temp": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("max_heating_target_temp"),
            ),
            "heating_temp_grate": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("heating_temp_grate"),
            ),
            "min_fuzzy_logic_power": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("min_fuzzy_logic_power"),
            ),
            "max_fuzzy_logic_power": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("max_fuzzy_logic_power"),
            ),
            "fuel_calorific_value_kwh_kg": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription(
                    "fuel_calorific_value_kwh_kg", multiplier=10
                ),
            ),
            "heating_weather_control": EcomaxBinaryParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("heating_weather_control"),
            ),
            "heating_schedule_switch": EcomaxBinaryParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("heating_schedule_switch"),
            ),
            "fuzzy_logic": EcomaxBinaryParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("fuzzy_logic"),
            ),
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        ProductType.ECOMAX_P,
    ), patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.async_setup_mixers",
        return_value=False,
    ):
        yield ecomax_common


@pytest.fixture(name="ecomax_i")
def fixture_ecomax_i(ecomax_common: EcoMAX):
    """Inject ecomax i data."""
    ecomax_common.data.update(
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

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        ProductType.ECOMAX_I,
    ), patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.async_setup_mixers",
        return_value=False,
    ):
        yield ecomax_common


@pytest.fixture()
def ecomax_860p3_o(ecomax_p: EcoMAX):
    """Inject data for ecoMAX 860P3-O.
    (product_type: 0, product_id: 51)
    """
    model = "ecoMAX860P3-O"
    product_id = ProductId.ECOMAX_860P3_O
    product_type = ProductType.ECOMAX_P

    regulator_data = RegulatorData()
    regulator_data.data = load_regdata_fixture("regdata__ecomax_860p3_o.json")

    ecomax_p.data.update(
        {
            "product": ProductInfo(
                type=product_type,
                id=product_id,
                uid="TEST",
                logo=13056,
                image=2816,
                model=model,
            ),
            "regdata": regulator_data,
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_id",
        product_id,
    ):
        yield ecomax_p


@pytest.fixture
def water_heater(ecomax_common: EcoMAX):
    """Inject water heater data."""
    ecomax_common.data.update(
        {
            "water_heater_pump": False,
            "water_heater_temp": 0.0,
            "water_heater_target": 0,
            "water_heater_target_temp": EcomaxParameter(
                device=ecomax_common,
                value=50,
                min_value=10,
                max_value=80,
                description=EcomaxParameterDescription("water_heater_target_temp"),
            ),
            "water_heater_work_mode": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=2,
                description=EcomaxParameterDescription("water_heater_work_mode"),
            ),
            "water_heater_hysteresis": EcomaxParameter(
                device=ecomax_common,
                value=5,
                min_value=0,
                max_value=10,
                description=EcomaxParameterDescription("water_heater_hysteresis"),
            ),
            "water_heater_disinfection": EcomaxBinaryParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription(
                    "water_heater_disinfection", cls=EcomaxBinaryParameter
                ),
            ),
            "water_heater_schedule_switch": EcomaxBinaryParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("water_heater_schedule_switch"),
            ),
        }
    )

    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.has_water_heater", True
    ):
        yield ecomax_common


@pytest.fixture
def mixers(ecomax_common: EcoMAX):
    """Inject mixer data."""
    mixer = Mixer(queue=Mock(spec=asyncio.Queue), parent=ecomax_common)
    mixer.data = {
        "pump": False,
        "current_temp": 0.0,
        "target_temp": 0,
        "work_mode": MixerParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=3,
            description=MixerParameterDescription("work_mode"),
        ),
        "mixer_target_temp": MixerParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("mixer_target_temp"),
        ),
        "day_target_temp": MixerParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("day_target_temp"),
        ),
        "night_target_temp": MixerParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("night_target_temp"),
        ),
        "min_target_temp": EcomaxParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription("min_target_temp"),
        ),
        "max_target_temp": EcomaxParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=EcomaxParameterDescription("max_target_temp"),
        ),
        "weather_control": MixerBinaryParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("weather_control"),
        ),
        "off_therm_pump": MixerBinaryParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("off_therm_pump"),
        ),
        "summer_work": MixerBinaryParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("summer_work"),
        ),
        "support": MixerBinaryParameter(
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("support"),
        ),
    }

    ecomax_common.data.update(
        {
            "mixer_sensors": True,
            "mixer_parameters": True,
            "mixer_count": 1,
            "mixers": {0: mixer},
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.has_mixers", True
    ), patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.async_setup_mixers",
        return_value=True,
    ):
        yield ecomax_common


@pytest.fixture
def thermostats(ecomax_common: EcoMAX):
    """Inject thermostats data."""
    thermostat = Thermostat(queue=Mock(spec=asyncio.Queue), parent=ecomax_common)
    thermostat.data = {
        "state": 0,
        "current_temp": 0.0,
        "target_temp": 16.0,
        "contacts": False,
        "schedule": False,
        "mode": ThermostatParameter(
            offset=0,
            device=ecomax_common,
            value=0,
            min_value=0,
            max_value=7,
            description=ThermostatParameterDescription("mode"),
        ),
        "hysteresis": ThermostatParameter(
            offset=0,
            device=ecomax_common,
            value=5,
            min_value=0,
            max_value=50,
            description=ThermostatParameterDescription("hysteresis", multiplier=10),
        ),
        "day_target_temp": ThermostatParameter(
            offset=0,
            device=ecomax_common,
            value=160,
            min_value=100,
            max_value=350,
            description=ThermostatParameterDescription(
                "day_target_temp", multiplier=10, size=2
            ),
        ),
        "night_target_temp": ThermostatParameter(
            offset=0,
            device=ecomax_common,
            value=160,
            min_value=100,
            max_value=350,
            description=ThermostatParameterDescription(
                "night_target_temp", multiplier=10, size=2
            ),
        ),
    }

    ecomax_common.data.update(
        {
            "thermostat_sensors": True,
            "thermostat_parameters": True,
            "thermostat_count": 1,
            "thermostats": {0: thermostat},
        }
    )

    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.has_thermostats", True
    ), patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.async_setup_thermostats",
        return_value=True,
    ):
        yield ecomax_common
