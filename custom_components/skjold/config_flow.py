"""Oppsett: automatisk via mDNS (zeroconf) eller manuelt med IP-adresse og port."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import KiAmpApi, KiAmpError
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, PRODUCT_MODELS, product


def unique_id_from_status(st: dict, fallback: str) -> str:
    """Samme id som mDNS-TXT «id» (vertsnavnet), så manuell og automatisk oppdagelse gir samme enhet."""
    for key in ("id", "serial", "mac"):
        if st.get(key):
            return str(st[key])
    return fallback


def entry_title(st: dict) -> str:
    return st.get("name") or PRODUCT_MODELS[product(st)]


class KiAmpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._name: str = "Skjold"

    async def _probe(self, host: str, port: int) -> dict[str, Any]:
        api = KiAmpApi(async_get_clientsession(self.hass), host, port)
        st = await api.status()
        if not isinstance(st, dict) or "power" not in st:
            raise KiAmpError("ikke en Skjold-enhet")
        return st

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> config_entries.ConfigFlowResult:
        self._host = str(discovery_info.host)
        self._port = discovery_info.port or DEFAULT_PORT
        props = discovery_info.properties or {}
        self._name = props.get("name") or PRODUCT_MODELS.get(props.get("product"), self._name)
        await self.async_set_unique_id(props.get("id") or self._host)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            try:
                st = await self._probe(self._host, self._port)
            except KiAmpError:
                return self.async_abort(reason="cannot_connect")
            return self.async_create_entry(title=entry_title(st), data={CONF_HOST: self._host, CONF_PORT: self._port})
        return self.async_show_form(step_id="confirm", description_placeholders={"name": self._name, "host": self._host})

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        """Lagt til fra «Legg til integrasjon»: enheter funnet med mDNS dukker opp av seg selv – her skrives IP inn."""
        return await self.async_step_manual(user_input)

    async def async_step_manual(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT) or DEFAULT_PORT)
            try:
                st = await self._probe(host, port)
            except KiAmpError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(unique_id_from_status(st, host))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
                return self.async_create_entry(title=entry_title(st), data={CONF_HOST: host, CONF_PORT: port})
        defaults = user_input or {}
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })
        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)
