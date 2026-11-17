"""YouTube Music innebygd (skjold_ytm): mapping fra ytmusicapi, strøm-URL-cache, kassetter og HTTP-rutene."""
import asyncio
import os
import sys
import tempfile
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
    y = Y.Ytm(lambda: {"ytmCookie": cookie, "ytmUser": ""}, cache_dir=tempfile.mkdtemp(prefix="ytm-"), make_client=lambda c, u: fake, extract=extract or ex)
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


def test_forsiden_lagres_og_vises_straks():
    y, fake, _n = mk()
    h = y.home()
    # ny Ytm med samme mappe (som etter en omstart): forsiden kommer fra disk uten å spørre YouTube
    y2 = Y.Ytm(lambda: {"ytmCookie": "SAPISID=abc; HSID=x", "ytmUser": ""}, cache_dir=y._dir,
               make_client=lambda c, u: (_ for _ in ()).throw(AssertionError("skal ikke spørre YouTube")))
    assert y2.home() == h
    # gammel kopi: vises straks, ny hentes i bakgrunnen
    y._home = (time.time() - 3600, h)
    started = []
    y.refresh_home_bg = lambda: started.append(1)
    assert y.home() is h and started == [1]


def test_spor_caches():
    y, fake, _n = mk()
    a = y.tracks("al:MPREb_a1")
    y.client = lambda: (_ for _ in ()).throw(AssertionError("skal komme fra minnet"))
    assert y.tracks("al:MPREb_a1") == a


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


def test_ett_oppslag_om_gangen_per_lat():
    """Forhåndshenting, strømmen og strømtesten samtidig: yt-dlp skal bare kjøre én gang (Pi-en ble for treg)."""
    import threading
    calls = {"n": 0}

    def slow(vid):
        calls["n"] += 1
        time.sleep(0.3)
        return {"url": f"https://x/videoplayback?expire={int(time.time()) + 7200}", "http_headers": {}}
    y, _f, _n = mk(extract=slow)
    ts = [threading.Thread(target=y.stream_url, args=("aaaaaaaaaaa",)) for _ in range(3)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert calls["n"] == 1


def test_strommen_hentes_i_biter_og_tar_imot_range():
    """YouTube kutter lange forespørsler: Skjold henter 1 MB om gangen og fornyer en utløpt adresse underveis."""
    from aiohttp import web, ClientSession
    data = bytes(i % 251 for i in range(int(2.5 * (1 << 20))))
    seen = {"ranges": [], "expired_once": False}

    async def upstream(r):
        if r.query.get("v") == "1" and len(seen["ranges"]) >= 1 and not seen["expired_once"]:
            seen["expired_once"] = True
            return web.Response(status=403)
        a, b = Y.re.match(r"bytes=(\d+)-(\d+)", r.headers["Range"]).groups()
        a, b = int(a), min(int(b), len(data) - 1)
        seen["ranges"].append((a, b))
        return web.Response(status=206, body=data[a:b + 1], content_type="audio/mp4",
                            headers={"Content-Range": f"bytes {a}-{b}/{len(data)}"})

    async def main():
        up_app = web.Application(); up_app.router.add_get("/vp", upstream)
        r1 = web.AppRunner(up_app); await r1.setup(); s1 = web.TCPSite(r1, "127.0.0.1", 0); await s1.start()
        port = s1._server.sockets[0].getsockname()[1]
        n = {"v": 0}

        def ex(vid):
            n["v"] += 1
            return {"url": f"http://127.0.0.1:{port}/vp?v={n['v']}&expire={int(time.time()) + 7200}", "http_headers": {}}
        y, _f, _n = mk(extract=ex)
        app = web.Application(); app.add_routes(Y.routes(y, {"stream_base": lambda: "", "play": lambda ts, i: None}))
        r2 = web.AppRunner(app); await r2.setup(); s2 = web.TCPSite(r2, "127.0.0.1", 0); await s2.start()
        p2 = s2._server.sockets[0].getsockname()[1]
        async with ClientSession() as c:
            async with c.get(f"http://127.0.0.1:{p2}/api/ytm/stream/aaaaaaaaaaa.m4a") as resp:
                body = await resp.read()
                full = (resp.status, int(resp.headers["Content-Length"]), body)
            async with c.get(f"http://127.0.0.1:{p2}/api/ytm/stream/aaaaaaaaaaa.m4a", headers={"Range": "bytes=100-199"}) as resp:
                part = (resp.status, resp.headers.get("Content-Range"), await resp.read())
        await r2.cleanup(); await r1.cleanup()
        return full, part
    full, part = asyncio.run(main())
    assert full[0] == 200 and full[1] == len(data) and full[2] == data
    assert seen["expired_once"] and len(seen["ranges"]) >= 3
    assert all(b - a + 1 <= (1 << 20) for a, b in seen["ranges"])
    assert part[0] == 206 and part[1] == f"bytes 100-199/{len(data)}" and part[2] == data[100:200]
