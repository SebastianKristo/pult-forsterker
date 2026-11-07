"""Skjold Radio – knapper, navigasjonshjul og volumknott → Skjold-daemonen (HTTP på 127.0.0.1:8765).

Radioen er en vanlig Skjold-enhet (KI_AMP_BOARD=kit: PCM5102A over I²S med XSMT på GPIO 26, TPA3116D2 bak GPIO 27,
skjerm med skjold-ui). Kit-profilen har ingen knapper på GPIO, så denne lille
tjenesten (skjold-radio-knapper.service) leser bare knappene fra pi/config/radio_pins.yaml og kaller daemonens API,
så daemonen trenger ingen egen «radio»-profil:

  favoritt 1–6   kort trykk: spill favoritten · hold 2 s: lagre det som spiller som favoritten
  hjulet         drei: bla i favorittene (starter etter 0,6 s ro) · trykk: spill/pause
  volumknotten   drei: volum ±2 · trykk: demp av/på
  av/på          kort trykk: av/på · hold 3 s: omstart

Logikken (RadioKnapper) er ren Python og testes i pi/tests/test_radio_knapper.py uten GPIO."""
import json
import os
import threading
import time
import urllib.request

PIN_FILES = ["/etc/skjold/radio_pins.yaml", os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "radio_pins.yaml"),
             "/usr/local/share/ki-amp/radio_pins.yaml"]
API = os.environ.get("SKJOLD_API", "http://127.0.0.1:8765")


def load_pins(paths=PIN_FILES):
    import yaml
    for p in paths:
        if os.path.isfile(p):
            with open(p) as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("fant ingen radio_pins.yaml")


def http(method, path, body=None, timeout=4):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw or b"{}")


class RadioKnapper:
    """Hendelser inn (fra GPIO eller tester) → API-kall ut. `api(method, path, body)` og `clock()` kan byttes i tester."""

    def __init__(self, cfg, api=http, clock=time.monotonic):
        self.cfg, self.api, self.clock = cfg or {}, api, clock
        self.step = int(self.cfg.get("volume_step", 2))
        self.settle = float((self.cfg.get("timing") or {}).get("wheel_settle", 0.6))
        self._wheel = 0          # netto hakk som venter på å bli til en favoritt
        self._wheel_at = 0.0
        self._cur = None         # favoritten vi har bladd til (1-basert)

    # --- favoritter og av/på ---
    def preset(self, n, held=False):
        if held:
            return self.api("POST", "/api/preset", {"n": n, "save": True})
        return self.api("POST", f"/api/presets/{n}/play", {})

    def power(self, held=False):
        if held:
            return self.api("POST", "/api/reboot", {})
        return self.api("POST", "/api/toggle", {})

    # --- volumknotten ---
    def volume(self, steps):
        return self.api("POST", "/api/volume", {"delta": int(steps) * self.step})

    def mute_toggle(self):
        st = self.api("GET", "/api/status")
        return self.api("POST", "/api/mute", {"mute": not bool(st.get("mute"))})

    # --- hjulet ---
    def wheel(self, steps):
        self._wheel += int(steps)
        self._wheel_at = self.clock()

    def wheel_press(self):
        return self.api("POST", "/api/transport", {"action": "playpause"})

    def tick(self):
        """Kalles jevnlig: når hjulet har stått i ro i `settle` sekunder, spilles favoritten man bladde til."""
        if not self._wheel or self.clock() - self._wheel_at < self.settle:
            return None
        st = self.api("GET", "/api/status")
        presets = [p for p in (st.get("presets") or []) if p]
        if not presets:
            self._wheel = 0
            return None
        cur = self._cur or int(st.get("preset") or 1)
        n = (cur - 1 + self._wheel) % len(presets) + 1
        self._wheel, self._cur = 0, n
        return self.api("POST", f"/api/presets/{n}/play", {})


def main():  # pragma: no cover - krever GPIO
    from gpiozero import Button, RotaryEncoder
    cfg = load_pins()
    k = RadioKnapper(cfg)
    b = float(cfg.get("bounce", 0.03))
    tm = cfg.get("timing") or {}
    keep = []

    def safe(f, *a, **kw):
        try:
            f(*a, **kw)
        except Exception as e:
            print("Skjold Radio:", e, flush=True)

    for i, pin in enumerate(cfg.get("presets") or [], start=1):
        btn = Button(pin, pull_up=True, bounce_time=b, hold_time=float(tm.get("hold_save", 2.0)))
        btn._held = False
        btn.when_held = lambda btn=btn, n=i: (setattr(btn, "_held", True), safe(k.preset, n, True))
        btn.when_released = lambda btn=btn, n=i: (safe(k.preset, n) if not btn._held else None, setattr(btn, "_held", False))
        keep.append(btn)
    pw = Button(cfg["power"], pull_up=True, bounce_time=b, hold_time=float(tm.get("hold_reboot", 3.0)))
    pw._held = False
    pw.when_held = lambda: (setattr(pw, "_held", True), safe(k.power, True))
    pw.when_released = lambda: (safe(k.power) if not pw._held else None, setattr(pw, "_held", False))
    keep.append(pw)
    w, v = cfg["wheel"], cfg["volume"]
    we = RotaryEncoder(w["a"], w["b"], max_steps=0)
    we.when_rotated_clockwise = lambda: k.wheel(1)
    we.when_rotated_counter_clockwise = lambda: k.wheel(-1)
    ve = RotaryEncoder(v["a"], v["b"], max_steps=0)
    ve.when_rotated_clockwise = lambda: safe(k.volume, 1)
    ve.when_rotated_counter_clockwise = lambda: safe(k.volume, -1)
    ws, vs = Button(w["sw"], pull_up=True, bounce_time=b), Button(v["sw"], pull_up=True, bounce_time=b)
    ws.when_pressed = lambda: safe(k.wheel_press)
    vs.when_pressed = lambda: safe(k.mute_toggle)
    keep += [we, ve, ws, vs]
    print("Skjold Radio: knapper klare", flush=True)
    while True:
        safe(k.tick)
        time.sleep(0.1)


if __name__ == "__main__":  # pragma: no cover
    main()
