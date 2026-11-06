"""Tester for Apple Hjem-tilbehøret (pi/skjold_homekit.py) uten nett og uten ekte iPhone."""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_homekit as hk  # noqa: E402

INPUTS = ["radio", "airplay", "bt", "aux", "usb"]


def bridge(st):
    calls = []
    b = {"state": lambda: st,
         "set_power": lambda v: calls.append(("power", v)), "set_input": lambda v: calls.append(("input", v)),
         "play_preset": lambda n: calls.append(("preset", n)), "set_volume": lambda v: calls.append(("volume", v)),
         "set_mute": lambda v: calls.append(("mute", v)), "transport": lambda a: calls.append(("transport", a))}
    return b, calls


def test_sources_and_active_id():
    src = hk.sources(INPUTS, ["NRK P3", None, "NRK Jazz"])
    assert [s[0] for s in src] == [1, 2, 3, 4, 5, 101, 103]
    assert src[1][1] == "AirPlay" and src[5][1] == "NRK P3"
    assert hk.active_id(INPUTS, {"input": "bt"}) == 3
    assert hk.active_id(INPUTS, {"input": "radio", "preset": 3}) == 103
    assert hk.active_id(INPUTS, {"input": "radio", "preset": 0}) == 1


def test_apply_identifier():
    b, calls = bridge({"volume": 30})
    hk.apply_identifier(b, INPUTS, 4)
    hk.apply_identifier(b, INPUTS, 102)
    assert calls == [("input", "aux"), ("preset", 2)]


def test_remote_keys():
    b, calls = bridge({"volume": 98})
    hk.apply_remote(b, 4)          # pil opp → volum +5, maks 100
    hk.apply_remote(b, 11)         # spill/pause
    hk.apply_remote(b, 7)          # høyre → neste
    assert hk.apply_remote(b, 99) is None
    assert calls == [("volume", 100), ("transport", "playpause"), ("transport", "next")]


def test_pin_format(tmp_path):
    p = hk.gen_pin()
    assert len(p) == 10 and p[3] == "-" and p[6] == "-" and p != "123-45-678"
    h = hk.SkjoldHomeKit(bridge({})[0], pin_file=str(tmp_path / "pin"), persist=str(tmp_path / "state"))
    assert h.pin() == h.pin()      # lagres og gjenbrukes


def test_build_accessory_with_pyhap(tmp_path):
    if not hk.HAP_OK:
        import pytest
        pytest.skip("HAP-python ikke installert")
    st = {"power": True, "input": "radio", "preset": 1, "volume": 34, "mute": False,
          "presets_full": [{"title": "NRK P3"}, {"title": "NRK P1"}], "version": "2.0", "product": "s1", "id": "stue"}
    b, calls = bridge(st)
    h = hk.SkjoldHomeKit(b, name="Stue", inputs=INPUTS, pin_file=str(tmp_path / "pin"), persist=str(tmp_path / "s"))
    from pyhap.loader import get_loader
    drv = mock.MagicMock()
    drv.loader = get_loader()
    acc = h._build(drv)
    assert acc.category == hk.CATEGORY_TELEVISION
    names = [s.display_name for s in acc.services]
    assert names.count("InputSource") == len(INPUTS) + 2 and "Television" in names and "TelevisionSpeaker" in names
    assert h._chars["ident"].value == 101 and h._chars["volume"].value == 34
    h._chars["ident"].client_update_value(3)        # velg Blåtann i Hjem-appen
    h._chars["volume"].client_update_value(50)
    h._chars["active"].client_update_value(0)
    assert ("input", "bt") in calls and ("volume", 50) in calls and ("power", False) in calls


def test_xhm_uri():
    # samme algoritme som pyhap (Accessory.xhm_uri): kategori 31 (TV), pin 013-89-335
    u = hk.xhm_uri("013-89-335", "ABCD")
    assert u.startswith("X-HM://") and u.endswith("ABCD") and len(u) == len("X-HM://") + 9 + 4
