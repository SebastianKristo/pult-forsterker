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


# ---------- album-kassetter, import og paring ----------
def test_album_resolve_navidrome_forst_saa_youtube():
    from skjold_nfc import resolve_album
    nd = lambda q: [{"id": "al1", "name": "Meteora (Bonus Edition)", "artist": "Linkin Park", "coverArt": "c1"}]
    ma = lambda q: [{"uri": "ytmusic://album/x", "name": "Meteora", "artist": "Linkin Park", "provider": "ytmusic"}]
    lo = resolve_album("Linkin Park", "Meteora", nd, ma)
    assert lo["kilde"] == "navidrome" and lo["id"] == "al1"
    lo = resolve_album("Linkin Park", "Meteora", lambda q: [], ma)
    assert lo["kilde"] == "ytmusic" and lo["uri"] == "ytmusic://album/x"
    assert resolve_album("Adele", "25", lambda q: [{"id": "x", "name": "21", "artist": "Adele"}], lambda q: []) is None


def test_album_fuzzy_artist_og_navn():
    from skjold_nfc import best_album, norm_navn
    assert norm_navn("Axwell Λ Ingrosso") == norm_navn("Axwell & Ingrosso")
    hits = [{"name": "More Than You Know", "artist": "Axwell /\\ Ingrosso"}, {"name": "More Than You Know", "artist": "Someone Else"}]
    assert best_album(hits, "Axwell Λ Ingrosso", "More Than You Know")["artist"].startswith("Axwell")
    assert best_album([{"name": "LIVING THINGS", "artist": "Linkin Park"}], "linkin park", "Living Things")


def test_album_kassett_scan_og_steg(tmp_path):
    from skjold_nfc import NfcStore, steps_for
    st = NfcStore(str(tmp_path / "c.json"))
    st.put({"uid": "04AA", "handling": "album", "verdi": "Linkin Park - Hybrid Theory"})
    c = st.get("04AA")
    assert c["navn"] == "Hybrid Theory" and c["undertittel"] == "Linkin Park" and c["omslag"].startswith("/api/nfc/cover?")

    def resolve(card):
        return st.lagre_losning(card["uid"], {"kilde": "navidrome", "id": "al9"})
    res = st.scan("04:aa", resolve=resolve, standard_rom="Kjøkken")
    assert res["card"]["losning"]["kilde"] == "navidrome"
    assert {"type": "nd_album", "verdi": "al9", "rom": "Kjøkken"} in res["steps"]
    yt = {**c, "losning": {"kilde": "ytmusic", "uri": "ytmusic://album/7"}}
    assert steps_for(yt)[-1] == {"type": "ma", "verdi": "ytmusic://album/7"}


def test_trenger_ny_losning_maks_en_gang_i_dognet():
    from skjold_nfc import trenger_ny_losning
    assert trenger_ny_losning({"handling": "album"})
    assert not trenger_ny_losning({"losning": {"kilde": "navidrome", "t": 0}}, now=10**9)
    assert not trenger_ny_losning({"losning": {"kilde": "ytmusic", "t": 1000}}, now=2000)
    assert trenger_ny_losning({"losning": {"kilde": "ytmusic", "t": 1000}}, now=1000 + 86401)


def test_import_og_ventende_kobles_til_ny_brikke(tmp_path):
    from skjold_nfc import NfcStore
    st = NfcStore(str(tmp_path / "c.json"))
    r = st.importer("# liste\nLinkin Park - Meteora\nAdele - 25\nLinkin Park - Meteora\n")
    assert r["lagt_til"] == 2 and r["hoppet_over"] == 1 and len(r["ventende"]) == 2
    res = st.scan("04-01", resolve=lambda c: c)
    assert res["known"] and res["card"]["verdi"] == {"artist": "Linkin Park", "album": "Meteora"}
    assert [v["album"] for v in st.oppsett()["ventende"]] == ["25"]
    st.sett_oppsett({"koble_ventende": False})
    assert not st.scan("04-02")["known"]
    assert st.importer("Adele - 25")["lagt_til"] == 0             # finnes allerede som ventende


def test_paring_lagres(tmp_path):
    from skjold_nfc import NfcStore
    st = NfcStore(str(tmp_path / "c.json"))
    assert st.sett_oppsett({"paret": "Stue Touch"})["paret"] == "Stue Touch"
    assert NfcStore(str(tmp_path / "c.json")).oppsett()["paret"] == "Stue Touch"


# ---------- Kassett-Wrapped ----------
def test_kassett_stats_topp_glemte_og_maned(tmp_path):
    import skjold_nfc as N
    s = N.NfcStore(str(tmp_path / "nfc.json"))
    a = s.put({"uid": "04A1", "handling": "album", "verdi": {"artist": "Linkin Park", "album": "Meteora"}})
    b = s.put({"uid": "04B2", "handling": "play_url", "verdi": "https://radio.example/stream", "navn": "Jazz"})
    c = s.put({"uid": "04C3", "handling": "nrk", "verdi": "p1", "navn": "NRK P1"})
    dag = 86400
    now = 1_800_000_000
    for i in range(3):
        s.logg.inn(a["uid"], "Meteora", "Navidrome", now=now - i * dag)
        s.logg.ut(a["uid"], now=now - i * dag + 1800)
    s.logg.inn(b["uid"], "Jazz", "radio", now=now - 2 * dag)
    s.logg.inn(c["uid"], "NRK P1", "NRK", now=now - 100 * dag)          # gammel: glemt
    st = s.stats("år", 8, now=now)
    assert st["topp"][0]["navn"] == "Meteora" and st["topp"][0]["spilt"] == 3 and st["topp"][0]["lyttetid"] == 5400
    assert st["favoritt"]["uid"] == a["uid"]
    assert [g["navn"] for g in st["glemte"]] == ["NRK P1"]
    assert st["totalt"]["spilt"] == 5 and st["totalt"]["kassetter"] == 3
    assert sum(m["spilt"] for m in st["per_maned"]) == 5
    assert s.stats("uke", 8, now=now)["totalt"]["spilt"] == 4                # NRK-avspillingen er eldre enn en uke


def test_scan_og_uttak_logges(tmp_path):
    import skjold_nfc as N
    s = N.NfcStore(str(tmp_path / "nfc.json"))
    s.put({"uid": "04D4", "handling": "play_url", "verdi": "https://x/y", "navn": "R"})
    s.scan("04D4")
    s.removed("04D4")
    h = s.logg.hendelser()
    assert len(h) == 1 and h[0]["u"] == "04-D4" and h[0]["k"] == "radio" and "d" in h[0]


def test_logg_er_rullerende(tmp_path):
    import skjold_nfc as N
    lg = N.KassettLogg(str(tmp_path / "l.json"))
    lg.MAKS = 10
    for i in range(25):
        lg.inn("04-AA", now=1000 + i)
    assert len(lg.hendelser()) == 10


# ---------- Del en kassett ----------
def test_delingskode_rundtur_uten_private_felt(tmp_path):
    import skjold_nfc as N
    kort = [
        {"uid": "01", "handling": "album", "verdi": {"artist": "Adele", "album": "25"}, "navn": "25", "undertittel": "Adele", "rom": ["Stue"]},
        {"uid": "02", "handling": "navidrome_album", "verdi": "al-123-hemmelig", "navn": "Meteora", "undertittel": "Linkin Park"},
        {"uid": "03", "handling": "play_url", "verdi": "https://radio.example/stream", "navn": "Jazz"},
        {"uid": "04", "handling": "play_url", "verdi": "https://nd.local/rest/stream?u=meg&p=hemmelig", "navn": "Privat"},
        {"uid": "05", "handling": "preset", "verdi": 3, "navn": "Favoritt 3"},
    ]
    d = N.del_kode(kort, fra="Sebastian")
    assert d["delt"] == 3 and d["hoppet_over"] == 2
    assert d["lenke"].startswith("skjold://kassett/del?d=") and len(d["kode"]) < 400
    tilbake = N.les_kode(d["lenke"])
    assert tilbake["fra"] == "Sebastian"
    alt = str(tilbake)
    assert "al-123" not in alt and "hemmelig" not in alt and "Stue" not in alt
    assert tilbake["kassetter"][1] == {"handling": "album", "verdi": {"artist": "Linkin Park", "album": "Meteora"},
                                       "navn": "Meteora", "undertittel": "Linkin Park", "omslag": tilbake["kassetter"][1]["omslag"]}
    assert N.les_kode(d["web"])["kassetter"] == tilbake["kassetter"]
    import pytest
    with pytest.raises(ValueError):
        N.les_kode("tull")
    with pytest.raises(ValueError):
        N.del_kode([kort[4]])


def test_importer_deling_blir_ventende_og_kobles_til_ny_brikke(tmp_path):
    import skjold_nfc as N
    s = N.NfcStore(str(tmp_path / "nfc.json"))
    kode = N.del_kode([{"uid": "01", "handling": "album", "verdi": {"artist": "Adele", "album": "25"}, "navn": "25"},
                       {"uid": "02", "handling": "play_url", "verdi": "https://radio.example/s", "navn": "Jazz"}], fra="Ola")["kode"]
    r = s.importer_deling(kode)
    assert r["lagt_til"] == 2 and r["fra"] == "Ola"
    assert s.importer_deling(kode)["lagt_til"] == 0                      # samme kode to ganger: ingen dubletter
    res = s.scan("04EE")                                                  # ny brikke → første ventende
    assert res["card"]["handling"] == "album" and res["card"]["fra"] == "Ola"
    res2 = s.scan("04FF")
    assert res2["card"]["handling"] == "play_url" and res2["card"]["verdi"] == "https://radio.example/s"
    assert s.oppsett()["ventende"] == []


def test_sky_deling_kryptert_rundtur():
    import skjold_nfc as N
    blob, key, n = N.sky_pakk([{"uid": "01", "handling": "album", "verdi": {"artist": "a-ha", "album": "Hunting High and Low"}, "navn": "HHL"}], "Kari")
    assert n == 1 and "Hunting" not in blob                               # skyen ser bare kryptert innhold
    k = N.sky_kode("abcdefgh23", key)
    assert N.er_sky_kode(k["lenke"]) == k["kode"] and N.er_sky_kode(k["web"]) == k["kode"]
    d = N.sky_les(k["kode"], lambda i: blob if i == "abcdefgh23" else None)
    assert d["fra"] == "Kari" and d["kassetter"][0]["verdi"]["album"] == "Hunting High and Low"
    import pytest
    feil = N.sky_kode("abcdefgh23", b"x" * 16)["kode"]
    with pytest.raises(ValueError):
        N.sky_les(feil, lambda i: blob)
    assert N.er_sky_kode("1abc") == ""
