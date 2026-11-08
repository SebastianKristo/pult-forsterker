"""YouTube Music innebygd (skjold_ytm): mapping fra ytmusicapi, strøm-URL-cache, kassetter og HTTP-rutene."""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_nfc as nfc  # noqa: E402
import skjold_ytm as Y  # noqa: E402

TH = {"thumbnails": [{"url": "https://lh3.googleusercontent.com/a=w60-h60"}, {"url": "https://lh3.googleusercontent.com/a=w120-h120"}]}


class FakeYT:
    def __init__(self):
        self.calls = []

    def get_library_playlists(self, limit=25):
        return [{"playlistId": "LM", "title": "Liked Music"}, {"playlistId": "PL1", "title": "Kjøkken", "count": "12", **TH}]

    def get_library_albums(self, limit=25, order=None):
        return [{"browseId": "MPREb_a1", "title": "Hounds of Love", "artists": [{"name": "Kate Bush"}], "year": "1985", **TH}]

    def get_home(self, limit=3):
        return [{"title": "Mixed for you", "contents": [{"playlistId": "RDMix", "title": "My Supermix", "description": "x", **TH},
                                                         {"browseId": "MPREb_b2", "title": "Blue", "artists": [{"name": "Joni Mitchell"}], **TH}]}]

    def get_album(self, bid):
        return {"title": "Hounds of Love", **TH, "tracks": [
            {"videoId": "aaaaaaaaaaa", "title": "Running Up That Hill", "artists": [{"name": "Kate Bush"}], "duration": "5:03"},
            {"videoId": None, "title": "utilgjengelig"}]}

    def get_playlist(self, pid, limit=100):
        return {"tracks": [{"videoId": "bbbbbbbbbbb", "title": "Song", "artists": [{"name": "A"}, {"name": "B"}],
                            "album": {"name": "Alb"}, "duration_seconds": 61, **TH}]}

    def get_liked_songs(self, limit=100):
        return {"tracks": [{"videoId": "ccccccccccc", "title": "Likt", "artists": [{"name": "C"}], "duration": "1:00:01"}]}

    def search(self, q, filter=None, limit=20):
        self.calls.append((q, filter))
        if filter == "songs":
            return [{"videoId": "ddddddddddd", "title": q, "artists": [{"name": "D"}], "duration": "3:00"}]
        if filter == "albums":
            return [{"browseId": "MPREb_x", "title": "Hounds of Love", "artists": [{"name": "Kate Bush"}], **TH},
                    {"browseId": "MPREb_y", "title": "Other", "artists": [{"name": "Kate Bush"}]}]
        return [{"browseId": "VLPLz", "title": "Liste", "author": [{"name": "Noen"}]}]


def mk(cookie="SAPISID=abc; HSID=x", extract=None):
    fake = FakeYT()
    n = {"x": 0}

    def ex(vid):
        n["x"] += 1
        return {"url": f"https://rr1.googlevideo.com/videoplayback?id={vid}&expire={int(time.time()) + 7200}&n={n['x']}",
                "http_headers": {"User-Agent": "UA", "Accept": "x"}}
    y = Y.Ytm(lambda: {"ytmCookie": cookie, "ytmUser": ""}, make_client=lambda c, u: fake, extract=extract or ex)
    return y, fake, n


def test_hjem_mapping():
    y, _f, _n = mk()
    h = y.home()
    ids = [c["id"] for c in h["playlists"]]
    assert ids[0] == "pl:LM" and "pl:PL1" in ids and ids.count("pl:LM") == 1
    pl1 = next(c for c in h["playlists"] if c["id"] == "pl:PL1")
    assert pl1["count"] == 12 and pl1["playlist"] and pl1["cover"].endswith("=w544-h544")
    assert h["newest"][0] == {"id": "al:MPREb_a1", "name": "Hounds of Love", "artist": "Kate Bush",
                              "cover": "https://lh3.googleusercontent.com/a=w544-h544", "count": 0, "playlist": False}
    assert [c["id"] for c in h["other"]] == ["al:MPREb_b2"] and [c["id"] for c in h["frequent"]] == ["pl:RDMix"]
    assert y.home() is h   # cache


def test_uten_innlogging_bare_forsiden():
    y, _f, _n = mk(cookie="")
    h = y.home()
    assert not y.signed_in() and h["playlists"] == [] and h["newest"] == [] and h["other"]


def test_spor_album_spilleliste_likte():
    y, _f, _n = mk()
    a = y.tracks("al:MPREb_a1")
    assert a == [{"id": "aaaaaaaaaaa", "title": "Running Up That Hill", "artist": "Kate Bush", "album": "Hounds of Love",
                  "dur": 303, "cover": "https://lh3.googleusercontent.com/a=w544-h544"}]
    p = y.tracks("pl:PL1")[0]
    assert p["artist"] == "A, B" and p["album"] == "Alb" and p["dur"] == 61
    assert y.tracks("pl:LM")[0]["dur"] == 3601
    try:
        y.tracks("xx:1"); assert False
    except ValueError:
        pass


def test_sok():
    y, _f, _n = mk()
    r = y.search("hei")
    assert r["tracks"][0]["id"] == "ddddddddddd" and r["albums"][0]["id"] == "al:MPREb_x" and r["playlists"][0]["id"] == "pl:PLz"


def test_strom_url_caches_og_fornyes():
    y, _f, n = mk()
    u1, h = y.stream_url("aaaaaaaaaaa")
    u2, _ = y.stream_url("aaaaaaaaaaa")
    assert u1 == u2 and n["x"] == 1 and h == {"User-Agent": "UA"}
    y._urls["aaaaaaaaaaa"] = (u1, time.time() - 1, h)   # utløpt
    assert y.stream_url("aaaaaaaaaaa")[0] != u1 and n["x"] == 2
    try:
        y.stream_url("../../etc"); assert False
    except ValueError:
        pass


def test_cookiefil(tmp_path):
    p = Y.cookie_jar("SAPISID=abc; __Secure-3PAPISID=d=e; tom", str(tmp_path / "c.txt"))
    lines = open(p).read().splitlines()
    assert lines[0].startswith("# Netscape") and len(lines) == 3 and lines[2].endswith("\t__Secure-3PAPISID\td=e")


def test_kassett_finner_album_uten_music_assistant():
    y, _f, _n = mk()
    lo = nfc.resolve_album("Kate Bush", "Hounds of Love", nd_search=lambda q: [], ma_search=None, ytm_find=y.find_album)
    assert lo["kilde"] == "ytmusic" and lo["ytm_id"] == "al:MPREb_x"
    card = {"handling": "album", "verdi": {"artist": "Kate Bush", "album": "Hounds of Love"}, "losning": lo}
    assert nfc.steps_for(card) == [{"type": "ytm", "verdi": "al:MPREb_x"}]
    # Navidrome vinner fortsatt hvis du har albumet
    nd = nfc.resolve_album("Kate Bush", "Hounds of Love", nd_search=lambda q: [{"id": 7, "name": "Hounds of Love", "artist": "Kate Bush"}],
                           ytm_find=y.find_album)
    assert nd["kilde"] == "navidrome"


def test_ruter():
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
    y, _f, _n = mk(extract=lambda vid: {"url": "http://127.0.0.1:1/ingen", "http_headers": {}})
    played = []
    app = web.Application()
    app.add_routes(Y.routes(y, {"stream_base": lambda: "http://10.0.0.5:8765", "play": lambda ts, i: played.append((ts, i))}))

    async def go():
        async with TestClient(TestServer(app)) as c:
            st = await (await c.get("/api/ytm/status")).json()
            assert st["signed_in"] and st["available"]
            h = await (await c.get("/api/ytm/home")).json()
            assert h["playlists"][0]["id"] == "pl:LM"
            t = await (await c.get("/api/ytm/tracks", params={"id": "al:MPREb_a1"})).json()
            assert t["tracks"][0]["stream"] == "http://10.0.0.5:8765/api/ytm/stream/aaaaaaaaaaa.m4a"
            assert (await c.get("/api/ytm/tracks", params={"id": "zz"})).status == 400
            s = await (await c.get("/api/ytm/search", params={"q": "x"})).json()
            assert s["tracks"][0]["stream"].endswith("/ddddddddddd.m4a")
            r = await c.post("/api/ytm/play", json={"id": "pl:PL1", "index": 0})
            assert (await r.json())["count"] == 1 and played[0][0][0]["stream"].endswith("/bbbbbbbbbbb.m4a")
            assert (await c.get("/api/ytm/stream/kort")).status == 400
            assert (await c.get("/api/ytm/stream/aaaaaaaaaaa.m4a")).status == 502   # upstream nås ikke
    asyncio.run(go())
