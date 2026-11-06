"""Skjold Hjul: volum, transport, romvalg, favoritter og videresending (pi/skjold_hjul.py)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_hjul as hj  # noqa: E402
import skjold_nfc as nfc  # noqa: E402


@pytest.fixture
def env(tmp_path):
    s = {"vol": 30, "log": [], "fwd": [], "steps": [], "peers": [{"navn": "Kjøkken", "base": "http://k:8765"}]}
    ctx = {"get_volume": lambda: s["vol"], "set_volume": lambda v: s.__setitem__("vol", v),
           "transport": lambda a: s["log"].append(a), "playing": lambda: True,
           "run_steps": lambda st: s["steps"].extend(st), "steps_for": nfc.steps_for,
           "peers": lambda: s["peers"], "clean_card": nfc.clean_card,
           "forward": lambda base, body: (s["fwd"].append((base, body)), {"volum": 55})[1]}
    return hj.Hjul(ctx, str(tmp_path / "hjul.json")), s


def test_volum_og_transport(env):
    h, s = env
    r = h.event({"device": "a", "type": "rot", "delta": 3})
    assert s["vol"] == 36 and r["volum"] == 36 and r["rom"] == "Her"
    h.event({"device": "a", "type": "rot", "delta": -50})
    assert s["vol"] == 0
    h.event({"device": "a", "type": "klikk"}); h.event({"device": "a", "type": "dobbel"})
    assert s["log"] == ["playpause", "next"]


def test_romvalg_og_videresending(env):
    h, s = env
    assert h.event({"device": "a", "type": "lang"})["rom"] == "Kjøkken"
    r = h.event({"device": "a", "type": "rot", "delta": 1})
    assert r == {"volum": 55, "rom": "Kjøkken"} and s["fwd"][0][0] == "http://k:8765" and s["fwd"][0][1]["lokal"]
    assert s["vol"] == 30
    assert h.event({"device": "a", "type": "lang"})["rom"] == "Her"
    s["peers"] = []
    h.set_config({"enheter": {"a": {"rom": "Kjøkken"}}})
    assert h.event({"device": "a", "type": "rot", "delta": 1})["rom"] == "Her"   # borte rom → her


def test_favoritter(env):
    h, s = env
    with pytest.raises(ValueError):
        h.event({"device": "a", "type": "fav", "n": 1})
    h.set_config({"favoritter": [{"navn": "P1", "handling": "preset", "verdi": 1, "volum": 25}]})
    r = h.event({"device": "a", "type": "fav", "n": 1, "batteri": 80})
    assert r["favoritt"] == "P1" and s["steps"] == [{"type": "volume", "verdi": 25}, {"type": "preset", "verdi": 1}]
    assert h.load()["enheter"]["a"]["batteri"] == 80
    h.event({"device": "a", "type": "lang"}); s["steps"].clear()
    h.event({"device": "a", "type": "fav", "n": 1})
    assert all(x["rom"] == "Kjøkken" for x in s["steps"])


def test_ukjent_og_glem(env):
    h, _ = env
    with pytest.raises(ValueError):
        h.event({"type": "tull"})
    h.event({"device": "a", "type": "hei"})
    assert "a" in h.load()["enheter"]
    h.set_config({"glem": ["a"]})
    assert h.load()["enheter"] == {}
