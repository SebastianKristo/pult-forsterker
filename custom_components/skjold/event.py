"""Power-knappen på Skjold S1 som event-entitet: single_press, double_press og long_press.

Daemonen setter status["last_event"] = {name: "power_<type>", seq, …} ved hvert trykk; entiteten avfyrer når seq endres."""
from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, product
from .entity import KiAmpEntity

EVENT_TYPES = ["single_press", "double_press", "long_press"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    if product(c.data) == "s1":
        add([KiAmpPowerEvent(c)])


class KiAmpPowerEvent(KiAmpEntity, EventEntity):
    _attr_translation_key = "power_button"
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = EVENT_TYPES
    _attr_icon = "mdi:power"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "power_button")
        self._seq = (coordinator.data or {}).get("last_event", {}) or {}
        self._seq = self._seq.get("seq")

    @callback
    def _handle_coordinator_update(self) -> None:
        ev = (self.coordinator.data or {}).get("last_event") or {}
        seq = ev.get("seq")
        if seq is not None and seq != self._seq:
            self._seq = seq
            kind = str(ev.get("name", "")).removeprefix("power_")
            if kind in EVENT_TYPES:
                self._trigger_event(kind, {"src": ev.get("src"), "action": ev.get("action")})
        super()._handle_coordinator_update()
