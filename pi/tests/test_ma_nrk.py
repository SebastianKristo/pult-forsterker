"""Music Assistant (mock-WebSocket) og NRK (parsing, fremdrift, avspilling) – uten nett."""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_ma as ma  # noqa: E402
import skjold_nrk as nrk  # noqa: E402


# ---------- Music Assistant ----------

class FakeWS:
    """Svarer som MA: server_info først, så ett svar per kommando (eventuelt i partial-biter)."""

    def __init__(self, handlers, log):
        self.handlers, self.log, self.out = handlers, log, [json.dumps({"server_version": "2.5.0", "schema_version": 27})]

    def send(self, raw):
        m = json.loads(raw)
        self.log.append((m["command"], m["args"]))
        res = self.handlers.get(m["command"], lambda a: None)(m["args"])
        if isinstance(res, tuple) and res[0] == "partial":
            self.out.append(json.dumps({"message_id": m["message_id"], "result": res[1], "partial": True}))
            self.out.append(json.dumps({"event": "player_updated"}))          # støy skal ignoreres
            self.out.append(json.dumps({"message_id": m["message_id"], "result": res[2]}))
        elif isinstance(res, Exception):
            self.out.append(json.dumps({"message_id": m["message_id"], "error_code": 999, "details": str(res)}))
        else:
            self.out.append(json.dumps({"message_id": m["message_id"], "result": res}))

    def recv(self):
        return self.out.pop(0)

    def close(self):
        pass


PLAYERS = [
    {"player_id": "ap_aabbcc", "display_name": "Kjøkken", "available": True},
    {"player_id": "dc:a6:32:11:22:33", "display_name": "Stue (Squeezelite)", "available": True},
    {"player_id": "upnp_x", "display_name": "Skjold S1", "available": True},
]

TRACK = {"media_type": "track", "uri": "tidal://track/1", "item_id": "1", "name": "Midnight City", "duration": 244,
         "artists": [{"name": "M83"}], "album": {"name": "Hurry Up", "metadata": {"images": [{"type": "thumb", "path": "https://img/a.jpg", "remotely_accessible": True}]}},
         "provider_mappings": [{"provider_domain": "tidal", "item_id": "1"}]}


def make(handlers, log):
    m = ma.MA(lambda: ("192.168.1.5", "tok"), lambda: "Skjold S1", lambda: "dc:a6:32:11:22:33",
              connect=lambda url, t: FakeWS(handlers, log))
    return m


def test_base_url_variants():
    assert ma.base_url("192.168.1.5") == ("ws://192.168.1.5:8095/ws", "http://192.168.1.5:8095")
    assert ma.base_url("http://ma.local:8095/") == ("ws://ma.local:8095/ws", "http://ma.local:8095")
    assert ma.base_url("ws://ma:9000/ws")[0] == "ws://ma:9000/ws"


def test_find_player_prefers_mac_then_name():
    assert ma.find_player(PLAYERS, "Skjold S1", "dc:a6:32:11:22:33")["player_id"] == "dc:a6:32:11:22:33"
    assert ma.find_player(PLAYERS, "Skjold S1", "")["player_id"] == "upnp_x"
    assert ma.find_player(PLAYERS, "Ukjent", "") is None


def test_search_normalises_and_sends_auth():
    log = []
    m = make({"auth": lambda a: {"ok": True}, "music/search": lambda a: {"tracks": [TRACK], "albums": []}}, log)
    r = m.search("midnight")
    assert log[0] == ("auth", {"token": "tok"})
    assert log[1][0] == "music/search" and log[1][1]["search_query"] == "midnight"
    t = r["tracks"][0]
    assert (t["name"], t["artist"], t["album"], t["provider"], t["image"]) == ("Midnight City", "M83", "Hurry Up", "TIDAL", "https://img/a.jpg")


def test_partial_results_are_joined():
    log = []
    m = make({"music/albums/library_items": lambda a: ("partial", [{"name": "A", "media_type": "album"}], [{"name": "B", "media_type": "album"}])}, log)
    assert [x["name"] for x in m.library("albums")] == ["A", "B"]


def test_play_uses_matching_player_and_option():
    log = []
    m = make({"players/all": lambda a: PLAYERS, "player_queues/play_media": lambda a: None}, log)
    r = m.play("tidal://track/1", "next")
    call = [c for c in log if c[0] == "player_queues/play_media"][0][1]
    assert r["player_id"] == "dc:a6:32:11:22:33"
    assert call == {"queue_id": "dc:a6:32:11:22:33", "media": ["tidal://track/1"], "option": "next"}


def test_play_without_player_gives_clear_error():
    m = make({"players/all": lambda a: []}, [])
    with pytest.raises(ma.MAError, match="fant ikke"):
        m.play("x://1")


def test_error_from_ma_is_raised():
    m = make({"music/search": lambda a: RuntimeError("bad token")}, [])
    with pytest.raises(ma.MAError, match="bad token"):
        m.search("x")


# ---------- NRK ----------

SEARCH = {"results": {"series": {"results": [
    {"type": "podcast", "seriesId": "abels_taarn", "title": "Abels tårn", "images": [{"uri": "https://gfx/a300.jpg", "width": 300}, {"uri": "https://gfx/a960.jpg", "width": 960}]},
    {"type": "series", "seriesId": "nitimen", "title": "Nitimen", "image": [{"url": "https://gfx/n.jpg", "width": 600}]}]},
    "episodes": {"results": [{"episodeId": "l_123", "titles": {"title": "Om stjerner", "subtitle": "Del 1"}, "durationInSeconds": 1800, "date": "2026-11-01T08:00:00Z"}]}}}

EPISODES = {"_embedded": {"episodes": [
    {"episodeId": "l_1", "titles": {"title": "Ep 1"}, "duration": {"iso8601": "PT1H2M3S"}},
    {"prfId": "MSPO123", "titles": {"title": "Ep 2"}, "duration": "PT30M"}]}}

MANIFEST = {"playable": {"assets": [{"url": "https://hls/x.m3u8", "format": "HLS"}, {"url": "https://cdn/x.mp3", "format": "MP3"}]}}


def test_parse_search_series_and_episodes():
    s = nrk.parse_series(SEARCH)
    assert [(x["id"], x["kind"]) for x in s] == [("abels_taarn", "podcast"), ("nitimen", "series")]
    assert s[0]["image"] == "https://gfx/a300.jpg"
    e = nrk.parse_episodes(SEARCH)
    assert e[0]["id"] == "l_123" and e[0]["duration"] == 1800 and e[0]["date"] == "2026-11-01"


def test_parse_episodes_durations_and_manifest():
    e = nrk.parse_episodes(EPISODES, "Serie", "https://img")
    assert [x["duration"] for x in e] == [3723, 1800]
    assert e[0]["image"] == "https://img" and e[0]["series"] == "Serie"
    assert nrk.parse_manifest(MANIFEST) == "https://cdn/x.mp3"
    with pytest.raises(nrk.NRKError):
        nrk.parse_manifest({"playable": None})


def test_progress_resume_and_heard(tmp_path):
    p = nrk.Progress(str(tmp_path / "p.json"))
    p.update("e1", 600, 1800, {"title": "T"})
    assert p.resume_at("e1") == 595
    p.update("e2", 10, 1800)
    assert p.resume_at("e2") == 0                       # for tidlig til å fortsette
    p.update("e3", 1750, 1800)
    assert p.get("e3")["heard"] and p.resume_at("e3") == 0
    assert [x["id"] for x in p.continue_list()] == ["e1"]
    assert nrk.Progress(str(tmp_path / "p.json")).resume_at("e1") == 595   # lagret på disk


def test_play_resumes_with_lyrion_seek(tmp_path, monkeypatch):
    calls, played = [], []
    fetch = lambda url: MANIFEST if "/playback/manifest/podcast/" in url else None
    ctx = {"play_url": lambda *a: played.append(a), "lyr_cmd": calls.append, "lyr_info": lambda: {"mode": "play"},
           "data_dir": str(tmp_path), "fetch": fetch}
    monkeypatch.setattr(nrk.time, "sleep", lambda s: None)
    routes = nrk.routes(ctx)
    n = ctx["nrk"]
    n.progress.update("l_1", 600, 1800)
    handler = [r for r in routes if r.path == "/api/nrk/play"][0].handler

    class Req:
        async def json(self):
            return {"id": "l_1", "title": "Ep 1", "series": "Abels tårn", "duration": 1800, "podcast": True}

    import asyncio
    res = asyncio.run(handler(Req()))
    body = json.loads(res.body)
    assert res.status == 200 and body["resume"] == 595
    assert played[0][0] == "https://cdn/x.mp3" and played[0][1] == "Abels tårn"
    for _ in range(50):
        if calls:
            break
        time.sleep(0.01)
    assert calls == [["time", 595]]
