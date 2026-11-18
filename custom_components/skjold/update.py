"""Fastvareoppdatering for Skjold-enheter med ESPHome (Skjold Sensor): ny fastvare fra skjold-lab.com."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .accessories import entities as accessories
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(accessories(hass.data[DOMAIN][entry.entry_id], "update"))
