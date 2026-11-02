"""Felles entitetsbase."""
from __future__ import annotations

import json
import os

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KiAmpCoordinator
from .const import DOMAIN, MANUFACTURER, PRODUCT_MODELS, product


def _load_names() -> dict[str, dict]:
    """Entitetsnavn fra translations/*.json, lest ved import (ikke i hendelsesløkka)."""
    out: dict[str, dict] = {}
    d = os.path.join(os.path.dirname(__file__), "translations")
    for f in ("en", "nb"):
        try:
            with open(os.path.join(d, f + ".json"), encoding="utf-8") as fh:
                out[f] = json.load(fh).get("entity", {})
        except (OSError, ValueError):
            out[f] = {}
    return out


_NAMES = _load_names()


class KiAmpEntity(CoordinatorEntity[KiAmpCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KiAmpCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        uid = coordinator.entry.unique_id or coordinator.entry.entry_id
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=coordinator.data.get("name") or PRODUCT_MODELS[product(coordinator.data)],
            manufacturer=MANUFACTURER,
            model=PRODUCT_MODELS[product(coordinator.data)],
            hw_version=coordinator.data.get("board") or None,
            sw_version=coordinator.data.get("version"),
            configuration_url=f"http://{coordinator.entry.data['host']}:{coordinator.entry.data['port']}/api/status",
        )

    @property
    def name(self):
        """Som Home Assistant, men med navnet fra oversettelsene også når HA ikke har lastet dem (ellers viser
        alle entitetene bare enhetsnavnet, «Skjold Node»)."""
        if "_attr_name" in self.__dict__ or "_attr_name" in type(self).__dict__:
            return super().name
        key = getattr(self, "_attr_translation_key", None)
        if not key:
            return super().name
        plat = type(self).__module__.rsplit(".", 1)[-1]
        lang = "nb" if str(getattr(getattr(self.hass, "config", None), "language", "") or "").startswith(("nb", "no", "nn")) else "en"
        for lg in (lang, "en"):
            n = _NAMES.get(lg, {}).get(plat, {}).get(key, {}).get("name")
            if n:
                return n
        return super().name
