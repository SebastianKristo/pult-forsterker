"""Kassettspilleren: hvilken Skjold den har kontakt med (vises på Kassetter-siden) og den delte ESPHome-nøkkelen."""
import base64
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


def test_spiller_spores_fra_spoler_og_scan():
    d.nfc_spillere.clear()
    d._nfc_spiller_sett("10.69.2.216")
    d._nfc_spiller_sett("10.69.2.216", "skjold-kassett", "04-A9-F2")
    d._nfc_spiller_sett("127.0.0.1")   # Skjold selv (Home Assistant/Homey «spill kassett») teller ikke
    sp = d._nfc_spillere_her()
    assert len(sp) == 1 and sp[0]["aktiv"] and sp[0]["navn"] == "skjold-kassett" and sp[0]["sist_uid"] == "04-A9-F2"
    d.nfc_spillere["10.69.2.216"]["sist"] = time.time() - 60
    assert not d._nfc_spillere_her()[0]["aktiv"]
    d.nfc_spillere.clear()


def test_esphome_nokkel_valideres_og_deles():
    old = dict(d.state.get("settings") or {})
    try:
        god = base64.b64encode(os.urandom(32)).decode()
        d.update_settings({"esphomeKey": god})
        assert d.settings()["esphomeKey"] == god
        d.update_settings({"esphomeKey": "ikke-en-nokkel"})
        d.update_settings({"esphomeKey": base64.b64encode(b"for kort").decode()})
        assert d.settings()["esphomeKey"] == god
        assert "esphomeKey" in d.SHARED_SETTINGS
    finally:
        d.state["settings"] = old


def test_airplay_volum_speiles_uten_sloyfe():
    """Skjold-volum → AirPlay-dB → tilbake via pvol-formelen i oled_display gir samme volum (telefonen hopper ikke)."""
    for v in range(1, 101):
        av = d.airplay_db(v)
        assert -30 <= av <= 0
        assert round(100 * (av + 30) / 30) == v
    assert d.airplay_db(0) == -144.0


def test_kassetter_er_felles_for_systemet(tmp_path):
    """Koble ny kassett fra Touch mens kassettspilleren er koblet til S1: S1 lærer brikken, sender kassetten til Touch,
    og Touch avslutter ventingen (som om spilleren var koblet dit)."""
    import asyncio
    import json as _j
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    import skjold_nfc as N

    sendt = []

    def fanget(metode, sti, body=None):
        sendt.append((metode, sti, body))
    gammel_til, gammel_nfc = d._nfc_til_andre, d.nfc
    d._nfc_til_andre = fanget
    d.nfc = N.NfcStore(str(tmp_path / "kort.json"))

    async def main():
        app = web.Application()
        app.router.add_route("*", "/api/nfc/{act}", d.h_nfc)
        app.router.add_route("DELETE", "/api/nfc/{act}/{uid}", d.h_nfc)
        async with TestClient(TestServer(app)) as c:
            kort = {"handling": "play_url", "verdi": "http://x/stream", "navn": "P3"}
            # Touch: start læring – sendes videre til de andre enhetene
            await c.post("/api/nfc/learn", json={"timeout": 60, "kort": kort})
            assert d.nfc.learning() and sendt[-1][1] == "/api/nfc/learn" and sendt[-1][2]["kort"]["navn"] == "P3"
            # S1 har lært brikken og sender kassetten hit med _laert
            r = await c.post("/api/nfc/cards", json={**kort, "uid": "04-A9-F2", "_laert": True}, headers={"X-Skjold-Peer": "s1"})
            assert r.status == 200
            assert not d.nfc.learning() and d.nfc.last["known"] and d.nfc.last["uid"] == d.nfc.get("04-A9-F2")["uid"]
            n = len(sendt)
            # endring fra en annen enhet sendes ikke videre (ingen sløyfe) …
            await c.post("/api/nfc/cards", json={**kort, "uid": "04-A9-F2", "navn": "P3 ny"}, headers={"X-Skjold-Peer": "s1"})
            assert len(sendt) == n
            # … men endringer gjort her gjør det, også sletting
            await c.post("/api/nfc/cards", json={**kort, "uid": "04-A9-F2", "navn": "P3 igjen"})
            await c.delete("/api/nfc/cards/04-A9-F2")
            assert [m for m, _s, _b in sendt[n:]] == ["POST", "DELETE"]
    try:
        asyncio.run(main())
    finally:
        d._nfc_til_andre, d.nfc = gammel_til, gammel_nfc


def test_kassett_med_en_laat_eller_hel_artist_fra_navidrome():
    """Biblioteket i Kassett-siden: én låt (getSong) eller hele artisten (alle album, eldste først)."""
    import skjold_nfc as N
    seen = []

    def opener(url):
        m = url.split("/rest/")[1].split(".view")[0]
        seen.append(m)
        if m == "getSong":
            return {"subsonic-response": {"status": "ok", "song": {"id": "s1", "title": "Substitute", "artist": "Gloria Gaynor", "album": "I Will Survive"}}}
        if m == "getArtist":
            return {"subsonic-response": {"status": "ok", "artist": {"album": [{"id": "b", "name": "B", "year": 1980}, {"id": "a", "name": "A", "year": 1975}]}}}
        if m == "getAlbum":
            aid = url.split("id=")[1].split("&")[0]
            return {"subsonic-response": {"status": "ok", "album": {"name": aid, "song": [{"id": aid + "1", "title": aid + "-1"}, {"id": aid + "2", "title": aid + "-2"}]}}}
        raise AssertionError(m)
    t = N.subsonic_tracks("http://nd", "u", "p", "song", "s1", opener)
    assert [x["title"] for x in t] == ["Substitute"] and "id=s1" in t[0]["url"]
    t = N.subsonic_tracks("http://nd", "u", "p", "artist", "ar1", opener)
    assert [x["title"] for x in t] == ["a-1", "a-2", "b-1", "b-2"]
    for h, typ in (("navidrome_song", "nd_song"), ("navidrome_artist", "nd_artist")):
        kort = N.clean_card({"uid": "04A9F2", "navn": "x", "handling": h, "verdi": "id1"})
        assert kort["handling"] == h and N.steps_for(kort)[-1] == {"type": typ, "verdi": "id1"}
        assert N.kilde_for(kort) == "Navidrome"
