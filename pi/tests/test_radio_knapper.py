import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from skjold_radio_knapper import RadioKnapper, load_pins  # noqa: E402


class FakeUi:
    """Skjermen (skjold-ui): registrerer hendelsene og sier om de ble brukt (menyen åpen)."""
    def __init__(self, consume=False):
        self.consume, self.events = consume, []

    def __call__(self, ev):
        self.events.append(ev)
        return self.consume(ev) if callable(self.consume) else self.consume


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
    k = RadioKnapper({"volume_step": 2}, api=api, ui=FakeUi())
    k.preset(3); k.preset(4, held=True); k.power(); k.power(held=True); k.volume(-2); k.mute_toggle()
    assert api.calls == [("POST", "/api/presets/3/play", {}), ("POST", "/api/preset", {"n": 4, "save": True}),
                         ("POST", "/api/toggle", {}), ("POST", "/api/reboot", {}), ("POST", "/api/volume", {"delta": -4}),
                         ("GET", "/api/status", None), ("POST", "/api/mute", {"mute": True})]


def test_wheel_waits_for_rest_then_wraps():
    t = [0.0]
    api = FakeApi({"preset": 5, "presets": [{"title": str(i)} for i in range(6)]})
    k = RadioKnapper({"timing": {"wheel_settle": 0.6}}, api=api, clock=lambda: t[0], ui=FakeUi())
    k.wheel(1); k.wheel(1)
    t[0] = 0.3
    assert k.tick() is None and not api.calls                   # dreier fortsatt
    t[0] = 1.0
    k.tick()
    assert api.calls[-1] == ("POST", "/api/presets/1/play", {})  # 5 + 2 = 7 → 1 (rundt)
    k.wheel(-1); t[0] = 2.0; k.tick()
    assert api.calls[-1] == ("POST", "/api/presets/6/play", {})


def test_every_event_goes_to_the_screen_first():
    api, ui = FakeApi({"mute": False}), FakeUi()
    k = RadioKnapper({}, api=api, ui=ui)
    k.preset(2); k.preset(5, held=True); k.wheel(1); k.wheel_press(); k.volume(-1); k.power()
    assert ui.events == [{"ev": "press", "src": "preset", "n": 2}, {"ev": "saved", "src": "preset", "n": 5},
                         {"ev": "turn", "src": "wheel", "d": 1}, {"ev": "press", "src": "wheel"},
                         {"ev": "turn", "src": "volume", "d": -1}, {"ev": "press", "src": "power"}]
    assert ("POST", "/api/transport", {"action": "playpause"}) in api.calls   # ikke brukt av skjermen → vanlig handling


def test_open_menu_takes_the_wheel():
    t = [0.0]
    api = FakeApi({"preset": 1, "presets": [{"title": str(i)} for i in range(6)]})
    ui = FakeUi(consume=lambda ev: ev["src"] == "wheel")   # menyen er åpen: skjold-ui bruker hjulet
    k = RadioKnapper({}, api=api, ui=ui, clock=lambda: t[0])
    k.wheel(1); k.wheel(1); k.wheel_press()
    t[0] = 5.0
    assert k.tick() is None and api.calls == []               # hjulet blar i menyen, ingen favoritt og ingen pause
    k.preset(3)
    assert api.calls == [("POST", "/api/presets/3/play", {})]  # favorittknappene virker alltid


def test_hold_wheel_opens_menu_and_cancels_browsing():
    t = [0.0]
    api, ui = FakeApi({"preset": 1, "presets": [{"title": "a"}, {"title": "b"}]}), FakeUi()
    k = RadioKnapper({}, api=api, ui=ui, clock=lambda: t[0])
    k.wheel(1); k.wheel_hold()
    assert ui.events[-1] == {"ev": "hold", "src": "wheel"}
    t[0] = 3.0
    assert k.tick() is None and not api.calls


def test_without_screen_buttons_work_as_before(monkeypatch):
    import skjold_radio_knapper as srk
    monkeypatch.setattr(srk, "UI", "http://127.0.0.1:9")   # ingen skjold-ui
    assert srk.ui_event({"ev": "press", "src": "wheel"}, timeout=0.2) is False
