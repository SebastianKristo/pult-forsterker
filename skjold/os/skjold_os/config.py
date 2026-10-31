"""Pinner og skjermoppsett fra node_pins.json (/etc/skjold eller repoet)."""
import json, os

_HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = [
    os.environ.get("SKJOLD_PINS", ""),
    "/etc/skjold/node_pins.json",
    os.path.join(_HERE, "..", "..", "node", "config", "node_pins.json"),   # repo: skjold/os/skjold_os -> skjold/node
]

DEFAULT_SCREEN = {"width": 160, "height": 128, "rotate": 2, "bgr": False, "h_offset": 0, "v_offset": 0,
                  "spi_port": 0, "spi_device": 0, "bus_speed_hz": 16000000,
                  "pinner": {"RESET": {"gpio": 24}, "A0": {"gpio": 25}},
                  "bakgrunnslys": {"gpio": 23, "pwm_hz": 500, "aktiv_hoy": False}}


def load_pins():
    for p in CANDIDATES:
        if p and os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f), p
            except (OSError, ValueError):
                pass
    return {"skjerm": DEFAULT_SCREEN}, None


def screen_cfg():
    pins, src = load_pins()
    s = dict(DEFAULT_SCREEN); s.update(pins.get("skjerm") or {})
    return s, src
