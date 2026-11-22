"""Contains base entity classes."""

from collections.abc import Callable, Generator, Iterable
from contextlib import suppress
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Final, Literal, NewType, cast, final, overload, override

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    device_registry as dr,
    entity_platform,
    entity_registry as er,
)
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyplumio.const import ProductType
from pyplumio.devices import Device
from pyplumio.devices.mixer import Mixer
from pyplumio.devices.thermostat import Thermostat
from pyplumio.filters import Filter, on_change, throttle
from pyplumio.helpers.event_manager import UnsubscribeFunc
from pyplumio.structures.sensor_data import ConnectedModules

from custom_components.plum_ecomax import PlumEcomaxConfigEntry

from .connection import EcomaxConnection
from .const import (
    ATTR_ENTITIES,
    ATTR_MIXERS,
    ATTR_REGDATA,
    ATTR_THERMOSTATS,
    CONF_CONNECTION_TYPE,
    CONF_HOST,
    CONF_SOURCE_DEVICE,
    CONF_STEP,
    CONF_UPDATE_INTERVAL,
    CONNECTION_TYPE_TCP,
    DOMAIN,
    LOGICAL_DEVICES,
    MANUFACTURER,
    DeviceType,
    ModuleType,
)

ALL: Final = "all"

UndefinedType = NewType("UndefinedType", object)
Undefined = UndefinedType(object())


@dataclass(frozen=True, kw_only=True)
class EcomaxEntityDescription(EntityDescription):
    """Describes an ecoMAX entity."""

    always_available: bool = False
    filter_fn: Callable[[Any], Filter] = on_change
    module: ModuleType = ModuleType.A
    product_types: set[ProductType] | Literal["all"] = ALL


@callback
def async_get_by_product_type[DescriptorT: EcomaxEntityDescription](
    product_type: ProductType, descriptions: Iterable[DescriptorT]
) -> Generator[DescriptorT]:
    """Filter descriptions by the product type."""
    for description in descriptions:
        product_types = description.product_types
        if product_types == ALL or product_type in product_types:
            yield description


@callback
def async_get_by_modules[DescriptorT: EcomaxEntityDescription](
    connected_modules: ConnectedModules, descriptions: Iterable[DescriptorT]
) -> Generator[DescriptorT]:
    """Filter descriptions by connected modules."""
    for description in descriptions:
        if getattr(connected_modules, description.module, None) is not None:
            yield description


@callback
def async_make_description_for_custom_entity[DescriptorT: EcomaxEntityDescription](
    description_factory: Callable[..., DescriptorT], entity: dict[str, Any]
) -> DescriptorT:
    """Make description from partial and entity data."""

    @callback
    def filter_wrapper(update_interval: int) -> Callable[..., Any]:
        """Return a filter function based on the update interval."""

        def filter_fn[CallableT: Callable[..., Any]](
            x: CallableT,
        ) -> Filter | CallableT:
            """Return a filter function."""
            return throttle(x, seconds=update_interval) if update_interval > 0 else x

        return filter_fn

    data = {**entity}

    if step := data.get(CONF_STEP, None):
        data["native_step"] = step
        del data[CONF_STEP]

    if unit_of_measurement := data.get(CONF_UNIT_OF_MEASUREMENT, None):
        data["native_unit_of_measurement"] = unit_of_measurement
        del data[CONF_UNIT_OF_MEASUREMENT]

    if update_interval := data.get(CONF_UPDATE_INTERVAL, None):
        data["filter_fn"] = filter_wrapper(update_interval)
        del data[CONF_UPDATE_INTERVAL]

    del data[CONF_SOURCE_DEVICE]
    return description_factory(**data)


@overload
def async_get_custom_entities[DescriptorT: EcomaxEntityDescription](
    platform: Platform,
    config_entry: PlumEcomaxConfigEntry,
    source_device: Literal[DeviceType.MIXER, DeviceType.THERMOSTAT],
    description_factory: Callable[..., DescriptorT],
) -> Generator[tuple[DescriptorT, int]]: ...


@overload
def async_get_custom_entities[DescriptorT: EcomaxEntityDescription](
    platform: Platform,
    config_entry: PlumEcomaxConfigEntry,
    source_device: Literal[DeviceType.ECOMAX, "regdata"],
    description_factory: Callable[..., DescriptorT],
) -> Generator[DescriptorT]: ...


@callback
def async_get_custom_entities[DescriptorT: EcomaxEntityDescription](
    platform: Platform,
    config_entry: PlumEcomaxConfigEntry,
    source_device: DeviceType | Literal["regdata"],
    description_factory: Callable[..., DescriptorT],
) -> Generator[tuple[DescriptorT, int] | DescriptorT]:
    """Return a list of custom entities."""
    entities: dict[str, Any] = config_entry.options.get(ATTR_ENTITIES, {})
    target_platform = str(platform)
    if not entities or target_platform not in entities:
        return

    index = 0
    for entity in entities[target_platform].values():
        entity_source = entity[CONF_SOURCE_DEVICE]
        if entity_source.startswith(LOGICAL_DEVICES):
            entity_source, index = entity[CONF_SOURCE_DEVICE].split("_", 1)

        if entity_source == source_device:
            description = async_make_description_for_custom_entity(
                description_factory, entity
            )
            yield description if index == 0 else (description, int(index))


class EcomaxEntity(Entity):
    """Represents an ecoMAX entity."""

    _attr_available = False
    _attr_has_entity_name = True
    _attr_should_poll = False
    connection: EcomaxConnection
    entity_description: EcomaxEntityDescription

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxEntityDescription
    ) -> None:
        """Initialize a new ecoMAX entity."""
        self.connection = connection
        self.entity_description = description

    @override
    async def async_added_to_hass(self) -> None:
        """Subscribe to events."""
        key = self._event_key
        async_update = self.entity_description.filter_fn(self.async_update)

        if (value := self.device.data.get(key, Undefined)) is not Undefined:
            await self._async_set_available(value)
            await async_update(value)

        self._subscribe_availability(key)
        self.async_on_remove(self.device.subscribe(key, async_update))

    @callback
    def _subscribe_availability(self, key: str) -> None:
        """Subscribe to availability updates."""
        if not self._attr_available:
            self.async_on_remove(
                self.device.subscribe_once(key, self._async_set_available)
            )

    async def _async_set_available(self, value: Any = None) -> None:
        """Mark entity as available."""
        self._attr_available = True

    @property
    def _event_key(self) -> str:
        """Return the device event key to subscribe to."""
        return self.entity_description.key

    @property
    @override
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity_description.always_available:
            return True

        return self.connection.connected.is_set() and self._attr_available

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.connection.uid}-{self.entity_description.key}"

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            configuration_url=(
                f"http://{self.connection.entry.data[CONF_HOST]}"
                if self.connection.entry.data[CONF_CONNECTION_TYPE]
                == CONNECTION_TYPE_TCP
                else None
            ),
            identifiers={(DOMAIN, self.connection.uid)},
            manufacturer=MANUFACTURER,
            model=self.connection.model,
            name=self.connection.name,
            serial_number=self.connection.uid,
            sw_version=self.connection.software[ModuleType.A],
        )

    @cached_property
    def device(self) -> Device:
        """Return the device handler."""
        return self.connection.device

    async def async_update(self, value: Any) -> None:
        """Update entity state."""
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class SubdeviceEntityDescription(EcomaxEntityDescription):
    """Describes an ecoMAX entity."""

    indexes: set[int] | Literal["all"] = ALL


@callback
def async_get_by_index[SubDescriptorT: SubdeviceEntityDescription](
    index: int, descriptions: Iterable[SubDescriptorT]
) -> Generator[SubDescriptorT]:
    """Filter mixer/circuit descriptions by the index."""
    index += 1
    for description in descriptions:
        if description.indexes == ALL or index in description.indexes:
            yield description


class ThermostatEntity(EcomaxEntity):
    """Represents a thermostat entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return the unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.THERMOSTAT}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key="thermostat",
            translation_placeholders={
                "device_name": self.connection.name,
                "thermostat_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.THERMOSTAT}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            sw_version=self.connection.software[ModuleType.ECOSTER],
            via_device_id=dr.async_get_device_id_by_identifier(
                self.hass,
                identifier=(DOMAIN, self.connection.uid),
                config_entry_id=self.connection.entry.entry_id,
            ),
        )

    @cached_property
    @final
    @override
    def device(self) -> Thermostat:
        """Return the mixer handler."""
        device = self.connection.device
        return cast(Thermostat, device.data[ATTR_THERMOSTATS][self.index])


class MixerEntity(EcomaxEntity):
    """Represents a mixer entity."""

    index: int

    @cached_property
    @override
    def unique_id(self) -> str:
        """Return a unique ID."""
        return (
            f"{self.connection.uid}-{DeviceType.MIXER}-"
            + f"{self.index}-{self.entity_description.key}"
        )

    @cached_property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            translation_key=(
                "circuit"
                if self.connection.product_type == ProductType.ECOMAX_I
                else "mixer"
            ),
            translation_placeholders={
                "device_name": self.connection.name,
                "mixer_number": str(self.index + 1),
            },
            identifiers={
                (DOMAIN, f"{self.connection.uid}-{DeviceType.MIXER}-{self.index}")
            },
            manufacturer=MANUFACTURER,
            via_device_id=dr.async_get_device_id_by_identifier(
                self.hass,
                identifier=(DOMAIN, self.connection.uid),
                config_entry_id=self.connection.entry.entry_id,
            ),
        )

    @cached_property
    @final
    @override
    def device(self) -> Mixer:
        """Return the mixer handler."""
        device = self.connection.device
        return cast(Mixer, device.data[ATTR_MIXERS][self.index])


class RegdataEntity(EcomaxEntity):
    """Represents a regulator data entity."""

    _regdata_key: int

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxEntityDescription
    ) -> None:
        """Initialize a new regdata entity."""
        self._regdata_key = int(description.key)
        super().__init__(connection, description)

    @callback
    @override
    def _subscribe_availability(self, key: str) -> None:
        """Subscribe to availability updates."""
        self.async_on_remove(self.device.subscribe(key, self._async_set_available))

    @override
    async def _async_set_available(self, value: Any = None) -> None:
        """Mark entity as available."""
        self._attr_available = isinstance(value, dict) and self._regdata_key in value

    @property
    @override
    def _event_key(self) -> str:
        """Return the device event key to subscribe to."""
        return ATTR_REGDATA


@callback
def _get_current_platform_domain() -> str | None:
    """Return the current entity platform domain if set."""
    with suppress(RuntimeError):
        return entity_platform.async_get_current_platform().domain

    return None


@callback
def _async_get_existing_unique_ids(
    hass: HomeAssistant,
    config_entry: PlumEcomaxConfigEntry,
    *,
    platform_domain: str | None = None,
) -> set[str]:
    """Return existing unique IDs for the current platform."""
    if platform_domain is None:
        platform_domain = _get_current_platform_domain()

    entity_registry = er.async_get(hass)
    return {
        registry_entry.unique_id
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if platform_domain is None or registry_entry.domain == platform_domain
    }


@callback
def _is_config_entry_active(config_entry: PlumEcomaxConfigEntry) -> bool:
    """Return whether the config entry can still register entities."""
    return config_entry.state in (
        ConfigEntryState.LOADED,
        ConfigEntryState.SETUP_IN_PROGRESS,
    )


@callback
def _is_entity_ready(entity: EcomaxEntity, existing_unique_ids: set[str]) -> bool:
    """Return whether an entity should be registered immediately."""
    description = entity.entity_description
    return (
        description.always_available
        or description.key in entity.device.data
        or entity.unique_id in existing_unique_ids
    )


@callback
def _subscribe_entity_registration(
    config_entry: PlumEcomaxConfigEntry,
    entity: EcomaxEntity,
    async_add_entities: AddEntitiesCallback,
) -> UnsubscribeFunc:
    """Subscribe a deferred entity to be registered on first key arrival."""

    async def _async_add_entity(_value: Any) -> None:
        """Register deferred entity once its backing key is stored."""
        if not _is_config_entry_active(config_entry):
            return

        async_add_entities([entity])

    return entity.device.subscribe_once(
        entity.entity_description.key, _async_add_entity
    )


@callback
def async_register_entities(
    hass: HomeAssistant,
    config_entry: PlumEcomaxConfigEntry,
    entities: Iterable[EcomaxEntity],
    async_add_entities: AddEntitiesCallback,
    *,
    immediate_entities: Iterable[EcomaxEntity] = (),
    platform_domain: str | None = None,
) -> None:
    """Register ready entities immediately and defer the rest until data arrives."""
    existing_unique_ids = _async_get_existing_unique_ids(
        hass, config_entry, platform_domain=platform_domain
    )
    ready_entities = list(immediate_entities)

    for entity in entities:
        if _is_entity_ready(entity, existing_unique_ids):
            ready_entities.append(entity)
        else:
            config_entry.async_on_unload(
                _subscribe_entity_registration(config_entry, entity, async_add_entities)
            )

    if ready_entities:
        async_add_entities(ready_entities)


@callback
def _filter_entities_by_index(
    entities_fn: Callable[[], Iterable[MixerEntity | ThermostatEntity]] | None,
    indexes: set[int],
) -> list[MixerEntity | ThermostatEntity]:
    """Build and filter sub-device entities for the given indexes."""
    if entities_fn is None:
        return []

    return [entity for entity in entities_fn() if entity.index in indexes]


@callback
def async_register_sub_device_entities(
    hass: HomeAssistant,
    config_entry: PlumEcomaxConfigEntry,
    connection: EcomaxConnection,
    sub_device_key: str,
    async_add_entities: AddEntitiesCallback,
    *,
    entities_fn: Callable[[], Iterable[MixerEntity | ThermostatEntity]] | None = None,
    custom_entities_fn: Callable[[], Iterable[MixerEntity | ThermostatEntity]]
    | None = None,
) -> None:
    """Register sub-device entities at setup and as new sub-devices appear."""
    platform_domain = _get_current_platform_domain()
    seen_indexes: set[int] = set()

    @callback
    def _register_new_sub_devices(sub_devices: dict[int, Device]) -> None:
        """Register entities for any newly discovered sub-device indexes."""
        new_indexes = set(sub_devices) - seen_indexes
        if not new_indexes:
            return

        seen_indexes.update(new_indexes)
        entities = _filter_entities_by_index(entities_fn, new_indexes)
        custom_entities = _filter_entities_by_index(custom_entities_fn, new_indexes)
        if not entities and not custom_entities:
            return

        async_register_entities(
            hass,
            config_entry,
            entities,
            async_add_entities,
            immediate_entities=custom_entities,
            platform_domain=platform_domain,
        )

    async def _async_on_sub_devices(sub_devices: dict[int, Device]) -> None:
        """Handle sub-device discovery events."""
        if not sub_devices or not _is_config_entry_active(config_entry):
            return

        _register_new_sub_devices(sub_devices)

    if sub_devices := connection.device.get_nowait(sub_device_key):
        _register_new_sub_devices(sub_devices)

    config_entry.async_on_unload(
        connection.device.subscribe(sub_device_key, _async_on_sub_devices)
    )
