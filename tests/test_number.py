"""Test Plum ecoMAX number."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
import pytest_asyncio
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxTcpConnection
from custom_components.plum_ecomax.number import EcomaxNumber, async_setup_entry


@pytest_asyncio.fixture(name="test_number")
async def fixture_test_number(
    hass: HomeAssistant,
    add_entities_callback: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    bypass_hass_write_ha_state,
) -> EcomaxNumber:
    """Setup number entities and get a single number."""
    await async_setup_entry(hass, config_entry, add_entities_callback)
    add_entities_callback.assert_called_once()
    numbers = add_entities_callback.call_args[0][0]
    number = [x for x in numbers if x.entity_description.key == "heating_set_temp"]
    yield number[0]


@pytest.mark.asyncio
async def test_async_setup_and_update_value(
    test_number: EcomaxNumber, mock_connection: EcomaxTcpConnection
) -> None:
    """Test setup and update of number entity."""
    # Check that entity value is unknown.
    assert isinstance(test_number, EcomaxNumber)
    assert test_number.value is None
    assert test_number.min_value is None
    assert test_number.max_value is None

    # Update entity and check that attributes was correctly set.
    await test_number.async_update()
    assert test_number.value == 65
    assert test_number.min_value == 40
    assert test_number.max_value == 80

    # Unset number parameter and check that attributes is unknown.
    mock_connection.ecomax.heating_set_temp = None
    await test_number.async_update()
    assert test_number.value is None
    assert test_number.min_value is None
    assert test_number.max_value is None


@pytest.mark.asyncio
async def test_async_set_value(
    test_number: EcomaxNumber, mock_connection: EcomaxTcpConnection
) -> None:
    """Test set number value."""
    await test_number.async_update()
    assert test_number.value == 65
    await test_number.async_set_value(70)
    assert test_number.value == 70
    assert mock_connection.ecomax.heating_set_temp == 70
