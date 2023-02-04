"""Test the switch platform."""

from unittest.mock import Mock, patch

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.const import ATTR_ECOMAX_CONTROL
from custom_components.plum_ecomax.switch import (
    MIXER_SWITCH_TYPES,
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
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers"
    ) as mock_setup_mixers:
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    await hass.async_block_till_done()
    mock_setup_mixers.assert_called_once()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    sensor_types = (
        SWITCH_TYPES[ProductType.ECOMAX_P] + MIXER_SWITCH_TYPES[ProductType.ECOMAX_P]
    )
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
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait",
        new_callable=Mock,
    ) as mock_set_value_nowait:
        await entity.async_turn_off()

    mock_set_value_nowait.assert_called_once_with(
        entity.entity_description.key, entity.entity_description.state_off
    )
    assert not entity.is_on

    # Turn the switch back on.
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.device.set_value_nowait",
        new_callable=Mock,
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
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers"
    ) as mock_setup_mixers:
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    await hass.async_block_till_done()
    mock_setup_mixers.assert_called_once()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    sensor_types = (
        SWITCH_TYPES[ProductType.ECOMAX_I] + MIXER_SWITCH_TYPES[ProductType.ECOMAX_I]
    )
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_switch(added_entities, sensor_type.key)


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_and_update_entry_without_mixers(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update switch entry for ecomax p without mixers."""
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.has_mixers", False
    ):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_switch(added_entities, "weather_control")


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_setup_mixers_error(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update switch entry for ecomax p
    with error during mixer setup."""
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers",
        return_value=False,
    ):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_switch(added_entities, "weather_control")
