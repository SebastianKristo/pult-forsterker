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


def test_logo_name_from_program_title_and_prefix():
    import skjold_logos as L
    assert L.logo_name("1-NRK Jazz") == "NRK Jazz"
    u = "https://cdn0-47115-liveicecast0.dna.contentdelivery.net/jazz_mp3_h?nrkjazz"
    assert L.logo_name("Jazzbrunsj: Waltz For You, Harald Bergersen", u) == "NRK Jazz"
    assert L.logo_name("Radio Montebello", "http://stream.example/x") == "Radio Montebello"


def test_radio_browser_tries_without_radio_prefix():
    import json as _j
    import skjold_logos as L
    seen = []
    def fetch(u, **k):
        seen.append(u)
        if "byname/Montebello?" in u:
            return _j.dumps([{"name": "Montebello", "countrycode": "NO", "favicon": "http://x/m.png"}]).encode()
        return b"[]"
    assert L.radio_browser_logo("Radio Montebello", fetch) == "http://x/m.png"


# --- Normalisering og matching av kanalnavn (NRK P1+ m.fl.) ---

import pytest  # noqa: E402


@pytest.mark.parametrize("navn", ["NRK P1+", "NRK P1 +", "NRK P1 Pluss", "nrk p1 plus", "NRK P1PLUSS", "NRKP1+",
                                  "1-NRK P1+", "NRK P1+ (Oslo, Norway / Pop)", "NRK Radio P1+", "P1+", "P1 pluss",
                                  "NRK P1+ - Musikk for voksne", "  NRK  P1+  "])
def test_p1pluss_varianter_gir_innebygd_logo(navn):
    assert L.nrk_key(navn) == "nrk-p1plus"
    assert L.canonical(navn) == "NRK P1+"
    assert L.nrk_file(navn).endswith(os.path.join("nrk", "nrk-p1plus.png"))


def test_normalisering():
    assert L._norm("NRK P1+") == L._norm("NRK P1 Pluss") == L._norm("nrk p1 plus") == "nrkp1pluss"
    assert L._norm("NRK P3 (Oslo, Norway / Pop)") == "nrkp3"
    assert L._norm("2. Radio Norge") == L._norm("Radio Norge") == "radionorge"
    assert L._norm("P10 Country") == L._norm("p10-country") == "p10country"
    assert L._norm("Rådio Kåfé") == "radiokafe"
    assert L._norm("") == "" and L._norm(None) == ""


@pytest.mark.parametrize("navn,fil", [
    ("NRK P1", "nrk-p1"), ("NRK P1 Oslo og Akershus", "nrk-p1"), ("NRK P2", "nrk-p2"), ("P2", "nrk-p2"),
    ("NRK P3", "nrk-p3"), ("NRK P3 Musikk", "nrk-p3"), ("NRK mP3", "nrk-mp3"), ("NRK MP3", "nrk-mp3"),
    ("NRK Jazz", "nrk-jazz"), ("NRK Klassisk", "nrk-klassisk"), ("NRK Folkemusikk", "nrk-folkemusikk"),
    ("NRK Sport", "nrk-sport"),
    # ikke NRK-logo: må ikke treffe feil kanal på et prefiks («NRK P13» er ikke P1)
    ("NRK P13", None), ("P13", None), ("NRK Alltid Nyheter", None), ("Radio Norge", None), ("P4", None),
    ("P4 Norge", None), ("P5 Hits", None), ("P10 Country", None), ("MP3 Radio X", None), ("", None),
])
def test_nrk_matching(navn, fil):
    assert L.nrk_key(navn) == fil


def test_p1pluss_varianter_samme_nokkel():
    assert L.key_for("", "NRK P1+") == L.key_for("", "NRK P1 Pluss") == L.key_for("", "nrk p1 plus")
    assert L.key_for("", "NRK P1+") != L.key_for("", "NRK P1")


def test_p1pluss_innebygd_foran_kildens_bilde(tmp_path):
    # Kilden (Radio Browser/Lyrion) ga et favicon/dødt bilde for NRK P1+: logoen i repoet brukes uansett
    setup(tmp_path)
    kall = []
    def fetch(u, **k):
        kall.append(u); return b"\x00\x00\x01\x00" + b"0" * 32     # .ico
    k = L.path_for("https://www.nrk.no/favicon.ico", "NRK P1+").split("k=")[1]
    body, ct = L.get(k, fetch=fetch)
    assert ct == "image/png" and body == open(L.nrk_file("NRK P1+"), "rb").read()
    assert kall == []


def test_logo_name_fra_nrk_url():
    u = "https://lyd.nrk.no/nrk_radio_p1pluss_mp3_h"
    assert L.logo_name("Nitimen", u) == "NRK P1+"
    assert L.logo_name("2-NRK P1+", u) == "NRK P1+"


def test_radio_browser_reserve_normalisert_navn(tmp_path):
    # ikke-NRK-kanal uten logo i repoet: kildens bilde feiler → Radio Browser, navnet matches normalisert
    setup(tmp_path)
    def fetch(u, **k):
        if "radio-browser" in u:
            return json.dumps([{"name": "P10 Country Norge", "countrycode": "NO", "favicon": "https://x/feil.png"},
                               {"name": "P10 COUNTRY", "countrycode": "NO", "favicon": "https://x/p10.png"}]).encode()
        if u == "https://x/p10.png":
            return PNG
        raise OSError("404")
    k = L.path_for("http://dod.example/logo.png", "P10 Country").split("k=")[1]
    assert L.get(k, fetch=fetch) == (PNG, "image/png")


def test_radio_browser_foretrekker_ikke_ico():
    def fetch(u, **k):
        return json.dumps([{"name": "Radio Norge", "countrycode": "NO", "favicon": "https://x/favicon.ico"},
                           {"name": "Radio Norge", "countrycode": "NO", "favicon": "https://x/logo.png"},
                           {"name": "Radio Norge", "countrycode": "NO", "favicon": "ikke-en-adresse"}]).encode()
    assert L.radio_browser_logo("Radio Norge", fetch) == "https://x/logo.png"


def test_radio_browser_prover_pluss_varianter():
    def fetch(u, **k):
        if "byname/Kanal%2B?" in u:
            return json.dumps([{"name": "Kanal+", "favicon": "https://x/k.png"}]).encode()
        return b"[]"
    assert L.radio_browser_logo("Kanal Pluss", fetch) == "https://x/k.png"
