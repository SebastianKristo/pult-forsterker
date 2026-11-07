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


def test_ndef_og_etikett():
    assert nfc.ndef_url("04a1b2") == "skjold://kassett/04-A1-B2"
    assert nfc.uid_from_ndef("skjold://kassett/04-A1-B2") == "04-A1-B2"
    svg = nfc.label_sheet_svg([{"navn": "Nitimen <3", "undertittel": "NRK P1", "omslag": "http://x/a.jpg"},
                               {"navn": "Uten bilde", "undertittel": ""}], image=lambda u: "data:image/png;base64,AA", start=2)
    assert svg.startswith("<svg") and "Nitimen &lt;3" in svg and "data:image/png;base64,AA" in svg
    assert svg.count('class="k"') == 2 and "UTEN BILDE" in svg


def test_spoler_folger_avspillingen(tmp_path):
    from skjold_nfc import Spoler
    s = Spoler(str(tmp_path / "spoler.json"))
    spill = {"playing": True, "paused": False, "position": 10, "title": "A"}
    assert s.status(spill, kassett_inne=True, now=100)["modus"] == "spill"
    assert s.status({**spill, "position": 11}, True, now=101)["rps"] == 0.5
    # pause → stopp
    assert s.status({**spill, "playing": False, "paused": True}, True, now=102)["modus"] == "stopp"
    # uten kassett står spolene stille (standard)
    assert s.status(spill, kassett_inne=False, now=103)["modus"] == "stopp"
    # hopp fremover → kort spoling, så vanlig fart igjen
    s.status({**spill, "position": 20}, True, now=110)
    r = s.status({**spill, "position": 80}, True, now=111)
    assert r["modus"] == "spol" and r["retning"] == 1 and r["rps"] == 1.6
    assert s.status({**spill, "position": 81}, True, now=111.5)["modus"] == "spol"
    assert s.status({**spill, "position": 83}, True, now=113)["modus"] == "spill"
    # hopp bakover → tilbake
    r = s.status({**spill, "position": 30}, True, now=114)
    assert r["modus"] == "tilbake" and r["retning"] == -1
    # ny låt → spol fremover
    s.status({**spill, "position": 31}, True, now=120)
    assert s.status({**spill, "position": 1, "title": "B"}, True, now=121)["modus"] == "spol"


def test_spoler_innstillinger_lagres(tmp_path):
    from skjold_nfc import Spoler
    p = str(tmp_path / "spoler.json")
    s = Spoler(p)
    assert s.sett({"fart": 9, "spol": 0.1, "på": False, "bare_kassett": False}) == \
        {"på": False, "fart": 1.5, "spol": 0.5, "bare_kassett": False, "vent": 2.5}
    s2 = Spoler(p)
    assert s2.cfg["på"] is False and s2.cfg["fart"] == 1.5
    assert s2.status({"playing": True, "position": 1, "title": "A"}, True, now=1)["modus"] == "stopp"


def test_spoler_tvang_ved_neste(tmp_path):
    from skjold_nfc import Spoler
    sp = Spoler(str(tmp_path / "s.json"))
    assert sp.skal_vente(True) == 2.5 and sp.skal_vente(False) == 0.0     # bare med kassett inne (standard)
    sp.tving(-1, 2.5, now=100.0)
    st = sp.status({"playing": False}, True, now=101.0)                  # lyden står mens den spoler
    assert st["modus"] == "tilbake" and st["retning"] == -1
    assert sp.status({"playing": True, "position": 1, "title": "Ny"}, True, now=103.0)["modus"] == "spill"
    assert sp.sett({"vent": 0})["vent"] == 0.0 and sp.skal_vente(True) == 0.0


def test_spoler_hopp_i_laaten_gir_fysisk_spoling(tmp_path):
    from skjold_nfc import Spoler
    sp = Spoler(str(tmp_path / "s.json"))
    sp.status({"playing": True, "position": 10, "title": "A"}, True, now=100.0)
    sp.status({"playing": True, "position": 82, "title": "A"}, True, now=101.0)   # spolt 0:10 → 1:22
    retning, hopp = sp.hent_hopp()
    assert retning == 1 and 70 < hopp < 72 and sp.hent_hopp() is None
    assert 1.0 <= sp.spoletid(hopp) <= 2.5 and sp.spoletid(600) == 2.5
    sp.status({"playing": True, "position": 30, "title": "A"}, True, now=102.0)   # bakover
    assert sp.hent_hopp()[0] == -1
    sp.sett({"vent": 0})
    sp.status({"playing": True, "position": 200, "title": "A"}, True, now=103.0)
    assert sp.hent_hopp() is None                                                  # av: ingen pause
