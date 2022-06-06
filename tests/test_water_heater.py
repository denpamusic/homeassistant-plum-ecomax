"""Test Plum ecoMAX water heater."""

from homeassistant.components.water_heater import (
    STATE_OFF,
    STATE_PERFORMANCE,
    WaterHeaterEntityFeature,
)
from homeassistant.const import PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
import pytest_asyncio
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.water_heater import (
    WATER_HEATER_MODES,
    EcomaxWaterHeater,
    async_setup_entry,
)


@pytest_asyncio.fixture(name="test_water_heater")
async def fixture_test_water_heater(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> EcomaxWaterHeater:
    """Setup water heater entities and get a single water heater."""
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()
    water_heaters = add_entities_callback.call_args[0][0]
    water_heater = [
        x for x in water_heaters if x.entity_description.key == "water_heater"
    ]
    yield water_heater[0]


@pytest.mark.asyncio
async def test_async_setup_and_update_entry(
    test_water_heater: EcomaxWaterHeater, mock_connection: EcomaxTcpConnection
) -> None:
    """Test setup and update of water heater entity."""
    # Check that sensor state is unknown and update it.
    assert isinstance(test_water_heater, EcomaxWaterHeater)
    assert test_water_heater.temperature_unit == TEMP_CELSIUS
    assert test_water_heater.precision == PRECISION_WHOLE
    assert (
        test_water_heater.supported_features
        == WaterHeaterEntityFeature.TARGET_TEMPERATURE
        + WaterHeaterEntityFeature.OPERATION_MODE
    )
    assert test_water_heater.operation_list == WATER_HEATER_MODES
    assert test_water_heater.min_temp is None
    assert test_water_heater.max_temp is None
    assert test_water_heater.current_temperature is None
    assert test_water_heater.target_temperature is None
    assert test_water_heater.target_temperature_high is None
    assert test_water_heater.target_temperature_low is None
    assert test_water_heater.current_operation is None

    # Update entity and check that attributes was correctly set.
    await test_water_heater.async_update()
    assert test_water_heater.min_temp == 40
    assert test_water_heater.max_temp == 60
    assert test_water_heater.current_temperature == 50
    assert test_water_heater.target_temperature == 50
    assert test_water_heater.target_temperature_high == 50
    assert test_water_heater.target_temperature_low == 45
    assert test_water_heater.current_operation == STATE_PERFORMANCE

    # Unset target temperature and check that attributes is unknown.
    mock_connection.ecomax.water_heater_target_temp = None
    await test_water_heater.async_update()
    assert test_water_heater.min_temp is None
    assert test_water_heater.max_temp is None
    assert test_water_heater.target_temperature is None
    assert test_water_heater.target_temperature_high is None
    assert test_water_heater.target_temperature_low is None
    assert test_water_heater.current_operation is None


@pytest.mark.asyncio
async def test_target_lower_without_hysteresis(
    test_water_heater: EcomaxWaterHeater, mock_connection: EcomaxTcpConnection
) -> None:
    """Test lower bound without hysteresis value."""
    mock_connection.ecomax.water_heater_hysteresis = None
    await test_water_heater.async_update()
    assert test_water_heater.target_temperature_low == 50


@pytest.mark.asyncio
async def test_async_set_temperature(
    test_water_heater: EcomaxWaterHeater, mock_connection: EcomaxTcpConnection
) -> None:
    """Test set water heater target temperature."""
    await test_water_heater.async_set_temperature(temperature=60)
    assert test_water_heater.target_temperature == 60
    assert mock_connection.ecomax.water_heater_target_temp == 60


@pytest.mark.asyncio
async def test_async_set_operation_mode(
    test_water_heater: EcomaxWaterHeater, mock_connection: EcomaxTcpConnection
) -> None:
    """Test set water heater operation mode."""
    await test_water_heater.async_set_operation_mode(STATE_OFF)
    assert test_water_heater.current_operation == STATE_OFF
    assert mock_connection.ecomax.water_heater_work_mode == WATER_HEATER_MODES.index(
        STATE_OFF
    )
