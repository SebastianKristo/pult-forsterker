"""Tynn HTTP-klient mot ki_amp_daemon.py på Pi-en."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class KiAmpError(Exception):
    """Forsterkeren svarte ikke."""


class KiAmpApi:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self._base = f"http://{host}:{port}/api"

    async def _req(self, method: str, path: str, json: dict | None = None) -> dict[str, Any]:
        try:
            async with asyncio.timeout(5):
                async with self._session.request(method, f"{self._base}{path}", json=json) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise KiAmpError(str(err)) from err

    @property
    def base(self) -> str:
        return self._base

    async def status(self) -> dict[str, Any]:
        return await self._req("GET", "/status")

    async def set_power(self, on: bool) -> dict[str, Any]:
        return await self._req("POST", "/power", {"on": on})

    async def set_input(self, inp: str) -> dict[str, Any]:
        return await self._req("POST", "/input", {"input": inp})

    async def set_volume(self, volume: int) -> dict[str, Any]:
        return await self._req("POST", "/volume", {"volume": volume})

    async def set_mute(self, mute: bool) -> dict[str, Any]:
        return await self._req("POST", "/mute", {"mute": mute})

    async def set_bt_pairing(self, on: bool = True) -> dict[str, Any]:
        return await self._req("POST", "/bt", {"pairing": on})

    async def set_loudness(self, on: bool | None = None, level: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if on is not None:
            body["on"] = on
        if level is not None:
            body["level"] = level
        return await self._req("POST", "/loudness", body)

    async def transport(self, action: str) -> dict[str, Any]:
        """play | pause | playpause | next | previous | stop (AirPlay/Bluetooth)."""
        return await self._req("POST", "/transport", {"action": action})

    async def set_auto_input(self, on: bool) -> dict[str, Any]:
        """Automatisk kildebytte når AirPlay/Bluetooth/Radio begynner å spille."""
        return await self._req("POST", "/auto_input", {"on": on})

    async def set_voice_profile(self, profile: str) -> dict[str, Any]:
        """Stemmeprofil for talemeldingene: en | no | trondersk."""
        return await self._req("POST", "/voice", {"profile": profile})

    async def set_usb_pc(self, pc: int) -> dict[str, Any]:
        """USB-delingsswitch: velg PC 1 eller 2 (tastatur, mus, disk og USB-lyd følger med)."""
        return await self._req("POST", "/usbsw", {"pc": pc})

    async def set_level(self, source: str, level: int) -> dict[str, Any]:
        """Nivå per kilde (0–100) i miksen."""
        return await self._req("POST", "/level", {"source": source, "level": level})

    async def set_mix(self, on: bool) -> dict[str, Any]:
        """Miks digitale kilder (AirPlay, Bluetooth, USB og Radio spiller samtidig)."""
        return await self._req("POST", "/mix", {"on": on})

    async def set_voice(self, on: bool) -> dict[str, Any]:
        """Talemeldinger («Bluetooth-paring …») av/på."""
        return await self._req("POST", "/voice", {"on": on})

    async def play_preset(self, n: int) -> dict[str, Any]:
        """Spill radiokanal 1–6 (Lyrion)."""
        return await self._req("POST", "/preset", {"n": n})

    async def save_preset(self, n: int) -> dict[str, Any]:
        """Lagre radiokanalen som spiller nå som kanal n."""
        return await self._req("POST", "/preset", {"n": n, "save": True})
