"""Plex/Jellyfin-klientene mot falske servere (ingen nett)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_medialib as M  # noqa: E402


def plex_get(url, headers=None, timeout=10):
    assert "X-Plex-Token=tok" in url
    if "/identity" in url:
        return {"MediaContainer": {"version": "1.40"}}
    if "/library/sections?" in url:
        return {"MediaContainer": {"Directory": [{"key": "3", "type": "artist"}, {"key": "1", "type": "movie"}]}}
    if "/library/sections/3/all" in url:
        return {"MediaContainer": {"Metadata": [{"ratingKey": 11, "title": "Meteora", "parentTitle": "Linkin Park", "thumb": "/t/11", "leafCount": 13}]}}
    if "/library/metadata/11/children" in url:
        return {"MediaContainer": {"title1": "Linkin Park", "title2": "Meteora", "Metadata": [
            {"ratingKey": 101, "title": "Numb", "grandparentTitle": "Linkin Park", "parentTitle": "Meteora", "duration": 185000,
             "Media": [{"Part": [{"key": "/library/parts/9/file.flac"}]}]}]}}
    if "/hubs/search" in url:
        return {"MediaContainer": {"Hub": [{"type": "album", "Metadata": [{"ratingKey": 11, "title": "Meteora", "parentTitle": "Linkin Park"}]}]}}
    return {"MediaContainer": {}}


def test_plex_bla_og_strom_url(tmp_path):
    p = M.Plex("http://plex:32400/", "tok", plex_get)
    assert p.test()["libraries"] == 1
    a = p.albums()[0]
    assert a["name"] == "Meteora" and a["cover"].startswith("http://plex:32400/t/11?X-Plex-Token=")
    t = p.album("11")["tracks"][0]
    assert t["url"] == "http://plex:32400/library/parts/9/file.flac?X-Plex-Token=tok" and t["duration"] == 185


def jf_get(url, headers=None, timeout=10):
    assert headers["X-Emby-Token"] == "key"
    if url.endswith("/Users"):
        return [{"Id": "u1", "Policy": {"IsAdministrator": True}}]
    if "/System/Info" in url:
        return {"Version": "10.10"}
    if "IncludeItemTypes=MusicAlbum" in url:
        return {"Items": [{"Id": "al1", "Name": "25", "AlbumArtist": "Adele"}]}
    if "ParentId=al1" in url:
        return {"Items": [{"Id": "tr1", "Name": "Hello", "Artists": ["Adele"], "Album": "25", "AlbumId": "al1", "RunTimeTicks": 2950000000}]}
    if url.endswith("/Users/u1/Items/al1"):
        return {"Name": "25", "AlbumArtist": "Adele"}
    return {"Items": []}


def test_jellyfin_album_og_find_album(tmp_path):
    j = M.Jellyfin("http://jf:8096", "key", jf_get)
    assert j.test()["ok"]
    t = j.album("al1")["tracks"][0]
    assert t["duration"] == 295 and "/Audio/tr1/universal?UserId=u1&api_key=key" in t["url"]
    lib = M.MediaLib(str(tmp_path / "m.json"), get=jf_get)
    lib.set({"kind": "jellyfin", "url": "jf:8096", "token": "key"})
    assert lib.public()["jellyfin"] == {"configured": True, "url": "http://jf:8096"}
    assert oct(os.stat(tmp_path / "m.json").st_mode & 0o777) == "0o600"
    kind, tracks = lib.find_album("Adele", "25")
    assert kind == "jellyfin" and tracks[0]["title"] == "Hello"
    assert lib.find_album("Adele", "21") is None
