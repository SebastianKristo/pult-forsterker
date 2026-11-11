"""Skjold S1 rev F: knapper, volumhjul, LED-ringer, relé, USB-switch og hodetelefondetekt på Pi-ens GPIO.

Ren logikk (ClickHold, S1FControls, ws_command, design_state, og mqtt_*) har ingen GPIO-avhengighet og
testes i pi/tests/test_s1f.py. S1FHardware kobler logikken til gpiozero. Pinnene leses fra pi/config/s1f_pins.yaml
(eller /etc/skjold/s1f_pins.yaml), aldri hardkodet.

Daemonen (ki_amp_daemon.py) gir et `api`-objekt med handlingene (set_input, set_power, transport …) og leser
`controls.ui` inn i status["ui"] for skjermprosessen (se pi/S1F.md for kontrakten).
"""
import json
import os
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
        self.objs = []
        for name, pin in (pins.get("buttons") or {}).items():
            if pin is None or name not in controls.btn:
                continue
            b = Button(int(pin), pull_up=True, bounce_time=bounce)
            b.when_pressed = lambda n=name: self._safe(controls.press, n)
            b.when_released = lambda n=name: self._safe(controls.release, n)
            self.objs.append(b)
        enc = pins.get("encoder") or {}
        if enc.get("a") is not None and enc.get("b") is not None:
            r = RotaryEncoder(int(enc["a"]), int(enc["b"]), max_steps=0, wrap=False)
            r.when_rotated_clockwise = lambda: self._safe(controls.rotate, 1)
            r.when_rotated_counter_clockwise = lambda: self._safe(controls.rotate, -1)
            self.objs.append(r)
        if enc.get("sw") is not None:
            s = Button(int(enc["sw"]), pull_up=True, bounce_time=bounce)
            s.when_pressed = lambda: self._safe(controls.press, "enc")
            s.when_released = lambda: self._safe(controls.release, "enc")
            self.objs.append(s)
        ah = pins.get("led_active_high", True) is not False
        self.leds = {}
        for name, pin in (pins.get("leds") or {}).items():
            if pin is not None:
                self.leds[name] = PWMLED(int(pin), active_high=ah, frequency=int(pins.get("led_hz") or 400))
        hp = pins.get("headphone_detect")
        if hp is not None:
            self.hp = DigitalInputDevice(int(hp), pull_up=True, bounce_time=0.15)
            inv = bool(pins.get("headphone_active_low"))
            upd = lambda: self._safe(api.set_headphones, bool(self.hp.value) != inv)   # pull-up: høy = plugget (bryter åpner)
            self.hp.when_activated = self.hp.when_deactivated = upd
            upd()
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
