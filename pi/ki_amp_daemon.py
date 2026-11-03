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
  GET  /api/cover  (albumbilde fra AirPlay/Blåtann, eller Lyrion når Radio er valgt; jpg/png, ETag = status["cover"])
  GET  /api/events  Server-Sent Events: «data: <samme JSON som /api/status>» straks noe endrer seg (sjekkes hvert 0,25 s),
                    ellers «: ping» hvert 15 s. Appen bruker dette i stedet for polling når det virker.
  Status har også: "product": "s1"|"node"|"core"|… (S1 = hovedkortet, Core = node med KI_AMP_NODE_GPIO=0),
                   "cover_url": relativ /api/cover?v=<hash> eller full https-URL (Spotify), "" uten bilde.
  CORS: alle /api/* svarer med Access-Control-Allow-Origin (+ OPTIONS-preflight og Private Network Access),
        så appen (capacitor://localhost, https://localhost) og andre web-UI kan bruke API-et direkte.
  POST /api/transport {"action":"play|pause|playpause|next|previous|stop"}  (AirPlay/Bluetooth/Radio)
  GET/POST /api/sky  Skjold-hjem (docs/SKJOLD_HJEM.md): {koblet, sted, stedNavn, aktivHoved, erHoved, tilkoblet};
                    POST {"kode":"K7Q2XM"} kobler enheten til et sted, {"koble_fra":true} kobler fra. Nøkkel i
                    /var/lib/ki-amp/sky.json (0600). Sky-adresse: KI_AMP_SKY_URL; KI_AMP_SKY=0 slår modulen av.
                    Status har "sky": {koblet, sted, erAktivHoved}.
  Radiofavoritter: inntil 50 (PRESETS_MAX). state["presets"] har alltid minst 6 plasser (None = tom plass, de 6 første
  er «knappeplassene» på S1/radiokortet) og vokser når flere legges til. Hver favoritt: {title,url,icon,genre}.
  GET  /api/presets                       {"presets":[{n,title,url,icon,image,genre}|null…], "items":[bare fylte],
                                           "count","max":50,"active","lyrion"}
  POST /api/preset  {"n":1-50}            spill kanal n  |  {"n":…, "save":true} lagre det som spiller nå på plass n
  POST /api/presets {"import":true}       hent favorittene (inntil 50) fra Lyrion | {"presets":[{title,url,icon}…]} erstatt alle
  POST /api/presets {"title","url","genre"?,"image"?}   legg til favoritt (første tomme plass, ellers bakerst).
                                          201 {"ok":true,"n":…, ...GET-svaret}; 400 ved manglende url eller fullt (50)
  PUT|POST /api/presets/order {"order":[n…]}   ny rekkefølge (gamle plassnumre, 1-basert; utelatte havner bakerst)
  DELETE /api/presets/{n}                 slett favoritt n (resten rykker opp)
  POST /api/presets/{n}/play              spill favoritt n (som POST /api/preset {"n":n})
  GET  /api/radio/search?q=…              {"q","norway":[st…],"world":[st…],"offline":bool} fra Radio Browser (cache 10 min)
  GET  /api/radio/browse                  {"shelves":[{"id","title","items":[st…]}…],"offline":bool}
                                          id: popular_no, pop, news, classical, jazz, rock, local
         st = {"id"(stationuuid),"name","genre","url"(url_resolved),"image"(favicon),"country"(kode),"codec","bitrate"}
  POST /api/radio/play {"url","title","image"?,"genre"?}   spill en kanal som ikke er favoritt (via Lyrion)
  Status: "lyrion": bool (tilkoblet), "lyrion_server": "host:port" for Lyrion JSON-RPC ("" når ikke funnet) – brukes av iOS-appen
          (skjold/ios) til rom/synk og Lyrion-knappen i Kilder. "lyrion_player": Squeezelite-spillerens MAC/playerid i Lyrion.
  Status: "presets" = [{n,title}…] (alle plasser), "presets_count" (antall fylte), "presets_max" (50),
          "radio_now": {"name","genre","now","image","url","n"(favoritt-nr, 0 = ikke favoritt),"playing"} | null
  KI_AMP_RADIOBROWSER=<base-URL> overstyrer Radio Browser-speilene (test).
  POST /api/spotify {"event":"playing|paused|stopped|track_changed|session_connected|session_disconnected|volume_changed|…",
                     "name":…, "artists":…, "album":…, "covers":…, "duration_ms":…, "position_ms":…, "user_name":…}
                     Spotify Connect-hendelse fra librespot (--onevent /usr/local/bin/ki-spotify-event, se ki-spotify.service).
                     «playing» bytter kilde til spotify når auto_input er på. Status: input «spotify», "spotify": {connected, playing, …}.
  GET  /api/spotify  siste Spotify-status (samme som status["spotify"])
  GET  /api/plex     siste Plex-status (samme som status["plex"]): {available, playing, paused, title, artist, album, …}
Radio: Squeezelite-spilleren styres gjennom Lyrion Music Servers JSON-RPC (KI_AMP_LMS_SERVER, ellers oppdaget på nettet).
Spotify Connect: librespot (fra raspotify-pakken) som ki-spotify.service, ut på ALSA-enheten «spotify» (softvol «KI Spotify» →
  dmix → loopback → CamillaDSP), som de andre kildene. Spillernavn = KI_AMP_NAME. librespot har ingen fjernstyring, så
  ◀◀/▶▶ virker ikke for Spotify (styres fra appen); pause/spill-pause og bytte bort fra Spotify starter tjenesten på nytt
  for å stoppe lyden. Volum fra Spotify-appen (volume_changed) settes som daemonvolum når Spotify er valgt.

KI_AMP_BOARD=node (Skjold Node, OLED-utgave: Pi 4/3B, lyd på 3,5 mm, 0,91" SSD1306 128×32 på I²C eies av Skjold OS):
  Pinner leses fra /etc/skjold/node_pins.json (schema 2; ellers repoets skjold/node/config/node_pins.json, ellers innebygde standardverdier).
  Knapper til GND: RADIO GPIO23, AIR·BT GPIO24, ◀◀ GPIO25, ▶▶ GPIO7. LED-ringer GPIO12/16/20/21 (programvare-PWM).
  Volum: 10 kΩ potmeter på ADS1115 A0 (I²C1 0x48), lest med smbus2 ~20 Hz. Volumet settes bare når knotten flyttes
  (glatting + hysterese ±2), så volum fra app/AirPlay står til knotten vris igjen («soft takeover»). Mangler ADS1115,
  fortsetter alt annet (nytt forsøk hvert 10. s). Uten ADS1115 (potmeter.metode "auto"|"rc"): RC-tidsmåling på GPIO17 –
  3V3 → pot pinne 3, glider → 1 kΩ → node → GPIO17, node → kondensator (1 µF; 100 nF–10 µF) → GND. Ladetiden ∝ motstand,
  median av 5 målinger ~10 Hz, selvkalibrerende endepunkter (lagres i /var/lib/ki-amp/node_pot_rc.json). I²C deles med OLED-en (Skjold OS) – daemonen tar aldri bussen eksklusivt.
  Daemonen rører aldri GPIO0/1 (HAT-EEPROM), 2/3 (I²C), 14/15 (UART) eller 18/19 (I²S). SPI er av (GPIO7 = knapp).
  RADIO: trykk = velg radio / neste favoritt (meny), hold 1 s = spill valgt favoritt.
  AIR·BT: trykk = bytt AirPlay ↔ Bluetooth, hold 2 s = BT-paring av/på.
  ◀◀/▶▶: forrige/neste spor (neste/forrige favoritt i radio). ▶▶ hold 1 s = spill/pause.
  ◀◀ hold 3 s = innstillingsmenyen (status["settings_menu"], og ui_event for eldre skjermprosesser): ◀◀/▶▶ = flytt,
  RADIO = endre verdi, AIR·BT = lukk; 20 s uten aktivitet / «Lukk» / ◀◀ hold 3 s = ut. Hold ◀◀ + ▶▶ 3 s = omstart.
  Standardnavn «Skjold Node» (KI_AMP_NAME overstyrer).
Felter i /api/status for skjermen (Skjold OS):
  rebooting: true          ~1,5 s før daemonen kjører systemctl reboot/poweroff (hold ◀◀+▶▶, hold POWER, POST /api/reboot)
  hold: {"key":"knob|src|radio|reboot","p":0–1,"title":…,"sub":…}   mens en knapp holdes inne (vises etter 0,35 s), null ellers;
        etter lagret favoritt i 2,5 s: {"key":"radio","p":1,"title":"Lagret","sub":"P4 på plass 3","saved":3}
  settings_menu: {"open":true,"cat":"INNSTILLINGER","idx":0-basert,"rows":[{"k","n","icon","v"}…],"left":s} | null
  menu: radiomenyen {"open","idx"(1–6),"until"} | null
  bt_pairing_left: sekunder igjen av BT-paringen (0 når av)
  airplay_device: navnet på AirPlay-klienten (Shairport-metadata «snam» via oled_display.py), "" når ingen
  input_seq: øker for hvert knappetrykk/-slipp, encoderhakk og potmeterflytt
  POST /api/reboot {"poweroff":bool}   omstart (eller slå av) etter 1,5 s med rebooting=true
  GET  /api/wifi                        {"networks":[{ssid,signal,security:"open|wpa2|wpa3",active}]} (nmcli; 503 uten NetworkManager)
  POST /api/wifi {"ssid","psk"?,"hidden"?}  koble til Wi-Fi med nmcli (appens oppsett, trinn 2)
  POST /api/test {"channel":"L"|"R"}   kort 440 Hz-tone i venstre/høyre høyttaler (oppsett trinn 3b / Innstillinger → Lyd)
  LED-ringer: RADIO = radio, AIR·BT = AirPlay/Bluetooth/Spotify (blinker under paring), ◀◀/▶▶ = noe spiller.
  KI_AMP_NODE_GPIO=0 (Skjold Core, ren Raspberry Pi): ingen knapper, potmeter eller LED-ringer – bare lyd og API.
  KI_AMP_NODE_BUTTONS=0 lar skjermprosessen eie knappene (daemonen styrer da bare LED-ringene).
  KI_AMP_NODE_POT=0 slår av potmeteret (ADS1115 og RC).
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
if not NAME or NAME == "Pultforsterker":   # gammelt standardnavn i ki-amp.env
    NAME = ("Skjold Core" if os.environ.get("KI_AMP_NODE_GPIO", "1") == "0" else "Skjold Node") if BOARD == "node" else ("Skjold S1" if BOARD == "main" else "Skjold")
    if os.environ.get("KI_AMP_PRODUCT", "").strip() == "touch":
        NAME = "Skjold Touch"
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
    NODE_FORBIDDEN = {0, 1, 2, 3, 14, 15, 18, 19}   # HAT-EEPROM, I²C (OLED + ADS1115), UART, I²S-klokker
    NODE_DEFAULT = {"btn": {"radio": 23, "airbt": 24, "prev": 25, "next": 7},
                    "hold": {"radio": 1.0, "airbt": 2.0, "prev": 3.0, "next": 1.0},
                    "led": {"radio": 12, "airbt": 16, "prev": 20, "next": 21},
                    "both_hold": 3.0, "led_hz": 1000, "led_active_high": True, "bounce": 0.05,
                    "adc": {"port": 1, "addr": 0x48, "ch": 0, "gain": 4.096},
                    "pot": {"vref": 3.3, "hz": 20.0, "alpha": 0.35, "hyst": 2, "dead": 1.5, "invert": False, "metode": "auto"},
                    "rc": {"gpio": 17, "c": 1e-6, "r_ser": 1000.0, "r_pot": 10000.0, "n": 5, "hz": 10.0}}

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
                if int(pj.get("schema", 1)) < 2:   # rev A/B (ST7735 + encoder): andre pinner – bruk standardverdiene
                    print(f"Node-pinner: {path} er schema {pj.get('schema', 1)} (gammel TFT/encoder-Node) – hoppes over", flush=True)
                    continue
                for b in pj["knapper"]["liste"]:
                    cfg["btn"][b["id"]] = int(b["gpio"])
                    cfg["hold"][b["id"]] = float(b.get("hold_s", cfg["hold"].get(b["id"], 2.0)))
                cfg["both_hold"] = float(pj["knapper"].get("hold_begge_s", cfg["both_hold"]))
                cfg["bounce"] = max(0.005, float(pj["knapper"].get("bounce_ms", 50)) / 1000)
                for l in pj.get("leds", {}).get("liste", []):
                    cfg["led"][l["for"]] = int(l["gpio"])
                cfg["led_hz"] = max(100, int(pj.get("leds", {}).get("pwm_hz", 1000)))
                cfg["led_active_high"] = bool(pj.get("leds", {}).get("aktiv_hoy", True))
                a, po = pj.get("adc") or {}, pj.get("potmeter") or {}
                cfg["adc"].update(port=int(a.get("i2c_port", 1)), addr=int(str(a.get("adresse", "0x48")), 16),
                                  ch=int(po.get("adc_kanal", a.get("kanal", 0))), gain=float(a.get("gain_v", 4.096)))
                cfg["pot"].update(vref=float(po.get("vref_v", 3.3)), hz=float(po.get("poll_hz", 20)), alpha=float(po.get("glatting", 0.35)),
                                  hyst=float(po.get("hysterese", 2)), dead=float(po.get("dodsone_pct", 1.5)), invert=bool(po.get("inverter", False)),
                                  metode=str(po.get("metode", "auto")).lower())
                rc = po.get("rc") or {}
                cfg["rc"].update({k: t(rc[j]) for k, j, t in (("gpio", "gpio", int), ("c", "kondensator_f", float), ("r_ser", "seriemotstand_ohm", float),
                                                              ("r_pot", "pot_ohm", float), ("n", "prover", int), ("hz", "poll_hz", float)) if j in rc})
                print(f"Node-pinner fra {os.path.normpath(path)}", flush=True)
                break
            except Exception as ex:
                print(f"Node-pinner: kunne ikke lese {path}: {ex}", flush=True)
        # aldri rør I²C/UART/HAT-EEPROM/I²S-pinner, og ingen dobbeltbruk
        used = set()
        for grp in ("btn", "led"):
            for k, p in list(cfg[grp].items()):
                if p in NODE_FORBIDDEN or p in used:
                    print(f"Node-pinner: GPIO{p} ({grp}/{k}) er reservert eller i bruk – hoppes over", flush=True)
                    del cfg[grp][k]
                else:
                    used.add(p)
        if cfg["rc"]["gpio"] in NODE_FORBIDDEN or cfg["rc"]["gpio"] in used:
            print(f"Node-pinner: RC-potmeter GPIO{cfg['rc']['gpio']} er reservert eller i bruk – RC-måling av", flush=True)
            cfg["rc"]["gpio"] = None
        return cfg

    NODE = _node_pins()
    BTN = {}            # knappene settes opp i setup_buttons (egen logikk for Node)
    LED = {}            # ringene er PWMLED (node_leds)
    LED_POWER = None    # ingen strømknapp/strømring på Node
    PIN_DAC_XSMT = None
    ENC = None          # ingen encoder på OLED-Noden – volum fra potmeteret (ADS1115)
    NODE_GPIO = os.environ.get("KI_AMP_NODE_GPIO", "1") == "1"   # 0 = Skjold Core: ren Pi uten knapper/potmeter/LED-ringer
    NODE_BUTTONS = NODE_GPIO and os.environ.get("KI_AMP_NODE_BUTTONS", "1") == "1"
else:
    BTN = {"airplay": 5, "bt": 6, "aux": 12, "usb": 13}
    LED = {"airplay": 7, "bt": 8, "aux": 9, "usb": 10}
    LED_POWER = 11      # PWM
    PIN_DAC_XSMT = None
BTN_POWER = {"radio": 3, "test": 26, "main": None}.get(BOARD, 16)   # main: POWER via MCP23017 (GPIO16 er PGA2311 CS) + knapp bak GPIO 15

SPOTIFY_ON = os.environ.get("KI_AMP_SPOTIFY", "1") == "1"   # Spotify Connect (librespot, ki-spotify.service)
PLEX_ON = os.environ.get("KI_AMP_PLEX", "0") == "1"           # Plex-spiller (Plexamp headless / Caldera Music, ki-plex.service)
if BOARD == "node":
    INPUTS = ["radio", "airplay", "bt"]
elif BOARD == "main":
    INPUTS = ["radio", "airplay", "bt", "aux", "aux2", "usb"]
else:
    INPUTS = ["radio", "airplay", "bt", "aux", "usb"]
if SPOTIFY_ON:
    INPUTS = INPUTS + ["spotify"]
if PLEX_ON:
    INPUTS = INPUTS + ["plex"]
CYCLE = ["radio", "airplay", "bt", "usb"] if BOARD == "radio" else INPUTS   # SOURCE-knappen
LEVEL_SOURCES = ["airplay", "bt", "usb", "radio", "aux", "aux2", "spotify", "plex"]   # eget nivå per kilde (ALSA softvol «KI <kilde>» på kortet Loopback)
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
         "levels": {"airplay": 100, "bt": 100, "usb": 100, "radio": 100, "aux": 100, "aux2": 100, "spotify": 100, "plex": 100},   # nivå per kilde (miks)
         "ui_event": None,      # Node: {"name":"settings","t":…} når ◀◀ holdes 3 s (skjermprosessen viser innstillinger)
         "poweroff": False,     # sammen med rebooting: true = slår av (ikke omstart)
         "boot_s": 45,          # siste målte oppstartstid (s, glidende snitt i /var/lib/skjold/boot_time) – «tilbake om ca. N s»
         "rebooting": False,    # settes ~1,5 s før daemonen starter omstart/slår av (skjermen viser omstart-animasjonen)
         "input_seq": 0,        # teller som øker for hver knapp-/potmeterhendelse
         "settings": {}}
spotify = {"connected": False, "playing": False, "paused": False, "title": "", "artist": "", "album": "", "cover": "",
           "duration": 0, "position": 0, "user": "", "event": "", "t": 0.0}
plex = {"available": False, "playing": False, "paused": False, "title": "", "artist": "", "album": "", "cover": "",
        "duration": 0, "position": 0, "t": 0.0}   # Plex-spilleren (pollet fra :32500, se plex_thread)   # siste librespot-hendelse (POST /api/spotify)   # innstillingsmodellen fra appen/web (skjold_settings.js) – se SETTINGS_DEF
LEVELS_ON = os.environ.get("KI_AMP_LEVELS", "1" if BOARD == "main" else "0") == "1"   # mix: ikke stopp de andre digitale kildene ved kildebytte   # loudness 0–10 dB · presets: radiokanal 1–6 · auto_input: bytt kilde når noe begynner å spille
_x9c_pos = None
_pairing_until = 0.0
menu = {"open": False, "idx": 1, "until": 0.0, "stepped": 0.0}   # kanalmeny på OLED (hold volumknotten 1 s i radio)
MENU_S = 6.0
MENU_AUTOPLAY_S = 1.8   # radiomenyen: valgt favoritt spiller av seg selv så lenge etter siste trykk

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


EARLY_DIR = os.environ.get("SKJOLD_RUN_DIR", "/run/skjold")   # skjold-early.service (skjold/os/skjold_early.py)
BOOT_TIME_FILE = os.environ.get("SKJOLD_BOOT_TIME", "/var/lib/skjold/boot_time")


def _release_early_leds(wait=1.0):
    """skjold-early.service kjører LED-jaget fra like etter kjernen. Be den slippe pinnene (SIGUSR1) før vi tar dem."""
    try:
        with open(os.path.join(EARLY_DIR, "early.pid")) as fh:
            pid = int(fh.read().strip() or 0)
        os.kill(pid, 10)   # SIGUSR1
    except Exception:
        return
    t_end = time.time() + wait
    while time.time() < t_end and not os.path.exists(os.path.join(EARLY_DIR, "early-leds-free")):
        time.sleep(0.02)


def read_boot_time(default=45):
    """Glidende snitt av oppstartstiden (skrives av Skjold OS når den har kontakt med daemonen)."""
    try:
        with open(BOOT_TIME_FILE) as fh:
            raw = fh.read().strip()
        v = json.loads(raw)
        v = v.get("avg") if isinstance(v, dict) else v
        return max(5, min(600, int(round(float(v)))))
    except Exception:
        return default


try:
    from gpiozero import Button, DigitalOutputDevice, OutputDevice, PWMLED, RotaryEncoder, LED as GLED
    HW = True
    if BOARD == "node" and not os.environ.get("GPIOZERO_PIN_FACTORY"):
        try:   # lgpio: tidsstyrt PWM (tx_pwm) i lgpio-biblioteket – jevnere enn gpiozero sin Python-tråd ved 1 kHz
            from gpiozero import Device
            from gpiozero.pins.lgpio import LGPIOFactory
            Device.pin_factory = LGPIOFactory()
        except Exception as e:
            print("lgpio-fabrikk ikke tilgjengelig (LED-PWM blir gpiozero-standard):", e, flush=True)
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
    elif BOARD == "node" and NODE_GPIO:   # LED-ringene: lgpio tx_pwm ≥ 1 kHz (3,5 mm-lyden bruker maskinvare-PWM0/1)
        _release_early_leds()
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
    "input_plex": "Pleks.",
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
    "input_plex": "Pleks.",
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


LED_LEVELS = [100, 60, 30, 0]   # gamle «led» (Høy, Middels, Lav, Av) → ledLevel i %
LED_GAMMA = 2.2                 # opplevd lysstyrke → PWM-andel (øyet er logaritmisk: 50 % opplevd ≈ 22 % duty)
LED_MODES = ["press", "always", "off"]   # ledMode: Ved trykk / Alltid / Av (appen kan også sende indeks 0–2)


def led_level():
    """Opplevd LED-lysstyrke 0–1 fra «ledLevel» (0–100). Eldre oppsett med bare «led» får nivået fra listen."""
    cur = state.get("settings") or {}
    try:
        if "ledLevel" in cur and cur["ledLevel"] is not None:
            return max(0.0, min(1.0, float(cur["ledLevel"]) / 100.0))
        i = int(cur.get("led", 0))
        return LED_LEVELS[i] / 100.0 if 0 <= i < len(LED_LEVELS) else 1.0
    except (TypeError, ValueError):
        return 1.0


def led_duty(b):
    """Opplevd lysstyrke 0–1 → PWM-andel (gamma)."""
    b = max(0.0, min(1.0, float(b)))
    return b ** LED_GAMMA


def led_mode():
    v = (state.get("settings") or {}).get("ledMode", "press")
    if isinstance(v, int) and not isinstance(v, bool):
        return LED_MODES[v] if 0 <= v < len(LED_MODES) else "press"
    return v if v in LED_MODES else "press"


def led_scale():
    """PWM-andel for full ring ved valgt lysstyrke. PWMLED (node, strøm-LED) skaleres; av/på-LED-er
    (MCP23017 på main, gpiozero LED på modules/radio) kan ikke dimmes – de slukkes bare ved 0 %."""
    return led_duty(led_level())


# ---------- Node: LED-ringene (egen tråd, ~50 Hz under animasjoner) ----------
# Alle verdier her er OPPLEVD lysstyrke 0–1; ganges med ledLevel og gjøres om til PWM-andel med gamma til slutt.
LED_FLASH_S = 1.2     # «Ved trykk»: ringen lyser fullt og toner ut over 1,2 s
LED_GLOW_S, LED_GLOW = 1.6, 0.55   # «Ved trykk»: ringen til ny kilde gløder kort når kilden byttes
LED_RINGS = ("radio", "airbt", "prev", "next")
LED_RING_OF_HOLD = {"radio": ("radio",), "src": ("airbt",), "settings": ("prev",), "play": ("next",), "reboot": ("prev", "next")}
_led_fx = {"flash": {}, "glow": (None, 0.0), "last_input": None, "base": {}, "reboot_t0": 0.0, "sent": {}}
_led_wake = threading.Event()


def _input_ring(inp):
    return "radio" if inp == "radio" else "airbt" if inp in ("airplay", "bt", "spotify", "plex") else None


def node_led_flash(ring):
    """Knappetrykk: ringen lyser opp (i modus «press» og «always»)."""
    _led_fx["flash"][ring] = time.time(); _led_wake.set()


def apply_node_leds(playing=None):
    """Node: grunnlyset for modus «Alltid» (RADIO = radio, AIR·BT = AirPlay/Blåtann/Spotify, ◀◀/▶▶ = noe spiller,
    svakt ellers). Selve skrivingen til pinnene gjør node_led_tick (trykk-blink, glød, paring, hold, omstart)."""
    if not node_leds:
        return
    on = state["power"]
    if playing is None:
        try:
            playing = bool(read_status().get("playing"))
        except Exception:
            playing = False
    ring = _input_ring(state["input"])
    _led_fx["base"] = {"radio": 1.0 if on and ring == "radio" else 0.0, "airbt": 1.0 if on and ring == "airbt" else 0.0,
                       "prev": (0.75 if playing else 0.3) if on else 0.0, "next": (0.75 if playing else 0.3) if on else 0.0}
    if _led_fx["last_input"] is not None and state["input"] != _led_fx["last_input"] and ring:
        _led_fx["glow"] = (ring, time.time())
    _led_fx["last_input"] = state["input"]
    node_led_tick()


def node_led_targets(now=None):
    """→ (opplevd lysstyrke per ring 0–1 før ledLevel, animasjon pågår?)."""
    now = time.time() if now is None else now
    out = {k: 0.0 for k in LED_RINGS}
    mode = led_mode()
    if state.get("rebooting"):   # omstart/slå av: alle opp, så toner de ut én etter én
        t = now - (_led_fx["reboot_t0"] or now)
        for i, k in enumerate(LED_RINGS):
            out[k] = 0.0 if mode == "off" else max(0.0, 1.0 - max(0.0, t - 0.25 - i * 0.18) / 0.7)
        return out, t < 2.5
    early = os.path.exists(os.path.join(EARLY_DIR, "early-leds-free")) and not os.path.exists(os.path.join(EARLY_DIR, "os-ready"))
    if early and mode != "off" and _uptime() < 180:   # fortsatt oppstart: fortsett jaget fra skjold-early til Skjold OS er klar
        ph = (now * 1.6) % len(LED_RINGS)
        for i, k in enumerate(LED_RINGS):
            d = (ph - i) % len(LED_RINGS)
            out[k] = max(0.0, 1.0 - d / 1.6)
        return out, True
    if mode == "off":
        return out, False
    anim = False
    if mode == "always":
        out.update({k: v for k, v in _led_fx["base"].items() if k in out})
    for k, t in list(_led_fx["flash"].items()):
        u = (now - t) / LED_FLASH_S
        if u >= 1:
            _led_fx["flash"].pop(k, None); continue
        out[k] = max(out[k], (1 - u) ** 1.5); anim = True
    g, t = _led_fx["glow"]
    if g and mode == "press":
        u = (now - t) / LED_GLOW_S
        if u < 1:
            out[g] = max(out[g], LED_GLOW * (min(1.0, u * 6) if u < 0.17 else (1 - u) / 0.83)); anim = True
        else:
            _led_fx["glow"] = (None, 0.0)
    for key, h in list(_press.items()):   # hold: ringen følger fremdriften
        el = now - h["t0"]
        if el < HOLD_SHOW_S:
            anim = True; continue
        p = min(1.0, el / max(0.1, h["dur"]))
        for k in LED_RING_OF_HOLD.get(key, ()):
            out[k] = max(out[k], 0.15 + 0.85 * p)
        anim = True
    if state["bt_pairing"]:
        out["airbt"] = (math.sin(now * 2 * math.pi * 1.1) + 1) / 2; anim = True
    return out, anim


def _uptime():
    try:
        with open("/proc/uptime") as fh:
            return float(fh.read().split()[0])
    except Exception:
        return 1e9


def node_led_tick(now=None):
    """Skriv ringene (bare de som har endret seg). Returnerer True mens noe animeres."""
    if not node_leds:
        return False
    tgt, anim = node_led_targets(now)
    lvl = led_level()
    for k, led in node_leds.items():
        d = round(led_duty(tgt.get(k, 0.0) * lvl), 4)
        if _led_fx["sent"].get(k) == d:
            continue
        try:
            led.value = d; _led_fx["sent"][k] = d
        except Exception as e:
            print("LED-ring:", e, flush=True)
    return anim


def node_led_thread(stop=None):
    while not (stop and stop.is_set()):
        try:
            anim = node_led_tick()
        except Exception as e:
            print("LED-tråd:", e, flush=True); anim = False
        _led_wake.wait(0.02 if anim else 0.25); _led_wake.clear()


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
    units = [u for u in ("shairport-sync", "bluealsa-aplay", "ki-usb-audio", "ki-squeezelite", "ki-aux1", "ki-aux2", "ki-spotify", "ki-plex")   # bare tjenester som er slått på
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
                "voice": True, "lang": 0, "vv": 1, "dim": 1, "off": 1, "clock": True, "clockStyle": 0, "bright": 0, "led": 0, "ledLevel": 100, "ledMode": "press", "auto": 1, "wake": True,
                # Musikktjenester – lagres her så appen (iOS/Android) og web-UI-et deler innloggingene
                "ytmEn": False, "ytmUser": "", "ytmCookie": "", "ndEn": False, "ndUrl": "", "ndUser": "", "ndPass": "",
                "plexEn": False, "plexUrl": "", "plexToken": "",
                "eq": {k: {"preset": p, "eq": e, "loud": k != "hp"} for k, p, e in (("air", 0, [0, 0, 0, 0, 0]), ("bt", 1, [6, 3, 0, 0, 1]), ("radio", 2, [-2, 0, 3, 2, 0]),
                                                                                     ("aux", 0, [0, 0, 0, 0, 0]), ("usb", 0, [0, 0, 0, 0, 0]), ("hp", 3, [3, 1, -1, -2, -3]))}}
VMAX = [100, 90, 80, 70]; VSTART = [None, 20, 30, 40]; LANG_PROFILE = {0: "no", 1: "en"}
SETTINGS_APPLIED = {"led", "ledLevel", "ledMode", "name", "nameCustom", "voice", "lang", "vmax", "vstart", "nUsb1", "nUsb2", "wake", "bright", "dim", "off", "clock", "clockStyle"}   # bright/dim/off/clock*: Skjold OS   # resten lagres og vises, men styrer ingenting ennå


def settings():
    s_ = dict(SETTINGS_DEF); s_["eq"] = {k: dict(v) for k, v in SETTINGS_DEF["eq"].items()}
    cur = state.get("settings") or {}
    for k, v in cur.items():
        if k == "eq" and isinstance(v, dict):
            for src, prof in v.items():
                if src in s_["eq"] and isinstance(prof, dict): s_["eq"][src].update(prof)
        elif k in s_: s_[k] = v
    if "ledLevel" not in cur or cur.get("ledLevel") is None:   # eldre oppsett: bare «led»
        s_["ledLevel"] = int(round(led_level() * 100))
    s_["ledMode"] = led_mode()
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
    if {"led", "ledLevel", "ledMode"} & set(changed_keys) and HW:
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


def _airplay_conf_name():
    try:
        with open(SHAIRPORT_CONF) as fh:
            m = re.search(r'^\s*name\s*=\s*"([^"]*)";', fh.read(), flags=re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def apply_name(force_services=False):
    """Sett spillernavnet. Tjenestene (AirPlay, Spotify, Blåtann) endres/restartes bare når navnet faktisk endres
    (ved oppstart kun hvis det avviker fra det installasjonen satte, dvs. KI_AMP_NAME)."""
    global NAME
    new = effective_name()
    old = _name_applied[0]
    NAME = new
    if old is None and not force_services and _airplay_conf_name() not in (None, new):
        force_services = True   # installasjonen satte et gammelt navn (f.eks. «Pultforsterker») i shairport-sync.conf
    if old == new or (old is None and new == NAME_ENV and not force_services):
        _name_applied[0] = new; return
    _name_applied[0] = new
    if HW and os.path.exists(AVAHI_SVC):
        threading.Thread(target=start_mdns_avahi, daemon=True).start()   # nytt navn i mDNS-annonsen
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


def _norm_led_patch(patch, cur):
    """«led» (Høy/Middels/Lav/Av) og «ledLevel» (0–100) holdes i takt; «ledMode» godtar navn eller indeks."""
    patch = dict(patch)
    if "ledLevel" in patch:
        try: patch["ledLevel"] = max(0, min(100, int(round(float(patch["ledLevel"])))))
        except (TypeError, ValueError): patch.pop("ledLevel")
    if "led" in patch and "ledLevel" not in patch:
        try: patch["ledLevel"] = LED_LEVELS[max(0, min(3, int(patch["led"])))]
        except (TypeError, ValueError): pass
    elif "ledLevel" in patch and "led" not in patch:
        v = patch["ledLevel"]; patch["led"] = 0 if v >= 80 else 1 if v >= 45 else 2 if v > 0 else 3
    if "ledMode" in patch:
        m = patch["ledMode"]
        if isinstance(m, int) and not isinstance(m, bool) and 0 <= m < len(LED_MODES): patch["ledMode"] = LED_MODES[m]
        elif m not in LED_MODES: patch.pop("ledMode")
    return patch


def update_settings(patch):
    cur = state.setdefault("settings", {})
    patch = _norm_led_patch(patch, cur)
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


# ---------- fjernstyring (Cloudflare Tunnel) – web-UI-et på denne enheten via f.eks. skjold-styring.smarthjemexperten.no ----------
# Enheten der fjernstyring slås på er «master»: tunnelen går hit. Tokenet lagres bare i REMOTE_FILE (0600), aldri i status.
REMOTE_FILE = os.path.join(os.path.dirname(STATE_FILE), "remote.json")
_remote_job = {"busy": False, "log": ""}


def _remote_cfg():
    try:
        with open(REMOTE_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {}


def remote_status():
    cfg = _remote_cfg()
    active = subprocess.run(["systemctl", "is-active", "--quiet", "cloudflared"]).returncode == 0 if HW else bool(cfg.get("enabled"))
    import shutil
    return {"enabled": bool(cfg.get("enabled")), "host": cfg.get("host", ""), "master": bool(cfg.get("enabled")), "active": active,
            "installed": bool(shutil.which("cloudflared")) or not HW, "busy": _remote_job["busy"], "log": _remote_job["log"][-600:],
            "has_token": bool(cfg.get("token"))}


def _remote_run(enable, token, host):
    _remote_job.update(busy=True, log="")
    def log(t):
        _remote_job["log"] += t.rstrip() + "\n"; print("Fjernstyring:", t.rstrip(), flush=True)
    try:
        cfg = _remote_cfg()
        if host: cfg["host"] = host.strip().removeprefix("https://").strip("/")
        if token: cfg["token"] = token.strip()
        if not HW:
            cfg["enabled"] = enable; log("simulering – ingen endring"); return
        q = dict(capture_output=True, text=True, timeout=300)
        if enable:
            if not cfg.get("token"):
                log("Mangler tunnel-token fra Cloudflare."); return
            import shutil
            if not shutil.which("cloudflared"):
                log("Installerer cloudflared …")
                cmds = ["mkdir -p --mode=0755 /usr/share/keyrings",
                        "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg",
                        "echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' > /etc/apt/sources.list.d/cloudflared.list",
                        "apt-get update -qq", "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq cloudflared"]
                for c in cmds:
                    r = subprocess.run(["sh", "-c", c], **q)
                    if r.returncode != 0:
                        log(f"Feilet: {c}\n{(r.stderr or r.stdout)[-300:]}"); return
            subprocess.run(["cloudflared", "service", "uninstall"], **q)
            r = subprocess.run(["cloudflared", "service", "install", cfg["token"]], **q)
            if r.returncode != 0:
                log("cloudflared service install feilet:\n" + (r.stderr or r.stdout)[-400:]); return
            subprocess.run(["systemctl", "enable", "--now", "cloudflared"], **q)
            cfg["enabled"] = True; log("Fjernstyring er på" + (f": https://{cfg['host']}" if cfg.get("host") else "") + ".")
        else:
            subprocess.run(["cloudflared", "service", "uninstall"], **q)
            cfg["enabled"] = False; log("Fjernstyring er av.")
    except Exception as e:
        log(f"Feil: {e!r}")
    finally:
        try:
            os.makedirs(os.path.dirname(REMOTE_FILE), exist_ok=True)
            fd = os.open(REMOTE_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh: json.dump(cfg, fh)
        except Exception:
            pass
        _remote_job["busy"] = False; changed()


async def h_remote_get(_r):
    return web.json_response(remote_status())


async def h_remote_post(r):
    try:
        b = await r.json()
    except Exception:
        b = {}
    if _remote_job["busy"]:
        return web.json_response({"error": "holder på – vent litt"}, status=409)
    threading.Thread(target=_remote_run, args=(bool(b.get("enable", True)), str(b.get("token") or ""), str(b.get("host") or "")), daemon=True).start()
    await asyncio.sleep(0.2)
    return web.json_response(remote_status())


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
    try:
        state["presets"] = norm_presets(state["presets"] if isinstance(state["presets"], list) else [])
    except Exception:
        state["presets"] = [None] * 6


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


# Etter play/pause fra appen/knappene: vis ny tilstand straks (i opptil 3 s) til kilden selv melder den, så status ikke
# blinker tilbake mens oled_display.py/Lyrion ennå ikke har oppdatert seg.
_transport_hint = {"playing": False, "until": 0.0, "src": ""}
PRODUCT = {"main": "s1", "node": "node" if BOARD != "node" or NODE_GPIO else "core"}.get(BOARD, BOARD)
if os.environ.get("KI_AMP_PRODUCT", "").strip() in ("s1", "node", "core", "touch"):   # Skjold Touch (7″ berøringsskjerm) m.fl.
    PRODUCT = os.environ["KI_AMP_PRODUCT"].strip()


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
    elif state["input"] == "plex" or (plex["playing"] and not st.get("playing")):
        st = {"playing": plex["playing"], "paused": plex["paused"], "source": "plex", "cover": plex["cover"],
              "title": plex["title"], "artist": plex["artist"], "album": plex["album"],
              "duration": plex["duration"], "position": plex["position"], "bt_device": st.get("bt_device", "")}
    extra = {"presets": [{"n": i + 1, "title": (p or {}).get("title", "")} for i, p in enumerate(state["presets"])],
             "presets_count": sum(1 for p in state["presets"] if p), "presets_max": PRESETS_MAX, "radio_now": radio_now(),
             "station": lyr.info.get("station", ""), "lyrion": lyr.connected,
             "source_label": (last_play.get("source") or "") if state["input"] == "radio" and last_play.get("source") and lyr.info.get("url") == last_play.get("url") else "",
             "lyrion_server": f"{lyr.host}:{lyr.port}" if lyr.host else "", "lyrion_player": lyr.player}
    playing, paused = bool(st.get("playing")), bool(st.get("paused"))
    if _transport_hint["until"] > time.time() and _transport_hint["src"] == st.get("source", ""):
        if playing == _transport_hint["playing"]:
            _transport_hint["until"] = 0   # kilden har tatt igjen
        else:
            playing = _transport_hint["playing"]; paused = not playing
    cover = st.get("cover", "") or ""
    cover_url = cover if cover.startswith(("http://", "https://")) else (f"/api/cover?v={cover}" if cover else "")
    return {**state, **extra, "playing": playing, "paused": paused, "cover_url": cover_url, "product": PRODUCT, "paused": bool(st.get("paused")), "source": st.get("source", ""), "cover": cover, "title": st.get("title", ""), "artist": st.get("artist", ""), "album": st.get("album", ""),
            "duration": st.get("duration", 0), "position": st.get("position", 0), "bt_device": st.get("bt_device", ""),
            "name": NAME, "version": VERSION, "id": socket.gethostname(), "presets": extra["presets"],
            "presets_count": extra["presets_count"], "presets_max": PRESETS_MAX, "radio_now": extra["radio_now"], "source_label": extra["source_label"], "lyrion_server": extra["lyrion_server"], "lyrion_player": extra["lyrion_player"],
            "usb_names": USBSW_NAMES, "voice_profiles": VOICE_PROFILES, "inputs": INPUTS, "board": BOARD,
            "spotify": dict(spotify), "plex": dict(plex), "airplay_device": raw_ap or "",
            "bt_pairing_left": max(0, int(round(_pairing_until - time.time()))) if state["bt_pairing"] else 0,
            "menu": dict(menu) if menu["open"] else None, "hold": hold_status(), "settings_menu": smenu_status(),
            "sky": sky.kort()}


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
    if plex["playing"] and inp != "plex" and st.get("source") != "plex":
        plex_cmd("pause")
    if not st.get("playing") or st.get("source") in ("", inp, "radio"):
        return
    try:
        if st.get("source") == "bt":
            _busctl("call", "org.bluez", _bt_player(), "org.bluez.MediaPlayer1", "Pause")
        elif st.get("source") == "airplay":
            _busctl("call", SPS[0], SPS[1], SPS[2], "Pause")
        elif st.get("source") == "spotify":
            spotify_stop()
        elif st.get("source") == "plex":
            plex_cmd("pause")
    except Exception as e:
        print("Pause annen kilde:", e, flush=True)


LEVEL_CTL = {"airplay": "KI AirPlay", "bt": "KI Bluetooth", "usb": "KI USB", "radio": "KI Radio", "aux": "KI AUX1", "aux2": "KI AUX2",
             "spotify": "KI Spotify", "plex": "KI Plex"}


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


def _hold_btn(b, short, held, key=None, info=None, on_change=None, ring=None):
    """Kort trykk = short(), hold = held(). gpiozero har ingen «was_held», så vi holder styr på det selv.
    Alt kjøres via _safe – et unntak i en knapp-callback dreper ellers lgpio-tråden og alle knappene slutter å virke.
    key/info: fremdrift i status["hold"] mens knappen holdes (info() → (tittel, undertekst) eller None = ingen hold-handling).
    on_change(): kalles ved trykk og slipp (brukes for «hold begge»)."""
    st = {"held": False}   # gpiozero tillater ikke nye attributter på Button

    def _p():
        st["held"] = False; input_event()
        if ring: node_led_flash(ring)
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
    menu.update(open=True, idx=state["preset"] or 1, until=time.time() + MENU_S, stepped=0.0); write_ctrl()


def menu_close():
    menu["open"] = False; write_ctrl()


def menu_step(d):
    menu["idx"] = (menu["idx"] - 1 + d) % len(state["presets"]) + 1; menu["until"] = time.time() + MENU_S
    menu["stepped"] = time.time(); write_ctrl()


def menu_pick():
    n = menu["idx"]; menu_close()
    if n <= len(state["presets"]) and state["presets"][n - 1]:
        _safe(play_preset, n)
    else:
        voice.say("radio_empty", n=n)


def menu_save():
    n = menu["idx"]; menu_close(); _safe(save_preset, n)


async def menu_task():
    while True:
        if menu["open"] and menu.get("stepped") and time.time() - menu["stepped"] > MENU_AUTOPLAY_S:
            menu["stepped"] = 0.0   # blått til en ny favoritt: spill den (som en bilradio) – hold er ikke nødvendig
            n = menu["idx"]
            if n != state["preset"] or state["input"] != "radio" or lyr.info.get("mode") != "play":
                if n <= len(state["presets"]) and state["presets"][n - 1]:
                    await asyncio.get_running_loop().run_in_executor(None, menu_pick)
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
    state["rebooting"] = True; state["poweroff"] = bool(poweroff); state["boot_s"] = read_boot_time(); _press.clear()
    _led_fx["reboot_t0"] = time.time(); _led_wake.set()
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


# ---------- Wi-Fi i oppsettet (appen) og høyttalertest ----------
def _nm_fields(line):
    """nmcli -t skiller felt med ':' og escaper ':' i verdier som '\\:'."""
    out, cur, esc = [], "", False
    for ch in line:
        if esc: cur += ch; esc = False
        elif ch == "\\": esc = True
        elif ch == ":": out.append(cur); cur = ""
        else: cur += ch
    out.append(cur)
    return out


def _wifi_scan():
    r = subprocess.run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "auto"],
                       capture_output=True, text=True, timeout=20)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout or "nmcli feilet").strip()[:200])
    nets = {}
    for line in r.stdout.splitlines():
        f = _nm_fields(line)
        if len(f) < 4 or not f[1].strip(): continue
        sec = f[3].upper()
        n = {"ssid": f[1], "signal": int(f[2] or 0) if f[2].isdigit() else 0, "active": f[0].strip() == "*",
             "security": "open" if not sec.strip() or sec.strip() == "--" else "wpa3" if "SAE" in sec or "WPA3" in sec else "wpa2"}
        old = nets.get(n["ssid"])
        if not old or n["active"] or (n["signal"] > old["signal"] and not old["active"]): nets[n["ssid"]] = n
    return sorted(nets.values(), key=lambda n: (not n["active"], -n["signal"]))


async def h_wifi_get(_r):
    """GET /api/wifi → {"networks":[{ssid,signal 0-100,security open|wpa2|wpa3,active}]} via NetworkManager (nmcli)."""
    try:
        return web.json_response({"networks": await asyncio.to_thread(_wifi_scan)})
    except FileNotFoundError:
        return web.json_response({"error": "nmcli finnes ikke på denne enheten", "networks": []}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e), "networks": []}, status=503)


async def h_wifi_post(r):
    """POST /api/wifi {"ssid","psk"?,"hidden"?:bool,"security"?:"wpa2|wpa3|open"} → kobler til med nmcli."""
    try:
        b = await r.json()
    except Exception:
        b = {}
    ssid, psk = str((b or {}).get("ssid") or "").strip(), str((b or {}).get("psk") or "")
    if not ssid or len(ssid) > 32: return web.json_response({"error": "mangler gyldig ssid"}, status=400)
    if psk and not 8 <= len(psk) <= 63: return web.json_response({"error": "passordet må ha 8–63 tegn"}, status=400)
    cmd = ["nmcli", "device", "wifi", "connect", ssid] + (["password", psk] if psk else []) + (["hidden", "yes"] if b.get("hidden") else [])
    try:
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=45)
    except FileNotFoundError:
        return web.json_response({"error": "nmcli finnes ikke på denne enheten"}, status=503)
    except subprocess.TimeoutExpired:
        return web.json_response({"error": "tidsavbrudd"}, status=504)
    if res.returncode:
        return web.json_response({"error": (res.stderr or res.stdout or "kunne ikke koble til").strip()[:200]}, status=400)
    return web.json_response({"ok": True, "ssid": ssid})


def _test_tone(channel):
    import wave, struct
    path = f"/tmp/skjold-test-{channel}.wav"
    if not os.path.exists(path):
        rate, n = 44100, int(44100 * 0.8)
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
            fr = bytearray()
            for i in range(n):
                env = min(1.0, i / 2000, (n - i) / 2000)
                v = int(9000 * env * math.sin(2 * math.pi * 440 * i / rate))
                fr += struct.pack("<hh", v if channel == "L" else 0, v if channel == "R" else 0)
            w.writeframes(bytes(fr))
    subprocess.run(["aplay", "-q", "-D", "default", path], timeout=10, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def h_test(r):
    """POST /api/test {"channel":"L"|"R"} → kort 440 Hz-tone i venstre eller høyre høyttaler (aplay)."""
    try:
        b = await r.json()
    except Exception:
        b = {}
    ch = str((b or {}).get("channel") or "").upper()
    if ch not in ("L", "R"): return web.json_response({"error": "channel må være L eller R"}, status=400)
    try:
        await asyncio.to_thread(_test_tone, ch)
    except FileNotFoundError:
        return web.json_response({"error": "aplay finnes ikke på denne enheten"}, status=503)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    return web.json_response({"ok": True, "channel": ch})


# ---------- innstillingsmeny på Node (◀◀ holdt 3 s) ----------
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
               ("ledLevel", "LED-lysstyrke", "○", ["100 %", "75 %", "50 %", "25 %", "10 %", "0 %"]),
               ("ledMode", "LED-modus", "○", ["Ved trykk", "Alltid", "Av"]),
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
    if k == "ledLevel": return "%d %%" % round(led_level() * 100)
    if k == "ledMode": return kind[LED_MODES.index(led_mode())]
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
    if k == "ledLevel":   # 100 → 75 → 50 → 25 → 10 → 0 → 100 (nærmeste trinn under nåverdien)
        steps = [100, 75, 50, 25, 10, 0]; now_ = round(led_level() * 100)
        update_settings({k: next((s_ for s_ in steps if s_ < now_), 100)}); return
    if k == "ledMode":
        update_settings({k: LED_MODES[(LED_MODES.index(led_mode()) + 1) % len(LED_MODES)]}); return
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
    """Skjold Node: RADIO, AIR·BT, ◀◀, ▶▶ (til GND, intern pull-up). Ingen encoder (volum = potmeter, node_pot_thread)."""
    objs, btn = [], {}
    for k, pin in NODE["btn"].items():
        b = _mk(Button, pin, pull_up=True, bounce_time=NODE["bounce"], hold_time=NODE["hold"].get(k, 2.0))
        if b:
            btn[k] = b; objs.append(b)

    def _radio_short():   # første trykk = radio, så neste favoritt (menyen på skjermen); i innstillingene: endre verdi
        if smenu["open"]:
            smenu_press()
        elif state["input"] != "radio":
            set_input("radio")
            menu_open()
        elif menu["open"]:
            menu_step(1)
        else:
            menu_open(); menu_step(1)

    def _radio_held():    # hold = spill favoritten som er valgt (tom plass i menyen + radio spiller = lagre der)
        if menu["open"] and menu["idx"] <= len(state["presets"]) and not state["presets"][menu["idx"] - 1] and state["input"] == "radio" and lyr.info.get("url"):
            menu_save()
        elif menu["open"]:
            menu_pick()
        elif state["preset"]:
            play_preset(state["preset"])
        else:
            set_input("radio")

    def _wireless():      # AirPlay ↔ Bluetooth (fra radio/Spotify: sist brukte trådløse); i innstillingene: lukk
        if smenu["open"]:
            smenu_close()
        elif state["input"] == "bt":
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
            n = menu["idx"]; p = state["presets"][n - 1] if n <= len(state["presets"]) else None
            if p:
                return (f"Spill favoritt {n}", p.get("title") or f"Kanal {n}")
            if state["input"] == "radio" and lyr.info.get("url"):
                return (f"Lagre på plass {n}", lyr.info.get("station") or "Det som spiller nå")
            return None
        if 0 < state["preset"] <= len(state["presets"]) and state["presets"][state["preset"] - 1]:
            return (f"Spill favoritt {state['preset']}", state["presets"][state["preset"] - 1].get("title", ""))
        return None

    if "radio" in btn:
        _hold_btn(btn["radio"], _radio_short, _radio_held, key="radio", info=_radio_info, ring="radio")
    if "airbt" in btn:
        _hold_btn(btn["airbt"], _wireless, _pair, key="src", ring="airbt",
                  info=lambda: ("Stopp paring", "Fortsett å holde") if state["bt_pairing"] else ("Blåtann-paring", "Fortsett å holde"))

    # ◀◀ + ▶▶ holdt samtidig = omstart (egen tidtaker fra den andre knappen trykkes). Mens begge er/var nede
    # undertrykkes de vanlige trykk-/hold-handlingene til begge er sluppet.
    both = {"on": False, "ending": False, "timer": None}

    def _both_pressed():
        return all(k in btn and btn[k].is_pressed for k in ("prev", "next"))

    def _both_fire():
        if _both_pressed():
            system_reboot(why="◀◀ + ▶▶ holdt")

    def _both_track():    # on_change for ◀◀ og ▶▶ (trykk og slipp)
        n = sum(1 for k in ("prev", "next") if k in btn and btn[k].is_pressed)
        if n == 2:
            both.update(on=True, ending=False)
            if both["timer"] is None:
                _press["reboot"] = {"t0": time.time(), "dur": NODE["both_hold"], "info": lambda: ("Omstart", "Hold begge")}
                both["timer"] = threading.Timer(NODE["both_hold"], lambda: _safe(_both_fire)); both["timer"].daemon = True
                both["timer"].start()
            return
        if both["timer"] is not None:
            both["timer"].cancel(); both["timer"] = None
        _press.pop("reboot", None)
        if n == 0 and both["on"]:
            both["ending"] = True          # siste slipp: handlingene for dette slippet er fortsatt undertrykt
        elif n == 1 and both["ending"]:
            both.update(on=False, ending=False)   # nytt enkelttrykk etter «hold begge»

    def _skip(act):
        if both["on"]:
            return
        if state["bt_pairing"] and act == "previous":   # ◀◀ avbryter paringen (som skjermen sier)
            bt_pairing(False); apply_input()
        elif smenu["open"]:
            smenu_step(1 if act == "next" else -1)
        elif menu["open"] and state["input"] == "radio":
            menu_step(1 if act == "next" else -1)
        else:
            transport(act)

    def _next_held():     # ▶▶ hold 1 s = spill/pause (i radiomenyen: spill valgt, i innstillingene: endre verdi)
        if both["on"] or _both_pressed():
            return
        if smenu["open"]:
            smenu_press()
        elif menu["open"]:
            menu_pick()
        else:
            transport("playpause")

    def _prev_held():     # ◀◀ hold 3 s = innstillinger av/på
        if both["on"] or _both_pressed():
            return
        smenu_close() if smenu["open"] else smenu_open()

    if "prev" in btn:
        _hold_btn(btn["prev"], lambda: _skip("previous"), _prev_held, key="settings", on_change=_both_track, ring="prev",
                  info=lambda: None if both["on"] else (("Lukk innstillinger", "Fortsett å holde") if smenu["open"] else ("Innstillinger", "Fortsett å holde")))
    if "next" in btn:
        _hold_btn(btn["next"], lambda: _skip("next"), _next_held, key="play", on_change=_both_track, ring="next",
                  info=lambda: None if both["on"] else (("Endre", "Fortsett å holde") if smenu["open"] else
                                                       ("Spill valgt", "Fortsett å holde") if menu["open"] else
                                                       ("Spill / pause", "Fortsett å holde")))
    print("Knapper klare (node): " + ", ".join(f"{k}=GPIO{p}" for k, p in NODE["btn"].items())
          + ", LED-ringer=" + ", ".join(f"{k}=GPIO{p}" for k, p in NODE["led"].items()), flush=True)
    return objs


# ---------- Node: potmeter (volum) via ADS1115 på I²C ----------
class Ads1115:
    """ADS1115 med smbus2, kontinuerlig modus (enkeltkanal mot GND). Åpner /dev/i2c-N delt (ingen eksklusiv lås)
    – Skjold OS skriver til OLED-en (0x3C) på samme buss. Hver lesing er én I²C-transaksjon i kjernen."""
    PGA = {6.144: 0, 4.096: 1, 2.048: 2, 1.024: 3, 0.512: 4, 0.256: 5}

    def __init__(self, port=1, addr=0x48, ch=0, gain=4.096, bus=None):
        self.addr, self.gain = addr, gain
        if bus is None:
            from smbus2 import SMBus
            bus = SMBus(port)
        self.bus = bus
        # OS=0 | MUX=1xx (AINch mot GND) | PGA | MODE=0 (kontinuerlig) | DR=100 (128 SPS) | COMP_QUE=11 (av)
        cfg = ((4 + (ch & 3)) << 12) | (self.PGA.get(gain, 1) << 9) | (0 << 8) | (4 << 5) | 3
        self.cfg = [(cfg >> 8) & 0xFF, cfg & 0xFF]
        self.configure()

    def configure(self):
        self.bus.write_i2c_block_data(self.addr, 0x01, self.cfg)

    def volts(self):
        hi, lo = self.bus.read_i2c_block_data(self.addr, 0x00, 2)
        raw = (hi << 8) | lo
        if raw >= 0x8000:
            raw -= 0x10000
        return raw * self.gain / 32768.0

    def close(self):
        try:
            self.bus.close()
        except Exception:
            pass


class PotVolume:
    """Spenning → volum 0–100 med glatting, dødsone i endene og hysterese. update() returnerer et nytt volum
    bare når knotten faktisk er flyttet minst «hyst» fra der den sist satte volumet («soft takeover»: volum fra
    app/AirPlay står til knotten vris igjen; da tar knotten over med sin egen posisjon). Første måling setter
    ikke volumet (startvolumet/lagret volum beholdes til knotten flyttes)."""

    def __init__(self, vref=3.3, alpha=0.35, hyst=2, dead=1.5, invert=False):
        self.vref, self.alpha, self.hyst, self.dead, self.invert = vref, alpha, hyst, dead, invert
        self.avg = None; self.anchor = None

    def percent(self, v):
        p = max(0.0, min(1.0, v / self.vref)) * 100.0
        if self.invert:
            p = 100.0 - p
        d = self.dead   # dødsone i endene så 0 og 100 nås sikkert
        return max(0.0, min(100.0, (p - d) * 100.0 / (100.0 - 2 * d)))

    def update(self, v):
        p = self.percent(v)
        self.avg = p if self.avg is None else self.avg + self.alpha * (p - self.avg)
        pos = int(round(self.avg))
        if self.anchor is None:
            self.anchor = pos; return None
        if abs(pos - self.anchor) >= self.hyst or (pos in (0, 100) and pos != self.anchor):
            self.anchor = pos; return pos
        return None


def node_pot_thread(make_adc=None, stop=None, make_rc=None):
    """Velger metode (potmeter.metode: ads1115 | rc | auto). auto: ADS1115 hvis den svarer ved oppstart, ellers RC på GPIO17.
    ADS1115: poller ~20 Hz. Mangler den (ikke koblet / feil adresse), prøver vi igjen hvert 10. s uten å stoppe noe annet."""
    a, pc = NODE["adc"], NODE["pot"]
    make_adc = make_adc or (lambda: Ads1115(a["port"], a["addr"], a["ch"], a["gain"]))
    metode = pc.get("metode", "auto")
    if metode not in ("ads1115", "rc"):
        try:
            d = make_adc(); d.volts(); d.close(); metode = "ads1115"
        except Exception as e:
            metode = "rc" if NODE["rc"].get("gpio") is not None else "ads1115"
            print(f"Potmeter: ADS1115 ikke funnet ({e})", flush=True)
    print(f"Potmeter-metode: {'ADS1115 (I²C, mest nøyaktig)' if metode == 'ads1115' else 'RC-tidsmåling på GPIO%s' % NODE['rc'].get('gpio')}"
          f" (potmeter.metode={pc.get('metode', 'auto')})", flush=True)
    if metode == "rc":
        return node_rc_thread(make_rc=make_rc, stop=stop)
    pot = PotVolume(pc["vref"], pc["alpha"], pc["hyst"], pc["dead"], pc["invert"])
    adc, warned, errs, period = None, False, 0, 1.0 / max(1.0, pc["hz"])
    while not (stop and stop.is_set()):
        if adc is None:
            try:
                adc = make_adc(); adc.volts()
                print(f"Potmeter: ADS1115 på I²C {a['port']} 0x{a['addr']:02x} kanal A{a['ch']}", flush=True)
                warned, errs = False, 0; pot.avg = pot.anchor = None
            except Exception as e:
                if adc is not None:
                    adc.close()
                adc = None
                if not warned:
                    print(f"Potmeter: fant ikke ADS1115 (0x{a['addr']:02x}): {e} – volum bare fra app/API, prøver igjen", flush=True)
                    warned = True
                (stop.wait(10) if stop else time.sleep(10)); continue
        try:
            v = adc.volts(); errs = 0
            new = pot.update(v)
            if new is not None and new != state["volume"]:
                input_event(); _safe(set_volume, new)
        except Exception as e:
            errs += 1
            if errs >= 10:   # modulen forsvant (løs ledning) – start på nytt
                print(f"Potmeter: ADS1115 svarer ikke ({e}) – prøver igjen", flush=True)
                adc.close(); adc = None; warned = False
            elif errs == 3:
                try:
                    adc.configure()   # f.eks. strømbrudd på modulen: konfigurasjonen er tapt
                except Exception:
                    pass
        (stop.wait(period) if stop else time.sleep(period))


# ---------- Node: potmeter uten ADC – RC-tidsmåling på én GPIO ----------
# 3V3 → pot pinne 3, glider (pinne 2) → 1 kΩ → node RC → GPIO17; node RC → kondensator → GND (pinne 1 ikke koblet).
# Måling: GPIO lav (tømmer kondensatoren), så inngang uten pull og tid til den leser høy (~1,3–1,6 V på BCM2711).
# t = R·C·ln(3,3/(3,3−Vth)) der R = 1 kΩ + motstanden mellom glider og pinne 3 – altså lineær i knottens posisjon.
RC_CAL_FILE = os.path.join(os.path.dirname(STATE_FILE), "node_pot_rc.json")


class RcGpio:
    """Rask lavnivå-tilgang til én pinne: lgpio (foretrukket), ellers RPi.GPIO, ellers gpiozero-pinneobjekt (function-bytte)."""

    def __init__(self, pin):
        self.pin, self.kind = pin, None
        try:
            import lgpio
            self.lg, self.h = lgpio, lgpio.gpiochip_open(0); self.kind = "lgpio"
            self.lg.gpio_claim_input(self.h, pin, lgpio.SET_PULL_NONE); return
        except Exception:
            pass
        try:
            import RPi.GPIO as G
            G.setwarnings(False); G.setmode(G.BCM); G.setup(pin, G.IN, pull_up_down=G.PUD_OFF)
            self.G, self.kind = G, "RPi.GPIO"; return
        except Exception:
            pass
        from gpiozero import Device
        if Device.pin_factory is None:
            Device.pin_factory = Device._default_pin_factory()
        self.p = Device.pin_factory.pin(pin); self.kind = "gpiozero"
        self.p.function = "input"; self.p.pull = "floating"

    def _claim(self, out):
        """lgpio: samme håndtak kan ta pinnen på nytt i annen modus – uten gpio_free (feilet free én gang, ble pinnen
        stående ufrigjort/frigjort og hver måling etterpå ga «GPIO not allocated»)."""
        lg = self.lg
        try:
            lg.gpio_claim_output(self.h, self.pin, 0) if out else lg.gpio_claim_input(self.h, self.pin, lg.SET_PULL_NONE)
        except lg.error:
            try:
                lg.gpio_free(self.h, self.pin)
            except lg.error:
                pass
            lg.gpio_claim_output(self.h, self.pin, 0) if out else lg.gpio_claim_input(self.h, self.pin, lg.SET_PULL_NONE)

    def low(self):
        if self.kind == "lgpio":
            self._claim(True)
        elif self.kind == "RPi.GPIO":
            self.G.setup(self.pin, self.G.OUT, initial=self.G.LOW)
        else:
            self.p.function = "output"; self.p.state = 0

    def release(self):
        if self.kind == "lgpio":
            self._claim(False)
        elif self.kind == "RPi.GPIO":
            self.G.setup(self.pin, self.G.IN, pull_up_down=self.G.PUD_OFF)
        else:
            self.p.function = "input"; self.p.pull = "floating"

    def read(self):
        if self.kind == "lgpio":
            return self.lg.gpio_read(self.h, self.pin) == 1
        if self.kind == "RPi.GPIO":
            return bool(self.G.input(self.pin))
        return bool(self.p.state)

    def close(self):
        try:
            self.release()
            if self.kind == "lgpio":
                self.lg.gpio_free(self.h, self.pin); self.lg.gpiochip_close(self.h)
        except Exception:
            pass


class RcPot:
    """Ladetid → posisjon 0–1. sample(): én måling (s) eller None ved tidsavbrudd. reading(): median av n.
    Endepunktene læres fra observerte ytterpunkter (lo/hi) og lagres; før knotten er vridd et stykke brukes teorien.
    Polling sover i små steg (τ_max/250) (lav CPU); bare for C < ~180 nF (målingen < 1 ms) spinner vi."""
    VTH_LN = 0.6   # ln(3,3/(3,3−1,5)) ≈ 0,55; litt romslig – bare startgjetning, kalibreringen tar over

    def __init__(self, io, c=1e-6, r_ser=1000.0, r_pot=10000.0, n=5, cal=None, clock=time.perf_counter, sleep=time.sleep):
        self.io, self.c, self.r_ser, self.r_pot, self.n, self.clock, self.sleep = io, c, r_ser, r_pot, max(1, n), clock, sleep
        self.tau_max = (r_ser + r_pot) * c
        self.timeout = 4.0 * self.tau_max + 0.002
        self.discharge = max(0.001, 5 * c * 220.0)   # tømmes via 220 Ω vernemotstand GPIO17 → node RC (begrenser strømmen inn i pinnen)
        self.step = self.tau_max / 250
        self.t_lo = self.VTH_LN * r_ser * c; self.t_hi = self.VTH_LN * (r_ser + r_pot) * c   # teori
        cal = cal or {}
        self.lo, self.hi = cal.get("t_min"), cal.get("t_max")
        if cal.get("c") not in (None, c):
            self.lo = self.hi = None   # annen kondensator – kalibrer på nytt
        self.dirty = False

    def sample(self):
        io = self.io
        io.low(); self.sleep(self.discharge); io.release()
        t0 = self.clock()
        while not io.read():
            if self.clock() - t0 > self.timeout:
                return None
            if self.tau_max >= 2e-3:   # bare under ~180 nF er hele målingen så kort (< 1 ms) at vi spinner
                self.sleep(self.step)
        return self.clock() - t0

    def reading(self):
        s = [self.sample() for _ in range(self.n)]
        ok = sorted(x for x in s if x is not None)
        if len(ok) * 2 <= len(s):
            return None
        return ok[len(ok) // 2]

    def learn(self, t):
        if self.lo is None or t < self.lo:
            self.lo = t; self.dirty = True
        if self.hi is None or t > self.hi:
            self.hi = t; self.dirty = True

    def calibrated(self):
        return self.lo is not None and self.hi is not None and self.hi - self.lo >= 0.5 * (self.t_hi - self.t_lo)

    def frac(self, t):
        """0 = knotten helt mot klokka (lang tid, høy motstand), 1 = helt med klokka (kort tid)."""
        lo, hi = (self.lo, self.hi) if self.calibrated() else (self.t_lo, self.t_hi)
        return max(0.0, min(1.0, 1.0 - (t - lo) / (hi - lo)))

    def cal(self):
        return {"t_min": self.lo, "t_max": self.hi, "c": self.c}


def node_rc_thread(make_rc=None, stop=None, cal_file=None):
    """RC-potmeteret i egen tråd (~10 Hz). Gjenbruker PotVolume (glatting, dødsone, hysterese, settes bare ved flytt)."""
    rc, pc = NODE["rc"], NODE["pot"]
    cal_file = cal_file or RC_CAL_FILE
    cal = {}
    try:
        with open(cal_file) as fh:
            cal = json.load(fh)
    except Exception:
        pass
    _w = (lambda s: stop.wait(s)) if stop else time.sleep
    try:
        meter = make_rc(cal) if make_rc else RcPot(RcGpio(rc["gpio"]), rc["c"], rc["r_ser"], rc["r_pot"], rc["n"], cal)
    except Exception as e:
        print(f"Potmeter (RC): GPIO{rc.get('gpio')} utilgjengelig: {e} – volum bare fra app/API", flush=True); return
    print(f"Potmeter (RC): GPIO{rc.get('gpio')} via {getattr(meter.io, 'kind', '?')}, C={meter.c * 1e6:g} µF, τ_max={meter.tau_max * 1000:.1f} ms"
          + ("" if meter.calibrated() else " – vri knotten helt rundt én gang for kalibrering"), flush=True)
    pot = PotVolume(pc["vref"], pc["alpha"], pc["hyst"], pc["dead"], pc["invert"])
    period, warned, saved = 1.0 / max(1.0, rc["hz"]), False, time.monotonic()
    while not (stop and stop.is_set()):
        t0 = time.monotonic()
        try:
            t = meter.reading()
        except Exception as e:
            print("Potmeter (RC):", e, flush=True); _w(2); continue
        if t is None:   # ikke koblet / feil kondensator – rør ikke volumet
            if not warned:
                print(f"Potmeter (RC): ingen ladetid på GPIO{rc.get('gpio')} (ikke koblet?) – prøver igjen", flush=True); warned = True
            pot.avg = pot.anchor = None; _w(2); continue
        if warned:
            print("Potmeter (RC): måler igjen", flush=True); warned = False
        meter.learn(t)
        new = pot.update(meter.frac(t) * pc["vref"])
        if new is not None and new != state["volume"]:
            input_event(); _safe(set_volume, new)
        if meter.dirty and time.monotonic() - saved > 30:
            try:
                os.makedirs(os.path.dirname(cal_file), exist_ok=True)
                with open(cal_file + ".tmp", "w") as fh:
                    json.dump(meter.cal(), fh)
                os.replace(cal_file + ".tmp", cal_file); meter.dirty = False
            except Exception:
                pass
            saved = time.monotonic()
        _w(max(0.01, period - (time.monotonic() - t0)))
    try:
        meter.io.close()
    except Exception:
        pass


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
                _led_wake.set()   # node_led_thread pulserer AIR·BT-ringen
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


async def h_cover(r):
    try:
        with open(COVER_RADIO if state["input"] == "radio" else COVER_FILE, "rb") as fh:
            img = fh.read()
    except OSError:
        return web.Response(status=404, headers={"Cache-Control": "no-store"})
    etag = '"' + hashlib.sha1(img).hexdigest()[:12] + '"'
    # ?v=<hash> fra status gir en ny URL per bilde – den kan caches lenge; uten v må nettleseren spørre hver gang
    cache = "public, max-age=86400, immutable" if r.query.get("v") else "no-cache"
    if r.headers.get("If-None-Match") == etag:
        return web.Response(status=304, headers={"ETag": etag, "Cache-Control": cache})
    ctype = "image/png" if img[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return web.Response(body=img, content_type=ctype, headers={"Cache-Control": cache, "ETag": etag})


def _event_key(st):
    """Det appen trenger å få vite straks (posisjonen teller bare ved hopp, ikke hvert sekund)."""
    return json.dumps({k: v for k, v in st.items() if k not in ("position", "bt_pairing_left", "hold", "settings_menu", "input_seq")},
                      sort_keys=True, default=str)


async def h_events(r):
    """Server-Sent Events: send status når den endrer seg. Pi Zero: én billig read_status() per 0,25 s per klient."""
    resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache",
                                       "X-Accel-Buffering": "no", **_cors_headers(r)})
    await resp.prepare(r)
    last, last_send = None, 0.0
    try:
        await resp.write(b"retry: 2000\n\n")
        while True:
            st = read_status(); key = _event_key(st); now = time.time()
            if key != last or now - last_send > 5:   # hvert 5. s uansett (posisjon/hold)
                await resp.write(b"data: " + json.dumps(st, default=str).encode() + b"\n\n")
                last, last_send = key, now
            await asyncio.sleep(0.25)
    except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
        pass
    return resp


def _cors_headers(r):
    h = {"Access-Control-Allow-Origin": r.headers.get("Origin") or "*", "Vary": "Origin",
         "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS", "Access-Control-Max-Age": "600",
         "Access-Control-Allow-Headers": r.headers.get("Access-Control-Request-Headers") or "Content-Type"}
    if r.headers.get("Access-Control-Request-Private-Network"):
        h["Access-Control-Allow-Private-Network"] = "true"
    return h


@web.middleware
async def cors_mw(r, handler):
    """CORS for /api/*: appen (capacitor://localhost / https://localhost) og web-UI fra en annen vert. API-et er åpent på
    LAN-et uansett (ingen innlogging/cookies), så origin speiles."""
    if not r.path.startswith("/api/"):
        return await handler(r)
    if r.method == "OPTIONS":
        return web.Response(status=204, headers=_cors_headers(r))
    try:
        resp = await handler(r)
    except web.HTTPException as e:
        resp = e
    if not resp.prepared:
        for k, v in _cors_headers(r).items():
            resp.headers.setdefault(k, v)
    if isinstance(resp, web.HTTPException) and not isinstance(resp, web.Response):
        raise resp
    return resp




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
            # Uten miks: AirPlay/Blåtann og radio skal aldri spille samtidig (Node/Core har ingen nivåstyring per kilde
            # som demper den andre) – stopp radioen når en trådløs kilde spiller.
            if not state["mix"] and st.get("playing") and st.get("source") in ("airplay", "bt") and lyr.info.get("mode") == "play":
                print("Stopper radio – %s spiller (miks er av)" % st.get("source"), flush=True)
                lyr.cmd(["pause", "1"]); lyr.info = {**lyr.info, "mode": "pause"}
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


# ---------- Plex (Plexamp headless / Caldera Music som ki-plex.service, lyd ut på ALSA «plex» → softvol «KI Plex») ----------
# Spilleren styres fra Plexamp-appen (den dukker opp som «cast»-mål). Daemonen leser tilstanden fra spillerens lokale
# Plex-companion-API på :32500 (/player/timeline/poll) og sender play/pause/neste/forrige dit. Svarer ikke API-et
# (eldre/nyere spiller), ser daemonen i stedet om tjenestens prosesser har en ALSA-avspillingsenhet åpen.
PLEX_PORT = int(os.environ.get("KI_AMP_PLEX_PORT", "32500"))
PLEX_USER = os.environ.get("KI_AMP_PLEX_USER", "ki-plex")
PLEX_CMD = {"play": "play", "pause": "pause", "playpause": None, "stop": "stop", "next": "skipNext", "previous": "skipPrevious"}
_plex_cid = [0]


def _plex_get(path, timeout=2.0):
    _plex_cid[0] += 1
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"http://127.0.0.1:{PLEX_PORT}{path}{sep}type=music&commandID={_plex_cid[0]}",
                                 headers={"X-Plex-Client-Identifier": "skjold-" + socket.gethostname(),
                                          "X-Plex-Device-Name": "Skjold", "Accept": "application/xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def plex_cmd(action):
    """Send play/pause/neste/forrige til Plex-spilleren. True hvis den svarte."""
    if action == "playpause":
        action = "pause" if plex["playing"] else "play"
    cmd = PLEX_CMD.get(action)
    if not cmd:
        return False
    try:
        _plex_get(f"/player/playback/{cmd}")
        return True
    except Exception as e:
        print("Plex:", e, flush=True)
        return False


def _plex_timeline():
    """Musikk-tidslinjen fra :32500 som dict, eller None hvis API-et ikke svarer."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(_plex_get("/player/timeline/poll?wait=0&includeMetadata=1"))
    except Exception:
        return None
    tl = next((t for t in root.iter("Timeline") if t.get("type") == "music"), None)
    if tl is None:
        return {"state": "stopped"}
    out = {"state": tl.get("state", "stopped"), "time": int(tl.get("time") or 0) // 1000,
           "duration": int(tl.get("duration") or 0) // 1000}
    tr = next(iter(tl.iter("Track")), None)
    if tr is not None:
        out.update(title=tr.get("title", ""), artist=tr.get("originalTitle") or tr.get("grandparentTitle", ""),
                   album=tr.get("parentTitle", ""))
        if not out["duration"]:
            out["duration"] = int(tr.get("duration") or 0) // 1000
        thumb = tr.get("thumb") or tr.get("parentThumb") or ""
        addr, port, proto = tl.get("address"), tl.get("port"), tl.get("protocol") or "http"
        if thumb.startswith(("http://", "https://")):
            out["cover"] = thumb
        elif thumb and addr and port:
            tok = tl.get("token") or ""
            out["cover"] = f"{proto}://{addr}:{port}{thumb}" + (f"?X-Plex-Token={tok}" if tok else "")
    return out


def _plex_pcm_open():
    """Har en prosess som kjører som ki-plex en ALSA-avspillingsenhet åpen? (reserve når API-et ikke svarer)"""
    try:
        import pwd
        uid = pwd.getpwnam(PLEX_USER).pw_uid
    except Exception:
        return False
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if os.stat(f"/proc/{pid}").st_uid != uid:
                continue
            for fd in os.listdir(f"/proc/{pid}/fd"):
                if re.match(r"/dev/snd/pcmC\d+D\d+p$", os.readlink(f"/proc/{pid}/fd/{fd}")):
                    return True
        except OSError:
            continue
    return False


def plex_thread():
    while True:
        time.sleep(1.5)
        try:
            if not state["power"]:
                continue
            was = plex["playing"]
            tl = _plex_timeline()
            if tl is None:
                on = _plex_pcm_open()
                plex.update(available=False, playing=on, paused=False, t=time.time())
                if not on:
                    plex.update(title="", artist="", album="", cover="", duration=0, position=0)
            else:
                st = tl["state"]
                plex.update(available=True, playing=st == "playing", paused=st == "paused", t=time.time(),
                            position=tl.get("time", 0), duration=tl.get("duration", 0))
                if st == "stopped":
                    plex.update(title="", artist="", album="", cover="")
                else:
                    for k in ("title", "artist", "album", "cover"):
                        if k in tl:
                            plex[k] = tl[k]
            if plex["playing"] and not was and state["auto_input"] and state["input"] != "plex" and "plex" in INPUTS:
                print("Auto-kilde: plex", flush=True)
                set_input("plex", announce=False)
            elif plex["playing"] != was:
                apply_input(); write_ctrl()
        except Exception as e:
            print("Plex-tråd:", e, flush=True)


async def h_plex_get(_r): return web.json_response(dict(plex))


async def h_transport(r):
    a = (await r.json()).get("action", "")
    if a not in TRANSPORT:
        return web.json_response({"error": f"action må være en av {sorted(TRANSPORT)}"}, status=400)
    before = read_status()
    try:
        await asyncio.get_running_loop().run_in_executor(None, transport, a)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    if a in ("play", "pause", "playpause", "stop"):
        want = (not before["playing"]) if a == "playpause" else a == "play"
        _transport_hint.update(playing=want, until=time.time() + 3.0, src=before["source"])
        return j()
    await asyncio.sleep(0.6)   # neste/forrige: la metadata rekke å oppdatere seg
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
        r = self.rpc(["favorites", "items", 0, 200, "want_url:1"], player=False)
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
                lp = last_play if last_play.get("url") else {}
                # Lyrion har ofte verken kanalnavn eller bilde for strømmer uten ICY-data, og rapporterer gjerne en
                # omdirigert adresse – bruk navnet/bildet vi selv startet med (favoritt, søk, Navidrome).
                same = lp and (loop.get("url", "") == lp["url"] or time.time() - lp["t"] < 3600)
                if same and lp.get("source"):   # låt fra et bibliotek (Navidrome): vår metadata er riktigere
                    song, artist, station = lp.get("track") or lp.get("title", ""), lp.get("artist", ""), lp.get("album", "")
                    if lp.get("art"): art = lp["art"]
                    if lp.get("duration") and not float(r.get("duration", 0) or 0): r["duration"] = lp["duration"]
                if same and not (station or loop.get("album")) and not lp.get("source"):
                    station = lp.get("title", "")
                if same and not art and lp.get("art"):
                    art = lp["art"]
                # Lyrions standardbilde for radio (masten i html/images/…) er ikke et ekte cover: bruk kanalens logo
                # (favoritt/søk) når vi har en – ellers ble logoen overstyrt av masten i alle appene.
                if not art or _generic_art(art):
                    logo = _known_logo(loop.get("url", ""), lp)
                    if logo: art = logo
                self.info = {"mode": r.get("mode", "stop"), "station": station if same and lp.get("source") else (station or loop.get("album", "")), "song": song,
                             "artist": artist, "url": lp["url"] if same and lp else loop.get("url", ""), "art": self.url(art),
                             "duration": float(r.get("duration", 0) or 0), "time": float(r.get("time", 0) or 0)}
                if not self.connected:
                    print("Lyrion tilkoblet, spiller", self.player, flush=True)
                self.connected = True
                self._sync_volume(r)
                self._fetch_art()
                if not any(state["presets"]):
                    favs = self.favorites()[:PRESETS_MAX]
                    if favs:
                        state["presets"] = norm_presets(favs); changed()
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


def _generic_art(a):
    a = str(a or "").lower()
    return "html/images/" in a or a.endswith(("/radio.png", "/radio.svg", "/cover.png")) or "/plugins/" in a and "icon" in a


def _known_logo(url, lp=None):
    """Logo for strømmen som spiller: favoritten med samme URL, sist startede strøm (søk/Navidrome) eller radio_tmp."""
    for p in state.get("presets") or []:
        if p and p.get("url") == url and (p.get("icon") or p.get("image")):
            return p.get("icon") or p.get("image")
    if lp and lp.get("art"):
        return lp["art"]
    if radio_tmp.get("url") == url and radio_tmp.get("icon"):
        return radio_tmp["icon"]
    if 0 < (state.get("preset") or 0) <= len(state.get("presets") or []):
        p = state["presets"][state["preset"] - 1]
        if p and lyr.info.get("mode") == "play" and (p.get("icon") or p.get("image")):
            return p.get("icon") or p.get("image")
    return ""


lyr = Lyrion()


PRESETS_MIN, PRESETS_MAX = 6, 50
last_play = {}   # siste strøm Skjold startet selv: {url,title,art,t} – fyller inn når Lyrion mangler metadata
radio_tmp = {}   # kanal spilt via /api/radio/play (ikke favoritt): {title,url,icon,genre}


def norm_presets(lst=None):
    """Minst 6 plasser, maks 50 fylte; tomme plasser bak de 6 første fjernes."""
    lst = [p if isinstance(p, dict) and p.get("url") else None for p in (state["presets"] if lst is None else lst)]
    head, tail = lst[:PRESETS_MIN], [p for p in lst[PRESETS_MIN:] if p]
    head += [None] * (PRESETS_MIN - len(head))
    out = head + tail
    while sum(1 for p in out if p) > PRESETS_MAX:
        out.pop(max(i for i, p in enumerate(out) if p))
    return out + [None] * (PRESETS_MIN - len(out))


def preset_out(i, p):
    if not p:
        return None
    return {"n": i + 1, "title": p.get("title", ""), "url": p.get("url", ""), "icon": p.get("icon", ""),
            "image": p.get("icon", "") or p.get("image", ""), "genre": p.get("genre", "")}


def presets_payload():
    out = [preset_out(i, p) for i, p in enumerate(state["presets"])]
    return {"presets": out, "items": [p for p in out if p], "count": sum(1 for p in out if p), "max": PRESETS_MAX,
            "active": state["preset"], "lyrion": lyr.connected}


def radio_now():
    if state["input"] != "radio":
        return None
    i = lyr.info; url = i.get("url", "")
    n = state["preset"] if state["preset"] and 0 < state["preset"] <= len(state["presets"]) and (state["presets"][state["preset"] - 1] or {}).get("url") == url else 0
    p = state["presets"][n - 1] if n else (radio_tmp if radio_tmp.get("url") == url else {})
    if not p and url:
        p = next((x for x in state["presets"] if x and x.get("url") == url), {})
    name = (p or {}).get("title") or i.get("station", "")
    if not name and not url:
        return None
    now = " – ".join(x for x in (i.get("artist", ""), i.get("song", "")) if x)
    return {"name": name, "genre": (p or {}).get("genre", ""), "now": now, "image": (p or {}).get("icon", "") or i.get("art", ""),
            "url": url, "n": n, "playing": i.get("mode") == "play"}


PROXIED = {}   # id -> opprinnelig strøm-URL (Navidrome o.l.), servert til Lyrion via /api/stream/<id>.mp3


def proxied_url(url):
    """Strømmer med innlogging i adressen (Navidrome/Subsonic) går via Skjold: Lyrion trenger da bare å nå Pi-en,
    og adressen er en ren …/<id>.mp3 som Lyrion kjenner igjen som lyd."""
    import hashlib as _h
    sid = _h.sha1(url.encode()).hexdigest()[:16]
    PROXIED[sid] = url
    while len(PROXIED) > 200: PROXIED.pop(next(iter(PROXIED)))
    return f"http://{_local_ip()}:{PORT}/api/stream/{sid}.mp3"


async def h_stream(r):
    sid = r.match_info["sid"].split(".")[0]
    url = PROXIED.get(sid)
    if not url:
        return web.Response(status=404)
    import aiohttp as _a
    hdr = {"User-Agent": "Skjold"}
    if r.headers.get("Range"): hdr["Range"] = r.headers["Range"]
    try:
        sess = _a.ClientSession(timeout=_a.ClientTimeout(total=None, sock_connect=8, sock_read=60))
        up = await sess.get(url, headers=hdr)
    except Exception as e:
        print("strøm-proxy: kunne ikke hente", url.split("?")[0], repr(e), flush=True)
        await sess.close(); return web.Response(status=502)
    out = web.StreamResponse(status=up.status, headers={k: v for k, v in up.headers.items()
                                                        if k in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges")})
    if "Content-Type" not in out.headers: out.content_type = "audio/mpeg"
    try:
        await out.prepare(r)
        async for chunk in up.content.iter_chunked(32768):
            await out.write(chunk)
        await out.write_eof()
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        up.release(); await sess.close()
    return out


def _diag_stream(url):
    """Feilsøking: kan Pi-en hente strømmen selv, og hva sier Lyrion etter et par sekunder?"""
    base = url.split("?")[0]
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-4095", "User-Agent": "Skjold"})
        with urllib.request.urlopen(req, timeout=6) as r:
            head = r.read(4096)
            print(f"  Strømtest {base}: HTTP {r.status}, {r.headers.get('Content-Type')}, {len(head)} byte, start={head[:4]!r}", flush=True)
    except Exception as e:
        print(f"  Strømtest {base}: FEIL {e!r}", flush=True)
    time.sleep(3)
    try:
        st = lyr.rpc(["status", "-", 1, "tags:aluo"])
        pl = (st.get("playlist_loop") or [{}])[0]
        print(f"  Lyrion etter 3 s: mode={st.get('mode')} tid={st.get('time')} låt={pl.get('title')!r} type={pl.get('type')!r} feil={st.get('error') or st.get('player_connected')}", flush=True)
    except Exception as e:
        print("  Lyrion-status feilet:", repr(e), flush=True)


def play_url(url, title="", image="", genre="", meta=None):
    """Spill en vilkårlig strøm via Lyrion (kanal som ikke er favoritt)."""
    if not url or not str(url).startswith(("http://", "https://")):
        raise ValueError("url må være http(s)")
    if not state["power"]:
        set_power(True)
    print(f"Spiller strøm via Lyrion: {title or '?'} ({url.split('?')[0]})", flush=True)
    lyr_url = proxied_url(url) if "/rest/stream" in url else url
    if lyr_url != url: print("  via Skjold:", lyr_url, flush=True)
    r = lyr.rpc(["playlist", "play", lyr_url, title or ""])
    print("  Lyrion svarte:", r, flush=True)
    threading.Thread(target=_diag_stream, args=(url,), daemon=True).start()
    radio_tmp.clear(); radio_tmp.update(title=title or "", url=url, icon=image or "", genre=genre or "")
    lyr.info = {**lyr.info, "mode": "play", "station": title or "", "song": "", "artist": "", "url": url, "art": image or ""}
    last_play.clear(); last_play.update(url=url, title=title or "", art=image or "", t=time.time(), **(meta or {}))
    n = next((k + 1 for k, p in enumerate(state["presets"]) if p and p.get("url") == url), 0)
    state["preset"] = n
    set_input("radio", announce=False)
    apply_input(); changed()


def play_preset(n, announce=True):
    p = state["presets"][n - 1] if 1 <= n <= len(state["presets"]) else None
    if not p:
        raise RuntimeError(f"radiokanal {n} er ikke lagret")
    if not state["power"]:
        set_power(True)
    lyr.rpc(["playlist", "play", p["url"], p.get("title", "")])
    lyr.info = {**lyr.info, "mode": "play", "station": p.get("title", ""), "song": "", "artist": "", "url": p["url"], "art": p.get("icon", "")}
    last_play.clear(); last_play.update(url=p["url"], title=p.get("title", ""), art=p.get("icon", ""), t=time.time())
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
    if not 1 <= n <= PRESETS_MAX:
        raise RuntimeError(f"plass må være 1–{PRESETS_MAX}")
    if n > len(state["presets"]):
        state["presets"] = state["presets"] + [None] * (n - len(state["presets"]))
    g = radio_tmp.get("genre", "") if radio_tmp.get("url") == i["url"] else ""
    state["presets"][n - 1] = {"title": i.get("station") or i.get("song") or f"Kanal {n}", "url": i["url"], "icon": i.get("art", ""), "genre": g}
    state["presets"] = norm_presets(); n = min(n, len(state["presets"]))
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
    return web.json_response(presets_payload())


async def h_preset(r):
    b = await r.json()
    try:
        n = int(b.get("n", 0))
    except (TypeError, ValueError):
        n = 0
    lim = PRESETS_MAX if b.get("save") else len(state["presets"])
    if not 1 <= n <= lim:
        return web.json_response({"error": f"n må være 1–{lim}"}, status=400)
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
            state["presets"] = norm_presets(favs[:PRESETS_MAX])
        elif isinstance(b.get("presets"), list):
            if sum(1 for p in b["presets"] if isinstance(p, dict) and p.get("url")) > PRESETS_MAX:
                return web.json_response({"error": f"maks {PRESETS_MAX} favoritter"}, status=400)
            state["presets"] = norm_presets(b["presets"])
        elif b.get("url") or b.get("title"):
            url = str(b.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return web.json_response({"error": "url må være http(s)"}, status=400)
            if sum(1 for p in state["presets"] if p) >= PRESETS_MAX:
                return web.json_response({"error": f"maks {PRESETS_MAX} favoritter"}, status=400)
            item = {"title": str(b.get("title") or url)[:120], "url": url,
                    "icon": str(b.get("image") or b.get("icon") or ""), "genre": str(b.get("genre") or "")[:60]}
            lst = list(state["presets"])
            k = next((i for i, p in enumerate(lst) if not p), None)
            if k is None:
                lst.append(item); k = len(lst) - 1
            else:
                lst[k] = item
            state["presets"] = norm_presets(lst); changed()
            return web.json_response({"ok": True, "n": k + 1, **presets_payload()}, status=201)
        else:
            return web.json_response({"error": "ukjent forespørsel"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    if state["preset"] > len(state["presets"]) or (state["preset"] and not state["presets"][state["preset"] - 1]):
        state["preset"] = 0
    changed()
    return web.json_response(presets_payload())


def _remap_active(old_lst):
    """Etter rekkefølge/sletting: finn aktiv favoritt igjen ut fra URL."""
    cur = old_lst[state["preset"] - 1] if 0 < state["preset"] <= len(old_lst) else None
    state["preset"] = next((i + 1 for i, p in enumerate(state["presets"]) if p and cur and p.get("url") == cur.get("url")), 0)


async def h_presets_order(r):
    try:
        b = await r.json(); order = [int(x) for x in b.get("order", [])]
    except Exception:
        return web.json_response({"error": "order må være en liste med plassnumre"}, status=400)
    old = list(state["presets"])
    if any(not 1 <= n <= len(old) for n in order) or len(set(order)) != len(order):
        return web.json_response({"error": f"ugyldig order (1–{len(old)}, ingen duplikater)"}, status=400)
    picked = [old[n - 1] for n in order if old[n - 1]]
    rest = [p for i, p in enumerate(old) if p and (i + 1) not in order]
    state["presets"] = norm_presets(picked + rest)
    _remap_active(old); changed()
    return web.json_response(presets_payload())


def _n_of(r):
    try:
        n = int(r.match_info["n"])
    except (KeyError, ValueError):
        n = 0
    return n if 1 <= n <= len(state["presets"]) else 0


async def h_preset_delete(r):
    n = _n_of(r)
    if not n or not state["presets"][n - 1]:
        return web.json_response({"error": "finnes ikke"}, status=404)
    old = list(state["presets"]); lst = list(old); lst.pop(n - 1)
    state["presets"] = norm_presets([p for p in lst if p])
    _remap_active(old); changed()
    return web.json_response(presets_payload())


async def h_preset_play(r):
    n = _n_of(r)
    if not n or not state["presets"][n - 1]:
        return web.json_response({"error": "finnes ikke"}, status=404)
    try:
        await asyncio.get_running_loop().run_in_executor(None, play_preset, n)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=409)
    return j()


# ---------- Radio Browser (søk/utforsk) ----------
RB_MIRRORS = [m for m in os.environ.get("KI_AMP_RADIOBROWSER", "").split(",") if m] or \
    ["https://de1.api.radio-browser.info", "https://de2.api.radio-browser.info", "https://fi1.api.radio-browser.info",
     "https://all.api.radio-browser.info"]
RB_CACHE_S = 600
_rb_cache = {}
_rb_good = [0]
RB_GENRES = [("pop", "Pop og hits", "pop"), ("news", "Nyheter og prat", "news"), ("classical", "Klassisk", "classical"),
             ("jazz", "Jazz", "jazz"), ("rock", "Rock", "rock"), ("local", "Lokal", "local")]
_RB_LABEL = {"pop": "Pop og hits", "hits": "Pop og hits", "top 40": "Pop og hits", "news": "Nyheter og prat", "talk": "Nyheter og prat",
             "classical": "Klassisk", "jazz": "Jazz", "rock": "Rock", "local": "Lokal"}


class RBOffline(Exception):
    pass


def rb_get(path, params):
    """GET mot Radio Browser med speil-fallback, timeout og 10 min cache. Kaster RBOffline når alle feiler."""
    import urllib.parse
    key = path + "?" + urllib.parse.urlencode(sorted(params.items()))
    hit = _rb_cache.get(key)
    if hit and time.time() - hit[0] < RB_CACHE_S:
        return hit[1]
    err = None
    for k in range(len(RB_MIRRORS)):
        base = RB_MIRRORS[(_rb_good[0] + k) % len(RB_MIRRORS)]
        try:
            req = urllib.request.Request(base.rstrip("/") + key, headers={"User-Agent": f"Skjold/2.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            _rb_good[0] = (_rb_good[0] + k) % len(RB_MIRRORS)
            _rb_cache[key] = (time.time(), data)
            if len(_rb_cache) > 200:
                for kk in sorted(_rb_cache, key=lambda x: _rb_cache[x][0])[:50]:
                    _rb_cache.pop(kk, None)
            return data
        except Exception as e:
            err = e
    if hit:
        return hit[1]   # gammel cache er bedre enn ingenting
    raise RBOffline(str(err))


def rb_station(s):
    tags = [t.strip() for t in (s.get("tags") or "").split(",") if t.strip()]
    genre = next((_RB_LABEL[t.lower()] for t in tags if t.lower() in _RB_LABEL), "") or ", ".join(tags[:2]).title()
    return {"id": s.get("stationuuid", ""), "name": (s.get("name") or "").strip(), "genre": genre,
            "url": s.get("url_resolved") or s.get("url") or "", "image": s.get("favicon") or "",
            "country": s.get("countrycode") or "", "codec": s.get("codec") or "", "bitrate": int(s.get("bitrate") or 0)}


def rb_list(params, limit=20):
    base = {"hidebroken": "true", "order": "clickcount", "reverse": "true", "limit": str(limit)}
    out, seen = [], set()
    for s in rb_get("/json/stations/search", {**base, **params}) or []:
        st = rb_station(s)
        if st["name"] and st["url"].startswith(("http://", "https://")) and st["url"] not in seen:
            seen.add(st["url"]); out.append(st)
    return out


def radio_search(q):
    try:
        no = rb_list({"name": q, "countrycode": "NO"}, 20)
        urls = {s["url"] for s in no}
        world = [s for s in rb_list({"name": q}, 30) if s["url"] not in urls and s["country"] != "NO"][:20]
        return {"q": q, "norway": no, "world": world, "offline": False}
    except RBOffline as e:
        return {"q": q, "norway": [], "world": [], "offline": True, "error": str(e)}


def radio_browse():
    from concurrent.futures import ThreadPoolExecutor
    jobs = [("popular_no", "Populære i Norge", {"countrycode": "NO"})] + \
           [(gid, title, {"countrycode": "NO", "tag": tag}) for gid, title, tag in RB_GENRES]
    offline = [False]

    def run(job):
        gid, title, params = job
        try:
            items = rb_list(params, 20)
            if len(items) < 4 and gid != "popular_no":   # for få norske: fyll på fra hele verden
                urls = {s["url"] for s in items}
                items += [s for s in rb_list({"tag": params["tag"]}, 20) if s["url"] not in urls]
            return {"id": gid, "title": title, "items": items[:20]}
        except RBOffline:
            offline[0] = True
            return {"id": gid, "title": title, "items": []}
    with ThreadPoolExecutor(4) as ex:
        shelves = list(ex.map(run, jobs))
    return {"shelves": shelves, "offline": offline[0]}


async def h_radio_search(r):
    q = (r.query.get("q") or "").strip()
    if not q:
        return web.json_response({"q": "", "norway": [], "world": [], "offline": False})
    return web.json_response(await asyncio.get_running_loop().run_in_executor(None, radio_search, q[:80]))


async def h_radio_browse(_r):
    return web.json_response(await asyncio.get_running_loop().run_in_executor(None, radio_browse))


async def h_radio_play(r):
    try:
        b = await r.json()
    except Exception:
        b = {}
    url = str(b.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return web.json_response({"error": "url må være http(s)"}, status=400)
    try:
        meta = {"track": str(b.get("track") or ""), "artist": str(b.get("artist") or ""), "album": str(b.get("album") or ""),
                "duration": float(b.get("duration") or 0), "source": str(b.get("source") or "")}
        await asyncio.get_running_loop().run_in_executor(None, lambda: play_url(url, str(b.get("title") or ""),
                                                         str(b.get("image") or ""), str(b.get("genre") or ""), meta))
    except Exception as e:
        print("radio/play feilet:", repr(e), flush=True)
        return web.json_response({"error": str(e)}, status=409)
    return j()


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
    if state["input"] == "plex" or st.get("source") == "plex":
        if not plex_cmd(action):
            raise RuntimeError("Plex-spilleren svarer ikke – styr den fra Plexamp-appen")
        plex.update(playing=action in ("play", "next", "previous") or (action == "playpause" and not plex["playing"]),
                    paused=action in ("pause",) or (action == "playpause" and plex["playing"]))
        return
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


# ---------- Skjold-hjem: sky-relé (docs/SKJOLD_HJEM.md) ----------
# Én WebSocket ut til skyen (Cloudflare Worker «skjold-hjem»). Skyen sender forespørsler («req») som besvares mot eget API
# på 127.0.0.1, eller – når denne enheten er aktiv hovedenhet og «til» er en annen enhet – mot den enheten på LAN-et
# (funnet via mDNS). Nøkkelen ligger bare i sky.json (0600) og vises aldri i API-et.
SKY_FILE = os.environ.get("KI_AMP_SKY_FILE", os.path.join(os.path.dirname(STATE_FILE), "sky.json"))
SKY_URL = os.environ.get("KI_AMP_SKY_URL", "https://skjold-styring.smarthjemexperten.no").rstrip("/")
SKY_PING_S = 20          # ping hvert 20. s (skyen kobler fra etter 45 s uten livstegn)
SKY_STILLE_S = 60        # ingen melding fra skyen på så lenge ⇒ ny tilkobling
SKY_MAX_BODY = 700_000   # Cloudflare tillater 1 MiB per WebSocket-melding; base64 gir +33 %
SKY_HOP = {"host", "connection", "content-length", "transfer-encoding", "keep-alive", "upgrade", "te", "trailer",
           "proxy-authorization", "proxy-connection"}


class SkyFeil(Exception):
    def __init__(self, melding, status=400):
        super().__init__(melding); self.status = status


class LanPeers:
    """Andre Skjold-enheter på LAN-et (mDNS _kipultamp._tcp). python3-zeroconf (kun søk, ingen annonsering – den gjør
    avahi), ellers «avahi-browse» hvert 30. s. Kjører i egen tråd; `peers` byttes ut atomisk: id → {id,navn,ip,port,produkt}."""
    TYPE = "_kipultamp._tcp.local."

    def __init__(self, own_id):
        self.own_id, self.peers, self._zc, self._navn = own_id, {}, None, {}

    def start(self):
        threading.Thread(target=self._run, daemon=True, name="sky-lan").start()

    def _sett(self, navn, info):
        p = dict(self.peers)
        if info and info.get("id") and info["id"] != self.own_id:
            self._navn[navn] = info["id"]; p[info["id"]] = info
        elif navn in self._navn:
            p.pop(self._navn.pop(navn), None)
        self.peers = p

    def _run(self):
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
        except Exception:
            return self._avahi_loop()
        try:
            self._zc = Zeroconf()

            def endring(zeroconf, service_type, name, state_change):
                if state_change is ServiceStateChange.Removed:
                    self._sett(name, None); return
                threading.Thread(target=self._los, args=(zeroconf, service_type, name), daemon=True).start()
            ServiceBrowser(self._zc, self.TYPE, handlers=[endring])
        except Exception as e:
            print("sky: mDNS-søk (zeroconf) feilet, bruker avahi-browse:", repr(e), flush=True)
            self._avahi_loop()

    def _los(self, zc, typ, name):
        try:
            info = zc.get_service_info(typ, name, 3000)
            if not info:
                return
            props = {(k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else (v or ""))
                     for k, v in (info.properties or {}).items()}
            ips = [a for a in info.parsed_addresses() if ":" not in a]
            if ips:
                self._sett(name, {"id": props.get("id", ""), "navn": props.get("name", name.split(".")[0]), "ip": ips[0],
                                  "port": info.port, "produkt": props.get("product", "")})
        except Exception as e:
            print("sky: mDNS-oppslag feilet:", repr(e), flush=True)

    @staticmethod
    def parse_avahi(text, own_id=""):
        """Tolker `avahi-browse -rpt _kipultamp._tcp` (linjer «=;iface;proto;navn;type;domene;vert;adresse;port;txt»)."""
        ut = {}
        for line in text.splitlines():
            f = line.split(";")
            if len(f) < 10 or f[0] != "=" or f[2] != "IPv4":
                continue
            txt = dict(kv.split("=", 1) for kv in re.findall(r'"([^"]*)"', ";".join(f[9:])) if "=" in kv)
            pid = txt.get("id", "")
            if pid and pid != own_id and pid not in ut:
                navn = re.sub(r"\\(\d{3})", lambda m: chr(int(m.group(1))), f[3])
                ut[pid] = {"id": pid, "navn": txt.get("name", navn), "ip": f[7], "port": int(f[8]), "produkt": txt.get("product", "")}
        return ut

    def _avahi_loop(self):
        while True:
            try:
                r = subprocess.run(["avahi-browse", "-rpt", "_kipultamp._tcp"], capture_output=True, text=True, timeout=15)
                self.peers = self.parse_avahi(r.stdout, self.own_id)
            except FileNotFoundError:
                print("sky: verken zeroconf eller avahi-browse – LAN-videresending av", flush=True); return
            except Exception as e:
                print("sky: avahi-browse feilet:", repr(e), flush=True)
            time.sleep(30)

    def close(self):
        if self._zc:
            try:
                self._zc.close()
            except Exception:
                pass


class Sky:
    def __init__(self, path=SKY_FILE, url=SKY_URL, local=None, ident=None, info=None, lan=None):
        self.path, self.default_url = path, url
        self.local = local or f"http://127.0.0.1:{PORT}"
        self.ident = ident or socket.gethostname()
        self.info = info or (lambda: {"navn": NAME, "produkt": PRODUCT, "versjon": VERSION})
        self.lan = lan if lan is not None else LanPeers(self.ident)
        self.cfg = self._les()
        self.tilkoblet, self.aktiv, self.hoved, self.sist_feil = False, None, None, ""
        self._ws, self._wake, self._http, self._subs = None, None, None, {}
        self._send_lock = None

    # --- lagring ---
    def _les(self):
        try:
            with open(self.path) as fh:
                c = json.load(fh)
            return c if all(c.get(k) for k in ("url", "sted", "id", "noekkel")) else {}
        except (OSError, ValueError):
            return {}

    def _skriv(self, cfg):
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump(cfg, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    # --- status (aldri nøkkelen) ---
    def status(self):
        return {"koblet": bool(self.cfg), "sted": self.cfg.get("sted"), "stedNavn": self.cfg.get("stedNavn"),
                "aktivHoved": self.aktiv, "erHoved": bool(self.cfg) and self.aktiv == self.cfg.get("id"),
                "tilkoblet": self.tilkoblet, "url": self.cfg.get("url") or self.default_url, "id": self.cfg.get("id") or self.ident,
                "feil": self.sist_feil or None}

    def kort(self):
        return {"koblet": bool(self.cfg), "sted": self.cfg.get("sted"), "erAktivHoved": self.status()["erHoved"]}

    # --- HTTP-klient ---
    def http(self):
        import aiohttp
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession()
        return self._http

    def _vekk(self):
        if self._wake:
            self._wake.set()
        if self._ws is not None and not self._ws.closed:
            asyncio.ensure_future(self._ws.close())

    async def kobl(self, kode, url=None):
        import aiohttp
        kode = re.sub(r"[\s-]", "", str(kode or "")).upper()
        if not re.fullmatch(r"[A-Z0-9]{6}", kode):
            raise SkyFeil("koden må ha seks tegn")
        base = (url or self.default_url).rstrip("/")
        i = self.info()
        try:
            async with self.http().post(base + "/enhet/kobl", json={"kode": kode, "id": self.ident, "navn": i.get("navn"),
                                                                     "produkt": i.get("produkt")},
                                        timeout=aiohttp.ClientTimeout(total=15)) as r:
                data = await r.json(content_type=None)
                if r.status != 200:
                    raise SkyFeil((data or {}).get("feil") or f"skyen svarte {r.status}", 404 if r.status == 404 else 502)
        except SkyFeil:
            raise
        except Exception as e:
            raise SkyFeil(f"fikk ikke kontakt med skyen: {e}", 502)
        cfg = {"url": base, "sted": data["sted"], "stedNavn": data.get("stedNavn"), "id": self.ident, "noekkel": data["noekkel"]}
        self._skriv(cfg)
        self.cfg, self.sist_feil, self.aktiv = cfg, "", None
        self._vekk()
        return self.status()

    def koble_fra(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        self.cfg, self.aktiv, self.hoved = {}, None, None
        self._vekk()
        return self.status()

    # --- WebSocket-løkka ---
    async def run(self):
        self._wake = asyncio.Event()
        self._send_lock = asyncio.Lock()
        pause = 2
        while True:
            if not self.cfg:
                self._wake.clear()
                await self._wake.wait()
                continue
            self._wake.clear()
            t0 = time.monotonic()
            try:
                await self._okt(dict(self.cfg))
                self.sist_feil = ""
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.sist_feil = str(e) or repr(e)
                if getattr(e, "status", None) == 401:
                    self.sist_feil = "skyen avviste enhetsnøkkelen – koble til på nytt"
                    pause = 60
            finally:
                self.tilkoblet, self._ws = False, None
                for t in list(self._subs.values()):
                    t.cancel()
                self._subs.clear()
            if time.monotonic() - t0 > 60:
                pause = 2   # var oppe en stund – prøv raskt igjen
            if self._wake.is_set():
                continue    # ny konfigurasjon (kobl/koble_fra)
            try:
                await asyncio.wait_for(self._wake.wait(), pause)
            except asyncio.TimeoutError:
                pass
            pause = min(60, pause * 2)

    async def _okt(self, cfg):
        url = re.sub(r"^http", "ws", cfg["url"]) + "/enhet/ws"
        ws = await asyncio.wait_for(self.http().ws_connect(url, headers={"Authorization": f"Bearer {cfg['id']}.{cfg['noekkel']}"},
                                                           autoping=True, max_msg_size=4 * 1024 * 1024), 20)
        self._ws, self.tilkoblet = ws, True
        print(f"sky: tilkoblet {cfg['url']} (sted {cfg['sted']})", flush=True)
        pinger = asyncio.create_task(self._pinger(ws))
        try:
            import aiohttp
            while True:
                try:
                    msg = await ws.receive(timeout=SKY_STILLE_S)
                except asyncio.TimeoutError:
                    raise RuntimeError("ingen livstegn fra skyen")
                if msg.type != aiohttp.WSMsgType.TEXT:
                    if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                        if ws.close_code and ws.close_code >= 4000:
                            raise RuntimeError(f"skyen lukket tilkoblingen ({ws.close_code})")
                        return
                    continue
                try:
                    m = json.loads(msg.data)
                except ValueError:
                    continue
                self._melding(m)
        finally:
            pinger.cancel()
            if not ws.closed:
                await ws.close()

    def _melding(self, m):
        t = m.get("t")
        if t == "ping":
            asyncio.create_task(self._send_raw('{"t":"pong"}'))
        elif t == "rolle":
            self.aktiv, self.hoved = m.get("aktiv"), m.get("hoved")
        elif t == "req":
            asyncio.create_task(self._req(m))
        elif t == "sub" and m.get("rid"):
            self._subs[m["rid"]] = asyncio.create_task(self._sub(m))
        elif t == "unsub":
            task = self._subs.pop(m.get("rid"), None)
            if task:
                task.cancel()

    def _hei(self):
        i = self.info()
        lan = sorted(self.lan.peers.values(), key=lambda p: p.get("id", "")) if self.lan else []
        return {"t": "hei", "id": self.cfg.get("id") or self.ident, "navn": i.get("navn"), "produkt": i.get("produkt"),
                "versjon": i.get("versjon"), "lan": lan}

    async def _pinger(self, ws):
        """«hei» ved tilkobling og når LAN-lista endres; ping hvert 20. s."""
        sist_hei, neste_ping = None, time.monotonic() + SKY_PING_S
        while not ws.closed:
            hei = self._hei()
            if hei != sist_hei:
                await self._send(hei); sist_hei = hei
            if time.monotonic() >= neste_ping:
                await self._send_raw('{"t":"ping"}'); neste_ping = time.monotonic() + SKY_PING_S
            await asyncio.sleep(2)

    async def _send_raw(self, tekst):
        ws = self._ws
        if ws is None or ws.closed:
            return False
        try:
            async with self._send_lock:
                await ws.send_str(tekst)
            return True
        except Exception:
            return False

    async def _send(self, obj):
        return await self._send_raw(json.dumps(obj, separators=(",", ":")))

    def _maal(self, til):
        """Basis-URL for forespørselen: eget API, eller en LAN-enhet (bare de mDNS har funnet – ingen vilkårlige adresser)."""
        if not til or til == self.ident or til == self.cfg.get("id"):
            return self.local
        p = (self.lan.peers if self.lan else {}).get(til)
        if p and p.get("ip") and p.get("port"):
            return f"http://{p['ip']}:{int(p['port'])}"
        return None

    @staticmethod
    def _sjekk_sti(m, p):
        if not p.startswith("/api/") or ".." in p or "\x00" in p:
            return "bare /api/* kan nås via skyen"
        if p.split("?")[0].rstrip("/") == "/api/sky" and m != "GET":
            return "skykobling kan bare endres lokalt"
        return None

    async def _req(self, m):
        import aiohttp
        import base64
        rid, metode, p = m.get("rid"), str(m.get("m") or "GET").upper(), str(m.get("p") or "/")

        def feil(s, tekst):
            return {"t": "res", "rid": rid, "s": s, "h": {"content-type": "application/json"},
                    "b": base64.b64encode(json.dumps({"feil": tekst}).encode()).decode()}
        hindring = self._sjekk_sti(metode, p)
        base = self._maal(m.get("til"))
        if hindring:
            res = feil(403, hindring)
        elif base is None:
            res = feil(502, f"finner ikke {m.get('til')} på LAN-et")
        else:
            try:
                body = base64.b64decode(m["b"]) if m.get("b") else None
                h = {k: v for k, v in (m.get("h") or {}).items() if k.lower() not in SKY_HOP}
                async with self.http().request(metode, base + p, data=body, headers=h, allow_redirects=False,
                                               timeout=aiohttp.ClientTimeout(total=20)) as r:
                    data = await r.read()
                    if len(data) > SKY_MAX_BODY:
                        res = feil(413, "svaret er for stort for reléet")
                    else:
                        hh = {k.lower(): v for k, v in r.headers.items()
                              if k.lower() in ("content-type", "cache-control", "etag", "last-modified")}
                        res = {"t": "res", "rid": rid, "s": r.status, "h": hh, "b": base64.b64encode(data).decode()}
            except Exception as e:
                res = feil(502, f"{type(e).__name__}: {e}")
        await self._send(res)

    async def _sub(self, m):
        import aiohttp
        rid, p = m.get("rid"), str(m.get("p") or "/api/events")
        base = self._maal(m.get("til"))
        avsluttet = False
        try:
            if base is None or self._sjekk_sti("GET", p):
                return
            async with self.http().get(base + p, timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=None),
                                       headers={"Accept": "text/event-stream"}) as r:
                if r.status != 200:
                    return
                async for line in r.content:
                    line = line.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        await self._send({"t": "ev", "rid": rid, "d": line[5:].lstrip(" ")})
        except asyncio.CancelledError:
            avsluttet = True   # unsub / frakobling – ikke svar
            raise
        except Exception as e:
            print("sky: SSE-relé feilet:", repr(e), flush=True)
        finally:
            self._subs.pop(rid, None)
            if not avsluttet:
                await self._send({"t": "res", "rid": rid, "s": 204})   # strømmen tok slutt ⇒ skyen lukker for klienten

    async def close(self):
        if self._http is not None and not self._http.closed:
            await self._http.close()


sky = Sky(lan=False)   # LAN-søket startes i on_startup (ikke ved import / i tester)


async def h_sky_get(_r):
    return web.json_response(sky.status())


async def h_sky_post(r):
    try:
        b = await r.json()
    except Exception:
        b = {}
    try:
        if b.get("koble_fra"):
            return web.json_response(sky.koble_fra())
        if b.get("kode"):
            return web.json_response(await sky.kobl(b["kode"], b.get("url")))
    except SkyFeil as e:
        return web.json_response({"error": str(e), "feil": str(e), **sky.status()}, status=e.status)
    return web.json_response({"error": "oppgi kode eller koble_fra"}, status=400)


AVAHI_SVC = "/etc/avahi/services/skjold.service"


def start_mdns_avahi():
    """Annonser via avahi-daemon (kjører allerede for AirPlay). To mDNS-svarere på samme maskin (avahi + python-zeroconf)
    gjør at spørringer fra Home Assistant/Homey ofte ikke blir besvart – derfor avahi når den finnes."""
    if not os.path.isdir(os.path.dirname(AVAHI_SVC)) or subprocess.run(["systemctl", "is-active", "--quiet", "avahi-daemon"]).returncode != 0:
        return False
    from xml.sax.saxutils import escape
    txt = {"id": socket.gethostname(), "version": VERSION, "name": NAME, "type": "pultforsterker", "product": PRODUCT, "path": "/api/status"}
    rec = "".join(f"<txt-record>{escape(k)}={escape(str(v))}</txt-record>" for k, v in txt.items())
    xml = ('<?xml version="1.0" standalone=\'no\'?>\n<!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n'
           f'<service-group><name>{escape(NAME)}</name><service><type>_kipultamp._tcp</type><port>{PORT}</port>{rec}</service></service-group>\n')
    try:
        old = open(AVAHI_SVC).read() if os.path.exists(AVAHI_SVC) else ""
        if old != xml:
            open(AVAHI_SVC, "w").write(xml)   # avahi leser mappen på nytt av seg selv (inotify)
        print(f"mDNS (avahi): {NAME}._kipultamp._tcp port {PORT}", flush=True); return True
    except Exception as e:
        print("avahi-tjeneste ikke skrevet:", repr(e), flush=True); return False


def start_mdns():
    if start_mdns_avahi():
        return None
    try:
        from zeroconf import ServiceInfo, Zeroconf
        info = ServiceInfo("_kipultamp._tcp.local.", f"{NAME}._kipultamp._tcp.local.",
                           addresses=[socket.inet_aton(_local_ip())], port=PORT,
                           properties={"id": socket.gethostname(), "version": VERSION, "name": NAME, "type": "pultforsterker",
                                       "product": PRODUCT, "path": "/api/status"},
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
    if os.environ.get("KI_AMP_SKY", "1") != "0":   # Skjold-hjem: sky-relé (gjør ingenting før enheten er koblet)
        sky.lan = LanPeers(sky.ident); sky.lan.start()
        app["sky"] = asyncio.create_task(sky.run())
    if node_leds:
        apply_node_leds(); threading.Thread(target=node_led_thread, daemon=True, name="node-led").start()


async def on_cleanup(app):
    if app.get("sky"):
        app["sky"].cancel()
    await sky.close()
    if sky.lan:
        sky.lan.close()
    if app.get("zc"):
        await asyncio.get_running_loop().run_in_executor(None, app["zc"].close)


def main():
    load_state()
    state["boot_s"] = read_boot_time()
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
    if PLEX_ON:
        threading.Thread(target=plex_thread, daemon=True).start()   # Plex: «spiller nå» + auto-kilde
    if BOARD == "node" and NODE_GPIO and HW and os.environ.get("KI_AMP_NODE_POT", "1") == "1":
        threading.Thread(target=node_pot_thread, daemon=True).start()   # volum fra potmeteret (ADS1115 eller RC)
    pot = os.environ.get("KI_AMP_POT", "")
    if pot.startswith("rc:"):   # rc:24 eller rc:24:inv (snu retningen)
        parts = pot.split(":")
        threading.Thread(target=pot_thread, args=(int(parts[1]), len(parts) > 2 and parts[2] == "inv"), daemon=True).start()
    app = web.Application(middlewares=[cors_mw])
    app.add_routes([web.get("/api/status", h_status), web.get("/api/events", h_events), web.post("/api/power", h_power), web.post("/api/toggle", h_toggle),
                    web.post("/api/input", h_input), web.post("/api/volume", h_volume), web.post("/api/mute", h_mute),
                    web.post("/api/bt", h_bt), web.post("/api/loudness", h_loudness), web.post("/api/transport", h_transport), web.get("/api/cover", h_cover), web.get("/api/remote", h_remote_get), web.post("/api/remote", h_remote_post), web.get("/api/stream/{sid}", h_stream), web.post("/api/voice", h_voice),
                    web.get("/api/presets", h_presets), web.post("/api/preset", h_preset), web.post("/api/presets", h_presets_set),
                    web.put("/api/presets/order", h_presets_order), web.post("/api/presets/order", h_presets_order),
                    web.delete("/api/presets/{n}", h_preset_delete), web.post("/api/presets/{n}/play", h_preset_play),
                    web.get("/api/radio/search", h_radio_search), web.get("/api/radio/browse", h_radio_browse), web.post("/api/radio/play", h_radio_play), web.post("/api/menu", h_menu), web.post("/api/auto_input", h_auto_input), web.post("/api/mix", h_mix), web.post("/api/usbsw", h_usbsw), web.post("/api/level", h_level), web.post("/api/hp_automute", h_hp_automute),
                    web.get("/api/settings", h_settings_get), web.post("/api/settings", h_settings_post),
                    web.post("/api/spotify", h_spotify), web.get("/api/spotify", h_spotify_get), web.get("/api/plex", h_plex_get), web.post("/api/reboot", h_reboot),
                    web.get("/api/wifi", h_wifi_get), web.post("/api/wifi", h_wifi_post), web.post("/api/test", h_test),
                    web.get("/api/sky", h_sky_get), web.post("/api/sky", h_sky_post)])
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
