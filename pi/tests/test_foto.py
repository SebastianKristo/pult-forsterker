"""Fotoskjermsparer: parserne for Unsplash, Wikimedia og NASA APOD, og mellomlagringen."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_foto as f  # noqa: E402


def test_unsplash():
    l = f.parse_unsplash([{"urls": {"raw": "https://images.unsplash.com/photo-1?ixid=abc"}, "description": None, "alt_description": "fjell i tåke",
                           "user": {"name": "Ola N", "links": {"html": "https://unsplash.com/@ola"}}, "location": {"name": "Lofoten"}, "color": "#223344"},
                          {"urls": {}}])
    assert len(l) == 1 and l[0]["url"].startswith("https://images.unsplash.com/photo-1?ixid=abc&w=1920")
    assert l[0]["credit"] == "Ola N · Unsplash" and l[0]["sted"] == "Lofoten" and "utm_source=skjold" in l[0]["link"]


def test_wikimedia_skaleres_og_krediteres():
    js = {"image": {"thumbnail": {"source": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Fjord.jpg/640px-Fjord.jpg"},
                    "image": {"source": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Fjord.jpg", "width": 6000, "height": 4000},
                    "artist": {"text": "<a>Kari</a>"}, "license": {"type": "CC BY-SA 4.0"}, "description": {"text": "En fjord"},
                    "file_page": "https://commons.wikimedia.org/wiki/File:Fjord.jpg"}}
    b = f.parse_wikimedia(js)
    assert b["url"].endswith("/1920px-Fjord.jpg") and b["credit"] == "Kari · CC BY-SA 4.0 · Wikimedia Commons" and b["liggende"]
    assert f.parse_wikimedia({"image": {"thumbnail": {"source": "x.svg"}}}) is None


def test_apod_hopper_over_video():
    l = f.parse_apod([{"media_type": "video", "url": "https://youtube"}, {"media_type": "image", "url": "https://apod/a.jpg", "title": "Tåke", "copyright": "\nPer\n"}])
    assert l == [{"url": "https://apod/a.jpg", "title": "Tåke", "credit": "Per · NASA APOD", "link": "https://apod.nasa.gov/apod/", "source": "apod"}]


def test_mellomlagring_og_nokkel():
    kall = []
    def hent(url, headers=None, timeout=0):
        kall.append(url)
        if "unsplash" in url:
            assert headers["Authorization"] == "Client-ID nøkkel"
            return [{"urls": {"raw": "https://u/1"}, "user": {"name": "A"}}]
        raise OSError("ingen nett")
    cfg = {"foto_kilder": "unsplash", "unsplash_key": "", "unsplash_tema": "nature"}
    x = f.Foto(lambda: cfg, hent, klokke=lambda: 1_000_000)
    r = x.bilder()
    assert r["items"] == [] and "nøkkel" in r["feil"] and not kall
    cfg["unsplash_key"] = "nøkkel"
    assert len(x.bilder()["items"]) == 1 and len(x.bilder()["items"]) == 1
    assert len(kall) == 1                                  # andre gang fra mellomlageret
