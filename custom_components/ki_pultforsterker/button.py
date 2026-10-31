"""Knapp: start Bluetooth-parring."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([KiAmpPairButton(c), KiAmpRebootButton(c), KiAmpPoweroffButton(c)] + [KiAmpPresetButton(c, n) for n in range(1, 7)])


class KiAmpPairButton(KiAmpEntity, ButtonEntity):
    _attr_translation_key = "bt_pair"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, c) -> None:
        super().__init__(c, "bt_pair")

    async def async_press(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_bt_pairing(True))


class KiAmpPresetButton(KiAmpEntity, ButtonEntity):
    """Radiokanal 1–6 – navnet følger stasjonen som er lagret på plassen."""
    _attr_icon = "mdi:radio"

    def __init__(self, c, n: int) -> None:
        super().__init__(c, f"preset_{n}")
        self._n = n

    @property
    def name(self) -> str:
        presets = self.coordinator.data.get("presets") or []
        title = presets[self._n - 1].get("title") if len(presets) >= self._n else ""
        return f"Radio {self._n}" + (f": {title}" if title else "")

    @property
    def available(self) -> bool:
        presets = self.coordinator.data.get("presets") or []
        return super().available and len(presets) >= self._n and bool(presets[self._n - 1].get("title"))

    async def async_press(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.play_preset(self._n))


class KiAmpRebootButton(KiAmpEntity, ButtonEntity):
    """Start Pi-en på nytt."""
    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, c) -> None:
        super().__init__(c, "reboot")

    async def async_press(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.reboot(False))


class KiAmpPoweroffButton(KiAmpEntity, ButtonEntity):
    """Slå av Pi-en (må slås på igjen med strømbryteren)."""
    _attr_translation_key = "poweroff"
    _attr_icon = "mdi:power"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, c) -> None:
        super().__init__(c, "poweroff")

    async def async_press(self) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.reboot(True))
