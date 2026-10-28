"""Felles entitetsbase."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KiAmpCoordinator
from .const import DOMAIN


class KiAmpEntity(CoordinatorEntity[KiAmpCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KiAmpCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        uid = coordinator.entry.unique_id or coordinator.entry.entry_id
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name="Pultforsterker",
            manufacturer="Sebastian / KI",
            model="TPA3116D2 + Pi Zero 2 W",
            sw_version=coordinator.data.get("version"),
            configuration_url=f"http://{coordinator.entry.data['host']}:{coordinator.entry.data['port']}/api/status",
        )
