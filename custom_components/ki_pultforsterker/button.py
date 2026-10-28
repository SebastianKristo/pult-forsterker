"""Knapp: start Bluetooth-parring."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([KiAmpPairButton(hass.data[DOMAIN][entry.entry_id])])


class KiAmpPairButton(KiAmpEntity, ButtonEntity):
    _attr_translation_key = "bt_pair"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, c) -> None:
        super().__init__(c, "bt_pair")

    async def async_press(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_bt_pairing(True))
