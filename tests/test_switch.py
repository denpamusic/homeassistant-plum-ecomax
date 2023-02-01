"""Test the switch platform."""

from unittest.mock import Mock, patch

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import ATTR_ECOMAX_CONTROL
from custom_components.plum_ecomax.switch import (
    ECOMAX_I_MIXER_SWITCH_TYPES,
    ECOMAX_P_MIXER_SWITCH_TYPES,
    ECOMAX_P_SWITCH_TYPES,
    SWITCH_TYPES,
    EcomaxSwitch,
    async_setup_entry,
)


@pytest.fixture(autouse=True)
def set_connection_name():
    """Set connection name."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name",
        "test",
        create=True,
    ):
        yield


def _lookup_switch(entities: list[EcomaxSwitch], key: str) -> EcomaxSwitch:
    """Lookup switch in the list."""
    for entity in entities:
        if entity.entity_description.key == key:
            return entity

    raise LookupError(f"Couldn't find '{key}' switch")


@pytest.mark.usefixtures("connected", "ecomax_p", "ecomax_control", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update switch entry for ecomax p."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    sensor_types = SWITCH_TYPES + ECOMAX_P_SWITCH_TYPES + ECOMAX_P_MIXER_SWITCH_TYPES
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_switch(added_entities, sensor_type.key)

    # Check that switch state is unknown and update it.
    entity = _lookup_switch(added_entities, ATTR_ECOMAX_CONTROL)
    assert isinstance(entity, EcomaxSwitch)
    mock_parameter = Mock(spec=Parameter)
    mock_parameter.configure_mock(value=STATE_ON)
    assert entity.is_on is None
    await entity.async_added_to_hass()
    assert entity.entity_registry_enabled_default
    assert entity.available
    await entity.async_update(mock_parameter)
    assert entity.is_on

    # Turn the switch off.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait"
    ) as mock_set_value_nowait:
        await entity.async_turn_off()

    mock_set_value_nowait.assert_called_once_with(
        entity.entity_description.key, entity.entity_description.state_off
    )
    assert not entity.is_on

    # Turn the switch back on.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait"
    ) as mock_set_value_nowait:
        await entity.async_turn_on()

    mock_set_value_nowait.assert_called_once_with(
        entity.entity_description.key, entity.entity_description.state_on
    )
    assert entity.is_on


@pytest.mark.usefixtures("ecomax_i", "ecomax_control", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_i(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update switch entry for ecomax p."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    sensor_types = SWITCH_TYPES + ECOMAX_I_MIXER_SWITCH_TYPES
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_switch(added_entities, sensor_type.key)


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_and_update_entry_without_mixers(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update switch entry for ecomax p without mixers."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    assert "Couldn't load mixer switch" in caplog.text

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_switch(added_entities, "weather_control")


@pytest.mark.usefixtures("ecomax_base")
async def test_async_setup_and_update_entry_with_no_sensor_data(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update switch entry for ecomax p without the
    sensor data.
    """
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    assert "Couldn't load device switches" in caplog.text


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_entry_with_control_parameter_timeout(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup switch entry with control parameter timeout."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    assert "Control parameter not present" in caplog.text


@pytest.mark.usefixtures("ecomax_unknown")
async def test_async_setup_and_update_entry_with_unknown_ecomax_model(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
    caplog,
) -> None:
    """Test setup and update switch entry for unknown ecomax model."""
    assert not await async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    assert "Couldn't setup platform due to unknown controller model" in caplog.text
