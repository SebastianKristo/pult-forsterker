#!/usr/bin/env python3
"""Skjold S1 rev F: test knapper, volumhjul, hodetelefondetekt og LED-ringer uten resten av Skjold.

Skriver hvert trykk, slipp, klikk (1/2/3), hold og vri til terminalen, og tenner ringen til knappen du trykker.
Stopp ki-amp først (den bruker de samme pinnene):
    sudo systemctl stop ki-amp
    python3 pi/tools/s1f_inputtest.py [sti/til/s1f_pins.yaml]
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_s1f as s1  # noqa: E402

pins = s1.load_pins(sys.argv[1] if len(sys.argv) > 1 else None)
print("Pinner fra", pins["_file"])
for k in ("buttons", "leds", "encoder"):
    print(f"  {k}: {pins.get(k)}")
print(f"  relé {pins.get('relay')}, hodetelefon {pins.get('headphone_detect')}, USB-switch {pins.get('usb_switch')}")


class Probe:
    def __init__(self):
        self.state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False, "preset": 1}
        self.last = "power"

    def __getattr__(self, name):
        def f(*a, **k):
            print(f"  → {name}{a if a else ''}", flush=True)
            if name == "set_input": self.state["input"] = a[0]
            if name == "set_volume": self.state["volume"] = a[0]
            if name == "set_power": self.state["power"] = a[0]
            if name == "bt_pairing": self.state["bt_pairing"] = a[0]
            return None
        return f

    def settings(self): return {"dblPower": 0, "hpOwn": True}
    def greeting_active(self): return False
    def smenu_is_open(self): return False
    def smenu_idx(self): return None
    def led_scale(self): return 1.0
    def set_headphones(self, on): print(f"  hodetelefon: {'plugget i' if on else 'ute'}", flush=True)


probe = Probe()
c = s1.S1FControls(probe, pins.get("timing"))
_press, _rel, _rot = c.press, c.release, c.rotate
c.press = lambda n, t=None: (print(f"{time.strftime('%H:%M:%S')} trykk  {n}", flush=True), _press(n, t))
c.release = lambda n, t=None: (print(f"{time.strftime('%H:%M:%S')} slipp  {n}", flush=True), _rel(n, t))
c.rotate = lambda d: (print(f"{time.strftime('%H:%M:%S')} vri    {'+' if d > 0 else '-'}", flush=True), _rot(d))
s1.S1FHardware(pins, c, probe)
print("Klar. Trykk, hold og vri (Ctrl+C for å avslutte).")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
