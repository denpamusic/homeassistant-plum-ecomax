"""Test the button platform."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.button import (
    BUTTON_TYPES,
    EcomaxButton,
    async_setup_entry,
)


def _lookup_button(entities: list[EcomaxButton], key: str) -> EcomaxButton:
    """Lookup entity in the list."""
    for entity in entities:
        if entity.entity_description.key == key:
            return entity

    raise LookupError(f"Couldn't find '{key}' button")


@pytest.mark.usefixtures("connected")
async def test_async_setup_and_update_entry(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: MockConfigEntry,
) -> None:
    """Test setup and press button entry."""
    assert await async_setup_entry(hass, config_entry, async_add_entities)
    await hass.async_block_till_done()
    async_add_entities.assert_called_once()
    args = async_add_entities.call_args[0]
    added_entities = args[0]
    assert len(added_entities) == len(BUTTON_TYPES)

    # Check that all buttons are present.
    for sensor_type in BUTTON_TYPES:
        assert _lookup_button(added_entities, sensor_type.key)

    # Test update sub-devices button.
    entity = _lookup_button(added_entities, "detect_sub_devices")
    assert isinstance(entity, EcomaxButton)
    assert entity.entity_registry_enabled_default
    assert entity.available
    with patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.async_update_sub_devices"
    ) as async_update_sub_devices:
        await entity.async_press()

    async_update_sub_devices.assert_awaited_once()

    # Check than async update on button raises not implemented error.
    with pytest.raises(NotImplementedError):
        await entity.async_update(1)

    # Check that async press on button return not implemented error
    # if press_fn doesn't exist in EcomaxConnection class.
    with pytest.raises(NotImplementedError), patch.object(
        entity.entity_description, "press_fn", "nonexistent"
    ):
        await entity.async_press()

    # Check that press_fn is getting called.
    with patch.object(entity.entity_description, "press_fn", "test_fn"), patch(
        "custom_components.plum_ecomax.connection.EcomaxConnection.test_fn", create=True
    ) as mock_test_fn:
        await entity.async_press()

    mock_test_fn.assert_called_once()

    # Check with nonexistent button.
    with pytest.raises(LookupError):
        _lookup_button(added_entities, "nonexistent")
