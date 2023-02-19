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
    ATTR_REGDATA,
    CONF_CAPABILITIES,
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
    CONNECTION_TYPE_TCP,
    DOMAIN,
)

UNKNOWN_ECOMAX_TYPE: Final = 99
DEVICE: Final = "/dev/ttyUSB0"
HOST: Final = "localhost"
PORT: Final = 8899


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for hass."""
    yield


@pytest.fixture(name="config_data")
def fixture_config_data():
    """Get config data."""
    yield {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
        CONF_DEVICE: DEVICE,
        CONF_HOST: HOST,
        CONF_PORT: PORT,
    }


@pytest.fixture(name="device_data")
def fixture_device_data():
    """Get the device data for config flow."""
    return {
        CONF_UID: "TEST",
        CONF_MODEL: "ecoMAX 850P2-C",
        CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
        CONF_PRODUCT_ID: 4,
        CONF_SOFTWARE: "6.10.32.K1",
        CONF_SUB_DEVICES: [ATTR_MIXERS],
        CONF_CAPABILITIES: [ATTR_REGDATA],
    }


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
    hass: HomeAssistant,
    config_data: dict[str, str],
    device_data: dict[str, str],
) -> MockConfigEntry:
    """Create mock config entry and add it to hass."""
    config_data |= device_data
    config_entry = MockConfigEntry(domain=DOMAIN, data=config_data, entry_id="test")
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture(name="connection_name")
def fixture_connection_name():
    """Patch ecoMAX connection name."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name",
        "test",
        create=True,
    ):
        yield


@pytest.fixture(name="connection")
def fixture_connection(
    hass: HomeAssistant, config_entry: MockConfigEntry, connection_name
) -> EcomaxConnection:
    """Get ecoMAX connection."""
    connection = EcomaxConnection(hass, config_entry, AsyncMock(spec=Connection))
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = connection
    return connection


@pytest.fixture(autouse=True)
def bypass_pyplumio_events():
    """Bypass pyplumio event system."""
    with patch(
        "pyplumio.helpers.event_manager.EventManager.create_event",
        side_effect=asyncio.TimeoutError,
    ):
        yield


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
    regulator_data = RegulatorData()
    regulator_data.data = {
        1: False,
        2: False,
        3: False,
        4: False,
        5: False,
        6: False,
        7: False,
        8: 1712,
        9: 1977,
        10: 2534,
        11: 1279,
        12: 2561,
        13: 2109,
        14: 2348,
        15: 4095,
        16: 214,
        17: 182,
        18: 0,
        19: 0,
        20: 0,
        21: 0,
        22: 0,
        23: 0,
        24: 0,
        25: 0,
        26: 0,
        27: 0,
        28: 0,
        29: 0,
        30: 36.46145248413086,
        31: 49.66331481933594,
        41: 0,
        42: 0,
        43: 0,
        44: 0,
        45: 0,
        46: 0,
        47: 0,
        48: 0,
        49: 0,
        50: 0,
        51: 0,
        52: 0,
        53: 0,
        54: 0,
        55: 0,
        56: 0,
        57: 0,
        58: 0,
        59: 0,
        60: 0,
        61: 0,
        62: 0,
        63: 8,
        64: 8,
        65: 0,
        66: 0,
        67: 0,
        68: 8,
        69: 8,
        70: 0,
        71: 0,
        72: 0,
        73: 0,
        74: False,
        75: False,
        76: False,
        77: False,
        78: False,
        79: False,
        80: False,
        81: True,
        82: True,
        83: True,
        84: True,
        85: True,
        86: True,
        87: True,
        88: True,
        89: True,
        90: True,
        91: True,
        92: True,
        93: True,
        94: True,
        95: True,
        96: False,
        97: False,
        98: False,
        99: False,
        100: False,
        101: False,
        102: False,
        103: False,
        104: False,
        105: False,
        106: False,
        107: False,
        108: False,
        109: 0,
        110: 8,
        111: False,
        112: False,
        113: False,
        114: False,
        115: False,
        116: False,
        117: False,
        118: False,
        119: False,
        120: False,
        121: False,
        122: False,
        123: False,
        124: False,
        125: False,
        126: False,
        127: False,
        128: False,
        129: False,
        130: False,
        131: False,
        132: False,
        133: False,
        134: False,
        135: False,
        136: True,
        137: False,
        138: False,
        139: False,
        140: True,
        142: False,
        143: True,
        144: False,
        145: 1.752262830734253,
        146: 0,
        147: True,
        148: True,
        149: False,
        150: False,
        151: False,
        152: False,
        153: 14,
        154: 80,
        155: 1,
        156: 23,
        157: 0,
        158: 0,
        159: 0,
        160: 0,
        161: 0,
        162: 0,
        163: 0,
        164: 0,
        165: 0,
        166: False,
        167: False,
        168: False,
        169: False,
        170: False,
        171: 0,
        172: 0,
        173: 0.0,
        174: 0.0,
        176: 0.0,
        178: 0,
        179: 0,
        181: 8.069148063659668,
        182: 600,
        183: 4462,
        184: 2053,
        185: 352,
        186: 2181,
        187: 22905.93359375,
        188: 10874,
        189: 176,
        190: 4083,
        191: "192.168.0.54",
        192: "255.255.255.0",
        193: "0.0.0.0",
        194: 1,
        195: "0.0.0.0",
        196: "255.255.255.0",
        197: "0.0.0.0",
        198: 1,
        199: 1,
        200: 100,
        201: 0,
        202: 0,
        203: "",
        204: 3.109999895095825,
        205: 17.889999389648438,
        206: False,
        207: False,
        208: True,
        209: False,
        210: False,
        211: False,
        212: True,
        213: 22.250240325927734,
        214: 0.0,
        215: 0.0,
        216: 22.5,
        217: 0.0,
        218: 0.0,
        219: 2,
        220: 255,
        221: 255,
        222: False,
        223: False,
        224: False,
        226: 5.1027116775512695,
        227: 49,
        228: 691200000,
        1024: 58.2193603515625,
        1025: 45.94587707519531,
        1026: 24.595382690429688,
        1027: 1.8267631530761719,
        1031: 37.54756164550781,
        1280: 63,
        1281: 45,
        1282: 0,
        1283: 0,
        1284: 0,
        1285: 0,
        1287: 39,
        1288: 36,
        1289: 36,
        1290: 36,
        1291: 36,
        1536: True,
        1538: False,
        1539: False,
        1540: False,
        1541: True,
        1542: False,
        1543: False,
        1544: True,
        1545: False,
        1546: False,
        1547: False,
        1548: False,
        1549: False,
        1550: False,
        1551: False,
        1552: False,
        1553: False,
        1554: False,
        1555: False,
        1556: False,
        1557: False,
        1558: False,
        1792: 3,
        1793: 8.989108085632324,
        1794: 50,
        1795: 73,
        1798: True,
        2048: 2,
        2049: 0,
    }

    ecomax_p.data.update(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_P,
                id=51,
                uid="TEST",
                logo=13056,
                image=2816,
                model="ecoMAX860P3-O",
            ),
            "regdata": regulator_data,
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_id", 51
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
