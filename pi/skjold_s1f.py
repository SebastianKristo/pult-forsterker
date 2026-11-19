"""Skjold S1 rev F: knapper, volumhjul, LED-ringer, relé, USB-switch og hodetelefondetekt på Pi-ens GPIO.

Ren logikk (ClickHold, S1FControls, ws_command, design_state, og mqtt_*) har ingen GPIO-avhengighet og
testes i pi/tests/test_s1f.py. S1FHardware kobler logikken til gpiozero. Pinnene leses fra pi/config/s1f_pins.yaml
(eller /etc/skjold/s1f_pins.yaml), aldri hardkodet.

Daemonen (ki_amp_daemon.py) gir et `api`-objekt med handlingene (set_input, set_power, transport …) og leser
`controls.ui` inn i status["ui"] for skjermprosessen (se pi/S1F.md for kontrakten).
"""
import json
import os
import re
import threading
import time

# ---------------------------------------------------------------- pinner

PIN_FILES = ["/etc/skjold/s1f_pins.yaml", os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "s1f_pins.yaml"),
             "/usr/local/share/ki-amp/s1f_pins.yaml"]

DEFAULT_TIMING = {"click_window": 0.38, "hold_show": 0.35, "hold_show_radio": 0.9, "hold_settings": 1.5, "hold_pair": 2.0,
                  "hold_save": 3.0, "hold_reboot": 3.0, "hold_reset_warn": 7.0, "hold_reset": 10.0, "usb_show": 1.8, "pair_s": 60, "bt_blink": 0.35, "usb_pulse": 0.15}


def _scalar(v):
    v = v.strip()
    if v.startswith(("'", '"')) and v.endswith(v[0]) and len(v) >= 2:
        return v[1:-1]
    lo = v.lower()
    if lo in ("true", "yes", "on"): return True
    if lo in ("false", "no", "off"): return False
    if lo in ("null", "none", "~", ""): return None
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: return v


def parse_yaml(text):
    """Liten YAML-leser for pinnefila (nøkkel: verdi, nøstet med innrykk, #-kommentarer). PyYAML brukes hvis den finnes."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    root = {}; stack = [(-1, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        ind = len(line) - len(line.lstrip())
        key, _, val = line.strip().partition(":")
        while stack and stack[-1][0] >= ind:
            stack.pop()
        cur = stack[-1][1]
        if val.strip() == "":
            cur[key] = {}; stack.append((ind, cur[key]))
        else:
            cur[key] = _scalar(val)
    return root


def load_pins(path=None):
    for p in ([path] if path else PIN_FILES):
        if p and os.path.exists(p):
            with open(p) as fh:
                cfg = parse_yaml(fh.read())
            cfg["_file"] = p
            cfg["timing"] = {**DEFAULT_TIMING, **(cfg.get("timing") or {})}
            return cfg
    raise FileNotFoundError("fant ingen s1f_pins.yaml")


# ---------------------------------------------------------------- pinne-editoren (web-UI → /api/s1f/pins)

ETC_PINS = PIN_FILES[0]          # brukerens egne pinner – vinner over standardfila og overskrives ikke av oppdateringer

# Den 40-pinners headeren på Pi 4: fysisk pinne → "3V3" | "5V" | "GND" | BCM-nummer (int). 27/28 er ID_SD/ID_SC (GPIO0/1).
HEADER = {1: "3V3", 2: "5V", 3: 2, 4: "5V", 5: 3, 6: "GND", 7: 4, 8: 14, 9: "GND", 10: 15, 11: 17, 12: 18, 13: 27, 14: "GND",
          15: 22, 16: 23, 17: "3V3", 18: 24, 19: 10, 20: "GND", 21: 9, 22: 25, 23: 11, 24: 8, 25: "GND", 26: 7, 27: 0, 28: 1,
          29: 5, 30: "GND", 31: 6, 32: 12, 33: 13, 34: "GND", 35: 19, 36: 16, 37: 26, 38: 20, 39: "GND", 40: 21}
FYSISK = {g: p for p, g in HEADER.items() if isinstance(g, int)}          # BCM → fysisk pinne
LYDKORT_FYS = (31, 40)                                                   # holdes fri til lydkortet (og GND)
RESERVERT = {0: "HAT-EEPROM (ID_SD)", 1: "HAT-EEPROM (ID_SC)", 18: "I²S BCK til lydkortet (PCM5102)",
             19: "I²S LRCK til lydkortet (PCM5102)", 21: "I²S DIN til lydkortet (PCM5102)"}
ALT_NAVN = {2: "I²C SDA", 3: "I²C SCL", 4: "GPCLK0", 7: "SPI CE1", 8: "SPI CE0", 9: "SPI MISO", 10: "SPI MOSI", 11: "SPI SCLK",
            14: "UART TXD", 15: "UART RXD", 18: "PCM CLK", 19: "PCM FS", 20: "PCM DIN", 21: "PCM DOUT"}
_I2C = "I²C må være av (ingen dtparam=i2c_arm=on i /boot/firmware/config.txt). Pinnen har fast pull-up til 3,3 V"
_UART = "UART må være av (enable_uart=0 og ingen seriell konsoll i cmdline.txt)"
_SPI = "SPI må være av (ingen dtparam=spi=on i /boot/firmware/config.txt)"
VARSEL = {2: _I2C, 3: _I2C, 14: _UART, 15: _UART, 7: _SPI, 8: _SPI, 9: _SPI, 10: _SPI, 11: _SPI}

# Funksjonene en pinne kan ha. id = «seksjon.nøkkel» (eller bare «nøkkel» på toppnivå) i s1f_pins.yaml.
FUNKSJONER = [
    {"id": "buttons.bt", "navn": "Knapp BT/AirPlay", "gruppe": "knapp"},
    {"id": "buttons.aux", "navn": "Knapp AUX", "gruppe": "knapp"},
    {"id": "buttons.radio", "navn": "Knapp RADIO", "gruppe": "knapp"},
    {"id": "buttons.usb", "navn": "Knapp USB", "gruppe": "knapp"},
    {"id": "buttons.power", "navn": "Knapp av/på", "gruppe": "knapp"},
    {"id": "leds.bt", "navn": "Lys BT/AirPlay", "gruppe": "lys"},
    {"id": "leds.aux", "navn": "Lys AUX", "gruppe": "lys"},
    {"id": "leds.radio", "navn": "Lys RADIO", "gruppe": "lys"},
    {"id": "leds.usb", "navn": "Lys USB", "gruppe": "lys"},
    {"id": "leds.power", "navn": "Lys av/på", "gruppe": "lys"},
    {"id": "encoder.a", "navn": "Volumhjul A", "gruppe": "hjul"},
    {"id": "encoder.b", "navn": "Volumhjul B", "gruppe": "hjul"},
    {"id": "encoder.sw", "navn": "Volumhjul trykk", "gruppe": "hjul"},
    {"id": "relay", "navn": "Relé (forsterker)", "gruppe": "rele"},
    {"id": "headphone_detect", "navn": "Hodetelefondetekt", "gruppe": "hp"},
    {"id": "usb_switch.pulse", "navn": "USB-switch puls", "gruppe": "usbsw"},
    {"id": "usb_switch.sense", "navn": "USB-switch PC 1-lys (valgfri)", "gruppe": "usbsw"},
    {"id": "dac_xsmt", "navn": "DAC XSMT (demping)", "gruppe": "dac"},
]
FUNK_IDS = [f["id"] for f in FUNKSJONER]
FUNK_NAVN = {f["id"]: f["navn"] for f in FUNKSJONER}
# Uten disse virker ikke S1 som den skal – gir en advarsel (ikke feil) når de står uten pinne
VIKTIGE = ["buttons.bt", "buttons.aux", "buttons.radio", "buttons.usb", "buttons.power", "encoder.a", "encoder.b", "encoder.sw", "relay"]


def standard_fil():
    """Standardfila (fra repoet eller /usr/local/share/ki-amp), uten brukerens /etc/skjold-fil."""
    for p in PIN_FILES[1:]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("fant ingen standard s1f_pins.yaml")


def _del(fid):
    return fid.split(".", 1) if "." in fid else (None, fid)


def pin_bruk(cfg):
    """{funksjon-id: BCM-nummer eller None} fra en innlest pinnefil."""
    out = {}
    for fid in FUNK_IDS:
        sek, key = _del(fid)
        v = (cfg.get(sek) or {}).get(key) if sek else cfg.get(key)
        out[fid] = v if isinstance(v, int) and not isinstance(v, bool) else None
    return out


def _norm(v):
    """Pinneverdi fra JSON: int, «17», «GPIO17», None/«»/«null» → int eller None. Ugyldig → ValueError."""
    if v is None or isinstance(v, bool) and v is False:
        return None
    if isinstance(v, bool):
        raise ValueError("ugyldig pinne: true")
    if isinstance(v, int):
        return v
    s = str(v).strip().lower()
    if s in ("", "null", "none", "ingen", "~"):
        return None
    if s.startswith("gpio"):
        s = s[4:]
    if not s.isdigit():
        raise ValueError(f"ugyldig pinne: {v!r}")
    return int(s)


def valider_pinner(tildeling):
    """Sjekk en full tildeling {funksjon-id: BCM|None} mot reglene i pi/tests/test_s1f.py.

    Feil (lagres ikke): ukjent funksjon, ugyldig nummer, reservert pinne (0/1 HAT-EEPROM, 18/19/21 I²S), fysisk pinne
    31–40 (lydkortet), samme pinne brukt to ganger. Advarsler (lagres): I²C/UART/SPI må være av, viktig funksjon uten pinne.
    Returnerer {"ok", "feil": [str], "advarsler": [str], "pinner": normalisert tildeling}."""
    feil, adv, ren = [], [], {}
    for fid, v in (tildeling or {}).items():
        if fid not in FUNK_NAVN:
            feil.append(f"ukjent funksjon: {fid}")
            continue
        try:
            ren[fid] = _norm(v)
        except ValueError as e:
            feil.append(f"{FUNK_NAVN[fid]}: {e}")
    brukt = {}
    for fid in FUNK_IDS:
        g = ren.get(fid)
        if g is None:
            continue
        navn = FUNK_NAVN[fid]
        if g not in FYSISK:
            feil.append(f"{navn}: GPIO{g} finnes ikke (0–27)")
            continue
        if g in RESERVERT:
            feil.append(f"{navn}: GPIO{g} er reservert – {RESERVERT[g]}")
        elif LYDKORT_FYS[0] <= FYSISK[g] <= LYDKORT_FYS[1]:
            feil.append(f"{navn}: GPIO{g} er fysisk pinne {FYSISK[g]} – pinne 31–40 holdes fri til lydkortet")
        brukt.setdefault(g, []).append(fid)
    for g, fids in sorted(brukt.items()):
        if len(fids) > 1:
            feil.append(f"GPIO{g} er brukt to ganger: " + " og ".join(FUNK_NAVN[f] for f in fids))
    for g, fids in sorted(brukt.items()):
        if g in VARSEL and g not in RESERVERT:
            adv.append(f"GPIO{g} ({ALT_NAVN[g]}, {FUNK_NAVN[fids[0]]}): {VARSEL[g]}")
    for fid in VIKTIGE:
        if fid in ren and ren[fid] is None:
            adv.append(f"{FUNK_NAVN[fid]} har ingen pinne")
    return {"ok": not feil, "feil": feil, "advarsler": adv, "pinner": ren}


def _yaml_verdi(v):
    return "null" if v is None else str(v)


def _ny_linje(innrykk, key, v, fid):
    venstre = f"{innrykk}{key}: {_yaml_verdi(v)}"
    if v is None:
        kom = f"{FUNK_NAVN[fid]} – ikke i bruk"
    else:
        kom = f"{FUNK_NAVN[fid]} (pinne {FYSISK.get(v, '?')}" + (f", {ALT_NAVN[v]} – {VARSEL[v].split(' (')[0]}" if v in VARSEL else "") + ")"
    return f"{venstre:<16} # {kom}"


MERKE = "# Endret i web-UI-et (Innstillinger → Maskinvare → Pinner). Slett fila (eller trykk «Tilbakestill») for standardpinnene."


def skriv_pinner(tekst, tildeling):
    """Sett pinneverdiene i teksten til en s1f_pins.yaml og behold resten (kommentarer, timing, lyd).

    Linjer der verdien er uendret, røres ikke. Endrede linjer får en ny kommentar (funksjon + fysisk pinne). Mangler en
    nøkkel (eldre fil), legges den til i seksjonen – eller seksjonen legges til nederst."""
    linjer = tekst.splitlines()
    for fid, v in tildeling.items():
        sek, key = _del(fid)
        rx = re.compile(r"^(\s+)" + re.escape(key) + r":(.*)$") if sek else re.compile(r"^()" + re.escape(key) + r":(.*)$")
        inne, funnet, slutt = sek is None, False, None
        for i, l in enumerate(linjer):
            if re.match(r"^\S", l) and not l.startswith("#"):
                if sek:
                    if inne and slutt is None:
                        slutt = i
                    inne = l.split(":", 1)[0].strip() == sek
                    continue
            m = rx.match(l)
            if inne and m and (sek is None or m.group(1)):
                if m.group(2).split("#", 1)[0].strip() == "":
                    continue                     # en seksjon med samme navn, ikke en verdi
                funnet = True
                if _scalar(m.group(2).split("#", 1)[0]) != v:
                    linjer[i] = _ny_linje(m.group(1), key, v, fid)
                break
        if funnet:
            continue
        if sek is None:
            linjer.append(_ny_linje("", key, v, fid))
            continue
        hode = next((i for i, l in enumerate(linjer) if re.match(r"^" + re.escape(sek) + r":\s*(#.*)?$", l)), None)
        if hode is None:
            linjer += [f"{sek}:", _ny_linje("  ", key, v, fid)]
        else:
            j = hode + 1
            while j < len(linjer) and (linjer[j].startswith((" ", "\t")) or not linjer[j].strip()):
                j += 1
            while j > hode + 1 and not linjer[j - 1].strip():
                j -= 1
            linjer.insert(j, _ny_linje("  ", key, v, fid))
    if MERKE not in linjer:
        linjer.insert(0, MERKE)
    return "\n".join(linjer) + "\n"


def lagre_pinner(tildeling, ut=None, kilde=None):
    """Valider og skriv pinnene til /etc/skjold/s1f_pins.yaml (atomisk). `tildeling` kan være delvis: det som mangler,
    beholdes fra fila som brukes nå. Teksten tas fra `ut` hvis den finnes (brukerens egne endringer i timing o.l.
    beholdes), ellers fra standardfila. Ugyldig → ValueError med valideringen som args[1]. Returnerer valideringen + "fil"."""
    ut = ut or ETC_PINS
    if kilde is None:
        kilde = ut if os.path.exists(ut) else standard_fil()
    with open(kilde) as fh:
        tekst = fh.read()
    full = {**pin_bruk(parse_yaml(tekst)), **(tildeling or {})}
    res = valider_pinner(full)
    if not res["ok"]:
        raise ValueError("; ".join(res["feil"]), res)
    ny = skriv_pinner(tekst, res["pinner"])
    if pin_bruk(parse_yaml(ny)) != res["pinner"]:      # skal aldri skje – men skriv aldri en fil som ikke leses tilbake likt
        raise ValueError("pinnefila ble ikke som forventet", res)
    d = os.path.dirname(ut)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = ut + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(ny); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, ut)
    return {**res, "fil": ut}


def tilbakestill_pinner(ut=None):
    """Slett /etc/skjold/s1f_pins.yaml, så standardfila brukes igjen. True hvis det fantes en fil."""
    ut = ut or ETC_PINS
    if os.path.exists(ut):
        os.remove(ut)
        return True
    return False


def pinne_regler():
    """Reglene og headeren til web-UI-et (samme data som valider_pinner bruker)."""
    return {"header": [{"fys": p, "type": g if isinstance(g, str) else ("id" if g in (0, 1) else "gpio"),
                        "gpio": g if isinstance(g, int) else None} for p, g in sorted(HEADER.items())],
            "reservert": {str(g): t for g, t in RESERVERT.items()}, "lydkort_fys": list(LYDKORT_FYS),
            "varsel": {str(g): t for g, t in VARSEL.items()}, "alt": {str(g): t for g, t in ALT_NAVN.items()},
            "funksjoner": FUNKSJONER, "viktige": VIKTIGE}


# ---------------------------------------------------------------- knappelogikk (ren, tid sendes inn)

class ClickHold:
    """Én knapp: klikk (eventuelt flere innen et vindu), hold med terskel, og fremdrift for hold-ringen.

    multi = 1: klikk sendes straks ved slipp. multi > 1: klikk telles og sendes når vinduet går ut, eller straks når
    maks antall er nådd. Holdes knappen forbi `hold`, sendes hold én gang og slippet ignoreres.

    hold2 (power): to trinn. Hold sendes da først når knappen SLIPPES etter `hold` (trinn 1, omstart), eller straks når
    den har vært holdt i `hold2` (trinn 2, tilbakestilling). `elapsed` er sekunder knappen har vært nede."""

    def __init__(self, name, emit, multi=1, window=0.38, hold=None, show=0.35, hold2=None):
        self.name, self.emit, self.multi, self.window, self.hold, self.show = name, emit, multi, window, hold, show
        self.hold2 = hold2; self.elapsed = 0.0
        self.down = None; self.held = False; self.clicks = 0; self.deadline = 0.0; self.progress = None

    def press(self, t):
        self.down = t; self.held = False; self.progress = None

    def release(self, t):
        if self.down is None:
            return
        el = t - self.down
        self.down = None; self.progress = None; self.elapsed = 0.0
        if self.held:
            self.held = False; return
        if self.hold2 and self.hold and el >= self.hold:      # sluppet mellom hold og hold2: trinn 1
            self.clicks = 0; self.emit("hold", self.name, 1); return
        if self.multi <= 1:
            self.emit("click", self.name, 1); return
        self.clicks += 1; self.deadline = t + self.window
        if self.clicks >= self.multi:
            n, self.clicks = self.clicks, 0; self.emit("click", self.name, n)

    def tick(self, t):
        if self.down is not None and not self.held and self.hold:
            el = t - self.down
            self.elapsed = el
            self.progress = round(min(1.0, el / self.hold), 3) if el >= self.show else None
            if self.hold2:
                if el >= self.hold2:
                    self.held = True; self.clicks = 0; self.progress = None; self.elapsed = 0.0
                    self.emit("hold", self.name, 2)
            elif el >= self.hold:
                self.held = True; self.clicks = 0; self.progress = None
                self.emit("hold", self.name, 1)
        if self.down is None and self.clicks and t >= self.deadline:
            n, self.clicks = self.clicks, 0; self.emit("click", self.name, n)


LED_LEVELS = [1.0, 0.55, 0.22, 0.0]   # Høy / Middels / Lav / Av
UI_SRC = {"bt": "air", "aux": "aux", "radio": "radio", "usb": "usb", "power": "power", "enc": "knob"}   # navn i skjold-ui
HOLD_KEY = {"bt": "src", "radio": "radio", "power": "reboot", "enc": "knob"}   # status["hold"]["key"] for skjermen
RING_OF = {"airplay": "bt", "bt": "bt", "aux": "aux", "aux2": "aux", "radio": "radio", "usb": "usb"}


class S1FControls:
    """Kobler knappehendelser til handlinger i daemonen. `api` har attributtene:
    state (dict), set_input(inp), set_power(on), set_mute(on), set_volume(v), transport(a), bt_pairing(on),
    step_preset(d), save_preset(n), usb_toggle(), reboot(), night_toggle(src), power_event(kind),
    smenu_open(), smenu_close(), smenu_step(d), smenu_press(), smenu_is_open(), settings() -> dict,
    set_headphones(on), ui_event(ev, src, d) -> bool.

    Hver fysiske hendelse sendes først til skjold-ui (pi/skjold_ui/KONTRAKT.md): `ui_event` returnerer True når skjermen
    brukte den (hilsenen vises, menyen er åpen, hjulet holdt = meny) – da gjøres ingenting her."""

    def __init__(self, api, timing=None):
        self.api = api
        self.T = {**DEFAULT_TIMING, **(timing or {})}
        T, e = self.T, self._on
        self.btn = {
            "bt": ClickHold("bt", e, hold=T["hold_pair"], show=T["hold_show"]),
            "aux": ClickHold("aux", e, hold=T.get("hold_routine", 2.0), show=T["hold_show"]),   # hold = rutine (valgfritt)
            "radio": ClickHold("radio", e, hold=T["hold_save"], show=T["hold_show_radio"]),
            "usb": ClickHold("usb", e, hold=T.get("hold_routine", 2.0), show=T["hold_show"]),
            "power": ClickHold("power", e, multi=2, window=T["click_window"], hold=T["hold_reboot"], show=T["hold_show"], hold2=T["hold_reset"]),
            "enc": ClickHold("enc", e, multi=3, window=T["click_window"], hold=T["hold_settings"], show=T["hold_show"]),
        }
        self.overlay = None           # {"type", ..., "until"}
        self.night_flash_t0 = 0.0
        self.usb_flash_t0 = 0.0
        self.reboot_t0 = 0.0
        self.lock = threading.RLock()

    # --- inn fra maskinvaren
    def press(self, name, t=None):
        t = time.monotonic() if t is None else t
        self._activity()
        with self.lock:
            self.btn[name].press(t)

    def release(self, name, t=None):
        t = time.monotonic() if t is None else t
        with self.lock:
            self.btn[name].release(t)

    def _activity(self):
        """Hvert trykk og hvert hakk på hjulet teller som aktivitet, så skjermen våkner fra dimming."""
        fn = getattr(self.api, "input_event", None)
        if fn:
            fn()

    def rotate(self, d):
        self._activity()
        with self.lock:
            if self.api.ui_event("turn", "knob", 1 if d > 0 else -1):
                return
            if self.api.smenu_is_open():
                self.api.smenu_step(1 if d > 0 else -1); return
            st = self.api.state
            self.api.set_volume(st.get("hp_volume" if self._hp_own() else "volume", 0) + (1 if d > 0 else -1))
            self.overlay = {"type": "volume", "until": time.monotonic() + 2.2}

    def tick(self, t=None):
        t = time.monotonic() if t is None else t
        with self.lock:
            for b in self.btn.values():
                b.tick(t)
            if self.overlay and t >= self.overlay.get("until", 0):
                self.overlay = None

    def _hp_own(self):
        return bool(self.api.state.get("headphones")) and bool(self.api.settings().get("hpOwn", True))

    # --- handlinger
    def _on(self, kind, name, n):
        a, st = self.api, self.api.state
        if a.ui_event("hold" if kind == "hold" else "press", UI_SRC[name], n if name == "enc" else 1):
            return
        inp = st.get("input")
        if kind == "hold" and name in ("aux", "usb"):
            fn = getattr(a, "hold_routine", None)   # rutine koblet til knappen (Innstillinger → Rutiner)
            if fn:
                fn(name)
            return
        if name == "bt":
            if kind == "hold":
                a.bt_pairing(True)
            elif st.get("bt_pairing"):
                a.bt_pairing(False)                       # trykk under paring = avbryt
            elif inp == "airplay":
                a.set_input("bt")
            elif inp == "bt":
                a.set_input("airplay")
            else:
                a.set_input(st.get("last_wireless") or "airplay")
        elif name == "aux":
            a.set_input("aux2" if inp == "aux" else "aux")
        elif name == "radio":
            if kind == "hold":
                a.save_preset(st.get("preset") or 1)
            elif inp != "radio":
                a.set_input("radio")
            else:
                a.step_preset(1)
        elif name == "usb":
            if not st.get("power"):
                # i standby bytter USB-knappen PC på USB-bryteren uten å slå på eller bytte lydkilde
                a.usb_toggle()
                now = time.monotonic()
                self.usb_flash_t0 = now
                self.overlay = {"type": "usb", "pc": int(st.get("usb_pc") or 1), "until": now + self.T["usb_show"]}
            elif inp != "usb":
                a.set_input("usb")
            else:
                a.usb_toggle()
        elif name == "power":
            if kind == "hold":
                # sluppet etter 3–10 s = omstart · holdt i 10 s = tilbake til fabrikkinnstillinger
                self.reboot_t0 = time.monotonic(); a.power_event("long_press")
                (a.factory_reset if n >= 2 else a.reboot)()
            elif n >= 2:
                a.power_event("double_press")
                if int(a.settings().get("dblPower", 0) or 0) == 0:
                    a.night_toggle("Skjold")
                    self.night_flash_t0 = time.monotonic()
            else:
                a.power_event("single_press"); a.set_power(not st.get("power"))
        elif name == "enc":
            if kind == "hold":
                (a.smenu_close if a.smenu_is_open() else a.smenu_open)()
            elif a.smenu_is_open():
                a.smenu_press()
            elif n == 1:
                a.set_mute(not st.get("mute")); self.overlay = {"type": "volume", "until": time.monotonic() + 2.2}
            elif n == 2:
                a.transport("next")
            else:
                a.transport("previous")

    @property
    def hold(self):
        """Hold-ringen i formatet skjold-ui leser: {"key": knob|src|radio|reboot, "p": 0–1}."""
        for k, b in self.btn.items():
            if b.progress is not None and k in HOLD_KEY:
                return {"key": HOLD_KEY[k], "p": b.progress}
        return None

    def flash_night(self):
        self.night_flash_t0 = time.monotonic()

    # --- status til skjermen
    @property
    def ui(self):
        hold = None
        for k, b in self.btn.items():
            if b.progress is not None:
                kind = {"bt": "pair", "radio": "save", "power": "reboot", "enc": "settings"}.get(k, k)
                hold = {"kind": kind, "p": b.progress}
                if k == "power":       # trinnene skjermen viser: 0–3 s omstart, 3–7 s «slipp for omstart», 7–10 s tilbakestill
                    el = b.elapsed
                    hold.update(s=round(el, 2), stage=0 if el < self.T["hold_reboot"] else 1 if el < self.T["hold_reset_warn"] else 2,
                                left=round(max(0.0, (self.T["hold_reboot"] if el < self.T["hold_reboot"] else self.T["hold_reset"]) - el), 1))
                    if hold["stage"] == 2: hold["kind"] = "reset"
        st = self.api.state
        screen = ("settings" if self.api.smenu_is_open() else
                 ("pairing" if st.get("bt_pairing") else ("main" if st.get("power") else "standby")))
        ov = dict(self.overlay) if self.overlay else None
        if ov:
            ov.pop("until", None)
        return {"screen": screen, "sel": self.api.smenu_idx(), "edit": False, "hold": hold, "overlay": ov}

    # --- LED-ringer (opplevd lysstyrke 0–1)
    def led_frame(self, t, st, level=1.0):
        out = {k: 0.0 for k in ("bt", "aux", "radio", "usb", "power")}
        if self.reboot_t0 and t - self.reboot_t0 < 30:
            out["power"] = level * (1.0 if int((t - self.reboot_t0) / 0.3) % 2 == 0 else 0.0); return out
        on = bool(st.get("power"))
        ring = RING_OF.get(st.get("input"))
        if on and ring:
            out[ring] = level
        if st.get("bt_pairing"):
            out["bt"] = level if int(t / self.T["bt_blink"]) % 2 == 0 else 0.0
        out["power"] = level if on else level * 0.15
        if self.usb_flash_t0 and t - self.usb_flash_t0 < self.T["usb_show"]:      # PC byttet i standby
            out["usb"] = level
        dt = t - self.night_flash_t0
        if self.night_flash_t0 and dt < 1.8:      # 3 blink ved nattmodus
            out["power"] = level if int(dt / 0.3) % 2 == 0 else 0.0
        return out


# ---------------------------------------------------------------- nattmodus via MQTT (Home Assistant)

def mqtt_night_discovery(base, hid, dev):
    """(topic, payload)-par for HA MQTT discovery: utløser for dobbelttrykk, event-entitet, knapp og bryter."""
    av = {"availability_topic": base + "/online"}
    return [
        (f"homeassistant/device_automation/{hid}/power_double/config",
         {"automation_type": "trigger", "topic": base + "/event/power", "type": "button_double_press", "subtype": "power",
          "payload": "double_press", "device": dev}),
        (f"homeassistant/device_automation/{hid}/power_single/config",
         {"automation_type": "trigger", "topic": base + "/event/power", "type": "button_short_press", "subtype": "power",
          "payload": "single_press", "device": dev}),
        (f"homeassistant/event/{hid}/power/config",
         {"name": "Power", "unique_id": f"{hid}_power_event", "state_topic": base + "/event/power",
          "event_types": ["single_press", "double_press", "long_press"],
          "value_template": '{"event_type": "{{ value }}"}', "device": dev, **av}),
        (f"homeassistant/button/{hid}/night/config",
         {"name": "Nattmodus", "unique_id": f"{hid}_night_button", "command_topic": base + "/set/night_trigger",
          "payload_press": "PRESS", "device": dev, "icon": "mdi:weather-night", **av}),
        (f"homeassistant/switch/{hid}/nattmodus/config",
         {"name": "Nattmodus", "unique_id": f"{hid}_nattmodus", "command_topic": base + "/set/night",
          "state_topic": base + "/night", "payload_on": "ON", "payload_off": "OFF", "state_on": "ON", "state_off": "OFF",
          "retain": True, "device": dev, "icon": "mdi:weather-night", **av}),
    ]


def parse_steps(payload):
    try:
        v = json.loads(payload)
        return [{"name": str(s.get("name", ""))[:40], "done": bool(s.get("done"))} for s in v if isinstance(s, dict)][:4]
    except Exception:
        return None


# ---------------------------------------------------------------- WebSocket-protokollen fra designet

DESIGN_INPUTS = ["wireless", "aux", "radio", "usb"]   # i = 0..3 i prototypen


def design_index(inp):
    return {"airplay": 0, "bt": 0, "spotify": 0, "aux": 1, "aux2": 1, "radio": 2, "usb": 3}.get(inp, 0)


def design_state(s, settings):
    """Tilstandsmelding som i publish() i prototypen, pluss hele status under «status»."""
    inp = s.get("input")
    return {"type": "state", "power": bool(s.get("power")), "main": True, "input": design_index(inp),
            "wl": "bt" if inp == "bt" or (inp not in ("airplay", "bt") and s.get("last_wireless") == "bt") else "air",
            "aux": 1 if inp == "aux2" else 0, "usb": max(0, int(s.get("usb_pc") or 1) - 1),
            "preset": max(0, int(s.get("preset") or 1) - 1), "vol": s.get("volume", 0), "muted": bool(s.get("mute")),
            "hp": bool(s.get("headphones")), "paused": bool(s.get("paused")), "title": s.get("title", ""),
            "sub": s.get("artist", ""), "st": s.get("album", ""), "name": s.get("name", ""),
            "presets": [p.get("title", "") for p in (s.get("presets") or []) if p][:6], "night": bool((s.get("night") or {}).get("on")) if isinstance(s.get("night"), dict) else bool(s.get("night")),
            "set": settings, "status": s}


def ws_command(m, a):
    """Utfør én melding fra web/app. `a` er samme api som S1FControls pluss: settings_patch(d), settings_reset(),
    presets_set(list), bt_forget(), speaker_test(ch), test_voice(), preview_clock(), night_set(on, src, steps),
    play_preset(n), usb_set(pc). Returnerer svar-dict eller None."""
    t = m.get("type")
    st = a.state
    if t == "input":
        i = int(m.get("i", 0))
        a.set_input([st.get("last_wireless") or "airplay", "aux", "radio", "usb"][max(0, min(3, i))])
    elif t == "wl":
        a.set_input("bt" if m.get("v") == "bt" else "airplay")
    elif t == "src":
        v = int(m.get("v", 0)); inp = st.get("input")
        if inp in ("aux", "aux2"): a.set_input("aux2" if v else "aux")
        elif inp == "usb": a.usb_set(v + 1)
        elif inp == "radio": a.play_preset(v + 1)
    elif t == "vol":
        a.set_volume(int(m.get("v", 0)))
    elif t == "mute":
        a.set_mute(not st.get("mute"))
    elif t == "power":
        a.set_power(not st.get("power"))
    elif t == "pause":
        a.transport("playpause")
    elif t == "next":
        a.transport("next")
    elif t == "set":
        a.settings_patch({m.get("k"): m.get("v")})
    elif t == "reset":
        a.settings_reset()
    elif t == "presets":
        a.presets_set([{"title": p[0], "url": p[1]} for p in (m.get("list") or []) if isinstance(p, (list, tuple)) and len(p) >= 2][:6])
    elif t == "forget":
        a.bt_forget()
    elif t in ("setup", "setupTest"):
        if m.get("ch") in ("L", "R"): a.speaker_test(m["ch"])
    elif t == "testVoice":
        a.test_voice()
    elif t == "previewClock":
        a.preview_clock()
    elif t == "nightMode":
        a.night_toggle(m.get("src") or "Appen")
    elif t == "nightState":
        if m.get("src") != "S1":
            a.night_set(bool(m.get("on")), m.get("src") or "Home Assistant", m.get("steps"))
    elif t in ("hello", "state", "updSync"):
        return None
    else:
        return {"type": "error", "error": f"ukjent melding: {t}"}
    return None


# ---------------------------------------------------------------- maskinvare (gpiozero)

class S1FHardware:
    def __init__(self, pins, controls, api):
        from gpiozero import Button, PWMLED, RotaryEncoder, DigitalInputDevice  # noqa: F401
        self.p, self.c, self.api = pins, controls, api
        bounce = float(pins.get("bounce") or 0.03)
        self.objs, self.leds, self.hp, self.feil = [], {}, None, []

        def lag(navn, fn):   # én pinne som feiler (f.eks. opptatt av I²C) skal ikke ta med seg resten
            try:
                o = fn()
                self.objs.append(o)
                return o
            except Exception as e:
                self.feil.append(f"{navn}: {e}")
                print(f"S1F: {navn} feilet: {e}", flush=True)
                return None

        for name, pin in (pins.get("buttons") or {}).items():
            if pin is None or name not in controls.btn:
                continue
            b = lag(f"knapp {name} (GPIO{pin})", lambda pin=pin: Button(int(pin), pull_up=True, bounce_time=bounce))
            if b:
                b.when_pressed = lambda n=name: self._safe(controls.press, n)
                b.when_released = lambda n=name: self._safe(controls.release, n)
        enc = pins.get("encoder") or {}
        if enc.get("a") is not None and enc.get("b") is not None:
            r = lag(f"volumhjul (GPIO{enc['a']}/{enc['b']})",
                    lambda: RotaryEncoder(int(enc["a"]), int(enc["b"]), max_steps=0, wrap=False))
            if r:
                r.when_rotated_clockwise = lambda: self._safe(controls.rotate, 1)
                r.when_rotated_counter_clockwise = lambda: self._safe(controls.rotate, -1)
        if enc.get("sw") is not None:
            s = lag(f"volumhjul trykk (GPIO{enc['sw']})", lambda: Button(int(enc["sw"]), pull_up=True, bounce_time=bounce))
            if s:
                s.when_pressed = lambda: self._safe(controls.press, "enc")
                s.when_released = lambda: self._safe(controls.release, "enc")
        ah = pins.get("led_active_high", True) is not False
        hz = int(pins.get("led_hz") or 400)
        for name, pin in (pins.get("leds") or {}).items():
            if pin is not None:
                led = lag(f"lys {name} (GPIO{pin})", lambda pin=pin: PWMLED(int(pin), active_high=ah, frequency=hz))
                if led:
                    self.leds[name] = led
        hp = pins.get("headphone_detect")
        if hp is not None:
            self.hp = lag(f"hodetelefondetekt (GPIO{hp})", lambda: DigitalInputDevice(int(hp), pull_up=True, bounce_time=0.15))
            if self.hp:
                inv = bool(pins.get("headphone_active_low"))
                upd = lambda: self._safe(api.set_headphones, bool(self.hp.value) != inv)   # pull-up: høy = plugget (bryter åpner)
                self.hp.when_activated = self.hp.when_deactivated = upd
                upd()
        if self.feil and any("GPIO2)" in f or "GPIO3)" in f for f in self.feil):
            print("S1F: GPIO2/3 er opptatt – er I²C på? Kommenter ut dtparam=i2c_arm=on i /boot/firmware/config.txt og start på nytt", flush=True)
        threading.Thread(target=self._loop, daemon=True).start()

    @staticmethod
    def _safe(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            print("S1F:", e, flush=True)

    def _loop(self):
        sent = {}
        while True:
            t = time.monotonic()
            self.c.tick(t)
            try:
                frame = self.c.led_frame(t, self.api.state, self.api.led_scale())
                for k, led in self.leds.items():
                    v = round(max(0.0, min(1.0, frame.get(k, 0.0))), 3)
                    if sent.get(k) != v:
                        led.value = v; sent[k] = v
            except Exception as e:
                print("S1F LED:", e, flush=True)
            time.sleep(0.02)
