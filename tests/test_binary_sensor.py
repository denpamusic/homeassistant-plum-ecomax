"""Test the binary sensor platform."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.binary_sensor import (
    BINARY_SENSOR_TYPES,
    MIXER_BINARY_SENSOR_TYPES,
    EcomaxBinarySensor,
    MixerBinarySensor,
    async_setup_entry,
)


def _lookup_binary_sensor(
    entities: list[EcomaxBinarySensor], key: str
) -> EcomaxBinarySensor:
    """Lookup entity in the list."""
    for entity in entities:
        if entity.entity_description.key == key:
            return entity

    raise LookupError(f"Couldn't find '{key}' binary sensor")


@pytest.fixture(autouse=True)
def set_connection_name():
    """Set connection name."""
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.name",
        "test",
        create=True,
    ):
        yield


@pytest.mark.usefixtures("connected", "ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_p(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update binary sensor entry for ecomax p."""
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers"
    ) as mock_setup_mixers:
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    await hass.async_block_till_done()
    mock_setup_mixers.assert_called_once()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    binary_sensor_types = (
        BINARY_SENSOR_TYPES[ProductType.ECOMAX_P]
        + MIXER_BINARY_SENSOR_TYPES[ProductType.ECOMAX_P]
    )
    assert len(added_entities) == len(binary_sensor_types)

    # Check that all binary sensors are present.
    for sensor_type in binary_sensor_types:
        assert _lookup_binary_sensor(added_entities, sensor_type.key)

    # Test ecomax p binary sensors.
    entity = _lookup_binary_sensor(added_entities, "heating_pump")
    assert isinstance(entity, EcomaxBinarySensor)
    await entity.async_added_to_hass()
    assert entity.entity_registry_enabled_default
    assert entity.available
    assert not entity.is_on
    await entity.async_update(True)
    assert entity.is_on

    # Test mixer binary sensors.
    mixer_entity = _lookup_binary_sensor(added_entities, "pump")
    assert isinstance(mixer_entity, MixerBinarySensor)
    assert "Mixer pump" in mixer_entity.name


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_async_setup_and_update_entry_with_ecomax_i(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update binary sensor entry for ecomax i."""
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.setup_mixers"
    ) as mock_setup_mixers:
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    await hass.async_block_till_done()
    mock_setup_mixers.assert_called_once()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    binary_sensor_types = (
        BINARY_SENSOR_TYPES[ProductType.ECOMAX_I]
        + MIXER_BINARY_SENSOR_TYPES[ProductType.ECOMAX_I]
    )
    assert len(added_entities) == len(binary_sensor_types)

    # Check that all binary sensors are present.
    for sensor_type in binary_sensor_types:
        assert _lookup_binary_sensor(added_entities, sensor_type.key)

    # Test mixer binary sensors. With ecomax i, mixers should
    # be always refered as circuits.
    mixer_entity = _lookup_binary_sensor(added_entities, "pump")
    assert isinstance(mixer_entity, MixerBinarySensor)
    assert "Circuit pump" in mixer_entity.name


@pytest.mark.usefixtures("ecomax_p")
async def test_async_setup_and_update_entry_without_mixers(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update binary sensor entry for ecomax p
    without mixers.
    """
    with patch(
        "custom_components.plum_ecomax.entity.EcomaxConnection.has_mixers", False
    ):
        assert await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]

    # Check that mixer sensor is not added.
    with pytest.raises(LookupError):
        _lookup_binary_sensor(added_entities, "pump")


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_async_setup_and_update_entry_with_setup_mixers_error(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and update binary sensor entry for ecomax p
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
        _lookup_binary_sensor(added_entities, "pump")
