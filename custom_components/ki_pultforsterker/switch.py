"""Strømbryter (relé) for forsterkerkortet."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    add([KiAmpPowerSwitch(c), KiAmpLoudnessSwitch(c), KiAmpVoiceSwitch(c)])


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


class KiAmpLoudnessSwitch(KiAmpEntity, SwitchEntity):
    """Loudness (bass-/diskantløft ved lavt volum) for AirPlay/BT/USB."""
    _attr_translation_key = "loudness"
    _attr_icon = "mdi:equalizer"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "loudness")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("loudness"))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_loudness(on=True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_loudness(on=False))


class KiAmpVoiceSwitch(KiAmpEntity, SwitchEntity):
    """Talemeldinger fra forsterkeren: Bluetooth-paring, tilkoblet/frakoblet, kildebytte."""
    _attr_translation_key = "voice"
    _attr_icon = "mdi:account-voice"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "voice")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("voice", True))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_voice(True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_voice(False))
