"""Skjold Kassett: kartotek, lær-modus, steg og uttak (pi/skjold_nfc.py)."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_nfc as nfc  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return nfc.NfcStore(str(tmp_path / "kort.json"))


def test_uid_normaliseres():
    assert nfc.norm_uid("04:a1:B2 c3") == "04-A1-B2-C3"
    assert nfc.norm_uid("04A1B2C3") == "04-A1-B2-C3"
    with pytest.raises(ValueError):
        nfc.norm_uid("04A")


def test_kort_valideres():
    with pytest.raises(ValueError):
        nfc.clean_card({"uid": "0401", "handling": "tull", "verdi": 1})
    with pytest.raises(ValueError):
        nfc.clean_card({"uid": "0401", "handling": "preset"})
    c = nfc.clean_card({"uid": "0401", "handling": "preset", "verdi": 3, "volum": "150", "rom": "Stue, Kjøkken"})
    assert c["volum"] == 100 and c["rom"] == ["Stue", "Kjøkken"] and c["ved_uttak"] == "ingenting"
    assert nfc.clean_card({"uid": "0401", "handling": "routine"})["verdi"] is None


def test_steg_per_rom():
    c = nfc.clean_card({"uid": "0401", "handling": "navidrome_album", "verdi": "al-1", "volum": 30, "rom": ["A", "B"]})
    s = nfc.steps_for(c)
    assert [x["type"] for x in s] == ["volume", "nd_album", "volume", "nd_album"]
    assert {x["rom"] for x in s} == {"A", "B"}
    url = nfc.steps_for(nfc.clean_card({"uid": "01", "handling": "play_url", "verdi": "http://x", "navn": "P13"}))
    assert url == [{"type": "play_url", "verdi": "http://x", "tittel": "P13"}]


def test_lagre_skanne_teller_og_slette(store):
    store.put({"uid": "04:01", "navn": "NRK P1", "handling": "preset", "verdi": 1, "ved_uttak": "pause"})
    r = store.scan("0401")
    assert r["known"] and not r["learned"] and r["steps"][0] == {"type": "preset", "verdi": 1}
    assert store.get("04-01")["spilt"] == 1
    assert store.scan("ffff")["known"] is False
    assert store.delete("04 01") and store.list() == []


def test_laer_modus_bruker_det_som_spiller(store):
    store.learn(10)
    assert store.learning()
    r = store.scan("AABB", current=lambda: {"navn": "Radio Norge", "handling": "preset", "verdi": 4})
    assert r["learned"] and r["card"]["uid"] == "AA-BB" and not store.learning()
    assert store.get("aabb")["navn"] == "Radio Norge"


def test_laer_modus_med_utkast_og_feil_uten_noe(store):
    store.learn(10, {"navn": "Album", "handling": "ma_uri", "verdi": "tidal://album/1"})
    assert store.scan("0102")["card"]["handling"] == "ma_uri"
    store.learn(10)
    with pytest.raises(ValueError):
        store.scan("0103", current=lambda: {})


def test_laer_tidsavbrudd(store):
    store.learn(5)
    store.learn_until = time.time() - 1
    assert store.scan("0104")["known"] is False


def test_uttak_pauser_bare_aktiv_kassett(store):
    store.put({"uid": "01", "handling": "preset", "verdi": 1, "ved_uttak": "pause"})
    store.put({"uid": "02", "handling": "preset", "verdi": 2, "ved_uttak": "pause"})
    store.scan("01")
    assert store.removed("02")["pause"] is False
    assert store.removed("01")["pause"] is True
    assert store.removed("01")["pause"] is False


def test_det_som_spiller_til_kassett():
    c = nfc.current_to_card({"input": "radio"}, {"n": 2, "name": "P3", "logo": "/api/logo?k=p2"}, {})
    assert c == {"navn": "P3", "handling": "preset", "verdi": 2, "omslag": "/api/logo?k=p2", "undertittel": "Radio"}
    c = nfc.current_to_card({"input": "radio"}, {}, {"url": "http://s", "album": "Kind of Blue", "artist": "Miles"})
    assert c["handling"] == "play_url" and c["navn"] == "Kind of Blue"
    assert nfc.current_to_card({"input": "aux"}, {}, {}) == {}


def test_learn_partial_draft_merges_current(tmp_path):
    s = nfc.NfcStore(str(tmp_path / "k.json"))
    s.learn(60, {"rom": ["Stue"], "volum": 30})
    cur = lambda: {"navn": "NRK P2", "handling": "preset", "verdi": 2}
    r = s.scan("04a1", cur)
    assert r["learned"] and r["card"]["rom"] == ["Stue"] and r["card"]["handling"] == "preset" and r["card"]["volum"] == 30
