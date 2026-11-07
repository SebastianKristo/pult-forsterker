"""Plex og Jellyfin som musikkilder ved siden av Navidrome (bla, søk, spill).

Daemonen snakker med serveren (token/API-nøkkel lagres på Skjold, ikke i nettleseren) og gir web/appene et felles,
normalisert format. Avspilling: strøm-URL-en til hvert spor spilles via Lyrion som Navidrome-spor (play_url for det
første, «playlist add» for resten).

Felles format:
  album:     {id, name, artist, year, cover, songCount}
  spilleliste: {id, name, songCount, cover}
  spor:      {id, title, artist, album, duration, cover, url}

API (ki_amp_daemon.py):
  GET  /api/medialib                       → {plex: {configured, url}, jellyfin: {configured, url}}
  POST /api/medialib {kind, url, token}    lagre (token tom = behold; url tom = fjern)
  POST /api/medialib/{kind}/test           → {ok, server, error}
  GET  /api/medialib/{kind}/albums?type=newest|random   GET …/album/{id}   GET …/playlists   GET …/playlist/{id}
  GET  /api/medialib/{kind}/search?q=      → {albums, tracks}
  POST /api/medialib/{kind}/play {album?|playlist?|track?}
"""
import json
import os
import urllib.parse
import urllib.request

UA = "Skjold/1.0"
KINDS = ("plex", "jellyfin")


def _get(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


class Plex:
    """Plex Media Server: X-Plex-Token. Musikkbibliotek = seksjoner med type «artist»."""

    def __init__(self, url, token, get=_get):
        self.url, self.token, self.get = url.rstrip("/"), token, get

    def _q(self, path, **p):
        p["X-Plex-Token"] = self.token
        sep = "&" if "?" in path else "?"
        return self.get(f"{self.url}{path}{sep}{urllib.parse.urlencode(p)}")

    def _img(self, thumb):
        return f"{self.url}{thumb}?X-Plex-Token={self.token}" if thumb else ""

    def _sections(self):
        d = self._q("/library/sections").get("MediaContainer", {})
        return [s["key"] for s in d.get("Directory", []) if s.get("type") == "artist"]

    def test(self):
        d = self._q("/identity").get("MediaContainer", {})
        return {"ok": True, "server": f"Plex {d.get('version', '')}".strip(), "libraries": len(self._sections())}

    def _album(self, a):
        return {"id": str(a.get("ratingKey")), "name": a.get("title", ""), "artist": a.get("parentTitle", ""),
                "year": a.get("year"), "cover": self._img(a.get("thumb")), "songCount": a.get("leafCount", 0)}

    def _track(self, t):
        part = ((t.get("Media") or [{}])[0].get("Part") or [{}])[0]
        url = f"{self.url}{part['key']}?X-Plex-Token={self.token}" if part.get("key") else ""
        return {"id": str(t.get("ratingKey")), "title": t.get("title", ""), "artist": t.get("originalTitle") or t.get("grandparentTitle", ""),
                "album": t.get("parentTitle", ""), "duration": int((t.get("duration") or 0) / 1000),
                "cover": self._img(t.get("parentThumb") or t.get("thumb")), "url": url}

    def albums(self, kind="newest", n=24):
        out = []
        sort = {"newest": "addedAt:desc", "random": "random"}.get(kind, "addedAt:desc")
        for s in self._sections():
            d = self._q(f"/library/sections/{s}/all", type=9, sort=sort, **{"X-Plex-Container-Size": n}).get("MediaContainer", {})
            out += [self._album(a) for a in d.get("Metadata", [])]
        return out[:n]

    def album(self, aid):
        d = self._q(f"/library/metadata/{aid}/children").get("MediaContainer", {})
        tracks = [self._track(t) for t in d.get("Metadata", [])]
        return {"album": {"id": aid, "name": d.get("title2") or d.get("parentTitle", ""), "artist": d.get("title1", ""),
                          "cover": self._img(d.get("thumb"))}, "tracks": tracks}

    def playlists(self):
        d = self._q("/playlists", playlistType="audio").get("MediaContainer", {})
        return [{"id": str(p.get("ratingKey")), "name": p.get("title", ""), "songCount": p.get("leafCount", 0),
                 "cover": self._img(p.get("composite"))} for p in d.get("Metadata", [])]

    def playlist(self, pid):
        d = self._q(f"/playlists/{pid}/items").get("MediaContainer", {})
        return [self._track(t) for t in d.get("Metadata", [])]

    def search(self, q):
        d = self._q("/hubs/search", query=q, limit=20).get("MediaContainer", {})
        albums, tracks = [], []
        for hub in d.get("Hub", []):
            if hub.get("type") == "album":
                albums += [self._album(a) for a in hub.get("Metadata", [])]
            elif hub.get("type") == "track":
                tracks += [self._track(t) for t in hub.get("Metadata", [])]
        return {"albums": albums, "tracks": tracks}


class Jellyfin:
    """Jellyfin: API-nøkkel (Dashbord → API-nøkler). Brukeren = første administrator (eller første bruker)."""

    def __init__(self, url, token, get=_get):
        self.url, self.token, self.get = url.rstrip("/"), token, get
        self._uid = None

    def _q(self, path, **p):
        q = ("?" + urllib.parse.urlencode(p)) if p else ""
        return self.get(f"{self.url}{path}{q}", {"X-Emby-Token": self.token, "Authorization": f'MediaBrowser Token="{self.token}"'})

    def _user(self):
        if not self._uid:
            users = self._q("/Users")
            u = next((x for x in users if (x.get("Policy") or {}).get("IsAdministrator")), users[0] if users else None)
            if not u:
                raise RuntimeError("fant ingen Jellyfin-bruker")
            self._uid = u["Id"]
        return self._uid

    def _img(self, iid):
        return f"{self.url}/Items/{iid}/Images/Primary?maxWidth=500&api_key={self.token}" if iid else ""

    def test(self):
        d = self._q("/System/Info")
        self._user()
        return {"ok": True, "server": f"Jellyfin {d.get('Version', '')}".strip()}

    def _album(self, a):
        return {"id": a["Id"], "name": a.get("Name", ""), "artist": a.get("AlbumArtist", ""), "year": a.get("ProductionYear"),
                "cover": self._img(a["Id"]), "songCount": a.get("ChildCount", 0)}

    def _track(self, t):
        return {"id": t["Id"], "title": t.get("Name", ""), "artist": ", ".join(t.get("Artists") or []) or t.get("AlbumArtist", ""),
                "album": t.get("Album", ""), "duration": int((t.get("RunTimeTicks") or 0) / 10_000_000),
                "cover": self._img(t.get("AlbumId") or t["Id"]),
                "url": f"{self.url}/Audio/{t['Id']}/universal?UserId={self._user()}&api_key={self.token}"
                       "&Container=mp3,flac,aac,m4a&AudioCodec=mp3&TranscodingContainer=mp3&MaxStreamingBitrate=320000"}

    def _items(self, **p):
        return self._q(f"/Users/{self._user()}/Items", Recursive="true", **p).get("Items", [])

    def albums(self, kind="newest", n=24):
        sort = {"newest": "DateCreated", "random": "Random"}.get(kind, "DateCreated")
        return [self._album(a) for a in self._items(IncludeItemTypes="MusicAlbum", SortBy=sort, SortOrder="Descending", Limit=n)]

    def album(self, aid):
        items = self._items(ParentId=aid, IncludeItemTypes="Audio", SortBy="ParentIndexNumber,IndexNumber")
        a = self._q(f"/Users/{self._user()}/Items/{aid}")
        return {"album": {"id": aid, "name": a.get("Name", ""), "artist": a.get("AlbumArtist", ""), "cover": self._img(aid)},
                "tracks": [self._track(t) for t in items]}

    def playlists(self):
        return [{"id": p["Id"], "name": p.get("Name", ""), "songCount": p.get("ChildCount", 0), "cover": self._img(p["Id"])}
                for p in self._items(IncludeItemTypes="Playlist")]

    def playlist(self, pid):
        d = self._q(f"/Playlists/{pid}/Items", UserId=self._user())
        return [self._track(t) for t in d.get("Items", []) if t.get("Type") == "Audio"]

    def search(self, q):
        return {"albums": [self._album(a) for a in self._items(SearchTerm=q, IncludeItemTypes="MusicAlbum", Limit=20)],
                "tracks": [self._track(t) for t in self._items(SearchTerm=q, IncludeItemTypes="Audio", Limit=30)]}


class MediaLib:
    """Lagrer oppsettet (data_dir/medialib.json, 0600) og gir riktig klient."""

    def __init__(self, path, get=_get):
        self.path, self.get = path, get
        self.cfg = {k: {"url": "", "token": ""} for k in KINDS}
        try:
            with open(path) as f:
                for k, v in json.load(f).items():
                    if k in KINDS and isinstance(v, dict):
                        self.cfg[k].update({x: str(v.get(x) or "") for x in ("url", "token")})
        except Exception:
            pass

    def public(self):
        return {k: {"configured": bool(v["url"] and v["token"]), "url": v["url"]} for k, v in self.cfg.items()}

    def set(self, b):
        k = b.get("kind")
        if k not in KINDS:
            raise ValueError("kind må være plex eller jellyfin")
        url = str(b.get("url") or "").strip().rstrip("/")
        if url and "://" not in url:
            url = "http://" + url
        self.cfg[k]["url"] = url
        if b.get("token"):
            self.cfg[k]["token"] = str(b["token"]).strip()
        if not url:
            self.cfg[k]["token"] = ""
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.cfg, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
        return self.public()

    def client(self, kind):
        c = self.cfg.get(kind)
        if not c or not (c["url"] and c["token"]):
            raise RuntimeError(f"{kind.capitalize()} er ikke satt opp")
        return (Plex if kind == "plex" else Jellyfin)(c["url"], c["token"], self.get)

    def find_album(self, artist, album):
        """Album-kassetter: finn albumet hos Plex/Jellyfin (etter Navidrome). → (kind, spor) eller None."""
        want = (artist.lower().strip(), album.lower().strip())
        for kind in KINDS:
            if not (self.cfg[kind]["url"] and self.cfg[kind]["token"]):
                continue
            try:
                c = self.client(kind)
                for a in c.search(f"{artist} {album}")["albums"] + c.search(album)["albums"]:
                    if a["name"].lower().strip() == want[1] and (not want[0] or want[0] in a["artist"].lower()):
                        tracks = c.album(a["id"])["tracks"]
                        if tracks:
                            return kind, tracks
            except Exception:
                continue
        return None
