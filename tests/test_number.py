"""Test the number platform."""

from unittest.mock import Mock, call, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.helpers.parameter import Parameter
from pyplumio.helpers.product_info import ProductType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.number import (
    MIXER_NUMBER_TYPES,
    NUMBER_TYPES,
    EcomaxNumber,
    async_setup_entry,
)


@pytest.fixture(autouse=True)
def bypass_async_get_current_platform():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.sensor.async_get_current_platform"):
        yield


@pytest.fixture(autouse=True)
def set_connection_name():
    """Set connection name."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name",
        "test",
        create=True,
    ):
        yield


def _lookup_number(entities: list[EcomaxNumber], key: str) -> EcomaxNumber:
    """Lookup number in the list."""
    for entity in entities:
        if entity.entity_description.key == key:
            return entity

    raise LookupError(f"Couldn't find '{key}' number")


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_async_added_removed_to_hass(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test adding and removing entity to/from hass."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    entity = _lookup_number(added_entities, "heating_target_temp")
    with patch(
        "custom_components.plum_ecomax.entity.Device.subscribe"
    ) as mock_subscribe:
        await entity.async_added_to_hass()

    assert mock_subscribe.call_count == 4
    mock_subscribe.assert_has_calls(
        [
            call("min_heating_target_temp", entity.async_set_min_value),
            call("max_heating_target_temp", entity.async_set_max_value),
        ]
    )

    # Test removing the entity from hass.
    with patch(
        "custom_components.plum_ecomax.entity.Device.unsubscribe"
    ) as mock_unsubscribe:
        await entity.async_will_remove_from_hass()

    assert mock_unsubscribe.call_count == 3
    mock_unsubscribe.assert_has_calls(
        [
            call("min_heating_target_temp", entity.async_set_min_value),
            call("max_heating_target_temp", entity.async_set_max_value),
        ]
    )


@pytest.mark.usefixtures("connected", "ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update number entry for ecomax p."""
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
        NUMBER_TYPES[ProductType.ECOMAX_P] + MIXER_NUMBER_TYPES[ProductType.ECOMAX_P]
    )
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_number(added_entities, sensor_type.key)

    entity = _lookup_number(added_entities, "heating_target_temp")
    assert isinstance(entity, EcomaxNumber)
    mock_parameter = Mock(spec=Parameter)
    mock_parameter.configure_mock(value=1, min_value=0, max_value=2)

    # Check that number values is unknown and update them.
    assert entity.native_value is None
    assert entity.native_min_value is None
    assert entity.native_max_value is None
    await entity.async_added_to_hass()
    assert entity.entity_registry_enabled_default
    assert entity.available
    await entity.async_update(mock_parameter)
    assert entity.native_value == 1
    assert entity.native_min_value == 0
    assert entity.native_max_value == 2

    # Test changing number value.
    with patch(
        "custom_components.plum_ecomax.entity.Device.set_value_nowait",
        new_callable=Mock,
    ) as mock_set_value_nowait:
        await entity.async_set_native_value(2.2)

    mock_set_value_nowait.assert_called_once_with(entity.entity_description.key, 2.2)
    assert entity.native_value == 2.2

    # Test changing minimal number value.
    assert entity.native_min_value == 0
    mock_parameter.value = 4
    await entity.async_set_min_value(mock_parameter)
    assert entity.native_min_value == 4

    # Test changing maximum number value.
    assert entity.native_max_value == 2
    mock_parameter.value = 5
    await entity.async_set_max_value(mock_parameter)
    assert entity.native_max_value == 5

    # Check mixer number name.
    entity = _lookup_number(added_entities, "mixer_target_temp")
    assert entity.device_info["name"] == "test Mixer 1"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_i(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update number entry for ecomax i."""
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
        NUMBER_TYPES[ProductType.ECOMAX_I] + MIXER_NUMBER_TYPES[ProductType.ECOMAX_I]
    )
    assert len(added_entities) == len(sensor_types)

    # Check that all sensors are present.
    for sensor_type in sensor_types:
        assert _lookup_number(added_entities, sensor_type.key)

    # Check mixer number name.
    entity = _lookup_number(added_entities, "mixer_target_temp")
    assert entity.device_info["name"] == "test Circuit 1"


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_and_update_entry_without_mixers(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update number entry for ecomax p without mixers."""
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.has_mixers", False
    ):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_number(added_entities, "mixer_target_temp")


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_setup_mixers_error(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update number entry for ecomax p
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
        _lookup_number(added_entities, "mixer_target_temp")
