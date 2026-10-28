"""Oppsett: automatisk via mDNS eller manuelt med IP."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import KiAmpApi, KiAmpError
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN


class KiAmpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._name: str = "Pultforsterker"

    async def _probe(self, host: str, port: int) -> dict[str, Any]:
        api = KiAmpApi(async_get_clientsession(self.hass), host, port)
        return await api.status()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> config_entries.ConfigFlowResult:
        self._host = str(discovery_info.host)
        self._port = discovery_info.port or DEFAULT_PORT
        props = discovery_info.properties
        self._name = props.get("name", self._name)
        await self.async_set_unique_id(props.get("id") or self._host)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            try:
                await self._probe(self._host, self._port)
            except KiAmpError:
                return self.async_abort(reason="cannot_connect")
            return self.async_create_entry(title=f"KI {self._name}", data={CONF_HOST: self._host, CONF_PORT: self._port})
        return self.async_show_form(step_id="confirm", description_placeholders={"name": self._name, "host": self._host})

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                st = await self._probe(user_input[CONF_HOST], user_input[CONF_PORT])
            except KiAmpError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(st.get("id") or user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"KI {st.get('name', 'Pultforsterker')}", data=user_input)
        schema = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_PORT, default=DEFAULT_PORT): int})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
