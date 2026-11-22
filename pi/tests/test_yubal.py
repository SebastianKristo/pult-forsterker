"""yubal: Skjold finner lenken selv, sender den til yubal, følger jobben og ber Navidrome skanne når den er ferdig."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_yubal as Y  # noqa: E402


class FalskYT:
    def __init__(self, treff=True):
        self.treff = treff

    def search(self, q, filter=None, limit=5):
        assert filter == "songs"
        return [{"videoId": "abcdefghijk", "title": "Septembermorgen", "artists": [{"name": "Kari Bremnes"}],
                 "album": {"name": "Svarta Bjørn", "id": "MPREb_x"}, "thumbnails": [{"url": "https://lh3/a"}]}] if self.treff else []

    def get_album(self, bid):
        assert bid == "MPREb_x"
        return {"title": "Svarta Bjørn", "audioPlaylistId": "OLAK5uy_abc"}


class FalskNd:
    def __init__(self):
        self.kall = []

    def _call(self, m, **k):
        self.kall.append(m)
        return {}


def lag(innst=None, treff=True):
    s = {"yubalUrl": "192.168.1.20", **(innst or {})}
    sendt, jobber, nd = [], {}, FalskNd()

    def http(url, data=None, timeout=10):
        sendt.append((url, data))
        if url.endswith("/api/health"):
            return {"status": "healthy"}
        if url.endswith("/api/jobs") and data is not None:
            jobber["j1"] = {"id": "j1", "status": "downloading", "progress": 0.4}
            return {"id": "j1", "message": "Job created"}
        if url.endswith("/api/jobs"):
            return {"jobs": list(jobber.values())}
        raise AssertionError(url)
    return Y.Yubal(lambda: s, lambda: nd, http=http, ytm_client=FalskYT(treff)), sendt, jobber, nd


def test_adresse_og_status():
    y, sendt, _j, _n = lag()
    assert y.base() == "http://192.168.1.20:8000"
    st = y.status()
    assert st["ok"] and st["konfigurert"] and st["auto"] and not st["album"]
    assert sendt[-1][0] == "http://192.168.1.20:8000/api/health"


def test_ikke_satt_opp():
    y, _s, _j, _n = lag({"yubalUrl": ""})
    assert y.status() == {"konfigurert": False, "ok": False, "feil": "", "auto": True, "album": False}
    with pytest.raises(RuntimeError):
        y.hent("noe")


def test_laater_lenke_og_jobb():
    y, sendt, jobber, nd = lag()
    r = y.hent("septembermorgen kari bremnes")
    assert r["url"] == "https://music.youtube.com/watch?v=abcdefghijk" and r["artist"] == "Kari Bremnes" and r["id"] == "j1"
    assert sendt[-1] == ("http://192.168.1.20:8000/api/jobs", {"url": "https://music.youtube.com/watch?v=abcdefghijk"})
    j = y.jobber()
    assert j[0]["status"] == "downloading" and j[0]["fremdrift"] == 40 and j[0]["tittel"] == "Septembermorgen"
    assert nd.kall == []
    jobber["j1"].update(status="completed", progress=1.0)
    assert y.jobber()[0]["fremdrift"] == 100 and nd.kall == ["startScan"]
    y.jobber()
    assert nd.kall == ["startScan"]   # bare én skanning per jobb


def test_hele_albumet():
    y, sendt, _j, _n = lag({"yubalAlbum": True})
    r = y.hent("septembermorgen")
    assert r["url"] == "https://music.youtube.com/playlist?list=OLAK5uy_abc" and r["tittel"] == "Svarta Bjørn"


def test_fant_ikke():
    y, _s, _j, _n = lag(treff=False)
    with pytest.raises(LookupError):
        y.hent("finnes ikke")


class FalskYT2:
    def search(self, q, filter=None, limit=8):
        return [{"videoId": "aaaaaaaaaaa", "title": "Hallelujah", "artists": [{"name": "Lordi"}], "album": {"name": "Hard Rock Hallelujah", "id": "A1"}},
                {"videoId": "bbbbbbbbbbb", "title": "Hallelujah", "artists": [{"name": "Leonard Cohen"}], "album": {"name": "Various Positions", "id": "A2"}},
                {"videoId": "ccccccccccc", "title": "Hallelujah (Live)", "artists": [{"name": "Jeff Buckley"}], "album": {"name": "Live", "id": "A3"}}]


def test_kandidater_bare_sikker_naar_artist_og_tittel_stemmer():
    y = Y.Yubal(lambda: {"yubalUrl": "x"}, lambda: None, http=lambda *a, **k: {}, ytm_client=FalskYT2())
    r = y.kandidater("hallelujah")
    assert r["sikker"] is None and len(r["kandidater"]) == 3   # bare tittelen: du må velge
    r = y.kandidater("hallelujah leonard cohen")
    assert r["sikker"]["vid"] == "bbbbbbbbbbb" and r["kandidater"][0]["vid"] == "bbbbbbbbbbb"
    r = y.kandidater("jeff buckley hallelujah")
    assert r["sikker"]["artist"] == "Jeff Buckley"   # «(Live)» teller ikke mot


def test_hent_valgt_laat():
    sendt = []
    y = Y.Yubal(lambda: {"yubalUrl": "x"}, lambda: None, http=lambda u, d=None, timeout=10: sendt.append((u, d)) or {"id": "j9"}, ytm_client=FalskYT2())
    r = y.hent(valgt={"vid": "bbbbbbbbbbb", "tittel": "Hallelujah", "artist": "Leonard Cohen"})
    assert r["id"] == "j9" and sendt[-1][1] == {"url": "https://music.youtube.com/watch?v=bbbbbbbbbbb"} and r["artist"] == "Leonard Cohen"


def test_hent_album_fra_navn():
    import skjold_yubal as sy

    class YT:
        def search(self, q, filter=None, limit=8):
            assert filter == "albums"
            return [{"browseId": "MPREb_feil", "title": "Annet", "artists": [{"name": "X"}]},
                    {"browseId": "MPREb_riktig", "title": "Noen ganger er det all right", "artists": [{"name": "Odd Børretzen"}]}]

        def get_album(self, bid):
            assert bid == "MPREb_riktig"
            return {"title": "Noen ganger er det all right", "audioPlaylistId": "OLAK5uy_abc", "artists": [{"name": "Odd Børretzen"}], "thumbnails": [{"url": "b"}]}

    sendt = []
    yb = sy.Yubal(lambda: {"yubalUrl": "nas"}, None, http=lambda u, d=None, timeout=10: (sendt.append(d), {"id": "j1"})[1], ytm_client=YT())
    r = yb.hent_album(album="Noen ganger er det all right", artist="Odd Børretzen")
    assert sendt[0] == {"url": "https://music.youtube.com/playlist?list=OLAK5uy_abc"} and r["id"] == "j1" and r["artist"] == "Odd Børretzen"
    r = yb.hent_album(album_id="al:OLAK5uy_xyz")
    assert sendt[1] == {"url": "https://music.youtube.com/playlist?list=OLAK5uy_xyz"}
