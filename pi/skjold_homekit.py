"""Skjold som HomeKit-tilbehør (TV-typen) med HAP-python.

Tilbehøret er ikke MFi-sertifisert: Hjem-appen viser «Ikke-sertifisert tilbehør», og man trykker «Legg til likevel».
Kildene (AirPlay, Blåtann, Radio, AUX, USB …) og radiofavorittene vises som innganger på «TV-en», volum og demping
styres via TelevisionSpeaker (iPhone-fjernkontrollen og volumknappene), og av/på følger Skjold.

Modulen kjenner ikke daemonen: den får en «bro» med funksjoner (state, set_power, set_input, play_preset,
set_volume, set_mute, transport) slik at den kan testes uten maskinvare og uten pyhap.
"""
from __future__ import annotations

import os
import random
import threading

try:   # valgfri avhengighet
    from pyhap.accessory import Accessory
    from pyhap.accessory_driver import AccessoryDriver
    from pyhap.const import CATEGORY_TELEVISION
    HAP_OK = True
except Exception:   # pragma: no cover - avhengig av installasjon
    Accessory = AccessoryDriver = None
    CATEGORY_TELEVISION = 31
    HAP_OK = False

INPUT_LABEL = {"airplay": "AirPlay", "bt": "Blåtann", "radio": "Radio", "aux": "AUX 1", "aux2": "AUX 2",
               "usb": "USB", "spotify": "Spotify", "plex": "Plex", "upnp": "UPnP/DLNA"}
PRESET_BASE = 100          # Identifier for radiofavoritt n = 100 + n
MAX_PRESETS = 12           # HomeKit liker ikke for mange innganger

# RemoteKey (HAP): 4 pil opp, 5 pil ned, 6 venstre, 7 høyre, 8 velg, 9 tilbake, 11 spill/pause, 15 info
REMOTE = {4: ("volume", +5), 5: ("volume", -5), 6: ("transport", "previous"), 7: ("transport", "next"),
          8: ("transport", "playpause"), 11: ("transport", "playpause")}


def gen_pin() -> str:
    """HomeKit-pin på formen 123-45-678, uten de enkle kodene Apple avviser."""
    bad = {"000-00-000", "111-11-111", "222-22-222", "333-33-333", "444-44-444", "555-55-555", "666-66-666",
           "777-77-777", "888-88-888", "999-99-999", "123-45-678", "876-54-321"}
    while True:
        d = "".join(random.SystemRandom().choice("0123456789") for _ in range(8))
        p = f"{d[:3]}-{d[3:5]}-{d[5:]}"
        if p not in bad:
            return p


def xhm_uri(pin: str, setup_id: str, category: int = CATEGORY_TELEVISION) -> str:
    """X-HM://-adressen Hjem-appen leser fra QR-koden (samme som pyhap sin, uten base36-pakken)."""
    payload = ((((0 << 4 | 0) << 8 | (category & 0xFF)) << 4 | 2) << 27) | (int(pin.replace("-", "")) & 0x7FFFFFFF)
    digits, out = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", ""
    while payload:
        payload, r = divmod(payload, 36)
        out = digits[r] + out
    return "X-HM://" + out.rjust(9, "0") + (setup_id or "")


def sources(inputs, presets):
    """[(identifier, navn, type)] – type 'input' eller 'preset'. presets: liste med titler (None for tomme plasser)."""
    out = [(i + 1, INPUT_LABEL.get(k, k), "input", k) for i, k in enumerate(inputs)]
    n = 0
    for i, title in enumerate(presets or []):
        if title and n < MAX_PRESETS:
            out.append((PRESET_BASE + i + 1, str(title)[:64], "preset", i + 1)); n += 1
    return out


def active_id(inputs, st) -> int:
    """Hvilken inngang som er aktiv: radiofavoritten når radio spiller en favoritt, ellers kilden."""
    inp = st.get("input")
    if inp == "radio" and st.get("preset"):
        return PRESET_BASE + int(st["preset"])
    return inputs.index(inp) + 1 if inp in inputs else 1


def apply_identifier(bridge, inputs, ident: int):
    if ident > PRESET_BASE:
        bridge["play_preset"](ident - PRESET_BASE)
    elif 1 <= ident <= len(inputs):
        bridge["set_input"](inputs[ident - 1])


def apply_remote(bridge, key: int):
    act = REMOTE.get(int(key))
    if not act:
        return None
    if act[0] == "volume":
        st = bridge["state"]()
        bridge["set_volume"](max(0, min(100, int(st.get("volume", 0)) + act[1])))
    else:
        bridge["transport"](act[1])
    return act


class SkjoldHomeKit:
    def __init__(self, bridge, name="Skjold", port=51826, persist="/var/lib/ki-amp/homekit.state",
                 pin_file="/var/lib/ki-amp/homekit.pin", inputs=None, mac=None):
        self.b, self.name, self.port, self.persist, self.pin_file = bridge, name, int(port), persist, pin_file
        self.inputs = list(inputs or ["radio", "airplay", "bt"])
        self.mac = mac
        self.driver = None
        self.acc = None
        self.thread = None
        self.err = "" if HAP_OK else "HAP-python mangler (kjør pi/update.sh)"
        self._chars = {}

    # --- pin og status ---
    def pin(self) -> str:
        try:
            with open(self.pin_file) as fh:
                p = fh.read().strip()
            if len(p) == 10:
                return p
        except OSError:
            pass
        p = gen_pin()
        try:
            os.makedirs(os.path.dirname(self.pin_file), exist_ok=True)
            with open(self.pin_file, "w") as fh:
                fh.write(p)
        except OSError:
            pass
        return p

    def info(self) -> dict:
        paired = bool(self.driver and self.driver.state and self.driver.state.paired)
        uri = ""
        try:
            if self.driver is not None and self.driver.state:
                uri = xhm_uri(self.pin(), self.driver.state.setup_id)
        except Exception:
            uri = ""
        return {"available": HAP_OK, "running": bool(self.thread and self.thread.is_alive()), "paired": paired,
                "pin": self.pin(), "setup_uri": uri, "port": self.port, "name": self.name, "error": self.err or None}

    # --- start/stopp ---
    def start(self):
        if not HAP_OK or (self.thread and self.thread.is_alive()):
            return
        self.err = ""
        self.thread = threading.Thread(target=self._run, name="homekit", daemon=True)
        self.thread.start()

    def stop(self):
        d = self.driver
        if d is not None:
            try:
                d.loop.call_soon_threadsafe(d.loop.create_task, d.async_stop())
            except Exception:
                pass
        if self.thread:
            self.thread.join(timeout=8)
        self.thread = None
        self.driver = None
        self.acc = None

    def reset(self):
        """Glem alle paringer (ny persist-fil); pin-koden beholdes."""
        running = bool(self.thread and self.thread.is_alive())
        self.stop()
        try:
            os.remove(self.persist)
        except OSError:
            pass
        if running:
            self.start()

    def _run(self):
        import asyncio
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            os.makedirs(os.path.dirname(self.persist), exist_ok=True)
            kw = {"port": self.port, "persist_file": self.persist, "pincode": self.pin().encode()}
            if self.mac:
                kw["mac"] = self.mac
            self.driver = AccessoryDriver(**kw)
            self.acc = self._build(self.driver)
            self.driver.add_accessory(accessory=self.acc)
            self.driver.start()
        except Exception as e:   # pragma: no cover - avhengig av nett/maskin
            self.err = f"HomeKit stoppet: {e}"
            print(self.err, flush=True)

    # --- tilbehøret ---
    def _build(self, driver):
        st = self.b["state"]()
        acc = Accessory(driver, self.name[:64] or "Skjold")
        acc.category = CATEGORY_TELEVISION
        acc.set_info_service(firmware_revision=str(st.get("version", "2.0")), manufacturer="Skjold",
                             model=str(st.get("product", "Skjold")), serial_number=str(st.get("id", "skjold"))[:64])
        tv = acc.add_preload_service("Television", ["RemoteKey", "SleepDiscoveryMode"])
        c = self._chars
        c["active"] = tv.configure_char("Active", value=1 if st.get("power") else 0, setter_callback=self._set_active)
        c["ident"] = tv.configure_char("ActiveIdentifier", value=active_id(self.inputs, st), setter_callback=self._set_ident)
        tv.configure_char("ConfiguredName", value=self.name[:64] or "Skjold")
        tv.configure_char("SleepDiscoveryMode", value=1)
        tv.configure_char("RemoteKey", setter_callback=self._remote)
        for ident, label, kind, _ref in sources(self.inputs, [p.get("title") if p else None for p in (st.get("presets_full") or [])]):
            src = acc.add_preload_service("InputSource", ["Name", "Identifier"])
            src.configure_char("Name", value=label)
            src.configure_char("ConfiguredName", value=label)
            src.configure_char("Identifier", value=ident)
            # InputSourceType: 0 OTHER, 2 TUNER (radio), 3 HDMI, 10 APPLICATION; IsConfigured 1; synlig 0
            src.configure_char("InputSourceType", value=2 if kind == "preset" else (10 if ident == 1 else 0))
            src.configure_char("IsConfigured", value=1)
            src.configure_char("CurrentVisibilityState", value=0)
            tv.add_linked_service(src)
        sp = acc.add_preload_service("TelevisionSpeaker", ["Active", "VolumeControlType", "VolumeSelector", "Volume"])
        sp.configure_char("Active", value=1)
        sp.configure_char("VolumeControlType", value=3)   # 3 = ABSOLUTE
        c["mute"] = sp.configure_char("Mute", value=bool(st.get("mute")), setter_callback=lambda v: self.b["set_mute"](bool(v)))
        c["volume"] = sp.configure_char("Volume", value=int(st.get("volume", 0)), setter_callback=lambda v: self.b["set_volume"](int(v)))
        sp.configure_char("VolumeSelector", setter_callback=self._vol_sel)
        tv.add_linked_service(sp)
        return acc

    def _set_active(self, v):
        self.b["set_power"](bool(v))

    def _set_ident(self, v):
        apply_identifier(self.b, self.inputs, int(v))

    def _remote(self, v):
        apply_remote(self.b, int(v))

    def _vol_sel(self, v):   # 0 = opp, 1 = ned
        st = self.b["state"]()
        self.b["set_volume"](max(0, min(100, int(st.get("volume", 0)) + (5 if int(v) == 0 else -5))))

    def sync(self):
        """Kalles fra daemonens changed(): oppdater verdiene Hjem-appen ser."""
        d, c = self.driver, self._chars
        if d is None or not c:
            return
        st = self.b["state"]()
        vals = {"active": 1 if st.get("power") else 0, "ident": active_id(self.inputs, st),
                "mute": bool(st.get("mute")), "volume": int(st.get("volume", 0))}

        def upd():
            for k, v in vals.items():
                ch = c.get(k)
                if ch is not None and ch.value != v:
                    ch.set_value(v)
        try:
            d.loop.call_soon_threadsafe(upd)
        except Exception:
            pass
