"""Constants for Plum ecoMAX test suite."""

from pyplumio.helpers.product_info import ProductType

from custom_components.plum_ecomax.const import (
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
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
)

# Config entry data for TCP connection.
MOCK_CONFIG_DATA = {
    CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
    CONF_DEVICE: "/dev/ttyUSB0",
    CONF_HOST: "example.com",
    CONF_PORT: 8899,
}

# Config entry data for serial connection.
MOCK_CONFIG_DATA_SERIAL = {
    CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
    CONF_DEVICE: "/dev/ttyUSB0",
    CONF_PORT: 8899,
}

# Device data that added on entry create.
MOCK_DEVICE_DATA = {
    CONF_UID: "D251PAKR3GCPZ1K8G05G0",
    CONF_MODEL: "ecoMAX 123A",
    CONF_SOFTWARE: "1.13.5.A1",
    CONF_PRODUCT_TYPE: ProductType.ECOMAX_P,
    CONF_SUB_DEVICES: [ATTR_MIXERS],
}

# Mock config entry data.
MOCK_CONFIG = dict(MOCK_CONFIG_DATA, **MOCK_DEVICE_DATA)
