"""Enhetsprofiler i Home Assistant-integrasjonen (custom_components/skjold/devices.py – ren Python, ingen HA)."""
import importlib.util
import os

_P = os.path.join(os.path.dirname(__file__), "..", "..", "custom_components", "skjold", "devices.py")
_spec = importlib.util.spec_from_file_location("skjold_ha_devices", _P)
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)


def test_main_model_per_product():
    assert D.main_model({"board": "s1f"}, "s1") == ("Skjold S1 rev F", "s1-s1f", "rev F")
    assert D.main_model({"board": "main"}, "s1")[0] == "Skjold S1"
    assert D.main_model({"board": "node"}, "node")[:2] == ("Skjold Node", "node-node")
    assert D.main_model({}, "core") == ("Skjold Core", "core", None)
    assert D.main_model({"board": "touch"}, "touch")[0] == "Skjold Touch"


def test_rost_devices():
    res = {"lyrion": True, "minis": [{"id": "AA:BB", "name": "Skjold Røst bad", "connected": True, "power": True,
                                      "playing": False, "volume": 40, "synced": True, "ip": "10.0.0.9"}, {"name": "uten id"}]}
    out = D.rost_devices(res)
    assert len(out) == 1 and out[0]["id"] == "aa:bb" and out[0]["volume"] == 40 and out[0]["synced"]
    assert D.rost_devices(None) == [] and D.rost_devices({"lyrion": False, "minis": []}) == []


def test_kassett_state():
    assert D.kassett_state(None, None) is None
    assert D.kassett_state({"cards": [], "last": {"uid": ""}}, None) is None   # ingen spiller i bruk
    nfc = {"cards": [{"uid": "04A1", "navn": "Jazz"}, {"uid": "04B2", "navn": "Jazz"}, {"uid": "04C3", "navn": "P3"}],
           "active": "04C3", "last": {"uid": "04C3", "navn": "P3", "t": 1700000000}}
    k = D.kassett_state(nfc, {"på": False})
    assert k["active"] == "P3" and k["last"] == "P3" and k["spoler"] is False
    assert D.card_option_names(k["cards"]) == ["Jazz (04A1)", "Jazz (04B2)", "P3"]


def test_hjul_devices():
    cfg = {"rom": ["Dette rommet", "Kjøkken"], "enheter": {"hjul-1": {"navn": "Stuehjul", "batteri": 81, "sist": 1700000000, "rom": "Kjøkken"},
                                                           "hjul-2": {}}}
    out = D.hjul_devices(cfg)
    assert [h["name"] for h in out] == ["Skjold Hjul", "Stuehjul"]
    stue = out[1]
    assert stue["battery"] == 81 and stue["room"] == "Kjøkken" and stue["rooms"] == ["Dette rommet", "Kjøkken"]
    assert out[0]["room"] == "Dette rommet"


def test_kassett_state_ventende_delte_og_mest_spilt():
    s = D.kassett_state({"cards": [{"uid": "04-A1", "navn": "Meteora", "spilt": 5}, {"uid": "04-B2", "navn": "25", "spilt": 2}],
                       "ventende": [{"artist": "Adele", "album": "21"},
                                    {"handling": "album", "verdi": {"artist": "a-ha", "album": "HHL"}, "fra": "Kari"}]}, None)
    assert s["ventende"] == 2 and s["ventende_delte"] == 1 and s["mest_spilt"] == "Meteora"
