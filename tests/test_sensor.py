"""Test the sensor platform."""

from unittest import mock
from unittest.mock import call, patch

from freezegun import freeze_time
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START,
    PERCENTAGE,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pyplumio.const import (
    ATTR_CURRENT_TEMP,
    ATTR_PASSWORD,
    ATTR_STATE,
    ATTR_TARGET_TEMP,
    DeviceState,
    ProductType,
)
from pyplumio.devices.ecomax import ATTR_FUEL_BURNED
from pyplumio.structures.fan_power import ATTR_FAN_POWER
from pyplumio.structures.fuel_consumption import ATTR_FUEL_CONSUMPTION
from pyplumio.structures.fuel_level import ATTR_FUEL_LEVEL
from pyplumio.structures.lambda_sensor import ATTR_LAMBDA_LEVEL
from pyplumio.structures.load import ATTR_LOAD
from pyplumio.structures.modules import ATTR_MODULES, ConnectedModules
from pyplumio.structures.power import ATTR_POWER
from pyplumio.structures.product_info import ATTR_PRODUCT, ProductInfo
from pyplumio.structures.statuses import ATTR_HEATING_TARGET, ATTR_WATER_HEATER_TARGET
from pyplumio.structures.temperatures import (
    ATTR_EXHAUST_TEMP,
    ATTR_FEEDER_TEMP,
    ATTR_FIREPLACE_TEMP,
    ATTR_HEATING_TEMP,
    ATTR_LOWER_BUFFER_TEMP,
    ATTR_LOWER_SOLAR_TEMP,
    ATTR_OPTICAL_TEMP,
    ATTR_OUTSIDE_TEMP,
    ATTR_RETURN_TEMP,
    ATTR_UPPER_BUFFER_TEMP,
    ATTR_UPPER_SOLAR_TEMP,
    ATTR_WATER_HEATER_TEMP,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plum_ecomax.connection import EcomaxConnection
from custom_components.plum_ecomax.const import DEVICE_CLASS_STATE, DOMAIN, FLOW_KGH
from custom_components.plum_ecomax.sensor import (
    ATTR_VALUE,
    SERVICE_CALIBRATE_METER,
    SERVICE_RESET_METER,
)


@pytest.fixture(autouse=True)
def bypass_connection_setup():
    """Mock async get current platform."""
    with patch("custom_components.plum_ecomax.connection.EcomaxConnection.async_setup"):
        yield


@pytest.fixture(autouse=True)
def bypass_async_migrate_entry():
    """Bypass async migrate entry."""
    with patch("custom_components.plum_ecomax.async_migrate_entry", return_value=True):
        yield


@pytest.fixture(autouse=True)
def set_connected(connected):
    """Assume connected."""


@pytest.fixture(name="frozen_time")
def fixture_frozen_time():
    """Get frozen time."""
    with freeze_time("2012-12-12 12:00:00") as frozen_time:
        yield frozen_time


@pytest.fixture(name="calibrate_meter")
async def fixture_calibrate_meter():
    """Calibeate meter."""

    async def calibrate_meter(hass: HomeAssistant, entity_id: str, value: float):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CALIBRATE_METER,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return calibrate_meter


@pytest.fixture(name="reset_meter")
async def fixture_reset_meter():
    """Reset meter."""

    async def reset_meter(hass: HomeAssistant, entity_id: str):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_METER,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        return hass.states.get(entity_id)

    return reset_meter


@pytest.mark.usefixtures("ecomax_p")
async def test_setup_meter_services(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test that meter services are set up."""
    with patch(
        "custom_components.plum_ecomax.sensor.async_get_current_platform"
    ) as mock_async_get_current_platform:
        await setup_integration(hass, config_entry)

    platform = mock_async_get_current_platform.return_value
    platform.async_register_entity_service.assert_has_calls(
        [
            call(SERVICE_RESET_METER, mock.ANY, "async_reset_meter"),
            call(SERVICE_CALIBRATE_METER, mock.ANY, "async_calibrate_meter"),
        ]
    )


@pytest.mark.usefixtures("ecomax_p")
async def test_heating_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test heating temperature sensor."""
    await setup_integration(hass, config_entry)
    heating_temperature_entity_id = "sensor.ecomax_heating_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_temperature_entity_id)
    assert entry
    assert entry.translation_key == "heating_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(heating_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Heating temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_HEATING_TEMP, 65)
    state = hass.states.get(heating_temperature_entity_id)
    assert state.state == "65"

    # Check that entity is disabled if unavailable on setup.
    del connection.device.data[ATTR_HEATING_TEMP]
    await hass.config_entries.async_remove(config_entry.entry_id)
    await setup_integration(hass, config_entry)
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_temperature_entity_id)
    assert entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test water heater temperature sensor."""
    await setup_integration(hass, config_entry)
    water_heater_temperature_entity_id = "sensor.ecomax_water_heater_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_temperature_entity_id)
    assert entry.translation_key == "water_heater_temp"
    assert entry
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(water_heater_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_WATER_HEATER_TEMP, 51)
    state = hass.states.get(water_heater_temperature_entity_id)
    assert state.state == "51"

    # Test without water heater.
    del connection.device.data[ATTR_WATER_HEATER_TEMP]
    await hass.config_entries.async_remove(config_entry.entry_id)
    await setup_integration(hass, config_entry)
    state = hass.states.get(water_heater_temperature_entity_id)
    assert state is None


@pytest.mark.usefixtures("ecomax_p")
async def test_outside_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test outside temperature sensor."""
    await setup_integration(hass, config_entry)
    outside_temperature_entity_id = "sensor.ecomax_outside_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(outside_temperature_entity_id)
    assert entry
    assert entry.translation_key == "outside_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    frozen_time.move_to("12:00:10")
    state = hass.states.get(outside_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Outside temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE

    # Dispatch new value.
    await connection.device.dispatch(ATTR_OUTSIDE_TEMP, 1)
    state = hass.states.get(outside_temperature_entity_id)
    assert state.state == "1"


@pytest.mark.usefixtures("ecomax_p")
async def test_heating_target_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test heating target temperature sensor."""
    await setup_integration(hass, config_entry)
    heating_target_temperature_entity_id = "sensor.ecomax_heating_target_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(heating_target_temperature_entity_id)
    assert entry
    assert entry.translation_key == "heating_target"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(heating_target_temperature_entity_id)
    assert state.state == "0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Heating target temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE

    # Dispatch new value.
    await connection.device.dispatch(ATTR_HEATING_TARGET, 65)
    state = hass.states.get(heating_target_temperature_entity_id)
    assert state.state == "65"


@pytest.mark.usefixtures("ecomax_p", "water_heater")
async def test_water_heater_target_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test water heater target temperature sensor."""
    await setup_integration(hass, config_entry)
    water_heater_target_temperature_entity_id = (
        "sensor.ecomax_water_heater_target_temperature"
    )

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(water_heater_target_temperature_entity_id)
    assert entry
    assert entry.translation_key == "water_heater_target"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(water_heater_target_temperature_entity_id)
    assert state.state == "0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Water heater target temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE

    # Dispatch new value.
    await connection.device.dispatch(ATTR_WATER_HEATER_TARGET, 50)
    state = hass.states.get(water_heater_target_temperature_entity_id)
    assert state.state == "50"


@pytest.mark.usefixtures("ecomax_p")
async def test_state_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test state sensor."""
    await setup_integration(hass, config_entry)
    state_entity_id = "sensor.ecomax_state"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(state_entity_id)
    assert entry
    assert entry.translation_key == "ecomax_state"

    # Get initial value.
    state = hass.states.get(state_entity_id)
    assert state.state == "off"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX State"
    assert state.attributes[ATTR_DEVICE_CLASS] == DEVICE_CLASS_STATE
    assert state.attributes[ATTR_VALUE] == 0

    # Dispatch new value.
    await connection.device.dispatch(ATTR_STATE, DeviceState.ALERT)
    state = hass.states.get(state_entity_id)
    assert state.state == "alert"

    # Dispatch unknown state.
    await connection.device.dispatch(ATTR_STATE, 99)
    state = hass.states.get(state_entity_id)
    assert state.state == "unknown"


@pytest.mark.usefixtures("ecomax_p")
async def test_service_password_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test service password sensor."""
    await setup_integration(hass, config_entry)
    service_password_entity_id = "sensor.ecomax_service_password"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(service_password_entity_id)
    assert entry.translation_key == "service_password"
    assert entry

    # Get initial value.
    state = hass.states.get(service_password_entity_id)
    assert state.state == "0000"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Service password"
    assert state.attributes[ATTR_ICON] == "mdi:form-textbox-password"

    # Dispatch new value.
    await connection.device.dispatch(ATTR_PASSWORD, "1234")
    state = hass.states.get(service_password_entity_id)
    assert state.state == "1234"


@pytest.mark.usefixtures("ecomax_p")
async def test_software_version_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test software version sensor."""
    await setup_integration(hass, config_entry)
    software_version_entity_id = "sensor.ecomax_software_version"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(software_version_entity_id)
    assert entry
    assert entry.translation_key == "software_version"

    # Get initial value.
    state = hass.states.get(software_version_entity_id)
    assert state.state == "6.10.32.K1"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Software version"

    # Dispatch new value.
    await connection.device.dispatch(
        ATTR_MODULES, ConnectedModules(module_a="1.0.0.T0")
    )
    state = hass.states.get(software_version_entity_id)
    assert state.state == "1.0.0.T0"


@pytest.mark.usefixtures("ecomax_p")
async def test_uid_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test uid sensor."""
    await setup_integration(hass, config_entry)
    uid_entity_id = "sensor.ecomax_uid"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(uid_entity_id)
    assert entry
    assert entry.translation_key == "uid"

    # Get initial value.
    state = hass.states.get(uid_entity_id)
    assert state.state == "TEST"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX UID"

    # Dispatch new value.
    await connection.device.dispatch(
        ATTR_PRODUCT,
        ProductInfo(
            type=ProductType.ECOMAX_I, id=0, uid="TEST2", logo=0, image=0, model="TEST2"
        ),
    )
    state = hass.states.get(uid_entity_id)
    assert state.state == "TEST2"


@pytest.mark.usefixtures("ecomax_p")
async def test_oxygen_level_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test oxygen level sensor."""
    await setup_integration(hass, config_entry)
    oxygen_level_entity_id = "sensor.ecomax_oxygen_level"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(oxygen_level_entity_id)
    assert entry
    assert entry.translation_key == "oxygen_level"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(oxygen_level_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Oxygen level"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:weather-windy-variant"

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_LAMBDA_LEVEL, 15)
    state = hass.states.get(oxygen_level_entity_id)
    assert state.state == "15"

    # Test without ecoLAMBDA.
    await connection.device.dispatch(ATTR_MODULES, ConnectedModules(ecolambda=None))
    await hass.config_entries.async_remove(config_entry.entry_id)
    await setup_integration(hass, config_entry)
    assert hass.states.get(oxygen_level_entity_id) is None


@pytest.mark.usefixtures("ecomax_p")
async def test_power_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test power sensor."""
    await setup_integration(hass, config_entry)
    power_entity_id = "sensor.ecomax_power"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(power_entity_id)
    assert entry
    assert entry.translation_key == "power"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(power_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfPower.KILO_WATT
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:radiator"

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_POWER, 16)
    state = hass.states.get(power_entity_id)
    assert state.state == "16"


@pytest.mark.usefixtures("ecomax_p")
async def test_fuel_level_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test fuel level sensor."""
    await setup_integration(hass, config_entry)
    fuel_level_entity_id = "sensor.ecomax_fuel_level"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuel_level_entity_id)
    assert entry
    assert entry.translation_key == "fuel_level"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 0

    # Get initial value.
    state = hass.states.get(fuel_level_entity_id)
    assert state.state == "0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuel level"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:gas-station"

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_FUEL_LEVEL, 20)
    state = hass.states.get(fuel_level_entity_id)
    assert state.state == "20"


@pytest.mark.usefixtures("ecomax_p")
async def test_fuel_consumption_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test fuel consumption sensor."""
    await setup_integration(hass, config_entry)
    fuel_consumption_entity_id = "sensor.ecomax_fuel_consumption"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuel_consumption_entity_id)
    assert entry
    assert entry.translation_key == "fuel_consumption"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 2

    # Get initial value.
    state = hass.states.get(fuel_consumption_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fuel consumption"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == FLOW_KGH
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:fire"

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_FUEL_CONSUMPTION, 2.5)
    state = hass.states.get(fuel_consumption_entity_id)
    assert state.state == "2.5"


@pytest.mark.usefixtures("ecomax_p")
async def test_load_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test load sensor."""
    await setup_integration(hass, config_entry)
    load_entity_id = "sensor.ecomax_load"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(load_entity_id)
    assert entry
    assert entry.translation_key == "load"

    # Get initial value.
    state = hass.states.get(load_entity_id)
    assert state.state == "0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Load"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:gauge"

    # Dispatch new value.
    await connection.device.dispatch(ATTR_LOAD, 50)
    state = hass.states.get(load_entity_id)
    assert state.state == "50"


@pytest.mark.usefixtures("ecomax_p")
async def test_fan_power_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test fan power sensor."""
    await setup_integration(hass, config_entry)
    fan_power_entity_id = "sensor.ecomax_fan_power"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fan_power_entity_id)
    assert entry
    assert entry.translation_key == "fan_power"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(fan_power_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fan power"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:fan"

    # Dispatch new value.
    await connection.device.dispatch(ATTR_FAN_POWER, 100)
    state = hass.states.get(fan_power_entity_id)
    assert state.state == "100"


@pytest.mark.usefixtures("ecomax_p")
async def test_flame_intensity_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test flame intensity sensor."""
    await setup_integration(hass, config_entry)
    flame_intensity_entity_id = "sensor.ecomax_flame_intensity"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(flame_intensity_entity_id)
    assert entry
    assert entry.translation_key == "flame_intensity"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(flame_intensity_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Flame intensity"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:fire"

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_OPTICAL_TEMP, 100)
    state = hass.states.get(flame_intensity_entity_id)
    assert state.state == "100"


@pytest.mark.usefixtures("ecomax_p")
async def test_feeder_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test feeder temperature sensor."""
    await setup_integration(hass, config_entry)
    feeder_temperature_entity_id = "sensor.ecomax_feeder_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(feeder_temperature_entity_id)
    assert entry
    assert entry.translation_key == "feeder_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(feeder_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Feeder temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_FEEDER_TEMP, 35)
    state = hass.states.get(feeder_temperature_entity_id)
    assert state.state == "35"


@pytest.mark.usefixtures("ecomax_p")
async def test_exhaust_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test exhaust temperature sensor."""
    await setup_integration(hass, config_entry)
    exhaust_temperature_entity_id = "sensor.ecomax_exhaust_temperature"

    # Test entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(exhaust_temperature_entity_id)
    assert entry
    assert entry.translation_key == "exhaust_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(exhaust_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Exhaust temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_EXHAUST_TEMP, 120)
    state = hass.states.get(exhaust_temperature_entity_id)
    assert state.state == "120"


@pytest.mark.usefixtures("ecomax_p")
async def test_return_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test return temperature sensor."""
    await setup_integration(hass, config_entry)
    return_temperature_entity_id = "sensor.ecomax_return_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(return_temperature_entity_id)
    assert entry
    assert entry.translation_key == "return_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(return_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Return temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_RETURN_TEMP, 45)
    state = hass.states.get(return_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_p")
async def test_lower_buffer_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test lower buffer temperature sensor."""
    await setup_integration(hass, config_entry)
    lower_buffer_temperature_entity_id = "sensor.ecomax_lower_buffer_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(lower_buffer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "lower_buffer_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(lower_buffer_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Lower buffer temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_LOWER_BUFFER_TEMP, 45)
    state = hass.states.get(lower_buffer_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_p")
async def test_upper_buffer_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test upper buffer temperature sensor."""
    await setup_integration(hass, config_entry)
    upper_buffer_temperature_entity_id = "sensor.ecomax_upper_buffer_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(upper_buffer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "upper_buffer_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(upper_buffer_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Upper buffer temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_UPPER_BUFFER_TEMP, 45)
    state = hass.states.get(upper_buffer_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_i")
async def test_lower_solar_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test lower solar temperature sensor."""
    await setup_integration(hass, config_entry)
    lower_solar_temperature_entity_id = "sensor.ecomax_lower_solar_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(lower_solar_temperature_entity_id)
    assert entry
    assert entry.translation_key == "lower_solar_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(lower_solar_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Lower solar temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_LOWER_SOLAR_TEMP, 45)
    state = hass.states.get(lower_solar_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_i")
async def test_upper_solar_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test upper solar temperature sensor."""
    await setup_integration(hass, config_entry)
    upper_solar_temperature_entity_id = "sensor.ecomax_upper_solar_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(upper_solar_temperature_entity_id)
    assert entry
    assert entry.translation_key == "upper_solar_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(upper_solar_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Upper solar temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_UPPER_SOLAR_TEMP, 45)
    state = hass.states.get(upper_solar_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_i")
async def test_fireplace_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test fireplace temperature sensor."""
    await setup_integration(hass, config_entry)
    fireplace_temperature_entity_id = "sensor.ecomax_fireplace_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fireplace_temperature_entity_id)
    assert entry
    assert entry.translation_key == "fireplace_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(fireplace_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Fireplace temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.dispatch(ATTR_FIREPLACE_TEMP, 45)
    state = hass.states.get(fireplace_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test mixer temperature sensor."""
    await setup_integration(hass, config_entry)
    mixer_temperature_entity_id = "sensor.ecomax_mixer_1_mixer_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(mixer_temperature_entity_id)
    assert entry
    assert entry.translation_key == "mixer_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(mixer_temperature_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Mixer 1 Mixer temperature"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.mixers[0].dispatch(ATTR_CURRENT_TEMP, 45)
    state = hass.states.get(mixer_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_p", "mixers")
async def test_mixer_target_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test mixer target temperature sensor."""
    await setup_integration(hass, config_entry)
    mixer_target_temperature_entity_id = (
        "sensor.ecomax_mixer_1_mixer_target_temperature"
    )

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(mixer_target_temperature_entity_id)
    assert entry
    assert entry.translation_key == "mixer_target_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(mixer_target_temperature_entity_id)
    assert state.state == "0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Mixer 1 Mixer target temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.mixers[0].dispatch(ATTR_TARGET_TEMP, 45)
    state = hass.states.get(mixer_target_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test circuit temperature sensor."""
    await setup_integration(hass, config_entry)
    circuit_temperature_entity_id = "sensor.ecomax_circuit_1_circuit_temperature"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circuit_temperature_entity_id)
    assert entry
    assert entry.translation_key == "circuit_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(circuit_temperature_entity_id)
    assert state.state == "0.0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Circuit 1 Circuit temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.mixers[0].dispatch(ATTR_CURRENT_TEMP, 45)
    state = hass.states.get(circuit_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_i", "mixers")
async def test_circuit_target_temperature_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    frozen_time,
) -> None:
    """Test circuit target temperature sensor."""
    await setup_integration(hass, config_entry)
    circuit_target_temperature_entity_id = (
        "sensor.ecomax_circuit_1_circuit_target_temperature"
    )

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(circuit_target_temperature_entity_id)
    assert entry
    assert entry.translation_key == "circuit_target_temp"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 1

    # Get initial value.
    state = hass.states.get(circuit_target_temperature_entity_id)
    assert state.state == "0"
    assert (
        state.attributes[ATTR_FRIENDLY_NAME]
        == "ecoMAX Circuit 1 Circuit target temperature"
    )
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    # Dispatch new value.
    frozen_time.move_to("12:00:10")
    await connection.device.mixers[0].dispatch(ATTR_TARGET_TEMP, 45)
    state = hass.states.get(circuit_target_temperature_entity_id)
    assert state.state == "45"


@pytest.mark.usefixtures("ecomax_p")
async def test_total_fuel_burned_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
    calibrate_meter,
    reset_meter,
    frozen_time,
) -> None:
    """Test total fuel burned sensor."""
    await setup_integration(hass, config_entry)
    fuel_burned_entity_id = "sensor.ecomax_total_fuel_burned"

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(fuel_burned_entity_id)
    assert entry
    assert entry.translation_key == "total_fuel_burned"
    options = entry.options["sensor"]
    assert options["suggested_display_precision"] == 2

    # Get initial value.
    state = hass.states.get(fuel_burned_entity_id)
    assert state.state == "0.0"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Total fuel burned"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfMass.KILOGRAMS
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.TOTAL_INCREASING
    assert state.attributes[ATTR_ICON] == "mdi:counter"

    # Move time 30 seconds in future and dispatch new value.
    await connection.device.dispatch(ATTR_FUEL_BURNED, 0.1)
    frozen_time.move_to("12:00:30")
    await connection.device.dispatch(ATTR_FUEL_BURNED, 0.2)
    state = hass.states.get(fuel_burned_entity_id)
    assert state.state == "0.3"

    # Test that value is restored after HASS restart.
    await hass.async_stop()
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()
    state = hass.states.get(fuel_burned_entity_id)
    assert state.state == "0.3"

    # Test that meter can be calibrated.
    state = await calibrate_meter(hass, fuel_burned_entity_id, 0.5)
    assert state.state == "0.5"

    # Test that meter can be reset.
    state = await reset_meter(hass, fuel_burned_entity_id)
    assert state.state == "0.0"


@pytest.mark.usefixtures("ecomax_860p3_o")
async def test_ash_pan_full_sensor(
    hass: HomeAssistant,
    connection: EcomaxConnection,
    config_entry: MockConfigEntry,
    setup_integration,
) -> None:
    """Test ash pan sensor for ecoMAX 860P3-O."""
    await setup_integration(hass, config_entry)
    ash_pan_full_entity_id = "sensor.ecomax_ash_pan_full"
    ash_pan_full_key = 227

    # Check entry.
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(ash_pan_full_entity_id)
    assert entry
    assert entry.translation_key == "ash_pan_full"

    # Get initial value.
    state = hass.states.get(ash_pan_full_entity_id)
    assert state.state == "49"
    assert state.attributes[ATTR_FRIENDLY_NAME] == "ecoMAX Ash pan full"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_ICON] == "mdi:tray-alert"

    # Dispatch new value.
    await connection.device.regdata.dispatch(ash_pan_full_key, 55)
    state = hass.states.get(ash_pan_full_entity_id)
    assert state.state == "55"
