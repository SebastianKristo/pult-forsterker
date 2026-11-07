"""Lydbøker fra Audiobookshelf (ABS) som kilde i Skjold.

Oppsett: ABS-adresse + API-token (ABS → Innstillinger → Brukere → din bruker → API-token).

GET  /api/abs                         {konfigurert, url, bibliotek?}
POST /api/abs {url, token}            lagre og test
GET  /api/abs/biblioteker             [{id, navn}]
GET  /api/abs/boker?bibliotek=        [{id, tittel, forfatter, varighet, progresjon, cover}]  (lydbøker og podkaster)
GET  /api/abs/bok/{id}                {id, tittel, forfatter, kapitler: [{tittel, start, slutt}], progresjon, sist_tid}
POST /api/abs/spill {id, fra_start?}  spill boka fra der du slapp (eller fra start)
POST /api/abs/sovetimer {modus: "kapittel"|"av", minutter?}
GET  /api/abs/naa                     {id, tittel, kapittel, posisjon, varighet, sovetimer}

Progresjon synkes tilbake til ABS hvert 30. sekund mens boka spilles, og ved pause/bytte.
Hastighet: Lyrion/Squeezelite kan ikke spille raskere, så hastighet støttes ikke (ABS-appen kan).
"""
import json
import os
import time
import urllib.parse
import urllib.request


class AbsClient:
    def __init__(self, url: str, token: str, opener=None):
        self.url, self.token = url.rstrip("/"), token
        self._open = opener or self._http

    def _http(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method,
                                     headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as f:
            raw = f.read()
        return json.loads(raw) if raw else {}

    def get(self, path):
        return self._open("GET", path, None)

    def libraries(self):
        return [{"id": l["id"], "navn": l.get("name", ""), "type": l.get("mediaType", "book")}
                for l in self.get("/api/libraries").get("libraries", [])]

    def progress_all(self):
        try:
            me = self.get("/api/me")
        except Exception:
            return {}
        return {p.get("libraryItemId"): p for p in me.get("mediaProgress") or []}

    def items(self, library_id, limit=200):
        prog = self.progress_all()
        r = self.get(f"/api/libraries/{urllib.parse.quote(library_id)}/items?limit={limit}&sort=media.metadata.title")
        out = []
        for it in r.get("results", []):
            md = (it.get("media") or {}).get("metadata") or {}
            p = prog.get(it["id"]) or {}
            out.append({"id": it["id"], "tittel": md.get("title", ""), "forfatter": md.get("authorName") or md.get("author") or "",
                        "varighet": (it.get("media") or {}).get("duration") or 0,
                        "progresjon": round(float(p.get("progress") or 0), 3), "ferdig": bool(p.get("isFinished")),
                        "cover": self.cover_url(it["id"])})
        return out

    def cover_url(self, item_id):
        return f"{self.url}/api/items/{item_id}/cover?token={urllib.parse.quote(self.token)}"

    def book(self, item_id):
        it = self.get(f"/api/items/{urllib.parse.quote(item_id)}?expanded=1")
        media = it.get("media") or {}
        md = media.get("metadata") or {}
        try:
            p = self.get(f"/api/me/progress/{urllib.parse.quote(item_id)}")
        except Exception:
            p = {}
        tracks = sorted(media.get("tracks") or media.get("audioFiles") or [], key=lambda t: t.get("index", 0))
        files, start = [], 0.0
        for t in tracks:
            dur = float(t.get("duration") or 0)
            ino = t.get("ino") or (t.get("metadata") or {}).get("ino") or ""
            url = t.get("contentUrl") or (f"/api/items/{item_id}/file/{ino}" if ino else "")
            if url:
                files.append({"url": self.url + url + ("&" if "?" in url else "?") + "token=" + urllib.parse.quote(self.token),
                              "start": float(t.get("startOffset", start)), "varighet": dur})
            start += dur
        return {"id": item_id, "tittel": md.get("title", ""), "forfatter": md.get("authorName") or "",
                "varighet": float(media.get("duration") or start), "cover": self.cover_url(item_id),
                "kapitler": [{"tittel": c.get("title", ""), "start": float(c.get("start", 0)), "slutt": float(c.get("end", 0))}
                             for c in media.get("chapters") or []],
                "filer": files, "sist_tid": float(p.get("currentTime") or 0), "progresjon": float(p.get("progress") or 0)}

    def save_progress(self, item_id, current, duration):
        dur = max(1.0, float(duration))
        body = {"currentTime": round(float(current), 1), "duration": dur, "progress": round(min(1.0, current / dur), 4),
                "isFinished": current >= dur - 30}
        return self._open("PATCH", f"/api/me/progress/{urllib.parse.quote(item_id)}", body)


def locate(files, t):
    """(filindeks, sekunder inn i fila) for bok-tiden t."""
    for i, f in enumerate(files):
        if t < f["start"] + f["varighet"] or i == len(files) - 1:
            return i, max(0.0, t - f["start"])
    return 0, 0.0


def chapter_at(chapters, t):
    for i, c in enumerate(chapters):
        if c["start"] <= t < c["slutt"]:
            return i
    return len(chapters) - 1 if chapters and t >= chapters[-1]["start"] else -1


class Audiobooks:
    def __init__(self, ctx, path=None, client_factory=AbsClient):
        """ctx: play(url, tittel, cover, start_s), queue(url, tittel), position() → (fil-url eller None, sekunder),
        pause(), playing() → bool."""
        self.ctx, self.path, self.mk = ctx, path, client_factory
        self.cfg = {"url": "", "token": "", "bibliotek": ""}
        self.cur = None            # bok som spilles: {id, tittel, filer, kapitler, varighet}
        self.sleep = None          # {"modus": "kapittel"|"minutter", "slutt": boktid|epoch}
        self._last_sync = 0.0
        if path and os.path.exists(path):
            try:
                self.cfg.update(json.load(open(path)))
            except Exception:
                pass

    def configured(self):
        return bool(self.cfg["url"] and self.cfg["token"])

    def client(self):
        if not self.configured():
            raise ValueError("Audiobookshelf er ikke satt opp – legg inn adresse og API-token")
        return self.mk(self.cfg["url"], self.cfg["token"])

    def public(self):
        return {"konfigurert": self.configured(), "url": self.cfg["url"], "bibliotek": self.cfg["bibliotek"],
                "har_token": bool(self.cfg["token"])}

    def sett(self, b):
        if b.get("url") is not None:
            u = str(b["url"]).strip().rstrip("/")
            if u and not u.startswith(("http://", "https://")):
                u = "http://" + u
            self.cfg["url"] = u
        if b.get("token"):
            self.cfg["token"] = str(b["token"]).strip()
        if b.get("bibliotek") is not None:
            self.cfg["bibliotek"] = str(b["bibliotek"])
        if self.path:
            with open(self.path + ".tmp", "w") as f:
                json.dump(self.cfg, f)
            os.chmod(self.path + ".tmp", 0o600)
            os.replace(self.path + ".tmp", self.path)
        out = self.public()
        if self.configured():
            try:
                out["biblioteker"] = self.client().libraries()
                out["ok"] = True
            except Exception as e:
                out["ok"], out["error"] = False, str(e)
        return out

    def play(self, item_id, fra_start=False):
        c = self.client()
        b = c.book(item_id)
        if not b["filer"]:
            raise ValueError("fant ingen lydfiler i boka")
        t = 0.0 if fra_start else b["sist_tid"]
        i, off = locate(b["filer"], t)
        self.cur = {k: b[k] for k in ("id", "tittel", "forfatter", "filer", "kapitler", "varighet", "cover")}
        self.ctx["play"](b["filer"][i]["url"], b["tittel"], b["cover"], off)
        for f in b["filer"][i + 1:]:
            self.ctx["queue"](f["url"], b["tittel"])
        return self.now()

    def book_time(self):
        """Boktid nå ut fra hvilken fil som spilles og posisjonen i den."""
        if not self.cur:
            return None
        url, pos = self.ctx["position"]()
        for f in self.cur["filer"]:
            if url and url.split("?")[0] == f["url"].split("?")[0]:
                return f["start"] + float(pos or 0)
        return None

    def now(self):
        if not self.cur:
            return {"id": None}
        t = self.book_time()
        k = chapter_at(self.cur["kapitler"], t) if t is not None else -1
        return {"id": self.cur["id"], "tittel": self.cur["tittel"], "forfatter": self.cur["forfatter"], "cover": self.cur["cover"],
                "posisjon": round(t, 1) if t is not None else None, "varighet": self.cur["varighet"],
                "kapittel": self.cur["kapitler"][k]["tittel"] if k >= 0 else "", "sovetimer": self.sleep}

    def set_sleep(self, modus, minutter=None):
        if modus == "av":
            self.sleep = None
        elif modus == "kapittel":
            t = self.book_time()
            if t is None or not self.cur or not self.cur["kapitler"]:
                raise ValueError("ingen bok med kapitler spilles nå")
            k = chapter_at(self.cur["kapitler"], t)
            self.sleep = {"modus": "kapittel", "slutt": self.cur["kapitler"][k]["slutt"]}
        else:
            self.sleep = {"modus": "minutter", "slutt": time.time() + 60 * float(minutter or 30)}
        return self.now()

    def tick(self, now=None):
        """Kalles hvert sekund av daemonen: sovetimer og synk av progresjon tilbake til ABS."""
        if not self.cur:
            return
        now = now or time.time()
        t = self.book_time()
        if self.sleep and t is not None:
            due = (self.sleep["modus"] == "kapittel" and t >= self.sleep["slutt"] - 0.5) or \
                  (self.sleep["modus"] == "minutter" and now >= self.sleep["slutt"])
            if due:
                self.sleep = None
                try:
                    self.ctx["pause"]()
                except Exception:
                    pass
                self.sync(force=True)
                return
        if t is not None and (now - self._last_sync >= 30) and self.ctx["playing"]():
            self.sync(now=now)

    def sync(self, force=False, now=None):
        t = self.book_time()
        if not self.cur or t is None:
            return False
        try:
            self.client().save_progress(self.cur["id"], t, self.cur["varighet"])
            self._last_sync = now or time.time()
            return True
        except Exception:
            return False
