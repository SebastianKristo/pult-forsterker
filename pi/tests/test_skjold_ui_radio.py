"""skjold-ui på Skjold Radio: hjulet ↔ menyen på skjermen (handle_input/radio_input) og oppsettfilene."""
import importlib
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
WEB = os.path.join(HERE, "..", "skjold_ui", "web")


@pytest.fixture
def sui(tmp_path, monkeypatch):
    monkeypatch.setenv("SKJOLD_GREETING", str(tmp_path / "greeting.json"))
    monkeypatch.setenv("SKJOLD_BACKLIGHT", str(tmp_path / "bl"))
    import skjold_ui.__main__ as m
    m = importlib.reload(m)
    got = []
    monkeypatch.setattr(m, "broadcast", got.append)
    m.ui["menu"] = False
    return m, got


def test_wheel_hold_opens_menu_then_goes_back(sui):
    m, got = sui
    assert m.handle_input({"ev": "hold", "src": "wheel"}) == {"consumed": True}
    assert got[-1]["ev"] == "menu_toggle"
    m.ui["menu"] = True   # skjermen melder menyen åpen (POST /ui/state)
    assert m.handle_input({"ev": "hold", "src": "wheel"}) == {"consumed": True}
    assert got[-1]["ev"] == "back"


def test_wheel_navigates_only_while_menu_is_open(sui):
    m, got = sui
    assert m.handle_input({"ev": "turn", "src": "wheel", "d": -1}) == {"consumed": False}
    assert got[-1] == {"ev": "browse", "d": -1}             # vis hvilken favoritt hjulet blar til
    assert m.handle_input({"ev": "press", "src": "wheel"}) == {"consumed": False}   # spill/pause
    m.ui["menu"] = True
    for ev in ({"ev": "turn", "src": "wheel", "d": 1}, {"ev": "press", "src": "wheel"}):
        assert m.handle_input(ev) == {"consumed": True}
        assert got[-1] == ev


def test_presets_power_volume_are_never_taken(sui):
    m, got = sui
    m.ui["menu"] = True
    assert m.handle_input({"ev": "press", "src": "preset", "n": 4}) == {"consumed": False}
    assert got[-1] == {"ev": "preset", "n": 4}
    assert m.handle_input({"ev": "saved", "src": "preset", "n": 2}) == {"consumed": False}
    assert got[-1] == {"ev": "saved", "n": 2}
    for src in ("power", "volume"):
        assert m.handle_input({"ev": "press", "src": src}) == {"consumed": False}


def test_greeting_still_takes_first_press(sui):
    m, got = sui
    m.greeting_write({"name": "Pappa", "state": "armed"})
    assert m.handle_input({"ev": "press", "src": "preset", "n": 1}) == {"consumed": True}
    assert got[-1] == {"ev": "dismiss_greeting"} and m.greeting_read()["state"] == "shown"


def test_backlight_and_net(sui, tmp_path):
    m, _ = sui
    d = tmp_path / "bl" / "10-0045"
    d.mkdir(parents=True)
    (d / "max_brightness").write_text("255\n")
    (d / "brightness").write_text("255\n")
    assert m.set_backlight(0.5)["ok"] and (d / "brightness").read_text() == "128"
    n = m.net_info()
    assert n["host"] and isinstance(n["ip"], str)


def test_layout_selection_files():
    idx = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    lay = open(os.path.join(WEB, "layout.js"), encoding="utf-8").read()
    assert "layout.js" in idx and "radio.js" in lay and "screen.js" in lay
    js = open(os.path.join(WEB, "radio.js"), encoding="utf-8").read()
    for ev in ("menu_toggle", "browse", "saved", "back", "dismiss_greeting"):
        assert "'" + ev + "'" in js
    # bare ekte daemon-endepunkter
    for path in ("/api/status", "/api/presets/", "/api/radio/browse", "/api/radio/play", "/api/input", "/api/plugins/sleep",
                 "/api/plugins/alarm", "/api/settings", "/api/wifi", "/api/medialib", "/api/transport"):
        assert path in js
