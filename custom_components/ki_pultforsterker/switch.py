"""Strømbryter (relé) for forsterkerkortet."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, is_node
from .entity import KiAmpEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    ents = [KiAmpPowerSwitch(c), KiAmpLoudnessSwitch(c), KiAmpVoiceSwitch(c), KiAmpAutoInputSwitch(c), KiAmpMixSwitch(c)]
    if not is_node(c.data):   # ingen hodetelefonjack på Node
        ents.append(KiAmpHpAutomuteSwitch(c))
    add(ents)


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


class KiAmpAutoInputSwitch(KiAmpEntity, SwitchEntity):
    """Bytt kilde automatisk når AirPlay, Bluetooth eller Radio begynner å spille (den andre settes på pause)."""
    _attr_translation_key = "auto_input"
    _attr_icon = "mdi:swap-horizontal-circle"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "auto_input")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("auto_input", True))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_auto_input(True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_auto_input(False))


class KiAmpMixSwitch(KiAmpEntity, SwitchEntity):
    """Miks digitale kilder: AirPlay, Bluetooth, USB og Radio kan spille samtidig (AUX er alltid alene)."""
    _attr_translation_key = "mix"
    _attr_icon = "mdi:call-merge"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mix")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("mix", False))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_mix(True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_mix(False))


class KiAmpHpAutomuteSwitch(KiAmpEntity, SwitchEntity):
    """Auto-demping: høyttalerne (TPA3116) dempes når hodetelefoner er plugget i front-jacken."""
    _attr_translation_key = "hp_automute"
    _attr_icon = "mdi:headphones-settings"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "hp_automute")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("hp_automute", True))

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_hp_automute(True))

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_updated_data(await self.coordinator.api.set_hp_automute(False))
