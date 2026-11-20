"""Nylig spilt: oppføringene fra radio, Navidrome/YouTube Music (startet av Skjold) og andre kilder."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_radiokanal():
    import ki_amp_daemon as d
    e = d.recent_entry({"input": "radio", "title": "Låt", "artist": "X", "radio_now": {"name": "NRK P1+", "url": "http://p1", "logo": "https://logo/p1.png"}}, {}, 100)
    assert e["key"] == "radio:nrk p1+" and e["station"] and e["image"] == "https://logo/p1.png"
    assert e["replay"] == {"url": "http://p1", "title": "NRK P1+", "image": "https://logo/p1.png"}


def test_navidrome_lat_spilles_igjen_med_samme_strom():
    import ki_amp_daemon as d
    lp = {"url": "http://nd/rest/stream?id=1", "title": "Vår i Oslo – Jens", "art": "http://nd/cover", "track": "Vår i Oslo", "artist": "Jens",
          "album": "A", "duration": 200.0, "source": "Navidrome"}
    e = d.recent_entry({"input": "radio", "title": "Vår i Oslo", "artist": "Jens", "radio_now": {"url": lp["url"], "name": "Vår i Oslo – Jens"}}, lp, 100)
    assert e["kind"] == "Navidrome" and not e["station"] and e["title"] == "Vår i Oslo" and e["sub"] == "Jens"
    assert e["replay"]["url"] == lp["url"] and e["replay"]["meta"]["source"] == "Navidrome"


def test_airplay_og_unike_oppforinger(tmp_path, monkeypatch):
    import ki_amp_daemon as d
    monkeypatch.setattr(d, "RECENT_FILE", str(tmp_path / "recent.json"))
    monkeypatch.setitem(d._recent, "items", [])
    a = d.recent_entry({"input": "airplay", "title": "Sang", "artist": "B"}, {}, 1)
    assert a["replay"] == {"input": "airplay"}
    d.recent_add(a)
    d.recent_add(d.recent_entry({"input": "radio", "radio_now": {"name": "P3", "url": "http://p3"}}, {}, 2))
    d.recent_add(dict(a, t=3))
    assert [x["key"] for x in d._recent["items"]] == [a["key"], "radio:p3"]
    assert d.recent_entry({"input": "airplay", "title": ""}, {}, 4) is None


def test_stemme_finner_radiofavoritt():
    import ki_amp_daemon as d
    p = [{"title": "NRK P1+"}, None, {"title": "P3"}, {"title": "Radio Norge"}]
    assert d.stemme_finn_favoritt("nrk p1+", p) == 1
    assert d.stemme_finn_favoritt("radio norge", p) == 4
    assert d.stemme_finn_favoritt("kanal 3", p) == 3
    assert d.stemme_finn_favoritt("2", p) == 0          # tom plass
    assert d.stemme_finn_favoritt("jazz", p) == 0
