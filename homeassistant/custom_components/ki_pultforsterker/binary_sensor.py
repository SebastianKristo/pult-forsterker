"""Spiller / spiller ikke."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpPlayingSensor(hass.data[DOMAIN][entry.entry_id])])


class KiAmpPlayingSensor(KiAmpEntity, BinarySensorEntity):
    _attr_translation_key = "playing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, c) -> None:
        super().__init__(c, "playing")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("playing"))
