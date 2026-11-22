import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_populaert as sp  # noqa: E402


def falsk(svar):
    kall = []

    def http(url, timeout=10):
        kall.append(url)
        for k, v in svar.items():
            if k in url:
                return v
        raise OSError("nett: " + url)
    return http, kall


def test_akkurat_na_fra_apple():
    http, kall = falsk({
        "songs.json": {"feed": {"results": [{"name": "Låt", "artistName": "Artist", "artworkUrl100": "https://x/100x100bb.jpg", "releaseDate": "2026-01-02"}]}},
        "albums.json": {"feed": {"results": [{"name": "Plate", "artistName": "Artist", "artworkUrl100": "https://x/100x100bb.jpg"}]}},
    })
    r = sp.Populaert(lambda: {}, http).hent("na")
    assert r["kilde"] == "Apple Music" and r["sanger"][0] == {"tittel": "Låt", "artist": "Artist", "album": "", "bilde": "https://x/400x400bb.jpg", "aar": "2026"}
    assert r["album"][0]["tittel"] == "Plate" and "/no/music/" in kall[0]


def test_tiar_fra_deezer_med_album_og_cache():
    spor = [{"title": f"Låt {i}", "artist": {"name": "A" if i % 2 else "B"}, "album": {"title": "Plate A" if i % 2 else f"Låt {i}", "cover_xl": "c"}} for i in range(30)]
    http, kall = falsk({
        "search/playlist": {"data": [{"id": 5, "title": "80s Hits", "nb_tracks": 60, "user": {"name": "Deezer Pop Editor"}}, {"id": 6, "nb_tracks": 3}]},
        "playlist/5/tracks": {"data": spor},
    })
    p = sp.Populaert(lambda: {}, http)
    r = p.hent("80")
    assert len(r["sanger"]) == 30 and r["kilde"].startswith("Deezer")
    assert [a["tittel"] for a in r["album"]] == ["Plate A"]   # singler med samme navn som låten telles ikke
    n = len(kall)
    p.hent("80")
    assert len(kall) == n


def test_ukjent_periode():
    try:
        sp.Populaert(lambda: {}, falsk({})[0]).hent("1850")
    except ValueError:
        return
    raise AssertionError
