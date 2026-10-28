"""Velg radiokanal (Lyrion-favoritt 1–6)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpPresetSelect(hass.data[DOMAIN][entry.entry_id])])


class KiAmpPresetSelect(KiAmpEntity, SelectEntity):
    _attr_translation_key = "preset"
    _attr_icon = "mdi:radio"

    def __init__(self, c) -> None:
        super().__init__(c, "preset")

    def _labels(self) -> list[tuple[int, str]]:
        return [(p["n"], f"{p['n']}. {p['title']}") for p in self.coordinator.data.get("presets") or [] if p.get("title")]

    @property
    def options(self) -> list[str]:
        return [label for _, label in self._labels()] or ["Ingen kanaler"]

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data.get("input") != "radio":
            return None
        act = self.coordinator.data.get("preset")
        return next((label for n, label in self._labels() if n == act), None)

    async def async_select_option(self, option: str) -> None:
        n = next((n for n, label in self._labels() if label == option), None)
        if n:
            self.coordinator.async_set_updated_data(await self.coordinator.api.play_preset(n))
