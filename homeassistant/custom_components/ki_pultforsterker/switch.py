"""Strømbryter (relé) for forsterkerkortet."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpPowerSwitch(hass.data[DOMAIN][entry.entry_id])])


class KiAmpPowerSwitch(KiAmpEntity, SwitchEntity):
    _attr_translation_key = "power"
    _attr_icon = "mdi:amplifier"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("power"))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_power(True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_power(False))
