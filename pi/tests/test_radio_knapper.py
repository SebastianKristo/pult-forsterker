import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from skjold_radio_knapper import RadioKnapper, load_pins  # noqa: E402


class FakeApi:
    def __init__(self, status):
        self.status, self.calls = status, []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.status if method == "GET" else {}


def test_pins_file_is_valid_and_has_no_conflicts():
    cfg = load_pins([os.path.join(os.path.dirname(__file__), "..", "config", "radio_pins.yaml")])
    pins = list(cfg["presets"]) + [cfg["power"]] + list(cfg["wheel"].values()) + list(cfg["volume"].values())
    assert len(cfg["presets"]) == 6 and len(pins) == len(set(pins))
    assert not set(pins) & {0, 1, 2, 3, 8, 10, 11, 18, 19, 20, 21, 26, 27}   # EEPROM, I²C, SPI0, I²S, XSMT og forsterker (kit)


def test_presets_power_volume_mute():
    api = FakeApi({"mute": False})
    k = RadioKnapper({"volume_step": 2}, api=api)
    k.preset(3); k.preset(4, held=True); k.power(); k.power(held=True); k.volume(-2); k.mute_toggle()
    assert api.calls == [("POST", "/api/presets/3/play", {}), ("POST", "/api/preset", {"n": 4, "save": True}),
                         ("POST", "/api/toggle", {}), ("POST", "/api/reboot", {}), ("POST", "/api/volume", {"delta": -4}),
                         ("GET", "/api/status", None), ("POST", "/api/mute", {"mute": True})]


def test_wheel_waits_for_rest_then_wraps():
    t = [0.0]
    api = FakeApi({"preset": 5, "presets": [{"title": str(i)} for i in range(6)]})
    k = RadioKnapper({"timing": {"wheel_settle": 0.6}}, api=api, clock=lambda: t[0])
    k.wheel(1); k.wheel(1)
    t[0] = 0.3
    assert k.tick() is None and not api.calls                   # dreier fortsatt
    t[0] = 1.0
    k.tick()
    assert api.calls[-1] == ("POST", "/api/presets/1/play", {})  # 5 + 2 = 7 → 1 (rundt)
    k.wheel(-1); t[0] = 2.0; k.tick()
    assert api.calls[-1] == ("POST", "/api/presets/6/play", {})
