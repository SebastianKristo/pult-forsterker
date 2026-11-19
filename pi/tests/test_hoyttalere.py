"""Høyttalerne (reléet til forsterkeren): egen av/på, og av under oppstart til lyden er klar."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class Rele:
    def __init__(self):
        self.value = False
        self.logg = []

    def __setattr__(self, k, v):
        if k == "value" and "logg" in self.__dict__:
            self.logg.append(bool(v))
        object.__setattr__(self, k, v)


@pytest.fixture
def d(monkeypatch):
    import ki_amp_daemon as d
    rele, xsmt = Rele(), Rele()
    monkeypatch.setattr(d, "relay_amp", rele)
    monkeypatch.setattr(d, "dac_xsmt", xsmt)
    monkeypatch.setattr(d, "HW", True)
    monkeypatch.setattr(d, "BOARD", "kit")
    monkeypatch.setattr(d, "S1F", True)
    monkeypatch.setattr(d, "changed", lambda *a, **k: None)
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)
    monkeypatch.setitem(d.state, "power", True)
    monkeypatch.setitem(d.state, "speakers", True)
    monkeypatch.setitem(d.state, "headphones", False)
    monkeypatch.setitem(d.state, "overtemp", False)
    monkeypatch.setattr(d, "_boot_hold", [False])
    return d, rele, xsmt


def test_av_under_oppstart(d):
    d, rele, _ = d
    d._boot_hold[0] = True
    assert d.speakers_on() is False
    d.apply_relay()
    assert rele.value is False
    d._boot_hold[0] = False
    d.apply_relay()
    assert rele.value is True


def test_hoyttalere_av_og_paa(d):
    d, rele, xsmt = d
    d.apply_relay()
    assert rele.value and xsmt.value
    d.set_speakers(False)
    assert rele.value is False and xsmt.value is False and d.state["speakers"] is False
    d.set_speakers(True)
    assert rele.value is True and xsmt.value is True


def test_hodetelefoner_med_autodemping_slaar_av_releet(d, monkeypatch):
    d, rele, _ = d
    monkeypatch.setitem(d.state, "hp_automute", True)
    d.apply_relay()
    assert rele.value is True
    monkeypatch.setitem(d.state, "headphones", True)
    d.apply_relay()
    assert rele.value is False


def test_power_av_gaar_foran_hoyttalere(d, monkeypatch):
    d, rele, _ = d
    monkeypatch.setitem(d.state, "power", False)
    d.apply_relay()
    assert rele.value is False


def test_hoyttalerniva_demper_bare_hoyttalerne(d, monkeypatch):
    d, _, _ = d
    monkeypatch.setitem(d.state, "settings", {"spkTrim": 2})
    assert d.spk_trim_db() == -12.0
    monkeypatch.setitem(d.state, "headphones", True)
    assert d.spk_trim_db() == 0.0
    monkeypatch.setitem(d.state, "headphones", False)
    monkeypatch.setitem(d.state, "settings", {"spkTrim": "tull"})
    assert d.spk_trim_db() == 0.0


def test_dempes_mens_releet_slaar_av_og_paa(d, monkeypatch):
    d, rele, _ = d
    logg = []

    class Dsp:
        def update_volume(self):
            logg.append(("demp", d._rele_demp[0]))

    monkeypatch.setattr(d, "dsp", Dsp())
    orig = Rele.__setattr__

    def spor(self, k, v):
        if k == "value" and self is rele:
            logg.append(("rele", bool(v), d._rele_demp[0]))
        orig(self, k, v)

    monkeypatch.setattr(Rele, "__setattr__", spor)
    d.apply_relay()                       # på
    d.set_speakers(False)                 # av
    releer = [x for x in logg if x[0] == "rele"]
    assert releer == [("rele", True, True), ("rele", False, True)], logg   # reléet byttes bare mens lyden er dempet
    assert logg[-1] == ("demp", False) and d._rele_demp[0] is False
