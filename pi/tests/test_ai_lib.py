"""Tester for lydbeskrivelse av biblioteket, «Spill noe til …» og podkastsammendrag.

Kjør:  python3 -m pytest -q pi/tests/test_ai_lib.py
"""
import json
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import skjold_libtag as lt  # noqa: E402
import skjold_ask as ask  # noqa: E402
import skjold_podsum as ps  # noqa: E402

SR = lt.SR
rng = np.random.default_rng(1)


def chord(freqs, secs=8, amp=0.3):
    t = np.arange(int(SR * secs)) / SR
    return (amp * sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)).astype(np.float32)


def clicks(bpm=120, secs=8):
    x = np.zeros(int(SR * secs), np.float32)
    step = int(SR * 60 / bpm)
    for i in range(0, len(x) - 400, step):
        x[i:i + 400] += rng.normal(0, 0.8, 400).astype(np.float32) * np.exp(-np.arange(400) / 60)
    return x


# ---------------------------------------------------------------- libtag

def test_describe_fields_and_ordering():
    soft = chord([261.6, 329.6, 392.0], amp=0.05)              # C-dur, svakt
    loud_noise = (rng.normal(0, 0.5, SR * 8)).astype(np.float32)
    a, b = lt.describe(soft, SR), lt.describe(loud_noise, SR)
    for k in ("bpm", "energy", "valence", "arousal", "acoustic", "instrumental", "mood"):
        assert k in a
    assert a["mood"] in lt.MOODS and b["mood"] in lt.MOODS
    assert b["energy"] > a["energy"]
    assert b["flatness"] > a["flatness"]
    assert a["acoustic"] and not b["acoustic"]
    assert a["instrumental"]


def test_describe_tempo_of_clicks():
    d = lt.describe(clicks(120), SR)
    assert 100 <= d["bpm"] <= 130 or 50 <= d["bpm"] <= 65 or 230 <= d["bpm"] <= 250


def test_mood_of():
    assert lt.mood_of(0.8, 0.8) in ("glad", "energisk")
    assert lt.mood_of(0.2, 0.2, 0.3) in ("trist", "mørk", "rolig")
    assert lt.mood_of(0.7, 0.2) in ("rolig", "drømmende")


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as d:
        s = lt.Store(os.path.join(d, "t.db"))
        base = {"bpm": 100, "energy": 0.2, "brightness": 0.3, "dynamics": 0.5, "flatness": 0.1, "perc": 0.1, "vocal": 0.1,
                "major": True, "valence": 0.6, "arousal": 0.2, "acoustic": True, "instrumental": True, "mood": "rolig"}
        s.put({"id": "1", "title": "Rolig", "artist": "A", "genre": "Jazz", "year": 1984}, base)
        s.put({"id": "2", "title": "Fest", "artist": "B", "genre": "Pop", "year": 2005},
              dict(base, bpm=128, energy=0.9, mood="energisk", acoustic=False, instrumental=False))
        s.put({"id": "3", "title": "Feil"}, None, error="dekoding")
        yield s


def test_store_search(store):
    assert [r["id"] for r in store.search(mood="rolig")] == ["1"]
    assert [r["id"] for r in store.search(energy="høy")] == ["2"]
    assert [r["id"] for r in store.search(acoustic=True)] == ["1"]
    assert [r["id"] for r in store.search(bpm="120-130")] == ["2"]
    assert [r["id"] for r in store.search(decade=1980)] == ["1"]
    assert store.count() == (2, 1)


# ---------------------------------------------------------------- «Spill noe til …»

@pytest.mark.parametrize("text,check", [
    ("rolig jazz til middag", lambda q: "jazz" in q["genres"] and "rolig" in q["moods"] and q["energy"] == "lav"),
    ("energisk for trening", lambda q: q["moods"] == ["energisk"] and q["energy"] == "høy"),
    ("noe norsk fra 80-tallet", lambda q: q["decade"] == 1980 and q["language"] == "norsk"),
    ("something like Radiohead from the 90s", lambda q: q["decade"] == 1990 and q["artists_like"] == ["Radiohead"]),
    ("30 minutter klassisk", lambda q: q["duration_min"] == 30 and q["genres"] == ["classical"]),
])
def test_rules(text, check):
    assert check(ask.parse_rules(text))


def test_clean_normalises_bad_llm_output():
    q = ask.clean('Her er svaret: {"genres": "Jazz", "moods": ["rolig", "sint"], "energy": "low", "decade": 85, "x": 1}')
    assert q["genres"] == ["jazz"] and q["moods"] == ["rolig"] and q["energy"] == "lav" and q["decade"] == 1980
    assert "x" not in q
    assert ask.clean("ikke json")["genres"] == []


def _llm(tmp, provider, resp):
    calls = []

    def post(url, body, headers, timeout=30):
        calls.append((url, body, headers))
        return resp
    llm = ask.LLM(os.path.join(tmp, "ai.json"), post=post)
    llm.set({"provider": provider, "anthropicKey": "sk-test-1234", "ollamaUrl": "http://ollama.test:11434"})
    return llm, calls


def test_anthropic_tool_use(tmp_path):
    llm, calls = _llm(str(tmp_path), "anthropic", {"content": [
        {"type": "tool_use", "name": "musikksok", "input": {"genres": ["jazz"], "moods": ["rolig"], "energy": "lav"}}]})
    q, how = ask.interpret("rolig jazz", llm)
    assert how == "llm" and q["genres"] == ["jazz"]
    url, body, headers = calls[0]
    assert url.endswith("/v1/messages") and headers["x-api-key"] == "sk-test-1234"
    assert body["tool_choice"] == {"type": "tool", "name": "musikksok"}
    assert llm.public()["anthropicKey"].endswith("1234") and "sk-" not in llm.public()["anthropicKey"]


def test_ollama_json_and_fallback(tmp_path):
    llm, _ = _llm(str(tmp_path), "ollama", {"message": {"content": '{"genres":["rock"],"moods":[],"energy":"high"}'}})
    q, how = ask.interpret("noe norsk rock fra 70-tallet", llm)
    assert how == "llm" and q["energy"] == "høy" and q["decade"] == 1970 and q["language"] == "norsk"   # tomme felt fra reglene

    def boom(*a, **k):
        raise OSError("nede")
    llm.post = boom
    q, how = ask.interpret("rolig jazz", llm)
    assert how == "regler" and q["genres"] == ["jazz"]


def test_resolve_prefers_tags_then_radio(store):
    class SR_:
        seed = None

        def start(self, seed):
            self.seed = seed
    played = []
    ctx = {"libtag": type("L", (), {"store": store})(), "subsonic": lambda: None, "smartradio": SR_(),
           "play_url": lambda *a: played.append(a), "rb_list": lambda p, n: [{"url": "http://r/x", "name": "Jazzradio"}]}
    r = ask.ask("rolig jazz", ctx)
    assert r["ok"] and r["source"] == "tags" and ctx["smartradio"].seed["id"] == "1"
    r = ask.ask("trist country", ctx)
    assert r["ok"] and r["source"] == "radio" and played[0][0] == "http://r/x"


# ---------------------------------------------------------------- podkastsammendrag

RSS = """<?xml version="1.0"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:podcast="https://podcastindex.org/namespace/1.0"><channel>
<title>Testpod</title>
<item><guid>e2</guid><title>Episode to</title><pubDate>Tue, 03 Nov 2026 06:00:00 GMT</pubDate>
<description>&lt;p&gt;Vi snakker om fjorder. Og mye mer.&lt;/p&gt;</description><enclosure url="http://x/e2.mp3" type="audio/mpeg"/>
<podcast:transcript url="http://x/e2.vtt" type="text/vtt"/></item>
<item><guid>e1</guid><title>Episode en</title><pubDate>Mon, 02 Nov 2026 06:00:00 GMT</pubDate>
<description>Første episode handler om fjell.</description><enclosure url="http://x/e1.mp3" type="audio/mpeg"/></item>
</channel></rss>""".encode()
VTT = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\nHei og velkommen.\n\n2\n00:00:03.000 --> 00:00:05.000\nI dag: fjorder.\n".encode()


def fake_fetch(url, timeout=20):
    return VTT if url.endswith(".vtt") else RSS


def test_parse_rss_and_transcript():
    f = ps.parse_rss(RSS)
    assert f["title"] == "Testpod" and [e["id"] for e in f["episodes"]] == ["e2", "e1"]
    assert f["episodes"][0]["transcript"] == "http://x/e2.vtt" and "<p>" not in f["episodes"][0]["desc"]
    assert ps.transcript_text("http://x/e2.vtt", fake_fetch) == "Hei og velkommen. I dag: fjorder."


def test_podsum_new_since_last_and_fallback(tmp_path):
    p = ps.PodSum({"data_dir": str(tmp_path)}, fetch=fake_fetch)
    p.set({"follow": [{"kind": "rss", "id": "http://x/feed"}]})
    first = p.build(mark=True)
    assert [i["title"] for i in first["items"]] == ["Episode to"]
    assert "Testpod: Episode to. Vi snakker om fjorder." in first["text"]
    assert p.build(mark=True)["items"] == []                       # ingenting nytt siden sist


def test_podsum_llm_uses_transcript(tmp_path):
    seen = {}

    class L:
        enabled = True

        def chat(self, system, user, **k):
            seen["user"] = user
            return "**Fjorder** forklart på ti minutter."
    out = ps.summarize([("Testpod", ps.parse_rss(RSS)["episodes"][0])], L(), fake_fetch)
    assert "I dag: fjorder" in seen["user"]
    assert out == ["Testpod: Fjorder forklart på ti minutter."]


def test_chunks_and_due():
    parts = ps.chunks("Setning. " * 120)
    assert all(len(c) <= 380 for c in parts) and len(parts) > 1
    import datetime as dt
    p = ps.PodSum({"data_dir": tempfile.mkdtemp()})
    p.cfg.update(enabled=True, follow=[{"kind": "rss", "id": "x"}], time="07:15", lastRun="")
    assert not p.due(dt.datetime(2026, 11, 6, 7, 0)) and p.due(dt.datetime(2026, 11, 6, 7, 20))


def test_ollama_needs_external_url(tmp_path):
    from skjold_ask import LLM, norm_ollama_url
    assert norm_ollama_url("") == ""
    assert norm_ollama_url("192.168.1.20") == "http://192.168.1.20:11434"
    assert norm_ollama_url("http://pc.local:8080/") == "http://pc.local:8080"
    assert norm_ollama_url("https://ollama.hjem") == "https://ollama.hjem:11434"
    llm = LLM(str(tmp_path / "ai.json"))
    llm.set({"provider": "ollama"})
    assert not llm.enabled                      # ingen lokal standard – må peke på en egen server
    llm.set({"ollamaUrl": "pc.local"})
    assert llm.enabled and llm.cfg["ollamaUrl"] == "http://pc.local:11434"


def test_ollama_test_lists_models(tmp_path):
    from skjold_ask import LLM
    seen = []

    def get(url, timeout=6):
        seen.append(url)
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:latest"}]}
        return {"version": "0.5.1"}
    llm = LLM(str(tmp_path / "ai.json"), get=get)
    r = llm.test_ollama("10.0.0.5")
    assert r["ok"] and r["models"] == ["llama3.2:latest", "qwen2.5:7b"] and r["version"] == "0.5.1"
    assert seen[0] == "http://10.0.0.5:11434/api/tags"

    def bad(url, timeout=6):
        raise OSError("Connection refused")
    r = LLM(str(tmp_path / "b.json"), get=bad).test_ollama("10.0.0.5")
    assert not r["ok"] and "OLLAMA_HOST" in r["error"]
    assert not LLM(str(tmp_path / "c.json")).test_ollama("")["ok"]
