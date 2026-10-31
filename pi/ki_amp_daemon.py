#!/usr/bin/env python3
"""Pultforsterker v2 – daemon på Raspberry Pi Zero 2 W.

Innganger: airplay | bt | aux | usb
  airplay/bt/usb kommer alle fra Pi-ens DAC (PCM5102A); aux er 3,5 mm bak.
  Relé 1+2 (L/R) velger DAC eller AUX inn til forsterkeren.
Front: 4 inngangsknapper med LED-ring, 16 mm POWER-knapp (kort trykk = standby,
  hold 3 s = omstart), encoder (volum, trykk = mute). OLED styres av oled_display.py.
Bak: KCD1 bryter all strøm (maskinvare). Strømrelé bryter 24 V til forsterkerkortet i standby.
Volum: 2 x X9C103S (INC/UD/CS delt).
LED-ringer: 2 x 4-kanals MOSFET-kort (3,3 V-jumper), POWER-ringen dimmes med PWM i standby.
HTTP-API (port 8765) + mDNS for Home Assistant-integrasjonen og Homey-appen.

API:
  GET  /                 web-app (PWA) for mobil/PC – hele mappa serveres på / (og /app/): /usr/local/share/ki-amp/webapp
                         (skjold-web-*.zip fra siste skjold-v*-utgivelse, ellers pi/webapp; KI_AMP_WEBAPP overstyrer)
  GET  /api/status
  POST /api/power  {"on":bool}   POST /api/toggle
  POST /api/input  {"input":"airplay|bt|aux|usb"}
  POST /api/volume {"volume":0-100} | {"delta":±n}
  POST /api/loudness {"on":bool, "level":0-10}
  POST /api/mute   {"mute":bool}
  POST /api/bt     {"pairing":true}   (gjør Pi-en synlig 2 min)
  POST /api/auto_input {"on":bool} (bytt kilde automatisk når AirPlay/BT/Radio begynner å spille)
  POST /api/usbsw {"pc":1|2} | {"toggle":true} (USB-delingsswitch: hvilken PC tastatur/mus/disk/USB-lyd følger)
  POST /api/voice {"on":bool} | {"profile":"en"|"no"|"trondersk"} (stemmeprofil for talemeldingene)
  POST /api/level {"source":"airplay|bt|usb|radio|aux|aux2","level":0-100} (nivå per kilde, brukes i miks)
  POST /api/mix {"on":bool} (miks digitale kilder: AirPlay, Bluetooth, USB og Radio kan spille samtidig)
  GET/POST /api/settings  innstillingsmodellen til app/web (samme nøkler som skjold_settings.js); POST = delvis oppdatering
  POST /api/hp_automute {"on":bool} (demp høyttalerne når hodetelefoner er plugget i fronten; status har "headphones")
  POST /api/voice  {"on":bool} (talemeldinger av/på) | {"say":"bt_pairing"} (test)
  GET  /api/cover  (albumbilde fra AirPlay, jpg/png)
  POST /api/transport {"action":"play|pause|playpause|next|previous|stop"}  (AirPlay/Bluetooth/Radio)
  GET  /api/presets                       radiokanaler 1–6 (Lyrion)
  POST /api/preset  {"n":1-6}             spill kanal n  |  {"n":1-6, "save":true} lagre det som spiller nå
  POST /api/presets {"import":true}       hent de 6 første favorittene fra Lyrion | {"presets":[{title,url,icon}…]}
  POST /api/spotify {"event":"playing|paused|stopped|track_changed|session_connected|session_disconnected|volume_changed|…",
                     "name":…, "artists":…, "album":…, "covers":…, "duration_ms":…, "position_ms":…, "user_name":…}
                     Spotify Connect-hendelse fra librespot (--onevent /usr/local/bin/ki-spotify-event, se ki-spotify.service).
                     «playing» bytter kilde til spotify når auto_input er på. Status: input «spotify», "spotify": {connected, playing, …}.
  GET  /api/spotify  siste Spotify-status (samme som status["spotify"])
Radio: Squeezelite-spilleren styres gjennom Lyrion Music Servers JSON-RPC (KI_AMP_LMS_SERVER, ellers oppdaget på nettet).
Spotify Connect: librespot (fra raspotify-pakken) som ki-spotify.service, ut på ALSA-enheten «spotify» (softvol «KI Spotify» →
  dmix → loopback → CamillaDSP), som de andre kildene. Spillernavn = KI_AMP_NAME. librespot har ingen fjernstyring, så
  ◀◀/▶▶ virker ikke for Spotify (styres fra appen); pause/spill-pause og bytte bort fra Spotify starter tjenesten på nytt
  for å stoppe lyden. Volum fra Spotify-appen (volume_changed) settes som daemonvolum når Spotify er valgt.

KI_AMP_BOARD=node (Skjold Node: Pi 4/3B, lyd på 3,5 mm, 1,8" ST7735 eies av skjermprosessen):
  Pinner leses fra /etc/skjold/node_pins.json (ellers repoets skjold/node/config/node_pins.json, ellers innebygde standardverdier).
  Knapper til GND: RADIO GPIO5, AIR·BT GPIO6, ◀◀ GPIO13, ▶▶ GPIO26. Encoder A17/B27/SW22. LED-ringer GPIO12/16/20/21 (programvare-PWM).
  Daemonen rører aldri GPIO23 (bakgrunnslys) eller SPI/skjermpinnene 7/8/9/10/11/24/25. Ingen strømknapp.
  RADIO: trykk = velg radio / neste favoritt (meny), hold 1 s = spill valgt favoritt.
  AIR·BT: trykk = bytt AirPlay ↔ Bluetooth, hold 2 s = BT-paring av/på.
  ◀◀/▶▶: forrige/neste spor (neste/forrige favoritt i radio), hold begge 3 s = omstart.
  Encoder: vri = volum, trykk = spill/pause, hold 3 s = innstillingsmenyen (status["settings_menu"], og ui_event for eldre
  skjermprosesser). I menyen: vri = flytt, trykk = endre verdi (samme vei som POST /api/settings), hold 3 s / 20 s uten
  aktivitet / «Lukk» = ut. Volumet rører seg ikke mens menyen er åpen.
  Standardnavn «Skjold Node» (KI_AMP_NAME overstyrer).
Felter i /api/status for skjermen (Skjold OS):
  rebooting: true          ~1,5 s før daemonen kjører systemctl reboot/poweroff (hold ◀◀+▶▶, hold POWER, POST /api/reboot)
  hold: {"key":"knob|src|radio|reboot","p":0–1,"title":…,"sub":…}   mens en knapp holdes inne (vises etter 0,35 s), null ellers;
        etter lagret favoritt i 2,5 s: {"key":"radio","p":1,"title":"Lagret","sub":"P4 på plass 3","saved":3}
  settings_menu: {"open":true,"cat":"INNSTILLINGER","idx":0-basert,"rows":[{"k","n","icon","v"}…],"left":s} | null
  menu: radiomenyen {"open","idx"(1–6),"until"} | null
  bt_pairing_left: sekunder igjen av BT-paringen (0 når av)
  airplay_device: navnet på AirPlay-klienten (Shairport-metadata «snam» via oled_display.py), "" når ingen
  input_seq: øker for hvert knappetrykk/-slipp og encoderhakk
  POST /api/reboot {"poweroff":bool}   omstart (eller slå av) etter 1,5 s med rebooting=true
  LED-ringer: RADIO = radio, AIR·BT = AirPlay/Bluetooth/Spotify (blinker under paring), ◀◀/▶▶ = noe spiller.
  KI_AMP_NODE_BUTTONS=0 lar skjermprosessen eie knappene/encoderen (daemonen styrer da bare LED-ringene).
"""
import asyncio
import json
import math
import mimetypes
import threading
import os
import re
import socket
import subprocess
import time
import hashlib
import urllib.request

from aiohttp import web

PORT = int(os.environ.get("KI_AMP_PORT", "8765"))
VERSION = "2.0"
STATUS_FILE = "/run/pultamp_status.json"
COVER_FILE = "/run/pultamp_cover"   # albumbilde fra oled_display.py (AirPlay/BT)
COVER_RADIO = "/run/pultamp_cover_radio"   # stasjons-/albumbilde fra Lyrion
CTRL_FILE = "/run/pultamp_ctrl.json"       # til oled_display.py
STATE_FILE = "/var/lib/ki-amp/state.json"
RELAY_ACTIVE_LOW = os.environ.get("RELAY_ACTIVE_LOW", "1") == "1"
# Maks X9C-trinn (0-99) ved volum 100 %. 6 ohm / 40 W-høyttalere på 24 V: 85 holder forsterkeren under 40 W.
MAX_TAP = max(10, min(99, int(os.environ.get("KI_AMP_MAX_TAP", "85"))))
PGA_DB = max(-40, min(0, int(os.environ.get("KI_AMP_PGA_DB", "-9"))))   # hovedkortet: fast dempning i PGA2311 (dB, 0 = 2,1 Vrms inn på forsterkeren = klipping)
DSP_WS = os.environ.get("KI_AMP_DSP_WS", "ws://127.0.0.1:1234")   # CamillaDSP (loudness + digitalt volum for AirPlay/BT/USB)
DSP_CAPTURE = os.environ.get("KI_AMP_DSP_CAPTURE", "hw:Loopback,1")
DSP_PLAYBACK = os.environ.get("KI_AMP_DSP_PLAYBACK", "hw:sndrpihifiberry")
DSP_FILE = os.environ.get("KI_AMP_DSP_FILE", "/etc/camilladsp/config.yml")
DSP_FORMAT = os.environ.get("KI_AMP_DSP_FORMAT", "S32LE")   # S16LE for Pi-ens 3,5 mm-utgang (testmodus)

# ---------- GPIO (BCM) ----------
# KI_AMP_BOARD=modules : modulbygget (XH-M562, X9C103S, relékort) – standard
# KI_AMP_BOARD=main    : Pultforsterker hovedkort rev B (PGA2311 på SPI0, knapper/LED/USB-mux via MCP23017 på I2C,
#                        GPIO 27 = «smart relé» (24 V til forsterker + 5 V_SW), GPIO 22 = TPA3116 SDZ, AUX 1 = I2S-ADC, AUX 2 = USB-kodek)
BOARD = os.environ.get("KI_AMP_BOARD", "modules")
# Spillernavnet (AirPlay/Spotify/Blåtann/mDNS). Node: «Skjold Node» med mindre brukeren har satt et annet (malverdien
# «Pultforsterker» i ki-amp.env regnes som ikke satt).
NAME = os.environ.get("KI_AMP_NAME", "").strip()
if not NAME or (BOARD == "node" and NAME == "Pultforsterker"):
    NAME = "Skjold Node" if BOARD == "node" else "Pultforsterker"
PIN_RELAY_AMP = 27      # modules: relé 3 (24 V til forsterker)   main: strømrelé + 5V_SW (høy = på)
PIN_RELAY_AUX = 22      # modules: relé lav = DAC, høy = AUX       main: TPA3116 SDZ (høy = forsterker på)
PIN_X9C_INC, PIN_X9C_UD, PIN_X9C_CS = 26, 14, 15   # modules (serial console må være av)
ENC = (23, 24, 25)      # CLK, DT, SW
if BOARD == "main":
    BTN = {}            # knappene sitter på MCP23017 GPA0-4 (AIR, BT, AUX, USB, PWR)
    LED = {}            # LED-ringene på MCP23017 GPB0-3
    LED_POWER = 12      # PWM0
    PIN_DAC_XSMT = 26
    PIN_AMP_SDZ = 22
    PIN_BTN_BAK = 15    # strømknapp bak
    PIN_MCP_INT = 14
    MCP_BTN = {"airplay": 0, "bt": 1, "aux": 2, "usb": 3}; MCP_BTN_POWER = 4
    MCP_LED = {"airplay": 0, "bt": 1, "aux": 2, "usb": 3}; MCP_USB_SEL = 4
    MCP_HP_DET, MCP_HP_EN = 5, 6   # GPA5: hodetelefonjack (bryterkontakt, høy = plugget i), GPA6: EN til TPA6132A2
elif BOARD == "radio":   # Radio Retro: Pi 4 + 3,5 mm + PAM8406, 6 favoritter, SOURCE/◀◀/▶▶, EC11, POWER i toppen
    BTN = {}
    LED = {}
    LED_POWER = 23      # LED-ringen via 2N2222A
    PIN_DAC_XSMT = None
    ENC = (17, 27, 22)
    FAV_BTN = [5, 6, 13, 19, 26, 16]
    FAV_LED = [2, 4, 7, 14, 15, 24]
    RADIO_BTN = {"source": 20, "prev": 21, "next": 12}
elif BOARD == "test":   # testbenk: Pi 4 alene, lyd på 3,5 mm, knapper/LED rett på headeren (unngår I2C, SPI, UART)
    BTN = {"airplay": 5, "bt": 6, "aux": 13, "usb": 19}
    LED = {"airplay": 16, "bt": 20, "aux": 21, "usb": 12}
    LED_POWER = 23
    PIN_DAC_XSMT = None
    ENC = (17, 27, 22)
elif BOARD == "node":   # Skjold Node: pinner fra node_pins.json (se docstring)
    NODE_FORBIDDEN = {0, 1, 2, 3, 7, 8, 9, 10, 11, 14, 15, 23, 24, 25}   # HAT-EEPROM, I²C, SPI/skjerm, UART, bakgrunnslys
    NODE_DEFAULT = {"btn": {"radio": 5, "airbt": 6, "prev": 13, "next": 26},
                    "hold": {"radio": 1.0, "airbt": 2.0, "prev": 3.0, "next": 3.0},
                    "led": {"radio": 12, "airbt": 16, "prev": 20, "next": 21}, "enc": (17, 27, 22),
                    "enc_hold": 3.0, "led_hz": 200, "led_active_high": True, "bounce": 0.05}

    def _node_pins():
        cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in NODE_DEFAULT.items()}
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [os.environ.get("KI_AMP_NODE_PINS", ""), "/etc/skjold/node_pins.json",
                 os.path.join(here, "..", "skjold", "node", "config", "node_pins.json"),
                 "/opt/skjold/src/skjold/node/config/node_pins.json"]
        for path in cands:
            if not path or not os.path.isfile(path):
                continue
            try:
                with open(path) as fh:
                    pj = json.load(fh)
                for b in pj["knapper"]["liste"]:
                    cfg["btn"][b["id"]] = int(b["gpio"])
                    cfg["hold"][b["id"]] = float(b.get("hold_s", cfg["hold"].get(b["id"], 2.0)))
                for l in pj.get("leds", {}).get("liste", []):
                    cfg["led"][l["for"]] = int(l["gpio"])
                cfg["led_hz"] = int(pj.get("leds", {}).get("pwm_hz", 200))
                cfg["led_active_high"] = bool(pj.get("leds", {}).get("aktiv_hoy", True))
                e = pj["encoder"]
                cfg["enc"] = (int(e["A"]["gpio"]), int(e["B"]["gpio"]), int(e["SW"]["gpio"]))
                cfg["enc_hold"] = float(e.get("hold_innstillinger_s", 3.0))
                print(f"Node-pinner fra {os.path.normpath(path)}", flush=True)
                break
            except Exception as ex:
                print(f"Node-pinner: kunne ikke lese {path}: {ex}", flush=True)
        # aldri rør skjerm/SPI/bakgrunnslys eller andre reserverte pinner, og ingen dobbeltbruk
        used = set()
        for grp in ("btn", "led"):
            for k, p in list(cfg[grp].items()):
                if p in NODE_FORBIDDEN or p in used or p in cfg["enc"]:
                    print(f"Node-pinner: GPIO{p} ({grp}/{k}) er reservert eller i bruk – hoppes over", flush=True)
                    del cfg[grp][k]
                else:
                    used.add(p)
        if any(p in NODE_FORBIDDEN for p in cfg["enc"]):
            print(f"Node-pinner: encoder {cfg['enc']} bruker reservert pinne – bruker standard", flush=True)
            cfg["enc"] = NODE_DEFAULT["enc"]
        return cfg

    NODE = _node_pins()
    BTN = {}            # knappene settes opp i setup_buttons (egen logikk for Node)
    LED = {}            # ringene er PWMLED (node_leds)
    LED_POWER = None    # ingen strømknapp/strømring på Node
    PIN_DAC_XSMT = None
    ENC = tuple(NODE["enc"])
    NODE_BUTTONS = os.environ.get("KI_AMP_NODE_BUTTONS", "1") == "1"
else:
    BTN = {"airplay": 5, "bt": 6, "aux": 12, "usb": 13}
    LED = {"airplay": 7, "bt": 8, "aux": 9, "usb": 10}
    LED_POWER = 11      # PWM
    PIN_DAC_XSMT = None
BTN_POWER = {"radio": 3, "test": 26, "main": None}.get(BOARD, 16)   # main: POWER via MCP23017 (GPIO16 er PGA2311 CS) + knapp bak GPIO 15

SPOTIFY_ON = os.environ.get("KI_AMP_SPOTIFY", "1") == "1"   # Spotify Connect (librespot, ki-spotify.service)
if BOARD == "node":
    INPUTS = ["radio", "airplay", "bt"]
elif BOARD == "main":
    INPUTS = ["radio", "airplay", "bt", "aux", "aux2", "usb"]
else:
    INPUTS = ["radio", "airplay", "bt", "aux", "usb"]
if SPOTIFY_ON:
    INPUTS = INPUTS + ["spotify"]
CYCLE = ["radio", "airplay", "bt", "usb"] if BOARD == "radio" else INPUTS   # SOURCE-knappen
LEVEL_SOURCES = ["airplay", "bt", "usb", "radio", "aux", "aux2", "spotify"]   # eget nivå per kilde (ALSA softvol «KI <kilde>» på kortet Loopback)
state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False,
         "loudness": True, "loudness_level": 5, "voice": True,
         "presets": [None] * 6, "preset": 0,
         "auto_input": os.environ.get("KI_AMP_AUTO_INPUT", "1") == "1",
         "mix": os.environ.get("KI_AMP_MIX", "0") == "1",
         "usb_pc": 1,   # usb_pc: aktiv PC på USB-delingsswitchen, 1 eller 2
         "headphones": False,   # hodetelefoner i front-jacken (hovedkortet)
         "last_wireless": "airplay",   # sist brukte trådløse kilde (airplay/bt) – «BT»-knappen på hovedkortet
         "hp_automute": os.environ.get("KI_AMP_HP_AUTOMUTE", "1") == "1",   # demp høyttalerne når hodetelefoner plugges i
         "overtemp": False,     # NTC på kjøleribben over ~75 °C (MCP GPA7) – TPA3116 dempes til den er under ~50 °C
         "levels": {"airplay": 100, "bt": 100, "usb": 100, "radio": 100, "aux": 100, "aux2": 100, "spotify": 100},   # nivå per kilde (miks)
         "ui_event": None,      # Node: {"name":"settings","t":…} når encoderen holdes 3 s (skjermprosessen viser innstillinger)
         "rebooting": False,    # settes ~1,5 s før daemonen starter omstart/slår av (skjermen viser omstart-animasjonen)
         "input_seq": 0,        # teller som øker for hver knapp-/encoderhendelse
         "settings": {}}
spotify = {"connected": False, "playing": False, "paused": False, "title": "", "artist": "", "album": "", "cover": "",
           "duration": 0, "position": 0, "user": "", "event": "", "t": 0.0}   # siste librespot-hendelse (POST /api/spotify)   # innstillingsmodellen fra appen/web (skjold_settings.js) – se SETTINGS_DEF
LEVELS_ON = os.environ.get("KI_AMP_LEVELS", "1" if BOARD == "main" else "0") == "1"   # mix: ikke stopp de andre digitale kildene ved kildebytte   # loudness 0–10 dB · presets: radiokanal 1–6 · auto_input: bytt kilde når noe begynner å spille
_x9c_pos = None
_pairing_until = 0.0
menu = {"open": False, "idx": 1, "until": 0.0}   # kanalmeny på OLED (hold volumknotten 1 s i radio)
MENU_S = 6.0

# ---------- maskinvare ----------
class _Dummy:
    value = False


def _mk(cls, *a, **k):
    """Lag én GPIO-enhet; feiler den (pinne opptatt, ikke koblet), fortsetter resten likevel."""
    try:
        return cls(*a, **k)
    except Exception as e:
        print(f"GPIO {a[0] if a else ''} ikke tilgjengelig ({cls.__name__}): {e}", flush=True)
        return None


try:
    from gpiozero import Button, DigitalOutputDevice, OutputDevice, PWMLED, RotaryEncoder, LED as GLED
    HW = True
except Exception as e:
    print("Kjører uten GPIO:", e)
    HW = False

relay_amp = relay_aux = _Dummy()
led_power = None
leds, fav_leds = {}, []
node_leds = {}
if HW:
    if BOARD == "radio":
        fav_leds = [l for l in (_mk(GLED, p) for p in FAV_LED) if l]
    elif BOARD == "main":
        relay_amp = _mk(OutputDevice, PIN_RELAY_AMP, active_high=True, initial_value=False) or _Dummy()     # strømrelé + 5V_SW
        amp_sdz = _mk(OutputDevice, PIN_AMP_SDZ, active_high=True, initial_value=False) or _Dummy()         # TPA3116 SDZ: høy = på
        dac_xsmt = _mk(OutputDevice, PIN_DAC_XSMT, active_high=True, initial_value=False)
        # PGA2311 bit-banges (SPI0 er opptatt av TFT og touch): MOSI GPIO 0, SCLK GPIO 1, CS GPIO 16
        pga_pins = (_mk(DigitalOutputDevice, 0, initial_value=False), _mk(DigitalOutputDevice, 1, initial_value=False), _mk(DigitalOutputDevice, 16, initial_value=True))
        pga = pga_pins if all(pga_pins) else None
        if not pga:
            print("PGA2311 (bit-bang GPIO 0/1/16) ikke tilgjengelig", flush=True)
    elif BOARD == "modules":
        relay_amp = _mk(OutputDevice, PIN_RELAY_AMP, active_high=not RELAY_ACTIVE_LOW, initial_value=True) or _Dummy()
        relay_aux = _mk(OutputDevice, PIN_RELAY_AUX, active_high=not RELAY_ACTIVE_LOW, initial_value=False) or _Dummy()
        x_inc = _mk(DigitalOutputDevice, PIN_X9C_INC, initial_value=True)
        x_ud = _mk(DigitalOutputDevice, PIN_X9C_UD, initial_value=False)
        x_cs = _mk(DigitalOutputDevice, PIN_X9C_CS, initial_value=True)
    elif BOARD == "node":   # LED-ringene: programvare-PWM (3,5 mm-lyden bruker maskinvare-PWM0/1)
        node_leds = {k: l for k, l in ((k, _mk(PWMLED, p, active_high=NODE["led_active_high"], frequency=NODE["led_hz"]))
                                       for k, p in NODE["led"].items()) if l}
    leds = {k: l for k, l in ((k, _mk(GLED, v)) for k, v in LED.items()) if l}
    led_power = _mk(PWMLED, LED_POWER, frequency=400) if LED_POWER is not None else None


class Mcp23017:
    """I2C I/O-ekspander på hovedkortet: GPA0-4 knapper (pull-up, aktiv lav), GPA5 jack-deteksjon, GPA6 HP-EN (ut),
    GPB5 overtemperatur (høy = kjøleribben > ~75 °C), GPB0-3 LED-ringer, GPB4 USB-mux (0 = PC 1)."""
    IODIRA, IODIRB, GPPUA, GPIOA, GPIOB, OLATA, OLATB, GPINTENA, IOCON = 0x00, 0x01, 0x0C, 0x12, 0x13, 0x14, 0x15, 0x04, 0x0A

    def __init__(self, addr=0x20, bus=1):
        self.addr, self.ok, self.olata, self.olatb, self.lock = addr, False, 0, 0, threading.Lock()
        try:
            from smbus2 import SMBus
            self.bus = SMBus(bus)
            self._w(self.IOCON, 0x04)                       # IOCON ODR: INTA open-drain (GPIO 14 er også UART TXD)
            self._w(self.IODIRA, 0xBF)                      # GPA6 (HP-EN) ut, resten inn
            self._w(self.GPPUA, 0x3F)                       # pull-up på knappene GPA0-4 og jack-deteksjon GPA5 (GPA7 drives av Schmitt-inverteren)
            self._w(self.GPINTENA, 0x3F); self._w(self.OLATA, 0x00)
            self._w(self.IODIRB, 0x20); self._w(self.OLATB, 0x00)   # GPB5 = overtemperatur inn (fra 74LVC1G14), resten ut
            self.ok = True
            print(f"MCP23017 på 0x{addr:02x} klar", flush=True)
        except Exception as e:
            print("MCP23017 ikke tilgjengelig:", e, flush=True)

    def _w(self, reg, val):
        self.bus.write_byte_data(self.addr, reg, val & 0xFF)

    def read_buttons(self):
        """Sett med trykte knapper (bitnummer) – aktiv lav."""
        if not self.ok:
            return set()
        with self.lock:
            v = self.bus.read_byte_data(self.addr, self.GPIOA)
        return {i for i in range(8) if not (v >> i) & 1}

    def read_overtemp(self):
        """GPB5 høy = kjøleribben er for varm (74LVC1G14-utgangen)."""
        if not self.ok:
            return False
        with self.lock:
            v = self.bus.read_byte_data(self.addr, self.GPIOB)
        return bool((v >> MCP_OVERTEMP) & 1)

    def set_b(self, bit, on):
        if not self.ok:
            return
        with self.lock:
            self.olatb = (self.olatb | (1 << bit)) if on else (self.olatb & ~(1 << bit))
            try:
                self._w(self.OLATB, self.olatb)
            except Exception as e:
                print("MCP23017:", e, flush=True)

    def set_a(self, bit, on):
        """Utgang på port A (bare GPA6 = HP-EN er satt som utgang)."""
        if not self.ok:
            return
        with self.lock:
            self.olata = (self.olata | (1 << bit)) if on else (self.olata & ~(1 << bit))
            try:
                self._w(self.OLATA, self.olata)
            except Exception as e:
                print("MCP23017:", e, flush=True)


class VButton:
    """Programvareknapp med samme grensesnitt som gpiozero.Button (when_pressed/held/released) – matet fra MCP23017."""
    def __init__(self, hold_time=2.0):
        self.hold_time = hold_time; self.when_pressed = self.when_held = self.when_released = None
        self._down = None; self._held = False

    def update(self, pressed, now):
        if pressed and self._down is None:
            self._down = now; self._held = False
            if self.when_pressed: self.when_pressed()
        elif pressed and not self._held and now - self._down >= self.hold_time:
            self._held = True
            if self.when_held: self.when_held()
        elif not pressed and self._down is not None:
            self._down = None
            if self.when_released: self.when_released()


mcp = Mcp23017() if (HW and BOARD == "main") else None


def x9c_step(n):
    if not HW or n == 0 or BOARD != "modules" or not (x_inc and x_ud and x_cs):
        return
    x_ud.value = n > 0
    x_cs.off(); time.sleep(5e-6)
    for _ in range(abs(n)):
        x_inc.off(); time.sleep(5e-6)
        x_inc.on(); time.sleep(5e-6)
    x_cs.on()


def vol_db(v):
    return -80.0 if v <= 0 else max(-60.0, 40.0 * math.log10(v / 100.0))


def pga_write(gain_code):
    """PGA2311: 16 bit (høyre, venstre), MSB først, data leses på stigende SCLK. 0 = mute, 192 = 0 dB, 0,5 dB per trinn."""
    if HW and BOARD == "main" and pga:
        mosi, sclk, cs = pga
        word = ((gain_code & 0xFF) << 8) | (gain_code & 0xFF)
        cs.off()
        for i in range(15, -1, -1):
            sclk.off(); mosi.value = bool((word >> i) & 1); sclk.on()
        sclk.off(); cs.on()


def apply_volume():
    """AUX: analogt volum (X9C på modulbygget, PGA2311 på hovedkortet). AirPlay/BT/USB: analogt på fast nivå, volum + loudness i CamillaDSP."""
    global _x9c_pos
    if BOARD in ("radio", "test", "node"):   # bare digitalt volum (CamillaDSP)
        dsp.update(); return
    if BOARD == "main":   # rev B: alt er digitalt – PGA2311 står fast, volum og nivåer i CamillaDSP/softvol.
        # Fast analogt nivå (KI_AMP_PGA_DB, standard -9 dB): DAC 2,1 Vrms * -9 dB = 0,74 Vrms = det TPA3116 (26 dB) klarer ved 24 V
        # uten å klippe. Da kan ikke full digital styrke overstyre forsterkeren. Hodetelefonforsterkeren har +6 dB for å kompensere.
        pga_write(0 if (state["mute"] or not state["power"]) else max(1, min(255, 192 + 2 * PGA_DB)))
        apply_levels(); dsp.update(); return
    if state["mute"] or not state["power"]:
        target = 0
    elif state["input"] == "aux":
        target = round(state["volume"] * MAX_TAP / 100)
    else:
        target = MAX_TAP
    if _x9c_pos is None:
        x9c_step(-100); _x9c_pos = 0
    x9c_step(target - _x9c_pos); _x9c_pos = target
    dsp.update()


# ---------- Talemeldinger (piper → espeak-ng som reserve), spilles gjennom dmix/CamillaDSP ----------
PHRASES = {
    "bt_pairing": "Bluetooth-paring. Velg Pultforsterker på telefonen.",
    "bt_pairing_timeout": "Ingen enhet koblet til. Paring avsluttet.",
    "bt_connected": "Koblet til {name}.",
    "bt_disconnected": "Bluetooth frakoblet.",
    "input_airplay": "AirPlay.",
    "input_bt": "Bluetooth.",
    "input_aux": "AUX.",
    "input_aux2": "AUX 2.",
    "input_usb": "USB.",
    "input_radio": "Radio.",
    "input_spotify": "Spotify.",
    "radio_preset": "{name}.",
    "radio_saved": "Lagret som kanal {n}.",
    "radio_empty": "Kanal {n} er tom. Hold knappen for å lagre.",
    "power_on": "Pultforsterker er klar.",
    "usb_pc": "USB til {name}.",
    "mix_on": "Miks på.",
    "mix_off": "Miks av.",
    "headphones_on": "Hodetelefoner.",
    "headphones_off": "Høyttalere.",
}
# Trøndersk: samme norske Piper-stemme (mann), men replikkene skrevet på trøndersk. Lages på Pi-en og caches.
PHRASES_TR = {
    "bt_pairing": "Blåtann-paring. Finn Pultforsterker på telefon'n, du.",
    "bt_pairing_timeout": "Ingen kobla sæ te. Æ gir opp å lete, æ.",
    "bt_connected": "No e æ kobla te {name}.",
    "bt_disconnected": "Blåtann e kobla fra.",
    "input_airplay": "Ærplei.",
    "input_bt": "Blåtann.",
    "input_aux": "Auks.",
    "input_aux2": "Auks to.",
    "input_usb": "U S B.",
    "input_radio": "Radio.",
    "input_spotify": "Spotify.",
    "radio_preset": "{name}.",
    "radio_saved": "Lagra på kanal {n}, ja.",
    "radio_empty": "Kanal {n} e tom, du. Hold inne knappen for å lagre.",
    "power_on": "Hei hei! No e æ klar, du.",
    "usb_pc": "U S B over te {name}.",
    "mix_on": "Miksing på.",
    "mix_off": "Miksing av.",
    "headphones_on": "Hodetelefona, ja.",
    "headphones_off": "Høgtalera igjen.",
}
# Stemmeprofiler: en = ferdiginnspilt engelsk AI-stemme (pi/sounds, laget med make_sounds.py),
# no = norsk Piper (bokmål), trondersk = norsk Piper med trønderske replikker. Velges i HA/Homey eller /api/voice.
VOICE_PROFILES = {"en": "English (AI)", "no": "Norsk", "trondersk": "Trøndersk"}
PROFILE_PHRASES = {"no": PHRASES, "trondersk": PHRASES_TR}
SOUNDS_DIR = os.environ.get("KI_AMP_SOUNDS", "/usr/local/share/ki-amp/sounds")
_vp = os.environ.get("KI_AMP_VOICE_PROFILE", "").strip() or os.environ.get("KI_AMP_VOICE_LANG", "en").strip()
state["voice_profile"] = _vp if _vp in VOICE_PROFILES else "en"
TTS_DIR = "/var/cache/ki-amp/tts"
PIPER_VOICE = os.environ.get("KI_AMP_PIPER_VOICE", "/opt/piper/no_NO-talesyntese-medium.onnx")


class Voice:
    def __init__(self):
        self._q = []; self._ev = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, key, delay=0.0, **kw):
        if not state.get("voice", True) or not state["power"] or key not in PHRASES:
            return
        prof = state.get("voice_profile", "en")
        if prof == "en":   # ferdig WAV: radio_preset_3.wav, radio_saved_3.wav … eller bt_pairing.wav
            for name in ([f"{key}_{kw['n']}"] if "n" in kw else []) + [key]:
                f = os.path.join(SOUNDS_DIR, name + ".wav")
                if os.path.exists(f):
                    self._q.append((time.time() + delay, f)); self._ev.set(); return
        table = PROFILE_PHRASES.get(prof, PHRASES)
        self._q.append((time.time() + delay, table.get(key, PHRASES[key]).format(**kw))); self._ev.set()

    def _wav(self, text):
        import hashlib
        os.makedirs(TTS_DIR, exist_ok=True)
        path = os.path.join(TTS_DIR, hashlib.sha1(text.encode()).hexdigest()[:16] + ".wav")
        if not os.path.exists(path):
            piper = subprocess.run(["sh", "-c", "command -v piper"], capture_output=True, text=True).stdout.strip()
            if piper and os.path.exists(PIPER_VOICE):
                subprocess.run([piper, "--model", PIPER_VOICE, "--output_file", path], input=text, text=True,
                               capture_output=True, timeout=30)
            if not os.path.exists(path):
                subprocess.run(["espeak-ng", "-v", "nb", "-s", "150", "-w", path, text], capture_output=True, timeout=15)
        return path if os.path.exists(path) else None

    def warm(self, prof=None):   # lag faste fraser på forhånd, så første melding kommer uten forsinkelse
        prof = prof or state.get("voice_profile", "en")
        if prof == "en" and os.path.isdir(SOUNDS_DIR):
            return   # ferdiginnspilt
        table = PROFILE_PHRASES.get(prof, PHRASES)
        for k, t in table.items():
            if "{" not in t:
                try: self._wav(t)
                except Exception: pass
        for n in range(1, 7):   # kanal 1–6 også
            for k in ("radio_saved", "radio_empty"):
                try: self._wav(table[k].format(n=n))
                except Exception: pass

    def _run(self):
        while True:
            self._ev.wait(); self._ev.clear()
            while self._q:
                t, text = self._q.pop(0)
                if t > time.time():
                    time.sleep(t - time.time())
                try:
                    wav = text if text.endswith(".wav") and os.path.exists(text) else self._wav(text)
                    if wav and state.get("voice", True):
                        subprocess.run(["aplay", "-q", "-D", "default", wav], timeout=20, check=False)
                except Exception as e:
                    print("Talemelding:", e, flush=True)


voice = Voice()


def set_voice(on):
    state["voice"] = bool(on); changed()


def set_voice_profile(prof):
    if prof not in VOICE_PROFILES:
        raise ValueError(f"profil må være en av {list(VOICE_PROFILES)}")
    state["voice_profile"] = prof; changed()
    def _hello():   # lag lydene for profilen, og si hei i den nye stemmen
        voice.warm(prof); voice.say("power_on")
    threading.Thread(target=_hello, daemon=True).start()


# ---------- CamillaDSP (loudness + digitalt volum) ----------
def dsp_config():
    lvl = state["loudness_level"] if state["loudness"] else 0
    return f"""devices:
  samplerate: 48000
  chunksize: 1024
  queuelimit: 4
  capture: {{type: Alsa, channels: 2, device: "{DSP_CAPTURE}", format: S32LE}}
  playback: {{type: Alsa, channels: 2, device: "{DSP_PLAYBACK}", format: {DSP_FORMAT}}}
filters:
  loud:
    type: Loudness
    parameters: {{fader: Main, reference_level: -10.0, high_boost: {lvl * 0.5:.1f}, low_boost: {float(lvl):.1f}, attenuate_mid: false}}
pipeline:
  - type: Filter
    channel: 0
    names: [loud]
  - type: Filter
    channel: 1
    names: [loud]
"""


class Dsp:
    """Egen tråd som holder CamillaDSP oppdatert via websocket (python3-websocket)."""
    def __init__(self):
        self._ev = threading.Event(); self._last_cfg = None
        threading.Thread(target=self._run, daemon=True).start()

    def update(self):
        self._ev.set()

    def _send(self, ws, cmd):
        ws.send(json.dumps(cmd)); return json.loads(ws.recv())

    def _run(self):
        try:
            import websocket
        except Exception as e:
            print("CamillaDSP-styring av (python3-websocket mangler):", e); return
        self._ev.set()   # skyv oppsett og volum ved oppstart
        while True:
            self._ev.wait(); self._ev.clear()
            cfg = dsp_config()
            try:   # samme oppsett på disk, så CamillaDSP starter riktig etter omstart/krasj
                if not os.path.exists(DSP_FILE) or open(DSP_FILE).read() != cfg:
                    with open(DSP_FILE + ".tmp", "w") as fh: fh.write(cfg)
                    os.replace(DSP_FILE + ".tmp", DSP_FILE)
            except Exception as e:
                print("CamillaDSP-fil:", e)
            try:
                ws = websocket.create_connection(DSP_WS, timeout=2)
                if cfg != self._last_cfg:
                    self._send(ws, {"SetConfig": cfg}); self._last_cfg = cfg
                db = vol_db(state["volume"]) if (state["input"] != "aux" or BOARD == "main") else 0.0
                self._send(ws, {"SetVolume": db})
                self._send(ws, {"SetMute": bool(state["mute"]) or not state["power"]})
                ws.close()
            except Exception as e:   # CamillaDSP ikke klar ennå – prøv igjen
                print("CamillaDSP:", e, flush=True); self._last_cfg = None; time.sleep(2); self._ev.set()


dsp = Dsp()


def apply_input():
    if not HW:
        return
    if BOARD == "main":
        if mcp:   # ringene: «BT» (AirPlay + Bluetooth), «RADIO», AUX (1 og 2), USB
            lit = {"airplay": state["input"] in ("airplay", "bt"), "bt": state["input"] == "radio",
                   "aux": state["input"] in ("aux", "aux2"), "usb": state["input"] == "usb"}
            for k, bit in MCP_LED.items():
                mcp.set_b(bit, bool(state["power"] and lit[k] and led_scale() > 0))
    else:
        relay_aux.value = state["input"] == "aux"
    leds_on = led_scale() > 0
    for k, led in leds.items():
        led.value = state["power"] and k == state["input"] and leds_on
    if USBSW_FRONT and usbsw.enabled and leds_on:   # PC 1/2-ringen lyser alltid når den er på, AIRPLAY/BT-ringen for AirPlay, BT og Radio
        if "airplay" in leds:
            leds["airplay"].value = state["power"]
        if "bt" in leds:
            leds["bt"].value = state["power"] and state["input"] in ("airplay", "bt", "radio")
    if BOARD == "node":
        apply_node_leds()
    if BOARD == "radio":
        for i, led in enumerate(fav_leds):
            led.value = state["power"] and state["input"] == "radio" and state["preset"] == i + 1 and leds_on
    if state["input"] != "bt" or not state["bt_pairing"]:
        pass  # BT-LED pulserer under parring (se pairing_task)


LED_SCALE = [1.0, 0.45, 0.15, 0.0]   # innstilling «led» (LED-ringer): Høy, Middels, Lav, Av


def led_scale():
    """Lysstyrke for LED-ringene fra innstillingen «led». PWMLED (node, strøm-LED) skaleres; av/på-LED-er
    (MCP23017 på main, gpiozero LED på modules/radio) kan ikke dimmes – de slukkes bare ved «Av»."""
    try:
        i = int(settings().get("led", 0))
    except Exception:
        i = 0
    return LED_SCALE[i] if 0 <= i < len(LED_SCALE) else 1.0


def apply_node_leds(playing=None):
    """Node: RADIO-ringen = radio, AIR·BT-ringen = AirPlay/Bluetooth/Spotify, ◀◀/▶▶ = noe spiller (svakt ellers)."""
    if not node_leds:
        return
    on = state["power"]
    if playing is None:
        try:
            playing = bool(read_status().get("playing"))
        except Exception:
            playing = False
    want = {"radio": 1.0 if on and state["input"] == "radio" else 0.0,
            "airbt": 1.0 if on and state["input"] in ("airplay", "bt", "spotify") else 0.0,
            "prev": (0.6 if playing else 0.08) if on else 0.0, "next": (0.6 if playing else 0.08) if on else 0.0}
    for k, led in node_leds.items():
        if k == "airbt" and state["bt_pairing"]:
            continue   # pairing_task blinker den
        try:
            led.value = want.get(k, 0.0) * led_scale()
        except Exception as e:
            print("LED-ring:", e, flush=True)


def speakers_on():
    """TPA3116 skal være aktiv: på, og ikke dempet av hodetelefoner (auto-demping)."""
    return state["power"] and not (state["headphones"] and state["hp_automute"]) and not state["overtemp"]


def apply_headphones():
    """Hodetelefonforsterker (TPA6132A2 EN på MCP GPA6) følger jacken; høyttalerne dempes via SDZ hvis auto-demping er på."""
    if not (HW and BOARD == "main"):
        return
    if mcp:
        mcp.set_a(MCP_HP_EN, state["power"] and state["headphones"])
    amp_sdz.value = speakers_on()


MCP_OVERTEMP = 5   # GPB5 (port B) – GPA7/GPB7 kan ikke brukes som innganger (Microchip-errata)


def set_overtemp(hot):
    if hot == state["overtemp"]:
        return
    state["overtemp"] = hot
    print("OVERTEMPERATUR: kjøleribben er for varm – forsterkeren dempes" if hot else "Temperatur OK igjen – forsterkeren er på", flush=True)
    if HW and BOARD == "main":
        amp_sdz.value = speakers_on()
    changed()


def set_headphones(plugged):
    if plugged == state["headphones"]:
        return
    state["headphones"] = plugged
    apply_headphones(); changed()
    voice.say("headphones_on" if plugged else "headphones_off")


def set_hp_automute(on):
    state["hp_automute"] = bool(on); apply_headphones(); changed()


def apply_power():
    if HW and BOARD == "main":   # rekkefølge mot plopp: av = XSMT/SDZ lav, så strøm; på = strøm, vent, så XSMT/SDZ høy
        if state["power"]:
            relay_amp.value = True; time.sleep(0.3)
            if dac_xsmt: dac_xsmt.value = True
            apply_volume(); time.sleep(0.2); apply_headphones()
        else:
            amp_sdz.value = False
            if mcp: mcp.set_a(MCP_HP_EN, False)
            if dac_xsmt: dac_xsmt.value = False
            time.sleep(0.1); relay_amp.value = False
    elif HW:
        relay_amp.value = state["power"]
    if HW:
        if led_power:
            led_power.value = (1.0 if state["power"] else 0.1) * led_scale()
        apply_input()
    apply_volume()   # mute i CamillaDSP + PGA2311 i standby
    # OLED av i standby håndteres av oled_display.py via ctrl-filen
    units = [u for u in ("shairport-sync", "bluealsa-aplay", "ki-usb-audio", "ki-squeezelite", "ki-aux1", "ki-aux2", "ki-spotify")   # bare tjenester som er slått på
             if subprocess.run(["systemctl", "is-enabled", "--quiet", u], check=False).returncode == 0]
    if not state["power"]:   # stopp det som spiller pent før tjenestene tas ned
        _pause_others("")
        if lyr.info.get("mode") == "play":
            lyr.cmd(["pause", "1"])
    subprocess.run(["systemctl", "start" if state["power"] else "stop", *units],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------- innstillinger (app/web, samme nøkler som skjold_settings.js) ----------
SETTINGS_DEF = {"bass": 0, "treb": 0, "bal": 0, "vstart": 0, "vmax": 0, "perIn": True, "hpOwn": True, "lvlAux": 0, "lvlUsb": 0,
                "name": 0, "nameCustom": "", "updChannel": 0, "updAuto": True, "setupDone": False, "nAux1": "AUX 1", "nAux2": "AUX 2", "nUsb1": "PC 1", "nUsb2": "PC 2", "hold": 2,
                "voice": True, "lang": 0, "vv": 1, "dim": 1, "off": 1, "clock": True, "clockStyle": 0, "bright": 0, "led": 0, "auto": 1, "wake": True,
                "eq": {k: {"preset": p, "eq": e, "loud": k != "hp"} for k, p, e in (("air", 0, [0, 0, 0, 0, 0]), ("bt", 1, [6, 3, 0, 0, 1]), ("radio", 2, [-2, 0, 3, 2, 0]),
                                                                                     ("aux", 0, [0, 0, 0, 0, 0]), ("usb", 0, [0, 0, 0, 0, 0]), ("hp", 3, [3, 1, -1, -2, -3]))}}
VMAX = [100, 90, 80, 70]; VSTART = [None, 20, 30, 40]; LANG_PROFILE = {0: "no", 1: "en"}
SETTINGS_APPLIED = {"led", "name", "nameCustom", "voice", "lang", "vmax", "vstart", "nUsb1", "nUsb2", "wake", "bright", "dim", "off", "clock", "clockStyle"}   # bright/dim/off/clock*: Skjold OS   # resten lagres og vises, men styrer ingenting ennå


def settings():
    s_ = dict(SETTINGS_DEF); s_["eq"] = {k: dict(v) for k, v in SETTINGS_DEF["eq"].items()}
    cur = state.get("settings") or {}
    for k, v in cur.items():
        if k == "eq" and isinstance(v, dict):
            for src, prof in v.items():
                if src in s_["eq"] and isinstance(prof, dict): s_["eq"][src].update(prof)
        elif k in s_: s_[k] = v
    return s_


def apply_settings(changed_keys=()):
    s_ = settings()
    global USBSW_NAMES
    env_names = _usbsw_n + ["PC 1", "PC 2"][len(_usbsw_n):]   # KI_AMP_USBSW_NAMES er standard til brukeren setter navn i appen
    USBSW_NAMES = [str(s_["nUsb1"] if s_["nUsb1"] != SETTINGS_DEF["nUsb1"] else env_names[0])[:16],
                   str(s_["nUsb2"] if s_["nUsb2"] != SETTINGS_DEF["nUsb2"] else env_names[1])[:16]]
    if "voice" in changed_keys: state["voice"] = bool(s_["voice"])
    if "lang" in changed_keys and LANG_PROFILE.get(int(s_["lang"]) if str(s_["lang"]).isdigit() else -1):
        state["voice_profile"] = LANG_PROFILE[int(s_["lang"])]
    vmax = VMAX[int(s_["vmax"])] if str(s_["vmax"]).isdigit() and int(s_["vmax"]) < len(VMAX) else 100
    if state["volume"] > vmax:
        state["volume"] = vmax; apply_volume()
    if "led" in changed_keys and HW:
        _safe(apply_input)
        if led_power: _safe(lambda: setattr(led_power, "value", (1.0 if state["power"] else 0.1) * led_scale()))
    if not changed_keys or {"name", "nameCustom"} & set(changed_keys):
        apply_name(force_services=bool(changed_keys))


# ---------- enhetsnavn (AirPlay / Spotify / Blåtann) ----------
NAMES = ["Skjold S1", "Stue", "Kontor", "Soverom"]   # samme liste som skjold_settings.js / app settings.ts
NAME_ENV = NAME   # KI_AMP_NAME eller kortets standard
SHAIRPORT_CONF = os.environ.get("KI_AMP_SHAIRPORT_CONF", "/etc/shairport-sync.conf")
SPOTIFY_DROPIN = os.environ.get("KI_AMP_SPOTIFY_DROPIN", "/etc/systemd/system/ki-spotify.service.d/ki-name.conf")
_name_applied = [None]


def effective_name():
    """Eget navn (nameCustom) > valg fra listen (name, satt av brukeren) > KI_AMP_NAME > kortets standard."""
    s_ = settings()
    custom = re.sub(r'[\x00-\x1f"\\/;]', "", str(s_.get("nameCustom") or "")).strip()[:32]
    if custom:
        return custom
    cur = state.get("settings") or {}
    if "name" in cur:   # bare når brukeren faktisk har valgt i appen; ellers gjelder env/standard
        try:
            return NAMES[int(cur["name"])]
        except Exception:
            pass
    return NAME_ENV


def apply_name(force_services=False):
    """Sett spillernavnet. Tjenestene (AirPlay, Spotify, Blåtann) endres/restartes bare når navnet faktisk endres
    (ved oppstart kun hvis det avviker fra det installasjonen satte, dvs. KI_AMP_NAME)."""
    global NAME
    new = effective_name()
    old = _name_applied[0]
    NAME = new
    if old == new or (old is None and new == NAME_ENV and not force_services):
        _name_applied[0] = new; return
    _name_applied[0] = new
    if not HW:
        print(f"navn: «{new}» (simulering – AirPlay/Spotify/Blåtann ikke endret)", flush=True); return
    threading.Thread(target=_apply_name_services, args=(new,), daemon=True).start()


def _apply_name_services(name):
    q = dict(check=False, timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # bare tjenester som faktisk er installert (simulering/testmaskin: ingenting skrives i /etc)
    try:   # AirPlay: name = "…"; i general-blokken
        if not os.path.isfile(SHAIRPORT_CONF): raise FileNotFoundError(SHAIRPORT_CONF + " finnes ikke – hopper over")
        with open(SHAIRPORT_CONF) as fh: conf = fh.read()
        new_conf, n = re.subn(r'^(\s*name\s*=\s*)"[^"]*";', lambda m: m.group(1) + '"' + name + '";', conf, count=1, flags=re.M)
        if n and new_conf != conf:
            with open(SHAIRPORT_CONF, "w") as fh: fh.write(new_conf)
            subprocess.run(["systemctl", "try-restart", "shairport-sync"], **q)
    except Exception as e:
        print("navn/AirPlay:", e, flush=True)
    try:   # Spotify: ki-spotify leser KI_AMP_NAME – drop-in overstyrer /etc/ki-amp.env
        if not os.path.isfile("/etc/systemd/system/ki-spotify.service"): raise FileNotFoundError("ki-spotify er ikke installert – hopper over")
        os.makedirs(os.path.dirname(SPOTIFY_DROPIN), exist_ok=True)
        with open(SPOTIFY_DROPIN, "w") as fh:
            fh.write('[Service]\nEnvironment="KI_AMP_NAME=%s"\n' % name.replace("%", "%%"))
        subprocess.run(["systemctl", "daemon-reload"], **q)
        subprocess.run(["systemctl", "try-restart", "ki-spotify"], **q)
    except Exception as e:
        print("navn/Spotify:", e, flush=True)
    try:
        subprocess.run(["bluetoothctl", "system-alias", name], **q)
    except Exception as e:
        print("navn/Blåtann:", e, flush=True)
    print(f"navn: «{name}» satt for AirPlay/Spotify/Blåtann", flush=True)


def update_settings(patch):
    cur = state.setdefault("settings", {})
    for k, v in patch.items():
        if k not in SETTINGS_DEF: continue
        if k == "eq":
            if not isinstance(v, dict): continue
            eq = cur.setdefault("eq", {})
            for src, prof in v.items():
                if src in SETTINGS_DEF["eq"] and isinstance(prof, dict):
                    cl = {kk: prof[kk] for kk in ("preset", "eq", "loud") if kk in prof}
                    if "eq" in cl and not (isinstance(cl["eq"], list) and len(cl["eq"]) == 5): cl.pop("eq")
                    eq.setdefault(src, {}).update(cl)
        else:
            cur[k] = v
    apply_settings(set(patch)); changed()


async def h_settings_get(_r): return web.json_response({"settings": settings(), "applied": sorted(SETTINGS_APPLIED), "schema_version": 1})


async def h_settings_post(r):
    body = await r.json()
    if not isinstance(body, dict): return web.json_response({"error": "forventer et objekt med nøkler"}, status=400)
    update_settings(body); return await h_settings_get(r)


def save_state():
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as fh:
            json.dump({k: state[k] for k in ("input", "volume", "mute", "loudness", "loudness_level", "voice", "presets", "preset", "auto_input", "mix", "usb_pc", "voice_profile", "levels", "hp_automute", "settings")}, fh)
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE) as fh:
            saved = json.load(fh)
            if isinstance(saved.get("levels"), dict):
                state["levels"].update({k: int(v) for k, v in saved.pop("levels").items() if k in state["levels"]})
            state.update({k: v for k, v in saved.items() if k in state})
    except Exception:
        pass


def write_ctrl():
    try:
        tmp = CTRL_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({**state, "lyrion": lyr.connected, "radio": lyr.info if state["input"] == "radio" else {},
                       "menu": dict(menu) if menu["open"] else None}, fh)
        os.replace(tmp, CTRL_FILE)
    except Exception:
        pass


def changed():
    write_ctrl(); save_state()


def read_raw():
    """AirPlay/Bluetooth-metadata fra oled_display.py, uavhengig av valgt kilde."""
    try:
        with open(STATUS_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {}


def read_status():
    st = read_raw()
    raw_ap = st.get("airplay_device", "")
    if state["input"] == "radio":   # metadata fra Lyrion
        r = lyr.info
        st = {"playing": r.get("mode") == "play", "paused": r.get("mode") == "pause", "source": "radio",
              "cover": lyr.cover_id, "title": r.get("song") or r.get("station", ""),
              "artist": r.get("artist") or (r.get("station", "") if r.get("song") else ""),
              "album": r.get("station", ""), "duration": r.get("duration", 0), "position": r.get("time", 0),
              "bt_device": st.get("bt_device", "")}
    elif state["input"] == "spotify" or (spotify["playing"] and not st.get("playing")):
        st = {"playing": spotify["playing"], "paused": spotify["paused"], "source": "spotify", "cover": spotify["cover"],
              "title": spotify["title"], "artist": spotify["artist"], "album": spotify["album"],
              "duration": spotify["duration"], "position": spotify["position"], "bt_device": st.get("bt_device", "")}
    extra = {"presets": [{"n": i + 1, "title": (p or {}).get("title", "")} for i, p in enumerate(state["presets"])],
             "station": lyr.info.get("station", ""), "lyrion": lyr.connected}
    return {**state, **extra, "playing": bool(st.get("playing")), "paused": bool(st.get("paused")), "source": st.get("source", ""), "cover": st.get("cover", ""), "title": st.get("title", ""), "artist": st.get("artist", ""), "album": st.get("album", ""),
            "duration": st.get("duration", 0), "position": st.get("position", 0), "bt_device": st.get("bt_device", ""),
            "name": NAME, "version": VERSION, "id": socket.gethostname(), "presets": extra["presets"],
            "usb_names": USBSW_NAMES, "voice_profiles": VOICE_PROFILES, "inputs": INPUTS, "board": BOARD,
            "spotify": dict(spotify), "airplay_device": raw_ap or "",
            "bt_pairing_left": max(0, int(round(_pairing_until - time.time()))) if state["bt_pairing"] else 0,
            "menu": dict(menu) if menu["open"] else None, "hold": hold_status(), "settings_menu": smenu_status()}


# ---------- USB-delingsswitch (Ugreen 2 PC → 4 USB) ----------
# Knappen på switchen trykkes via optokobler (PC817) fra USBSW_PULSE. Hvilken PC som er valgt leses fra switchens
# PC 1-LED via en PC817 til USBSW_SENSE (intern pull-up). USBSW_SENSE_PC1 sier hvilket nivå som betyr PC 1.
USBSW_PULSE = os.environ.get("KI_AMP_USBSW_PULSE", "").strip()
USBSW_SENSE = os.environ.get("KI_AMP_USBSW_SENSE", "").strip()
USBSW_SENSE_PC1 = os.environ.get("KI_AMP_USBSW_SENSE_PC1", "low").strip().lower()   # low | high
USBSW_FRONT = os.environ.get("KI_AMP_USBSW_FRONT", "0") == "1"
# opto = via PC817 (GPIO høy = trykk). direct = ledningen fra knappen rett på GPIO: pinnen står åpen (inngang uten pull)
# og trekkes til 0 V under trykket. Bare trygt når knappens «varme» side er 3,3 V eller lavere (mål først!).
HP_DET_INV = os.environ.get("KI_AMP_HP_DET_INV", "0") == "1"   # 1 hvis jacken er koblet motsatt (lav = plugget i)
USBSW_MODE = os.environ.get("KI_AMP_USBSW_MODE", "mux" if BOARD == "main" else "opto").strip().lower()   # mux = TS3USB221 på hovedkortet (MCP GPB4)   # 1 = AIRPLAY-knappen blir PC 1/2, BT-knappen blir AIRPLAY/BT
_usbsw_n = [n.strip() for n in os.environ.get("KI_AMP_USBSW_NAMES", "").split(",") if n.strip()]
USBSW_NAMES = (_usbsw_n + ["PC 1", "PC 2"][len(_usbsw_n):])[:2]   # f.eks. KI_AMP_USBSW_NAMES=MacBook,Jobb-PC


class _OpenDrain:
    """Direkte kobling til knappen: høyimpedans i ro, 0 V under trykk (som en åpen kollektor)."""
    def __init__(self, pin):
        self.pin, self.ok = pin, False
        try:
            import lgpio
            self.lg = lgpio; self.h = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_input(self.h, pin, lgpio.SET_PULL_NONE)
            self.ok = True
        except Exception as e:
            print(f"USB-switch: GPIO {pin} ikke tilgjengelig (direkte):", e, flush=True)

    def on(self):    # trekk knappen til 0 V
        self.lg.gpio_free(self.h, self.pin); self.lg.gpio_claim_output(self.h, self.pin, 0)

    def off(self):   # slipp: tilbake til åpen inngang
        self.lg.gpio_free(self.h, self.pin); self.lg.gpio_claim_input(self.h, self.pin, self.lg.SET_PULL_NONE)


class UsbSwitch:
    def __init__(self):
        self.pulse = self.sense = None
        self.lock = threading.Lock()

    @property
    def enabled(self):
        return self.pulse is not None

    def start(self):
        if USBSW_MODE == "mux":   # hovedkortet: nivå på MCP23017 GPB4 velger PC direkte – ingen puls, ingen avlesning
            if not mcp or not mcp.ok:
                return
            self.pulse = "mux"; state["usbsw"] = True; state["usb_pc_names"] = USBSW_NAMES
            mcp.set_b(MCP_USB_SEL, state["usb_pc"] == 2)
            print(f"USB-switch: mux på hovedkortet, aktiv {USBSW_NAMES[state['usb_pc'] - 1]}", flush=True); return
        if not (HW and USBSW_PULSE):
            return
        if USBSW_MODE == "direct":
            self.pulse = _OpenDrain(int(USBSW_PULSE))
            if not self.pulse.ok:
                self.pulse = None; return
        else:
            self.pulse = _mk(DigitalOutputDevice, int(USBSW_PULSE), initial_value=False)
        if USBSW_SENSE:
            from gpiozero import DigitalInputDevice
            self.sense = _mk(DigitalInputDevice, int(USBSW_SENSE), pull_up=True, bounce_time=0.05)
            if self.sense:
                self.sense.when_activated = self.sense.when_deactivated = lambda: _safe(self._update)
                self._update()
        state["usbsw"] = self.enabled; state["usb_pc_names"] = USBSW_NAMES
        print(f"USB-switch: puls GPIO {USBSW_PULSE}, avlesning {'GPIO ' + USBSW_SENSE if self.sense else 'av'} "
              f"(PC 1 = {USBSW_SENSE_PC1}), modus {USBSW_MODE}, aktiv {USBSW_NAMES[state['usb_pc'] - 1]}", flush=True)

    def read(self):
        """1 eller 2 fra LED-avlesningen, None uten avlesning. is_active = pinnen er lav (optokobleren leder)."""
        if not self.sense:
            return None
        low = bool(self.sense.is_active)
        return 1 if low == (USBSW_SENSE_PC1 == "low") else 2

    def _update(self):
        pc = self.read()
        if pc and pc != state["usb_pc"]:
            state["usb_pc"] = pc; changed()
            voice.say("usb_pc", n=pc, name=USBSW_NAMES[pc - 1])
            print("USB-switch:", USBSW_NAMES[pc - 1], flush=True)

    def _press(self):
        self.pulse.on(); time.sleep(0.15); self.pulse.off(); time.sleep(0.5)   # som et trykk; switchen trenger litt tid

    def set(self, pc):
        if not self.enabled:
            raise RuntimeError("USB-switch er ikke satt opp (KI_AMP_USBSW_PULSE)")
        with self.lock:
            if self.pulse == "mux":
                if pc != state["usb_pc"]:
                    mcp.set_b(MCP_USB_SEL, pc == 2); state["usb_pc"] = pc; changed()
                    voice.say("usb_pc", n=pc, name=USBSW_NAMES[pc - 1])
                return
            cur = self.read() or state["usb_pc"]
            if cur == pc:
                return
            self._press()
            if self.sense and self.read() != pc:   # prøv én gang til hvis den ikke byttet
                self._press()
            new = self.read() or pc
            if new != state["usb_pc"]:
                voice.say("usb_pc", n=new, name=USBSW_NAMES[new - 1])
            state["usb_pc"] = new; changed()

    def toggle(self):
        self.set(2 if (self.read() or state["usb_pc"]) == 1 else 1)


usbsw = UsbSwitch()


# ---------- handlinger ----------
def set_power(on):
    was = state["power"]
    state["power"] = bool(on); apply_power(); changed()
    if state["power"] and not was:
        voice.say("power_on", delay=2.5)   # vent til tjenestene er oppe igjen


def set_input(inp, announce=True):
    if inp in INPUTS:
        prev = state["input"]
        state["input"] = inp
        if inp in ("airplay", "bt"):
            state["last_wireless"] = inp   # «BT»-knappen på hovedkortet går tilbake til den sist brukte trådløse kilden
        apply_input(); apply_volume(); changed()
        if prev != inp:
            if not (state["mix"] and inp != "aux"):   # miks: la AirPlay/BT/USB/Radio spille videre oppå hverandre
                threading.Thread(target=_pause_others, args=(inp,), daemon=True).start()
            if announce:
                voice.say("input_" + inp)


def _pause_others(inp):
    """Som en ekte inngangsvelger: stopp AirPlay/Bluetooth som spiller på en annen kilde enn den valgte."""
    st = read_status()
    if lyr.info.get("mode") == "play" and inp != "radio":
        lyr.cmd(["pause", "1"])
    if spotify["playing"] and inp != "spotify" and st.get("source") != "spotify":
        spotify_stop()   # Spotify spiller i bakgrunnen mens en annen kilde vises
    if not st.get("playing") or st.get("source") in ("", inp, "radio"):
        return
    try:
        if st.get("source") == "bt":
            _busctl("call", "org.bluez", _bt_player(), "org.bluez.MediaPlayer1", "Pause")
        elif st.get("source") == "airplay":
            _busctl("call", SPS[0], SPS[1], SPS[2], "Pause")
        elif st.get("source") == "spotify":
            spotify_stop()
    except Exception as e:
        print("Pause annen kilde:", e, flush=True)


LEVEL_CTL = {"airplay": "KI AirPlay", "bt": "KI Bluetooth", "usb": "KI USB", "radio": "KI Radio", "aux": "KI AUX1", "aux2": "KI AUX2",
             "spotify": "KI Spotify"}


def apply_levels():
    """Nivå per kilde via ALSA softvol (asound.conf) – bare når kontrollene finnes (hovedkortet / rev B-oppsett)."""
    if not LEVELS_ON:
        return
    for src, name in LEVEL_CTL.items():
        v = int(state["levels"].get(src, 100))
        if not state["mix"] and src != state["input"]:   # uten miks: bare valgt kilde slipper gjennom
            v = 0
        subprocess.run(["amixer", "-q", "-c", "Loopback", "sset", name, f"{max(0, min(100, v))}"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_level(src, v):
    if src not in LEVEL_SOURCES:
        raise ValueError(f"kilde må være en av {LEVEL_SOURCES}")
    state["levels"][src] = max(0, min(100, int(v))); apply_levels(); changed()


def set_loudness(on=None, level=None):
    if on is not None:
        state["loudness"] = bool(on)
    if level is not None:
        state["loudness_level"] = max(0, min(10, int(level)))
    apply_volume(); changed()


def set_volume(v):
    state["volume"] = max(0, min(100, int(v)))
    if state["volume"] > 0:
        state["mute"] = False
    apply_volume(); changed()


def set_mute(m):
    state["mute"] = bool(m); apply_volume(); changed()


_pairing_known = ""


def bt_pairing(on=True, reason=""):
    global _pairing_until, _pairing_known
    if on and not state["bt_pairing"]:
        voice.say("bt_pairing")
    elif not on and state["bt_pairing"] and reason == "timeout":
        voice.say("bt_pairing_timeout")
    state["bt_pairing"] = bool(on)
    _pairing_until = time.time() + 120 if on else 0
    _pairing_known = read_status().get("bt_device", "") if on else ""
    for args in ([["power", "on"], ["pairable", "on"], ["discoverable", "on"]] if on else [["discoverable", "off"]]):
        subprocess.run(["bluetoothctl", *args], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    changed()


# ---------- knapper ----------
def _safe(fn, *a):
    try:
        fn(*a)
    except Exception as e:
        print("Knapp:", e, flush=True)


_power_press_t = 0.0


def _hold_btn(b, short, held, key=None, info=None, on_change=None):
    """Kort trykk = short(), hold = held(). gpiozero har ingen «was_held», så vi holder styr på det selv.
    Alt kjøres via _safe – et unntak i en knapp-callback dreper ellers lgpio-tråden og alle knappene slutter å virke.
    key/info: fremdrift i status["hold"] mens knappen holdes (info() → (tittel, undertekst) eller None = ingen hold-handling).
    on_change(): kalles ved trykk og slipp (brukes for «hold begge»)."""
    st = {"held": False}   # gpiozero tillater ikke nye attributter på Button

    def _p():
        st["held"] = False; input_event()
        if key:
            _press[key] = {"t0": time.time(), "dur": float(getattr(b, "hold_time", 2.0) or 2.0), "info": info}
        if on_change: _safe(on_change)

    def _h():
        st["held"] = True
        if key: _press.pop(key, None)
        _safe(held)

    def _r():
        input_event()
        if key: _press.pop(key, None)
        if on_change: _safe(on_change)
        if not st["held"]:
            _safe(short)
    b.when_pressed, b.when_held, b.when_released = _p, _h, _r


def menu_open():
    if not lyr.connected:
        return
    menu.update(open=True, idx=state["preset"] or 1, until=time.time() + MENU_S); write_ctrl()


def menu_close():
    menu["open"] = False; write_ctrl()


def menu_step(d):
    menu["idx"] = (menu["idx"] - 1 + d) % 6 + 1; menu["until"] = time.time() + MENU_S; write_ctrl()


def menu_pick():
    n = menu["idx"]; menu_close()
    if state["presets"][n - 1]:
        _safe(play_preset, n)
    else:
        voice.say("radio_empty", n=n)


def menu_save():
    n = menu["idx"]; menu_close(); _safe(save_preset, n)


async def menu_task():
    while True:
        if menu["open"] and time.time() > menu["until"]:
            menu_close()
        if smenu["open"] and time.time() > smenu["until"]:
            smenu_close()
        await asyncio.sleep(0.3)


# ---------- skjermhendelser (Skjold OS): input_seq, hold-fremdrift, bekreftelser, omstart ----------
_press = {}                          # knapp som holdes inne: key → {"t0", "dur", "info"}
_toast = {"v": None, "until": 0.0}   # kort bekreftelse i status["hold"] (f.eks. «Lagret»)
HOLD_SHOW_S = 0.35                   # vis hold-fremdrift først etter dette (et vanlig trykk skal ikke blinke)
REBOOT_DELAY = 1.5


def input_event():
    state["input_seq"] = int(state.get("input_seq") or 0) + 1


def toast(title, sub="", key="radio", secs=2.5, **extra):
    _toast.update(v={"key": key, "p": 1, "title": title, "sub": sub, **extra}, until=time.time() + secs)


def hold_status():
    now = time.time()
    if _toast["v"] and now < _toast["until"]:
        return dict(_toast["v"])
    best = None
    for k, h in list(_press.items()):
        el = now - h["t0"]
        if el < HOLD_SHOW_S:
            continue
        try:
            txt = h["info"]() if h.get("info") else None
        except Exception:
            txt = None
        if not txt:
            continue
        cand = {"key": k, "p": round(min(1.0, el / max(0.1, h["dur"])), 3), "title": txt[0], "sub": txt[1]}
        if best is None or k == "reboot":
            best = cand
    return best


def system_reboot(poweroff=False, why=""):
    """Omstart/slå av: status["rebooting"]=true skrives ut først, så skjermen rekker omstart-animasjonen."""
    if state.get("rebooting"):
        return
    state["rebooting"] = True; _press.clear()
    print(f"{why or 'Omstart'} – {'slår av' if poweroff else 'starter på nytt'} om {REBOOT_DELAY} s", flush=True)
    save_state(); write_ctrl()

    def _go():
        time.sleep(REBOOT_DELAY)
        if os.environ.get("KI_AMP_NO_REBOOT") == "1":   # test/simulering
            print("KI_AMP_NO_REBOOT=1: hopper over systemctl", flush=True); return
        subprocess.run(["systemctl", "poweroff" if poweroff else "reboot"], check=False)
    threading.Thread(target=_go, daemon=True).start()


async def h_reboot(r):
    try:
        b = await r.json()
    except Exception:
        b = {}
    system_reboot(bool((b or {}).get("poweroff")), "API")
    return j()


# ---------- innstillingsmeny på Node (encoder holdt 3 s) ----------
# (nøkkel, navn, ikon, valg) – nøklene er de samme som i /api/settings (skjold_settings.js). Valg: liste = indeks,
# bool = På/Av, None = bare visning. «auto_input» er en tilstand, ikke en innstilling (samme som POST /api/auto_input).
SMENU_ITEMS = [("bright", "Lysstyrke", "▣", ["Auto", "Høy", "Middels", "Lav"]),
               ("vmax", "Maks volum", "♪", ["100 %", "90 %", "80 %", "70 %"]),
               ("vstart", "Startvolum", "♪", ["Sist brukt", "20", "30", "40"]),
               ("voice", "Talebeskjed", "♪", bool),
               ("lang", "Språk", "♪", ["Norsk", "English", "Svenska", "Dansk"]),
               ("clock", "Standby-klokke", "▣", bool),
               ("clockStyle", "Klokkestil", "▣", ["Node", "Stor", "Analog", "Ord", "Linje", "Dato"]),
               ("dim", "Dimme etter", "▣", ["Av", "30 s", "1 min"]),
               ("off", "Slukk etter", "▣", ["Av", "2 min", "5 min"]),
               ("led", "LED-ringer", "○", ["Høy", "Middels", "Lav", "Av"]),
               ("auto_input", "Auto-kilde", "⇄", bool),
               ("_name", "Navn", "i", None), ("_lyrion", "Lyrion", "◠", None), ("_version", "Programvare", "i", None),
               ("_close", "Lukk", "×", None)]
SMENU_S = 20.0
smenu = {"open": False, "idx": 0, "until": 0.0}


def _smenu_value(k, kind):
    if k == "_name": return NAME
    if k == "_lyrion": return "Tilkoblet" if lyr.connected else "Frakoblet"
    if k == "_version": return VERSION
    if k == "_close": return ""
    v = state["auto_input"] if k == "auto_input" else settings().get(k)
    if kind is bool: return "På" if v else "Av"
    try: return kind[int(v)]
    except (TypeError, ValueError, IndexError): return str(v)


def smenu_status():
    if not smenu["open"]:
        return None
    return {"open": True, "cat": "INNSTILLINGER", "idx": smenu["idx"], "left": max(0, round(smenu["until"] - time.time(), 1)),
            "rows": [{"k": k, "n": n, "icon": ic, "v": _smenu_value(k, kind)} for k, n, ic, kind in SMENU_ITEMS]}


def smenu_open():
    menu["open"] = False
    smenu.update(open=True, idx=0, until=time.time() + SMENU_S)
    state["ui_event"] = {"name": "settings", "t": time.time()}; write_ctrl()


def smenu_close():
    smenu["open"] = False; write_ctrl()


def smenu_step(d):
    smenu["idx"] = (smenu["idx"] + d) % len(SMENU_ITEMS); smenu["until"] = time.time() + SMENU_S; write_ctrl()


def smenu_press():
    """Trykk = neste verdi for raden (lagres med update_settings, som POST /api/settings)."""
    smenu["until"] = time.time() + SMENU_S
    k, _n, _ic, kind = SMENU_ITEMS[smenu["idx"]]
    if k == "_close":
        smenu_close(); return
    if kind is None:
        return
    if k == "auto_input":
        state["auto_input"] = not state["auto_input"]; changed(); return
    cur = settings().get(k)
    if kind is bool:
        new = not cur
    else:
        try: new = (int(cur) + 1) % len(kind)
        except (TypeError, ValueError): new = 0
    update_settings({k: new})


def setup_buttons():
    if not HW:
        return []
    objs = []
    if BOARD == "radio":
        for i, pin in enumerate(FAV_BTN):   # kort trykk = spill kanal, hold 2 s = lagre det som spiller
            b = _mk(Button, pin, pull_up=True, bounce_time=0.05, hold_time=2.0)
            if not b:
                continue
            _hold_btn(b, lambda n=i + 1: play_preset(n), lambda n=i + 1: save_preset(n))
            objs.append(b)
        src = _mk(Button, RADIO_BTN["source"], pull_up=True, bounce_time=0.05) or _Dummy()
        src.when_pressed = lambda: _safe(lambda: set_input(CYCLE[(CYCLE.index(state["input"]) + 1) % len(CYCLE)] if state["input"] in CYCLE else CYCLE[0]))
        objs.append(src)
        for k, act in (("prev", "previous"), ("next", "next")):
            b = _mk(Button, RADIO_BTN[k], pull_up=True, bounce_time=0.05) or _Dummy()
            b.when_pressed = lambda a=act: _safe(transport, a)
            objs.append(b)
    if BOARD == "node":
        return setup_node_buttons() if NODE_BUTTONS else []
    mcp_btns = {}
    if BOARD == "main" and mcp and mcp.ok:   # knappene via MCP23017 – pollet fra INT-pinnen og hvert 50 ms
        for name, bit in MCP_BTN.items():
            mcp_btns[name] = VButton(hold_time=2.0)
        mcp_btns["power"] = VButton(hold_time=3.0)
        bits = dict(MCP_BTN, power=MCP_BTN_POWER)

        hp_last, hp_since = [state["headphones"]], [time.time()]

        def mcp_poll():
            while True:
                try:
                    pressed = mcp.read_buttons(); now = time.time()
                    for name, vb in mcp_btns.items():
                        if (bits[name] in pressed) != (vb._down is not None) and not vb.when_held:
                            input_event()   # knapper uten _hold_btn (som teller selv)
                        vb.update(bits[name] in pressed, now)
                    # jack-bryteren: kontakten ligger mot OUTL (0 V) uten plugg = lav; plugg inn bryter den = pull-up = høy
                    _safe(lambda: set_overtemp(mcp.read_overtemp()))   # GPB5 høy = for varmt
                    plugged = (MCP_HP_DET not in pressed) != HP_DET_INV
                    if plugged == hp_last[0]:
                        hp_since[0] = now
                    elif now - hp_since[0] > 0.15:   # 150 ms stabilt før vi tror på det
                        hp_last[0] = plugged; hp_since[0] = now
                        _safe(lambda: set_headphones(plugged))
                except Exception as e:
                    print("MCP-knapper:", e, flush=True); time.sleep(1)
                time.sleep(0.03)
        threading.Thread(target=mcp_poll, daemon=True).start()
        bak = _mk(Button, PIN_BTN_BAK, pull_up=True, bounce_time=0.05)
        if bak:
            bak.when_pressed = lambda: _safe(lambda: set_power(not state["power"]))   # strømknappen bak
            objs.append(bak)
    for name, pin in (BTN.items() if not mcp_btns else [(n, None) for n in MCP_BTN]):
        b = mcp_btns[name] if mcp_btns else _mk(Button, pin, pull_up=True, bounce_time=0.05, hold_time=2.0)
        if not b:
            continue
        if USBSW_FRONT and usbsw.enabled and name == "airplay":
            # USB-switch montert: knappen oppe til venstre er «PC 1/2» (kort trykk bytter PC)
            b.when_pressed = lambda: _safe(usbsw.toggle)
        elif USBSW_FRONT and usbsw.enabled and name == "bt":
            # «AIRPLAY/BT»: kort trykk AirPlay → BT (hvis tilkoblet) → Radio (hvis Lyrion) → AirPlay, hold 2 s = BT-parring
            def _cycle():
                order = ["airplay"] + (["bt"] if read_raw().get("bt_device") else []) + (["radio"] if lyr.connected else [])
                cur = state["input"]
                set_input(order[(order.index(cur) + 1) % len(order)] if cur in order else "airplay")
            _hold_btn(b, _cycle, lambda: bt_pairing(not state["bt_pairing"]))
        elif name == "airplay" and BOARD == "main":
            # hovedkortet: knappen oppe til venstre heter «BT». Kort trykk veksler Bluetooth ↔ AirPlay (fra en annen kilde: sist brukte
            # trådløse). Hold 2 s mens Bluetooth er valgt = BT-parring av/på.
            def _wireless():
                if state["input"] == "bt":
                    set_input("airplay")
                elif state["input"] == "airplay":
                    set_input("bt")
                else:
                    set_input(state.get("last_wireless", "bt"))
            _hold_btn(b, _wireless, lambda: bt_pairing(not state["bt_pairing"]) if state["input"] == "bt" else None)
        elif name == "bt" and BOARD == "main":
            # knappen oppe til høyre heter «RADIO»: første trykk velger radio, neste trykk går til neste favoritt (menyen vises)
            def _radio():
                if state["input"] != "radio":
                    set_input("radio")
                else:
                    step_preset(1)
            _hold_btn(b, _radio, menu_open)
        elif name == "airplay":
            # kort trykk: AirPlay; trykk igjen mens AirPlay er valgt = Radio (Lyrion), og tilbake
            _hold_btn(b, lambda: set_input("radio" if state["input"] == "airplay" and lyr.connected else "airplay"),
                      lambda: bt_pairing(not state["bt_pairing"]))   # hold AIRPLAY 2 s = BT-parring av/på
        elif name == "aux" and BOARD == "main":
            b.when_pressed = lambda: _safe(set_input, "aux2" if state["input"] == "aux" else "aux")   # AUX-knappen veksler AUX 1 / AUX 2
        elif name == "usb" and BOARD == "main":
            # USB-knappen: første trykk velger USB-lyd, hvert trykk etterpå bytter USB-huben mellom PC 1 og PC 2 (lyden følger PC-en)
            def _usb():
                if not state["power"] and usbsw.enabled:   # standby: knappen bytter bare PC (huben har strøm, lyset er av)
                    usbsw.toggle()
                elif state["input"] != "usb":
                    set_input("usb")
                elif usbsw.enabled:
                    usbsw.toggle()
            b.when_pressed = lambda: _safe(_usb)
        else:
            b.when_pressed = lambda n=name: _safe(set_input, n)
        objs.append(b)
    p = mcp_btns["power"] if mcp_btns else ((BTN_POWER is not None and _mk(Button, BTN_POWER, pull_up=True, bounce_time=0.05, hold_time=3.0)) or _Dummy())
    _hold_btn(p, lambda: set_power(not state["power"]), lambda: system_reboot(why="POWER holdt"),   # hold 3 s = omstart
              key="reboot", info=lambda: ("Omstart", "Fortsett å holde"))
    objs.append(p)
    vol = _mk(RotaryEncoder, ENC[0], ENC[1], max_steps=0, wrap=False) or _Dummy()
    vol.when_rotated_clockwise = lambda: _safe(lambda: (input_event(), menu_step(1) if menu["open"] else set_volume(state["volume"] + 2)))
    vol.when_rotated_counter_clockwise = lambda: _safe(lambda: (input_event(), menu_step(-1) if menu["open"] else set_volume(state["volume"] - 2)))
    objs.append(vol)
    sw = _mk(Button, ENC[2], pull_up=True, bounce_time=0.05, hold_time=1.0) or _Dummy()

    def sw_released():
        if menu["open"]:
            menu_pick()                      # trykk i menyen = spill kanalen
        else:
            set_mute(not state["mute"])      # ellers mute som før

    def sw_held():
        if menu["open"]:
            menu_save()                      # hold i menyen = lagre det som spiller på plassen
        elif state["input"] == "radio" or lyr.connected:
            if state["input"] != "radio":
                set_input("radio")
            menu_open()                      # hold 1 s = kanalmeny

    _hold_btn(sw, sw_released, sw_held)
    objs.append(sw)
    print(f"Knapper klare ({BOARD}): " + (", ".join(f"{n}=GPIO{p}" for n, p in BTN.items()) + (f", power=GPIO{BTN_POWER}" if BTN_POWER is not None else ", power=bare knapp bak (MCP mangler)") if not mcp_btns else "via MCP23017 + knapp bak GPIO 15") + f", encoder={ENC}", flush=True)
    return objs


def setup_node_buttons():
    """Skjold Node: RADIO, AIR·BT, ◀◀, ▶▶ (til GND, intern pull-up) + EC11. Ingen strømknapp."""
    objs, btn = [], {}
    for k, pin in NODE["btn"].items():
        b = _mk(Button, pin, pull_up=True, bounce_time=NODE["bounce"], hold_time=NODE["hold"].get(k, 2.0))
        if b:
            btn[k] = b; objs.append(b)

    def _radio_short():   # første trykk = radio, så neste favoritt (menyen på skjermen)
        if state["input"] != "radio":
            set_input("radio")
            menu_open()
        elif menu["open"]:
            menu_step(1)
        else:
            menu_open(); menu_step(1)

    def _radio_held():    # hold = spill favoritten som er valgt (tom plass i menyen + radio spiller = lagre der)
        if menu["open"] and not state["presets"][menu["idx"] - 1] and state["input"] == "radio" and lyr.info.get("url"):
            menu_save()
        elif menu["open"]:
            menu_pick()
        elif state["preset"]:
            play_preset(state["preset"])
        else:
            set_input("radio")

    def _wireless():      # AirPlay ↔ Bluetooth (fra radio/Spotify: sist brukte trådløse)
        if state["input"] == "bt":
            set_input("airplay")
        elif state["input"] == "airplay":
            set_input("bt")
        else:
            set_input(state.get("last_wireless", "airplay"))

    def _pair():
        if not state["bt_pairing"] and state["input"] != "bt":
            set_input("bt", announce=False)
        bt_pairing(not state["bt_pairing"]); apply_input()

    def _radio_info():
        if menu["open"]:
            n = menu["idx"]; p = state["presets"][n - 1]
            if p:
                return (f"Spill favoritt {n}", p.get("title") or f"Kanal {n}")
            if state["input"] == "radio" and lyr.info.get("url"):
                return (f"Lagre på plass {n}", lyr.info.get("station") or "Det som spiller nå")
            return None
        if state["preset"] and state["presets"][state["preset"] - 1]:
            return (f"Spill favoritt {state['preset']}", state["presets"][state["preset"] - 1].get("title", ""))
        return None

    if "radio" in btn:
        _hold_btn(btn["radio"], _radio_short, _radio_held, key="radio", info=_radio_info)
    if "airbt" in btn:
        _hold_btn(btn["airbt"], _wireless, _pair, key="src",
                  info=lambda: ("Stopp paring", "Fortsett å holde") if state["bt_pairing"] else ("Blåtann-paring", "Fortsett å holde"))

    def _both_held():     # hold ◀◀ og ▶▶ samtidig = omstart
        if all(k in btn and btn[k].is_pressed for k in ("prev", "next")):
            system_reboot(why="◀◀ + ▶▶ holdt")

    def _both_track():    # fremdrift for «hold begge» regnes fra da den andre knappen ble trykket
        if all(k in btn and btn[k].is_pressed for k in ("prev", "next")):
            _press.setdefault("reboot", {"t0": time.time(), "dur": float(NODE["hold"].get("next", 3.0)),
                                         "info": lambda: ("Omstart", "Hold begge")})
        else:
            _press.pop("reboot", None)

    def _skip(act):
        if state["bt_pairing"] and act == "previous":   # ◀◀ avbryter paringen (som skjermen sier)
            bt_pairing(False); apply_input()
        elif smenu["open"]:
            smenu_step(1 if act == "next" else -1)
        elif menu["open"] and state["input"] == "radio":
            menu_step(1 if act == "next" else -1)
        elif any(btn[k].is_pressed for k in ("prev", "next") if k in btn):
            return   # den andre knappen holdes fortsatt (på vei mot «hold begge»)
        else:
            transport(act)

    for k, act in (("prev", "previous"), ("next", "next")):
        if k in btn:
            _hold_btn(btn[k], lambda a=act: _skip(a), _both_held, on_change=_both_track)

    def _enc(d):          # vri: innstillingsmeny > radiomeny > volum
        input_event()
        if smenu["open"]:
            smenu_step(d)
        elif menu["open"]:
            menu_step(d)
        else:
            set_volume(state["volume"] + 2 * d)
    vol = _mk(RotaryEncoder, ENC[0], ENC[1], max_steps=0, wrap=False) or _Dummy()
    vol.when_rotated_clockwise = lambda: _safe(_enc, 1)
    vol.when_rotated_counter_clockwise = lambda: _safe(_enc, -1)
    objs.append(vol)
    sw = _mk(Button, ENC[2], pull_up=True, bounce_time=NODE["bounce"], hold_time=NODE["enc_hold"]) or _Dummy()

    def _sw_short():      # trykk = spill/pause (i radiomenyen: spill valgt, i innstillingene: endre verdi)
        if smenu["open"]:
            smenu_press()
        elif menu["open"]:
            menu_pick()
        else:
            transport("playpause")

    def _sw_held():       # hold 3 s = innstillinger av/på
        smenu_close() if smenu["open"] else smenu_open()

    _hold_btn(sw, _sw_short, _sw_held, key="knob",
              info=lambda: ("Lukk innstillinger", "Fortsett å holde") if smenu["open"] else ("Innstillinger", "Fortsett å holde"))
    objs.append(sw)
    print("Knapper klare (node): " + ", ".join(f"{k}=GPIO{p}" for k, p in NODE["btn"].items())
          + f", encoder={ENC}, LED-ringer=" + ", ".join(f"{k}=GPIO{p}" for k, p in NODE["led"].items()), flush=True)
    return objs


# ---------- potensiometer som volumknapp (test uten ADC: RC-tidsmåling) ----------
# KI_AMP_POT=rc:24  -> pot (VCC→3,3 V, OUT→node), node→kondensator→GND, node→220 Ω→GPIO 24
# Pi-en har ingen analog inngang, så vi lader kondensatoren gjennom poten og måler tiden til GPIO-en leser «høy».
def pot_thread(pin, invert=False):
    try:
        import lgpio
        h = lgpio.gpiochip_open(0)
    except Exception as e:
        print("Potensiometer av (lgpio):", e, flush=True); return
    def _free():
        try:
            lgpio.gpio_free(h, pin)
        except Exception:
            pass   # ikke tatt ennå (første runde)
    lo, hi, avg, last = None, None, None, None
    print(f"Potensiometer på GPIO {pin} (RC) – vri helt rundt én gang for kalibrering", flush=True)
    while True:
        try:
            _free(); lgpio.gpio_claim_output(h, pin, 0); time.sleep(0.02)   # tøm kondensatoren
            _free(); lgpio.gpio_claim_input(h, pin)
            t0 = time.perf_counter()
            while lgpio.gpio_read(h, pin) == 0 and time.perf_counter() - t0 < 0.25:
                pass
            t = time.perf_counter() - t0
            if t >= 0.25 or t < 0.00002:   # ikke koblet til (pinnen henger lav/høy) – ikke rør volumet
                time.sleep(0.5); continue
            avg = t if avg is None else avg * 0.7 + t * 0.3
            lo = avg if lo is None else min(lo, avg); hi = avg if hi is None else max(hi, avg)
            if hi - lo > 0.0005:
                v = round(100 * (1 - (avg - lo) / (hi - lo)))                # lav tid (lav motstand) = høyt volum
                if invert:
                    v = 100 - v
                if last is None or abs(v - last) >= 2:
                    if last is not None:
                        set_volume(v)
                    last = v
        except Exception as e:
            print("Potensiometer:", e, flush=True); time.sleep(1)
        time.sleep(0.05)


async def pairing_task():
    """BT-LED pulserer under parring, og parring slås av etter 2 min eller når en enhet kobler til."""
    import math
    while True:
        if state["bt_pairing"]:
            dev = read_status().get("bt_device", "")
            if time.time() > _pairing_until:
                bt_pairing(False, "timeout"); apply_input()
            elif dev and dev != _pairing_known:   # en ny enhet koblet til
                bt_pairing(False, "connected"); apply_input()
            elif HW and "airbt" in node_leds:
                node_leds["airbt"].value = (math.sin(time.time() * 2 * math.pi * 1.1) + 1) / 2 * led_scale()
            elif HW and "bt" in leds:
                leds["bt"].value = (math.sin(time.time() * 2 * math.pi * 1.1) + 1) / 2 > 0.5 and led_scale() > 0
        await asyncio.sleep(0.05)


# ---------- HTTP ----------
def j(_r=None):
    return web.json_response(read_status())


async def h_status(_r): return j()
async def h_power(r): set_power((await r.json()).get("on", True)); return j()
async def h_toggle(_r): set_power(not state["power"]); return j()
async def h_input(r):
    inp = (await r.json()).get("input", "")
    if inp not in INPUTS:
        return web.json_response({"error": f"input må være en av {INPUTS}"}, status=400)
    set_input(inp); return j()
async def h_volume(r):
    b = await r.json()
    if b.get("source") == "airplay" and not (state["input"] == "airplay" or state["auto_input"]):
        return j()   # AirPlay-volum skal ikke styre en annen valgt kilde
    set_volume(state["volume"] + int(b["delta"]) if "delta" in b else int(b.get("volume", state["volume"]))); return j()
async def h_mute(r): set_mute((await r.json()).get("mute", True)); return j()
async def h_bt(r): bt_pairing((await r.json()).get("pairing", True)); return j()
async def h_voice(r):
    b = await r.json()
    if "on" in b:
        set_voice(b["on"])
    if b.get("profile"):   # {"profile": "en" | "no" | "trondersk"}
        try:
            set_voice_profile(b["profile"])
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
    if b.get("say"):   # test: {"say":"bt_pairing"}
        voice.say(b["say"])
    return j()


async def h_cover(_r):
    try:
        with open(COVER_RADIO if state["input"] == "radio" else COVER_FILE, "rb") as fh:
            img = fh.read()
    except OSError:
        return web.Response(status=404)
    ctype = "image/png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return web.Response(body=img, content_type=ctype, headers={"Cache-Control": "max-age=3600"})




def follow_source():
    """Bytt kilde automatisk når AirPlay eller Bluetooth begynner å spille (som en vanlig forsterker med auto-input)."""
    last = (None, False)
    last_dev = None
    tick = 0
    while True:
        time.sleep(1)
        tick += 1
        if LEVELS_ON and tick % 5 == 0:   # softvol-kontrollene finnes først når kilden har åpnet lyd – sett nivåene jevnlig
            _safe(apply_levels)
        if node_leds:   # ◀◀/▶▶-ringene følger «spiller nå»
            _safe(apply_node_leds)
        try:
            st = read_raw()          # rå AirPlay/BT-status – også når Radio er valgt
            dev = st.get("bt_device", "")
            if last_dev is not None and dev != last_dev and state["power"]:
                if dev:
                    voice.say("bt_connected", name=dev)
                else:
                    voice.say("bt_disconnected")
            last_dev = dev
            cur = (st.get("source"), bool(st.get("playing")))
            if lyr.info.get("mode") == "play" and state["input"] != "radio" and not st.get("playing"):
                cur = ("radio", True)
            if state["auto_input"] and cur != last and cur[1] and cur[0] in ("airplay", "bt", "radio") and state["power"] and state["input"] != cur[0]:
                print("Auto-kilde:", cur[0], flush=True)
                set_input(cur[0], announce=False)
            last = cur
        except Exception as e:
            print("Auto-kilde:", e, flush=True)


# ---------- Spotify Connect (librespot --onevent → POST /api/spotify) ----------
def spotify_stop():
    """librespot har ingen pause-API – start tjenesten på nytt (stopper avspillingen, enheten dukker opp igjen i appen)."""
    if spotify["playing"]:
        spotify.update(playing=False, paused=False)
        subprocess.run(["systemctl", "restart", "ki-spotify"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ms(v):
    try:
        return int(float(v)) // 1000
    except (TypeError, ValueError):
        return 0


_spotify_conn = [0.0]


def spotify_event(b):
    ev = str(b.get("event") or b.get("player_event") or "").strip().lower()
    was = spotify["playing"]
    spotify.update(event=ev, t=time.time())
    if ev in ("session_connected", "session_client_changed"):
        spotify.update(connected=True, user=b.get("user_name", spotify["user"]))
        _spotify_conn[0] = time.time()
    elif ev == "volume_changed" and b.get("volume") not in (None, ""):
        # Volumet i Spotify-appen følger daemonvolumet (som AirPlay-pvol). librespot kjører med --volume-ctrl fixed
        # (lyden skaleres ikke to ganger); de første 3 s etter tilkobling ignoreres (librespot melder --initial-volume).
        try:
            v = round(int(float(b["volume"])) * 100 / 65535)
        except (TypeError, ValueError):
            v = None
        if v is not None and state["input"] == "spotify" and time.time() - _spotify_conn[0] > 3:
            set_volume(v)
    elif ev == "session_disconnected":
        spotify.update(connected=False, playing=False, paused=False)
    elif ev in ("playing", "started"):
        spotify.update(playing=True, paused=False, connected=True)
    elif ev == "paused":
        spotify.update(playing=False, paused=True)
    elif ev in ("stopped", "unavailable"):
        spotify.update(playing=False, paused=False)
    if b.get("name"):
        spotify["title"] = str(b["name"])
    if b.get("artists"):
        spotify["artist"] = ", ".join(str(b["artists"]).split("\n"))
    if b.get("album"):
        spotify["album"] = str(b["album"])
    if b.get("covers"):
        spotify["cover"] = str(b["covers"]).split("\n")[0]
    if b.get("duration_ms") not in (None, ""):
        spotify["duration"] = _ms(b["duration_ms"])
    if b.get("position_ms") not in (None, ""):
        spotify["position"] = _ms(b["position_ms"])
    if spotify["playing"] and not was and state["auto_input"] and state["power"] and state["input"] != "spotify" and "spotify" in INPUTS:
        print("Auto-kilde: spotify", flush=True)
        set_input("spotify", announce=False)
    else:
        apply_input(); write_ctrl()


async def h_spotify(r):
    try:
        b = await r.json()
    except Exception:
        b = dict(await r.post())
    if not isinstance(b, dict) or not (b.get("event") or b.get("player_event")):
        return web.json_response({"error": "mangler event"}, status=400)
    spotify_event(b)
    return web.json_response(dict(spotify))


async def h_spotify_get(_r): return web.json_response(dict(spotify))


async def h_transport(r):
    a = (await r.json()).get("action", "")
    if a not in TRANSPORT:
        return web.json_response({"error": f"action må være en av {sorted(TRANSPORT)}"}, status=400)
    try:
        await asyncio.get_running_loop().run_in_executor(None, transport, a)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    await asyncio.sleep(0.6)   # la metadata rekke å oppdatere seg
    return j()
async def h_loudness(r):
    b = await r.json(); set_loudness(b.get("on"), b.get("level")); return j()


# ---------- Lyrion Music Server (radio via Squeezelite) ----------
LMS_SERVER = os.environ.get("KI_AMP_LMS_SERVER", "").strip()
LMS_PORT = int(os.environ.get("KI_AMP_LMS_PORT", "9000"))


def _player_mac():
    if os.environ.get("KI_AMP_LMS_PLAYER"):
        return os.environ["KI_AMP_LMS_PLAYER"].lower()
    try:
        return open("/sys/class/net/eth0/address").read().strip().lower()   # samme -m som ki-squeezelite.service
    except OSError:
        return "00:00:00:00:00:01"


class Lyrion:
    """Tynn JSON-RPC-klient mot Lyrion + poller for stasjon, låt og stasjonsbilde."""

    def __init__(self):
        self.host = LMS_SERVER or None
        self.port = LMS_PORT
        self.player = _player_mac()
        self.info = {}
        self.connected = False
        self.cover_id = ""
        self._art = None
        self._vol_ok = False
        if os.environ.get("KI_AMP_LMS", "1") == "1":
            threading.Thread(target=self._run, daemon=True).start()

    def discover(self):
        """Lyrions UDP-oppdagelse (port 3483) – svaret gir JSON-porten."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); s.settimeout(2)
        try:
            s.sendto(b"eIPAD\0NAME\0JSON\0", ("255.255.255.255", 3483))
            data, addr = s.recvfrom(1024)
            i, port = 1, LMS_PORT
            while i + 5 <= len(data):
                tag, ln = data[i:i + 4], data[i + 4]; val = data[i + 5:i + 5 + ln]; i += 5 + ln
                if tag == b"JSON":
                    port = int(val.decode())
            self.host, self.port = addr[0], port
            print("Lyrion funnet:", self.host, self.port, flush=True)
        except OSError:
            pass
        finally:
            s.close()

    def rpc(self, cmd, player=True):
        if not self.host:
            raise RuntimeError("Lyrion ikke funnet (sett KI_AMP_LMS_SERVER)")
        body = json.dumps({"id": 1, "method": "slim.request", "params": [self.player if player else "", cmd]}).encode()
        req = urllib.request.Request(f"http://{self.host}:{self.port}/jsonrpc.js", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return json.loads(r.read()).get("result", {})

    def cmd(self, c):
        try:
            self.rpc(c)
        except Exception as e:
            print("Lyrion:", e, flush=True)

    def url(self, path):
        if not path:
            return ""
        return path if path.startswith("http") else f"http://{self.host}:{self.port}/{path.lstrip('/')}"

    def favorites(self):
        r = self.rpc(["favorites", "items", 0, 100, "want_url:1"], player=False)
        out = []
        for it in r.get("loop_loop", []):
            if int(it.get("isaudio", 0)) and it.get("url"):
                out.append({"title": it.get("name", ""), "url": it["url"], "icon": self.url(it.get("image", ""))})
        return out

    def _run(self):
        last_try = 0
        while True:
            time.sleep(1.5)
            if not self.host:
                if time.time() - last_try > 30:
                    last_try = time.time(); self.discover()
                continue
            try:
                r = self.rpc(["status", "-", 1, "tags:aAlcKNjJxuo"])
                loop = (r.get("playlist_loop") or [{}])[0]
                station = r.get("current_title") or loop.get("remote_title") or ""
                song, artist = loop.get("title", ""), loop.get("artist", "")
                if song and not artist and " - " in song and int(r.get("remote", 0) or 0):
                    artist, song = song.split(" - ", 1)
                if song == station:
                    song = ""
                art = loop.get("artwork_url") or (f"music/{loop['coverid']}/cover.jpg" if loop.get("coverid") else "")
                self.info = {"mode": r.get("mode", "stop"), "station": station or loop.get("album", ""), "song": song,
                             "artist": artist, "url": loop.get("url", ""), "art": self.url(art),
                             "duration": float(r.get("duration", 0) or 0), "time": float(r.get("time", 0) or 0)}
                if not self.connected:
                    print("Lyrion tilkoblet, spiller", self.player, flush=True)
                self.connected = True
                self._sync_volume(r)
                self._fetch_art()
                if not any(state["presets"]):
                    favs = self.favorites()[:6]
                    if favs:
                        state["presets"] = favs + [None] * (6 - len(favs)); changed()
                        print("Radiokanaler hentet fra Lyrion-favoritter:", [f["title"] for f in favs], flush=True)
                if state["input"] == "radio":
                    write_ctrl()
            except urllib.error.HTTPError as e:
                self.connected = False; print("Lyrion:", e, flush=True); time.sleep(10)
            except Exception as e:
                if self.connected:
                    print("Lyrion borte:", e, flush=True)
                self.connected = False; self.info = {}
                if not LMS_SERVER:
                    self.host = None

    def _sync_volume(self, r):
        """Volumet ligger i CamillaDSP. Lyrion settes til «fast utnivå» (Squeezelite får alltid 100 %), men glideren i
        Lyrion speiler forsterkerens volum: endres den i Lyrion, tar vi det over – endres det her, flyttes glideren."""
        v = r.get("mixer volume")
        if v is None:
            return
        v = abs(int(float(v)))   # negativt = mutet i Lyrion
        if not self._vol_ok:
            self.rpc(["playerpref", "digitalVolumeControl", "0"])   # «Output level is fixed at 100%»
            self._vol_ok = True; self._lms_vol = None
        if self._lms_vol is not None and v != self._lms_vol:      # noen dro i glideren i Lyrion
            self._lms_vol = v
            if state["input"] == "radio":
                set_volume(v)
        elif v != state["volume"]:                                # vårt volum er endret – vis det i Lyrion
            self.rpc(["mixer", "volume", state["volume"]])
            self._lms_vol = state["volume"]
        else:
            self._lms_vol = v

    def _fetch_art(self):
        art = self.info.get("art", "")
        if art == self._art:
            return
        self._art = art
        if not art:
            self.cover_id = ""; return
        try:
            with urllib.request.urlopen(art, timeout=5) as r:
                img = r.read()
            with open(COVER_RADIO + ".tmp", "wb") as fh:
                fh.write(img)
            os.replace(COVER_RADIO + ".tmp", COVER_RADIO)
            self.cover_id = hashlib.sha1(img).hexdigest()[:12]
        except Exception as e:
            print("Stasjonsbilde:", e, flush=True); self.cover_id = ""


lyr = Lyrion()


def play_preset(n, announce=True):
    p = state["presets"][n - 1] if 1 <= n <= 6 else None
    if not p:
        raise RuntimeError(f"radiokanal {n} er ikke lagret")
    if not state["power"]:
        set_power(True)
    lyr.rpc(["playlist", "play", p["url"], p.get("title", "")])
    lyr.info = {**lyr.info, "mode": "play", "station": p.get("title", ""), "song": "", "artist": "", "url": p["url"]}
    state["preset"] = n
    set_input("radio", announce=False)
    apply_input(); changed()
    if announce:
        voice.say("radio_preset", n=n, name=p.get("title") or f"kanal {n}")


def step_preset(d):
    filled = [i + 1 for i, p in enumerate(state["presets"]) if p]
    if not filled:
        raise RuntimeError("ingen radiokanaler lagret")
    cur = state["preset"] if state["preset"] in filled else filled[0] - (1 if d > 0 else -1)
    idx = (filled.index(cur) + d) % len(filled) if cur in filled else (0 if d > 0 else len(filled) - 1)
    play_preset(filled[idx])


def save_preset(n):
    i = lyr.info
    if not i.get("url"):
        raise RuntimeError("ingen radiokanal spiller nå")
    state["presets"][n - 1] = {"title": i.get("station") or i.get("song") or f"Kanal {n}", "url": i["url"], "icon": i.get("art", "")}
    state["preset"] = n
    toast("Lagret", f"{state['presets'][n - 1]['title']} på plass {n}", saved=n)
    apply_input(); changed()
    voice.say("radio_saved", n=n)


async def h_auto_input(r):
    state["auto_input"] = bool((await r.json()).get("on", True)); changed(); return j()


async def h_usbsw(r):
    b = await r.json()
    try:
        if b.get("toggle"):
            await asyncio.get_running_loop().run_in_executor(None, usbsw.toggle)
        else:
            pc = int(b.get("pc", 0))
            if pc not in (1, 2):
                return web.json_response({"error": "pc må være 1 eller 2"}, status=400)
            await asyncio.get_running_loop().run_in_executor(None, usbsw.set, pc)
    except RuntimeError as e:
        return web.json_response({"error": str(e)}, status=409)
    return j()


async def h_level(r):
    b = await r.json()
    try:
        set_level(b.get("source", ""), int(b.get("level", 100)))
    except (ValueError, TypeError) as e:
        return web.json_response({"error": str(e)}, status=400)
    return j()


async def h_hp_automute(r):
    set_hp_automute(bool((await r.json()).get("on", True))); return j()


async def h_mix(r):
    on = bool((await r.json()).get("on", False))
    if on != state["mix"]:
        voice.say("mix_on" if on else "mix_off")
    state["mix"] = on; changed(); return j()


async def h_menu(r):
    b = await r.json()
    a = b.get("action")
    {"open": menu_open, "close": menu_close, "pick": menu_pick, "save": menu_save,
     "up": lambda: menu_step(-1), "down": lambda: menu_step(1)}.get(a, lambda: None)()
    return web.json_response({"menu": menu})


async def h_presets(_r):
    return web.json_response({"presets": state["presets"], "active": state["preset"], "lyrion": lyr.connected})


async def h_preset(r):
    b = await r.json()
    n = int(b.get("n", 0))
    if not 1 <= n <= 6:
        return web.json_response({"error": "n må være 1–6"}, status=400)
    try:
        fn = save_preset if b.get("save") else play_preset
        await asyncio.get_running_loop().run_in_executor(None, fn, n)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    await asyncio.sleep(1.0)
    return j()


async def h_presets_set(r):
    b = await r.json()
    try:
        if b.get("import"):
            favs = await asyncio.get_running_loop().run_in_executor(None, lyr.favorites)
            state["presets"] = (favs[:6] + [None] * 6)[:6]
        elif isinstance(b.get("presets"), list):
            state["presets"] = ([p if p and p.get("url") else None for p in b["presets"]] + [None] * 6)[:6]
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    changed()
    return web.json_response({"presets": state["presets"], "active": state["preset"]})


# ---------- avspillingskontroll (AirPlay via Shairport Sync D-Bus, Bluetooth via BlueZ AVRCP) ----------
TRANSPORT = {"play", "pause", "playpause", "next", "previous", "stop"}
SPS = ("org.gnome.ShairportSync", "/org/gnome/ShairportSync", "org.gnome.ShairportSync.RemoteControl")
SPS_CMD = {"play": "Play", "pause": "Pause", "playpause": "PlayPause", "next": "Next", "previous": "Previous", "stop": "Stop"}
BT_CMD = {"play": "Play", "pause": "Pause", "next": "Next", "previous": "Previous", "stop": "Stop"}


def _busctl(*args):
    r = subprocess.run(["busctl", "--system", *args], capture_output=True, text=True, timeout=4)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or "busctl feilet")
    return r.stdout


def _bt_player():
    out = _busctl("tree", "--list", "org.bluez")
    players = [l.strip() for l in out.splitlines() if re.search(r"/dev_[0-9A-F_]+/player\d+$", l.strip())]
    if not players:
        raise RuntimeError("ingen Bluetooth-enhet med avspillingskontroll tilkoblet")
    return players[0]


def transport(action):
    if state["input"] == "radio":
        if action in ("next", "previous"):
            step_preset(1 if action == "next" else -1); return
        lyr.cmd({"play": ["play"], "pause": ["pause", "1"], "playpause": ["pause"], "stop": ["stop"]}[action])
        if action == "play" and lyr.info.get("mode") == "stop" and state["preset"]:
            play_preset(state["preset"])
        return
    st = read_status()
    if state["input"] == "spotify" or st.get("source") == "spotify":
        if action in ("pause", "stop") or (action == "playpause" and spotify["playing"]):
            spotify_stop(); return
        raise RuntimeError("Spotify styres fra Spotify-appen (librespot har ingen fjernstyring)")
    src = st.get("source") or ("bt" if state["input"] == "bt" else "airplay")
    if src == "bt" or state["input"] == "bt":
        if action == "playpause":
            action = "pause" if st.get("playing") else "play"
        _busctl("call", "org.bluez", _bt_player(), "org.bluez.MediaPlayer1", BT_CMD[action])
    else:
        _busctl("call", SPS[0], SPS[1], SPS[2], SPS_CMD[action])


def _local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def start_mdns():
    try:
        from zeroconf import ServiceInfo, Zeroconf
        info = ServiceInfo("_kipultamp._tcp.local.", f"{NAME}._kipultamp._tcp.local.",
                           addresses=[socket.inet_aton(_local_ip())], port=PORT,
                           properties={"id": socket.gethostname(), "version": VERSION, "name": NAME, "type": "pultforsterker"},
                           server=f"{socket.gethostname()}.local.")
        zc = Zeroconf(); zc.register_service(info)
        print(f"mDNS: {NAME}._kipultamp._tcp på {_local_ip()}:{PORT}", flush=True); return zc
    except Exception as e:
        print("mDNS ikke startet:", repr(e), flush=True); return None


async def on_startup(app):
    # zeroconf sin synkrone API kan ikke kalles fra aiohttp-løkka (gir EventLoopBlocked etter 10 s) – kjør i egen tråd
    app["zc"] = await asyncio.get_running_loop().run_in_executor(None, start_mdns)
    app["btn"] = setup_buttons()
    app["pair"] = asyncio.create_task(pairing_task())
    app["menu"] = asyncio.create_task(menu_task())


async def on_cleanup(app):
    if app.get("zc"):
        await asyncio.get_running_loop().run_in_executor(None, app["zc"].close)


def main():
    load_state()
    if state["input"] not in INPUTS:   # f.eks. «aux» lagret fra et annet kort
        state["input"] = "airplay"
    state["usbsw"], state["usb_pc_names"] = False, USBSW_NAMES
    state["voice_profiles"] = VOICE_PROFILES
    if state.get("voice_profile") not in VOICE_PROFILES:
        state["voice_profile"] = "en"
    threading.Thread(target=voice.warm, daemon=True).start()   # etter load_state: riktig profil
    apply_settings()   # navn på USB-switch, maksvolum osv. fra lagrede innstillinger
    usbsw.start()
    if settings()["vstart"] and str(settings()["vstart"]).isdigit() and VSTART[int(settings()["vstart"])]:
        state["volume"] = VSTART[int(settings()["vstart"])]   # startvolum
    apply_power(); changed()
    if BOARD == "node" and HW and NAME == NAME_ENV:   # Blåtann-navnet følger spillernavnet («Skjold Node»); ellers apply_name
        threading.Thread(target=lambda: subprocess.run(["bluetoothctl", "system-alias", NAME], check=False, timeout=10,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()
    threading.Thread(target=follow_source, daemon=True).start()   # auto-kilde (kan slås av) + BT-talemeldinger
    pot = os.environ.get("KI_AMP_POT", "")
    if pot.startswith("rc:"):   # rc:24 eller rc:24:inv (snu retningen)
        parts = pot.split(":")
        threading.Thread(target=pot_thread, args=(int(parts[1]), len(parts) > 2 and parts[2] == "inv"), daemon=True).start()
    app = web.Application()
    app.add_routes([web.get("/api/status", h_status), web.post("/api/power", h_power), web.post("/api/toggle", h_toggle),
                    web.post("/api/input", h_input), web.post("/api/volume", h_volume), web.post("/api/mute", h_mute),
                    web.post("/api/bt", h_bt), web.post("/api/loudness", h_loudness), web.post("/api/transport", h_transport), web.get("/api/cover", h_cover), web.post("/api/voice", h_voice),
                    web.get("/api/presets", h_presets), web.post("/api/preset", h_preset), web.post("/api/presets", h_presets_set), web.post("/api/menu", h_menu), web.post("/api/auto_input", h_auto_input), web.post("/api/mix", h_mix), web.post("/api/usbsw", h_usbsw), web.post("/api/level", h_level), web.post("/api/hp_automute", h_hp_automute),
                    web.get("/api/settings", h_settings_get), web.post("/api/settings", h_settings_post),
                    web.post("/api/spotify", h_spotify), web.get("/api/spotify", h_spotify_get), web.post("/api/reboot", h_reboot)])
    # web-app (PWA) for mobil/PC: http://<pi>:8765/  (filer i pi/webapp)
    webdir = os.environ.get("KI_AMP_WEBAPP", "")
    for cand in ([webdir] if webdir else []) + ["/usr/local/share/ki-amp/webapp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")]:
        if cand and os.path.isdir(cand):
            webdir = cand; break
    if webdir and os.path.isdir(webdir):
        root = os.path.realpath(webdir)
        mimetypes.add_type("application/manifest+json", ".webmanifest"); mimetypes.add_type("image/svg+xml", ".svg")
        mimetypes.add_type("text/javascript", ".js"); mimetypes.add_type("font/woff2", ".woff2")

        async def h_index(_r): return web.FileResponse(os.path.join(root, "index.html"), headers={"Cache-Control": "no-cache"})

        async def h_web(r):
            """Hele web-app-mappa på '/' (icons/, manifest.webmanifest, assets/ …). Ingen sti ut av mappa."""
            rel = r.match_info.get("path", "")
            if rel.startswith("api/") or "\x00" in rel: raise web.HTTPNotFound()
            full = os.path.realpath(os.path.join(root, rel))
            if full != root and not full.startswith(root + os.sep): raise web.HTTPNotFound()
            if os.path.isdir(full): full = os.path.join(full, "index.html")
            if not os.path.isfile(full): raise web.HTTPNotFound()
            ct = mimetypes.guess_type(full)[0] or "application/octet-stream"
            cache = "no-cache" if full.endswith((".html", ".webmanifest")) or os.path.basename(full) in ("sw.js", "service-worker.js") else "max-age=3600"
            return web.FileResponse(full, headers={"Cache-Control": cache, "Content-Type": ct})
        app.add_routes([web.get("/", h_index), web.get("/index.html", h_index), web.static("/app", root),
                        web.get("/{path:.+}", h_web)])   # sist: /api/* og /app/ vinner
    app.on_startup.append(on_startup); app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)


if __name__ == "__main__":
    main()
