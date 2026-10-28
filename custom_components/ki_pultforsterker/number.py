"""Loudness-styrke 0–10."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpLoudnessLevel(hass.data[DOMAIN][entry.entry_id])])


class KiAmpLoudnessLevel(KiAmpEntity, NumberEntity):
    _attr_translation_key = "loudness_level"
    _attr_icon = "mdi:tune-vertical"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "dB"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "loudness_level")

    @property
    def native_value(self) -> float | None:
        v = self.coordinator.data.get("loudness_level")
        return None if v is None else float(v)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_loudness(level=int(value)))
