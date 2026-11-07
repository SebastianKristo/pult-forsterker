import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_logos as L  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def setup(tmp_path):
    L.CACHE_DIR = str(tmp_path)
    L._reg.clear()
    L.lyrion_base = lambda: "http://127.0.0.1:9000"


def test_relative_lyrion_path_made_absolute(tmp_path):
    setup(tmp_path)
    seen = []
    def fetch(u, **k):
        seen.append(u); return PNG
    p = L.path_for("imageproxy/abc/image.png", "Kanal X")
    k = p.split("k=")[1]
    body, ct = L.get(k, fetch=fetch)
    assert ct == "image/png" and body == PNG
    assert seen == ["http://127.0.0.1:9000/imageproxy/abc/image.png"]


def test_http_url_and_cache(tmp_path):
    setup(tmp_path)
    n = []
    def fetch(u, **k):
        n.append(u); return PNG
    k = L.path_for("http://example.com/logo.png", "Y").split("k=")[1]
    assert L.get(k, fetch=fetch)[1] == "image/png"
    L._reg.clear()                       # også etter omstart (registeret tomt) leses cachen
    assert L.get(k, fetch=fetch)[0] == PNG
    assert len(n) == 1


def test_nrk_builtin_when_source_fails(tmp_path):
    setup(tmp_path)
    def fetch(u, **k):
        raise OSError("nede")
    k = L.path_for("", "NRK P3").split("k=")[1]
    body, ct = L.get(k, fetch=fetch)
    assert ct == "image/png" and body[:4] == b"\x89PNG"   # PNG: appene viser ikke SVG


def test_radio_browser_lookup(tmp_path):
    setup(tmp_path)
    def fetch(u, **k):
        if "radio-browser" in u:
            return json.dumps([{"name": "Annen", "favicon": "http://x/a.png"},
                               {"name": "Radio Norge", "countrycode": "NO", "favicon": "http://x/rn.png"}]).encode()
        assert u == "http://x/rn.png"
        return PNG
    k = L.path_for("", "Radio Norge").split("k=")[1]
    assert L.get(k, fetch=fetch)[1] == "image/png"


def test_negative_cached(tmp_path):
    setup(tmp_path)
    calls = []
    def fetch(u, **k):
        calls.append(u); return b"not an image"
    k = L.path_for("http://x/bad", "").split("k=")[1]
    assert L.get(k, fetch=fetch) is None
    n = len(calls)
    assert L.get(k, fetch=fetch) is None and len(calls) == n


def test_bad_key():
    assert L.get("../../etc/passwd") is None


def test_generic_lyrion_art_does_not_share_key():
    import skjold_logos as L
    g = "http://10.69.1.65:9000/html/images/radio.png"
    a, b = L.path_for(g, "NRK Jazz"), L.path_for(g, "Radio Montebello")
    assert a and b and a != b
    assert L._reg[a.split("=")[1]]["src"] == ""     # standardbildet brukes ikke som logo


def test_nrk_logo_served_as_png(tmp_path, monkeypatch):
    import skjold_logos as L
    monkeypatch.setattr(L, "CACHE_DIR", str(tmp_path))
    k = L.path_for("", "NRK P3 (Oslo, Norway / Pop)").split("=")[1]
    body, ct = L.get(k, fetch=lambda *a, **kw: (_ for _ in ()).throw(OSError("offline")))
    assert ct == "image/png" and body[:8] == b"\x89PNG\r\n\x1a\n"
