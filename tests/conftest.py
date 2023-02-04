"""Fixtures for the test suite."""

import asyncio
from typing import Final
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pyplumio import Connection
from pyplumio.const import DeviceState
from pyplumio.devices import Mixer, Thermostat
from pyplumio.devices.ecomax import EcoMAX
from pyplumio.helpers.network_info import NetworkInfo
from pyplumio.helpers.product_info import ConnectedModules, ProductInfo, ProductType
from pyplumio.structures.ecomax_parameters import (
    EcomaxBinaryParameter,
    EcomaxParameter,
    EcomaxParameterDescription,
)
from pyplumio.structures.mixer_parameters import (
    MixerParameter,
    MixerParameterDescription,
)
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
    CONF_CONNECTION_TYPE,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
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
        CONF_SOFTWARE: "6.10.32.K1",
        CONF_SUB_DEVICES: [ATTR_MIXERS],
    }


@pytest.fixture(autouse=True)
def bypass_async_ha_write_state():
    """Bypass writing state to hass."""
    with patch("homeassistant.helpers.entity.Entity.async_write_ha_state"):
        yield


@pytest.fixture
def async_add_entities():
    """Mock add entities callback."""
    with patch(
        "homeassistant.helpers.entity_platform.AddEntitiesCallback"
    ) as mock_async_add_entities:
        yield mock_async_add_entities


@pytest.fixture(name="config_entry")
def fixture_config_entry(
    hass: HomeAssistant, config_data: dict[str, str], device_data: dict[str, str]
) -> MockConfigEntry:
    """Create mock config entry and add it to hass."""
    config_data |= device_data
    config_entry = MockConfigEntry(domain=DOMAIN, data=config_data, entry_id="test")
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = EcomaxConnection(
        hass, config_entry, AsyncMock(spec=Connection)
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture(autouse=True)
def bypass_pyplumio_events():
    """Bypass pyplumio event system."""
    with patch(
        "pyplumio.helpers.task_manager.TaskManager.create_event",
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
        "custom_components.plum_ecomax.connection.EcomaxConnection.get_device",
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
            "ciculation_pump": False,
            "pending_alerts": False,
            "heating_temp": 0.0,
            "outside_temp": 0.0,
            "heating_target": 0,
            "state": DeviceState.OFF,
            "password": "0000",
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
                value=STATE_ON,
                min_value=STATE_OFF,
                max_value=STATE_ON,
                description=EcomaxParameterDescription(
                    ATTR_ECOMAX_CONTROL, cls=EcomaxBinaryParameter
                ),
            )
        }
    )
    yield ecomax_common


@pytest.fixture
def ecomax_p(ecomax_common: EcoMAX):
    """Inject ecomax p data."""
    ecomax_common.data.update(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_P,
                product=4,
                uid="TEST",
                logo=1024,
                image=2816,
                model="ecoMAX850P2-C",
            ),
            "modules": ConnectedModules(
                module_a="6.10.32.K1",
                module_lambda="0.8.0",
                module_panel="6.30.36",
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
            "heating_target_temp": EcomaxParameter(
                device=ecomax_common,
                value=0,
                min_value=0,
                max_value=1,
                description=EcomaxParameterDescription("heating_target_temp"),
            ),
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        ProductType.ECOMAX_P,
    ):
        yield ecomax_common


@pytest.fixture
def ecomax_i(ecomax_common: EcoMAX):
    """Inject ecomax i data."""
    ecomax_common.data.update(
        {
            "product": ProductInfo(
                type=ProductType.ECOMAX_I,
                product=0,
                uid="TEST",
                logo=1,
                image=2816,
                model="ecoMAX 850i",
            ),
            "modules": ConnectedModules(
                module_a="109.10.129.P1",
                module_lambda="0.8.0",
                module_panel="109.14.79",
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
    ):
        yield ecomax_common


@pytest.fixture
def ecomax_unknown(ecomax_common: EcoMAX):
    """Inject unknown ecomax data."""
    ecomax_common.data.update(
        {
            "product": ProductInfo(
                type=UNKNOWN_ECOMAX_TYPE,
                product=0,
                uid="TEST",
                logo=1,
                image=2816,
                model="Unknown model",
            ),
            "modules": ConnectedModules(),
        }
    )

    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.product_type",
        UNKNOWN_ECOMAX_TYPE,
    ):
        yield ecomax_common


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
            value=1,
            min_value=0,
            max_value=1,
            description=MixerParameterDescription("mixer_target_temp"),
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
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers",
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
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_thermostats",
        return_value=True,
    ):
        yield ecomax_common
