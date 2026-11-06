"""Planlagte programopptak (episoder, behold N, RSS), NRK-programguide og endringslogg."""
import os
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_programs as P  # noqa: E402


def _mp3(path, n=20000):
    with open(path, "wb") as fh:
        fh.write(b"\xff\xfb" + b"\0" * n)


def test_add_keep_and_smb_copy(tmp_path):
    progs = P.Programs(str(tmp_path / "prog"))
    smb = tmp_path / "smb" / "Programmer"
    t0 = time.mktime((2026, 11, 7, 9, 0, 0, 0, 0, -1))
    for w in range(4):
        src = tmp_path / f"r{w}.mp3"
        _mp3(src)
        progs.add(str(src), "Nitimen", t0 + w * 7 * 86400, 3 * 3600, "NRK P1", keep=2, extra_dirs=[str(smb)])
    lst = progs.listing()
    assert len(lst) == 1 and lst[0]["id"] == "nitimen"
    eps = lst[0]["episodes"]
    assert len(eps) == 2 and eps[0]["t"] > eps[1]["t"]
    assert sorted(os.listdir(tmp_path / "prog" / "nitimen")) == sorted(e["file"] for e in eps)
    assert len(os.listdir(smb / "Nitimen")) == 2           # eldste slettet på SMB også
    assert progs.path("nitimen", eps[0]["file"])
    assert progs.path("..", "x.mp3") is None and progs.path("nitimen", "../index.json") is None
    progs.remove_episode("nitimen", eps[1]["file"])
    assert len(progs.listing()[0]["episodes"]) == 1


def test_feed_is_valid_rss(tmp_path):
    progs = P.Programs(str(tmp_path))
    src = tmp_path / "a.mp3"
    _mp3(src)
    progs.add(str(src), "Søndagsåpent & co", time.time(), 3600, "NRK P1", image="https://x/y.jpg")
    xml = P.build_feed(progs.listing(), "http://10.0.0.5:8765")
    root = ET.fromstring(xml)
    items = root.findall("./channel/item")
    assert len(items) == 1
    enc = items[0].find("enclosure")
    assert enc.get("url").startswith("http://10.0.0.5:8765/api/recordings/prog/sondagsapent-co/") and enc.get("type") == "audio/mpeg"
    assert "Søndagsåpent & co" in items[0].find("title").text
    one = ET.fromstring(P.build_feed(progs.listing(), "http://h", only="annet"))
    assert not one.findall("./channel/item")


def test_parse_epg_and_schedule():
    res = {"entries": [
        {"title": "Nitimen", "plannedStart": "2026-11-07T09:03:00+01:00", "duration": "PT2H57M", "programId": "MDFP1"},
        {"programTitle": "Dagsnytt", "plannedStart": "/Date(1762502400000+0100)/", "plannedEnd": "/Date(1762503300000+0100)/"},
        {"title": "Nitimen", "plannedStart": "2026-11-07T09:03:00+01:00", "duration": "PT2H57M"},   # duplikat
    ]}
    shows = P.parse_epg(res)
    assert [s["title"] for s in shows].count("Nitimen") == 1
    nit = next(s for s in shows if s["title"] == "Nitimen")
    assert nit["dur"] == 2 * 3600 + 57 * 60
    dag = next(s for s in shows if s["title"] == "Dagsnytt")
    assert dag["dur"] == 900
    sc = P.schedule_from_show(nit, "p1", keep=5)
    assert sc["program"] == "Nitimen" and sc["minutes"] == 177 and sc["nrk"] == "p1" and sc["url"].startswith("https://lyd.nrk.no/")
    assert sc["days"] == [time.localtime(nit["start"]).tm_wday] and sc["keep"] == 5
    g = P.nrk_guide("p1", "2026-11-07", fetch=lambda url: res if "/epg/p1?date=2026-11-07" in url else None)
    assert len(g) == 2


def test_changelog_cache_and_offline(tmp_path):
    rels = [
        {"tag_name": "skjold-v0.1.9", "name": "Skjold skjold-v0.1.9", "body": "x", "prerelease": False, "published_at": "2026-01-01"},
        {"tag_name": "skjold-v0.1.10", "name": "Skjold skjold-v0.1.10", "prerelease": False, "published_at": "2026-01-02",
         "body": "## What's Changed\r\n* Radiologoer by @SebastianKristo in https://github.com/a/b/pull/114\r\n\r\n**Full Changelog**: https://x"},
        {"tag_name": "skjold-v0.1.11", "name": "beta", "body": "b", "prerelease": True},
        {"tag_name": "annet-v1", "body": ""},
    ]
    calls = []
    cl = P.Changelog(str(tmp_path / "c.json"), fetch=lambda u: calls.append(u) or rels)
    d = cl.payload("skjold-v0.1.10")
    assert d["notes"]["tag"] == "skjold-v0.1.10"
    assert d["notes"]["body"] == "## Endringer\n* Radiologoer"
    assert [r["tag"] for r in d["history"]] == ["skjold-v0.1.10", "skjold-v0.1.9"]   # versjonssortert, uten beta
    assert [r["tag"] for r in cl.payload("x", beta=True)["history"]][0] == "skjold-v0.1.11"
    assert len(calls) == 1                                    # cachet
    def boom(u): raise OSError("offline")
    off = P.Changelog(str(tmp_path / "c.json"), fetch=boom)
    off.refresh(max_age=0)
    d2 = off.payload("skjold-v0.1.10")
    assert d2["notes"]["tag"] == "skjold-v0.1.10"
