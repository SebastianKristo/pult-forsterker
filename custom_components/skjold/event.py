"""Power-knappen på Skjold S1 som event-entitet: single_press, double_press og long_press.

Daemonen setter status["last_event"] = {name: "power_<type>", seq, …} ved hvert trykk; entiteten avfyrer når seq endres."""
from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, product
from .entity import KiAmpEntity
from .devices import ACCESSORY_MODELS, stav_devices

EVENT_TYPES = ["single_press", "double_press", "long_press"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    c = hass.data[DOMAIN][entry.entry_id]
    ents: list = []
    if product(c.data) == "s1":
        ents.append(KiAmpPowerEvent(c))
    ents += [StavKeyEvent(c, h) for h in stav_devices(c.extras.get("stav"))]
    if ents:
        add(ents)


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


STAV_TYPES = ["kort", "lang", "dobbel"]


class StavKeyEvent(CoordinatorEntity, EventEntity):
    """Tastene på Skjold Stav: kort, lang eller dobbelt trykk, med tasten i «knapp» (ok, vol_opp, spill_pause …).
    Avfyrer også hendelsen skjold_stav_tast {enhet, navn, knapp, type} på HA-bussen, for automasjoner."""
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = STAV_TYPES
    _attr_icon = "mdi:remote-tv"
    _attr_translation_key = "stav_key"

    def __init__(self, c, h) -> None:
        super().__init__(c)
        uid = c.entry.unique_id or c.entry.entry_id
        self._dev = h["id"]
        self._attr_unique_id = f"{uid}_stav_{h['id']}_event"
        self._attr_name = "Tast"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{uid}_stav_{h['id']}")}, name=h["name"],
                                            manufacturer=MANUFACTURER, model=ACCESSORY_MODELS["stav"], via_device=(DOMAIN, uid))
        self._seq = ((c.data or {}).get("stav_event") or {}).get("seq")

    @callback
    def _handle_coordinator_update(self) -> None:
        ev = (self.coordinator.data or {}).get("stav_event") or {}
        seq = ev.get("seq")
        if seq is not None and seq != self._seq:
            self._seq = seq
            if str(ev.get("enhet") or "") == self._dev:
                typ = ev.get("type") if ev.get("type") in STAV_TYPES else "kort"
                data = {"knapp": ev.get("knapp"), "enhet": self._dev, "navn": ev.get("navn")}
                self._trigger_event(typ, data)
                self.hass.bus.async_fire("skjold_stav_tast", {**data, "type": typ})
        super()._handle_coordinator_update()
