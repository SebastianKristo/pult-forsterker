"""Podkaster for Skjold: alle offentlige podkaster, favoritter og «fortsett der du slapp».

Kilder:
  * Apple Podcasts-katalogen (åpent søke-API og topplister per land og sjanger, ingen nøkkel). Katalogen peker til
    podkastens egen RSS-strøm, og det er den vi spiller fra, så dette dekker nesten alle offentlige podkaster.
  * NRK (pi/skjold_nrk.py): programmer og podkaster fra NRK slås sammen med søket.
  * Egen RSS-adresse: lim inn adressen til en hvilken som helst podkast-strøm.
  * Podme (pi/skjold_podme.py): med e-post og passord i innstillingene (podmeEmail/podmePass) kommer podkastene du
    følger i Podme med i Mine podkaster, Podme er med i søket, og premium-episoder spilles med abonnementet ditt.
  * Spotify: podkaster som også ligger på Spotify, har nesten alltid en offentlig RSS-strøm og finnes i søket.
    Podkaster som bare finnes på Spotify, kan ikke spilles her (Spotify slipper dem ikke ut).

Favoritter lagres på enheten (podkast_favoritter.json), så de vises likt i appen, web-UI og på Skjold Touch.
Episoder spilles via Lyrion (play_url i daemonen); posisjonen lagres mens de spiller (som NRK-episodene).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

UA = "Skjold/1.0 (+https://skjold-lab.com)"
ITUNES = os.environ.get("KI_AMP_ITUNES", "https://itunes.apple.com")
ITNS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
LAND = os.environ.get("KI_AMP_POD_LAND", "no")
MAX_EP = 300

# Apple Podcasts-sjangre (id → navn). Rekkefølgen er rekkefølgen knappene vises i.
SJANGRE = [(0, "Alle"), (1489, "Nyheter"), (1324, "Samfunn og kultur"), (1303, "Komedie"), (1488, "True crime"),
           (1487, "Historie"), (1545, "Sport"), (1321, "Næringsliv"), (1318, "Teknologi"), (1533, "Vitenskap"),
           (1512, "Helse"), (1305, "Barn og familie"), (1483, "Fiksjon"), (1309, "TV og film"), (1310, "Musikk"),
           (1304, "Utdanning"), (1301, "Kunst"), (1502, "Fritid"), (1314, "Religion")]


class PodError(RuntimeError):
    pass


def _http(url, fetch=None, timeout=12.0) -> bytes:
    if fetch:
        r = fetch(url)
        return r if isinstance(r, (bytes, bytearray)) else str(r).encode()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(8 * 1024 * 1024)
    except urllib.error.HTTPError as e:
        raise PodError(f"{urllib.parse.urlsplit(url).netloc} svarte {e.code}")
    except Exception as e:
        raise PodError(f"får ikke kontakt med {urllib.parse.urlsplit(url).netloc}: {e}")


def _json(url, fetch=None):
    try:
        return json.loads(_http(url, fetch).decode("utf-8", "replace"))
    except PodError:
        raise
    except Exception:
        raise PodError("uventet svar fra podkastkatalogen")


def _big(img: str) -> str:
    """Apple-omslag i 600 px i stedet for 100 px."""
    return re.sub(r"/\d+x\d+(bb)?\.(jpg|png|webp)$", r"/600x600bb.\2", img or "")


def _secs(v) -> float:
    """itunes:duration: «1234», «12:34» eller «1:02:03»."""
    s = str(v or "").strip()
    if not s:
        return 0.0
    try:
        n = [float(x) for x in s.split(":")]
    except ValueError:
        return 0.0
    t = 0.0
    for x in n:
        t = t * 60 + x
    return t


def _dato(v) -> tuple[str, float]:
    try:
        d = parsedate_to_datetime(str(v))
        return d.strftime("%Y-%m-%d"), d.timestamp()
    except Exception:
        return "", 0.0


def _txt(el, tag) -> str:
    x = el.find(tag)
    return (x.text or "").strip() if x is not None and x.text else ""


def _rens(s: str, n=400) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s.replace("&nbsp;", " ")).strip()
    return s[:n]


def ep_id(url: str) -> str:
    return "ep:" + hashlib.sha1(str(url).encode()).hexdigest()[:16]


def parse_rss(data: bytes) -> dict:
    """Podkast-RSS → {title, author, image, description, episodes:[…]} (nyeste først)."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise PodError("adressen er ikke en podkast-strøm (RSS)")
    ch = root.find("channel")
    if ch is None:
        raise PodError("adressen er ikke en podkast-strøm (RSS)")
    img_el = ch.find(ITNS + "image")
    image = (img_el.get("href") if img_el is not None else "") or _txt(ch, "image/url")
    title = _txt(ch, "title")
    out = {"title": title, "author": _txt(ch, ITNS + "author"), "image": image,
           "description": _rens(_txt(ch, "description") or _txt(ch, ITNS + "summary")), "episodes": []}
    for it in ch.findall("item"):
        enc = it.find("enclosure")
        url = (enc.get("url") if enc is not None else "") or ""
        typ = (enc.get("type") if enc is not None else "") or ""
        if not url.startswith(("http://", "https://")) or typ.startswith("video"):
            continue
        dato, ts = _dato(_txt(it, "pubDate"))
        ei = it.find(ITNS + "image")
        out["episodes"].append({"id": ep_id(url), "url": url, "title": _txt(it, "title") or title, "date": dato, "ts": ts,
                                "duration": _secs(_txt(it, ITNS + "duration")), "image": (ei.get("href") if ei is not None else "") or image,
                                "description": _rens(_txt(it, "description") or _txt(it, ITNS + "summary"), 300), "show": title})
        if len(out["episodes"]) >= MAX_EP:
            break
    out["episodes"].sort(key=lambda e: -e["ts"])
    return out


def _apple(r: dict) -> dict:
    return {"id": f"apple:{r.get('collectionId') or r.get('trackId')}", "title": r.get("collectionName") or r.get("trackName") or "",
            "author": r.get("artistName") or "", "image": _big(r.get("artworkUrl600") or r.get("artworkUrl100") or ""),
            "genre": r.get("primaryGenreName") or "", "src": "apple", "feed": r.get("feedUrl") or ""}


def parse_top(res) -> list[dict]:
    """Toppliste: det gamle iTunes-formatet (feed.entry) eller Apples nye (feed.results)."""
    feed = (res or {}).get("feed") or {}
    out = []
    for e in feed.get("entry") or []:
        try:
            pid = e["id"]["attributes"]["im:id"]
        except (KeyError, TypeError):
            continue
        imgs = e.get("im:image") or []
        out.append({"id": f"apple:{pid}", "title": (e.get("im:name") or {}).get("label", ""), "author": (e.get("im:artist") or {}).get("label", ""),
                    "image": _big(imgs[-1].get("label", "") if imgs else ""), "genre": ((e.get("category") or {}).get("attributes") or {}).get("label", ""),
                    "src": "apple"})
    for r in feed.get("results") or []:
        out.append({"id": f"apple:{r.get('id')}", "title": r.get("name", ""), "author": r.get("artistName", ""), "image": _big(r.get("artworkUrl100", "")),
                    "genre": ((r.get("genres") or [{}])[0] or {}).get("name", ""), "src": "apple"})
    return [x for x in out if x["title"]]


class Favoritter:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        try:
            with open(path) as f:
                self.items = [x for x in json.load(f) if isinstance(x, dict) and x.get("id")]
        except Exception:
            self.items = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.items, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def add(self, x: dict) -> list:
        pid = str(x.get("id") or "")
        if not re.match(r"^(apple:\d+|rss:https?://\S+|nrk:[\w.~-]+|podme:\d+)$", pid):
            raise PodError("ukjent podkast")
        item = {"id": pid, "title": str(x.get("title") or "")[:120], "author": str(x.get("author") or "")[:80],
                "image": str(x.get("image") or "")[:600], "kind": str(x.get("kind") or "")[:12], "t": time.time(),
                "src": pid.split(":", 1)[0] if pid.split(":", 1)[0] in ("apple", "rss", "nrk", "podme") else "apple"}
        with self.lock:
            self.items = [y for y in self.items if y["id"] != pid] + [item]
            self.items = self.items[-200:]
            self._save()
        return self.items

    def remove(self, pid: str) -> list:
        with self.lock:
            self.items = [y for y in self.items if y["id"] != pid]
            self._save()
        return self.items

    def has(self, pid: str) -> bool:
        return any(y["id"] == pid for y in self.items)


class Pod:
    def __init__(self, data_dir: str, fetch=None, nrk=None, settings=None):
        from skjold_nrk import Progress
        self.fetch, self.nrk, self.settings = fetch, nrk, settings or (lambda: {})
        self.data_dir = data_dir
        self._podme = None             # (e-post, passord, klient)
        self._podme_favs = (0.0, [])   # (tid, podkaster du følger i Podme)
        self.favs = Favoritter(os.path.join(data_dir, "podkast_favoritter.json"))
        self.progress = Progress(os.path.join(data_dir, "podkast_fremdrift.json"))
        self._feed: dict = {}          # apple:id → RSS-adresse
        self._shows: dict = {}         # id → (tid, show)
        self._top: dict = {}           # sjanger → (tid, liste)

    # ----- Podme -----
    def podme(self):
        """Podme-klienten når e-post og passord er satt i innstillingene, ellers None."""
        s = self.settings() or {}
        email, pw = str(s.get("podmeEmail") or "").strip(), str(s.get("podmePass") or "")
        if not email or not pw:
            return None
        if not self._podme or self._podme[:2] != (email, pw):
            from skjold_podme import Podme
            self._podme = (email, pw, Podme(email, pw, os.path.join(self.data_dir, "podme_token.json")))
            self._podme_favs = (0.0, [])
        return self._podme[2]

    def podme_favs(self) -> list:
        """Podkastene du følger i Podme (10 min mellomlager). Tom liste uten Podme eller ved feil."""
        pm = self.podme()
        if not pm:
            return []
        if time.time() - self._podme_favs[0] < 600:
            return self._podme_favs[1]
        try:
            lst = [{k: v for k, v in x.items() if k != "description"} for x in pm.my_podcasts()]
        except Exception:
            lst = self._podme_favs[1]
        self._podme_favs = (time.time(), lst)
        return lst

    def podme_status(self) -> dict:
        pm = self.podme()
        if not pm:
            return {"configured": False}
        try:
            me = pm.me()
            return {"configured": True, "ok": True, "user": me.get("user", ""), "shows": len(self.podme_favs())}
        except Exception as e:
            return {"configured": True, "ok": False, "error": str(e)}

    def all_favs(self) -> list:
        """Egne favoritter + podkastene du følger i Podme (uten dobbelt)."""
        egne = list(self.favs.items)
        ids = {x["id"] for x in egne}
        return egne + [x for x in self.podme_favs() if x["id"] not in ids]

    def fav(self, add=None, remove=None) -> list:
        pm = self.podme()
        if add:
            self.favs.add(add)
            pid = str(add.get("id") or "")
            if pm and pid.startswith("podme:"):
                try:
                    pm.follow(int(pid[6:]), True)
                    self._podme_favs = (0.0, self._podme_favs[1])
                except Exception:
                    pass
        if remove:
            self.favs.remove(remove)
            if pm and remove.startswith("podme:"):
                try:
                    pm.follow(int(remove[6:]), False)
                    self._podme_favs = (0.0, [x for x in self._podme_favs[1] if x["id"] != remove])
                except Exception:
                    pass
        return self.all_favs()

    def resolve(self, url: str) -> str:
        """Lydadressen som skal spilles: «podme:<id>» byttes mot Podme-fila, alt annet er en vanlig adresse."""
        if url.startswith("podme:"):
            pm = self.podme()
            if not pm:
                raise PodError("logg inn på Podme i Innstillinger for å spille denne")
            return pm.audio_url(int(url[6:]))
        return url

    # ----- katalog -----
    def genres(self):
        return [{"id": g, "name": n} for g, n in SJANGRE]

    def top(self, genre: int = 0, n: int = 100) -> list[dict]:
        hit = self._top.get(genre)
        if hit and time.time() - hit[0] < 6 * 3600:
            return hit[1]
        g = f"/genre={int(genre)}" if genre else ""
        urls = [f"{ITUNES}/{LAND}/rss/toppodcasts/limit={n}{g}/json"]
        if not genre:
            urls.append(f"https://rss.applemarketingtools.com/api/v2/{LAND}/podcasts/top/{n}/podcasts.json")
        last = None
        for u in urls:
            try:
                lst = parse_top(_json(u, self.fetch))
                if lst:
                    self._top[genre] = (time.time(), lst)
                    return lst
            except PodError as e:
                last = e
        if last:
            raise last
        return []

    def search(self, q: str) -> list[dict]:
        q = q.strip()
        if not q:
            return []
        if re.match(r"^https?://", q):   # en RSS-adresse limt inn i søkefeltet
            s = self.show("rss:" + q)
            return [{"id": "rss:" + q, "title": s["title"], "author": s["author"], "image": s["image"], "src": "rss"}]
        res = _json(f"{ITUNES}/search?" + urllib.parse.urlencode({"media": "podcast", "entity": "podcast", "limit": 50, "country": LAND, "term": q}), self.fetch)
        out = []
        for r in (res or {}).get("results") or []:
            a = _apple(r)
            if a["feed"]:
                self._feed[a["id"]] = a["feed"]
            out.append({k: v for k, v in a.items() if k != "feed"})
        pm = self.podme()
        if pm:   # Podme (også premium) etter NRK, før Apple-treffene med samme navn
            try:
                pr = [{k: v for k, v in x.items() if k != "description"} for x in pm.search(q)[:15]]
                titler = {x["title"].lower() for x in pr}
                out = pr + [x for x in out if x["title"].lower() not in titler]
            except Exception:
                pass
        if self.nrk:   # NRK først når navnet passer, så «Abels tårn» finner NRK-serien
            try:
                nr = [{"id": f"nrk:{s['id']}", "title": s["title"], "author": "NRK", "image": s["image"], "src": "nrk", "kind": s.get("kind", "")}
                      for s in self.nrk.search(q).get("series", [])[:12]]
                titler = {x["title"].lower() for x in nr}
                out = nr + [x for x in out if x["title"].lower() not in titler or x["author"].upper() != "NRK"]
            except Exception:
                pass
        return out

    def _feed_for(self, pid: str) -> str:
        if pid.startswith("rss:"):
            return pid[4:]
        if pid in self._feed:
            return self._feed[pid]
        num = pid.split(":", 1)[1]
        res = _json(f"{ITUNES}/lookup?" + urllib.parse.urlencode({"id": num, "entity": "podcast", "country": LAND}), self.fetch)
        for r in (res or {}).get("results") or []:
            if r.get("feedUrl"):
                self._feed[pid] = r["feedUrl"]
                return r["feedUrl"]
        raise PodError("podkasten har ingen offentlig strøm (bare i Apple Podcasts)")

    def show(self, pid: str, fresh: bool = False) -> dict:
        hit = self._shows.get(pid)
        if hit and not fresh and time.time() - hit[0] < 900:
            return self._decorate(pid, hit[1])
        if pid.startswith("nrk:"):
            if not self.nrk:
                raise PodError("NRK er ikke tilgjengelig")
            sid, _, kind = pid[4:].partition("~")
            s = self.nrk.series(sid, kind)
            show = {"title": s["title"], "author": "NRK", "image": s["image"], "description": s.get("subtitle", ""), "src": "nrk", "kind": s.get("kind", ""),
                    "episodes": [{"id": e["id"], "nrk": True, "podcast": e.get("podcast"), "title": e["title"], "date": e.get("date", ""), "ts": 0,
                                  "duration": e.get("duration", 0), "image": e.get("image") or s["image"], "description": e.get("subtitle", ""), "show": s["title"]}
                                 for e in s.get("episodes", [])]}
        elif pid.startswith("podme:"):
            pm = self.podme()
            if not pm:
                raise PodError("logg inn på Podme i Innstillinger for å se denne podkasten")
            show = pm.show(int(pid[6:]))
            show.pop("id", None)
        elif pid.startswith(("apple:", "rss:")):
            show = parse_rss(_http(self._feed_for(pid), self.fetch))
            show["src"] = "apple" if pid.startswith("apple:") else "rss"
            if not show["title"]:
                show["title"] = "Podkast"
        else:
            raise PodError("ukjent podkast")
        self._shows[pid] = (time.time(), show)
        return self._decorate(pid, show)

    def _decorate(self, pid, show):
        eps = []
        for e in show["episodes"]:
            p = self.progress.get(e["id"]) if not e.get("nrk") else (self.nrk.progress.get(e["id"]) if self.nrk else {})
            eps.append({**e, "pos": p.get("pos", 0), "heard": bool(p.get("heard"))} if p else e)
        return {**show, "id": pid, "fav": self.favs.has(pid), "episodes": eps}

    def new_episodes(self, n: int = 30) -> list[dict]:
        """De nyeste episodene fra favorittene (to fra hver), nyeste først."""
        favs = [f for f in self.all_favs() if not f["id"].startswith("podme:")]
        pm = self.podme()

        def hent(f):
            try:
                s = self.show(f["id"])
                return [{**e, "pid": f["id"], "show": s["title"]} for e in s["episodes"][:2]]
            except Exception:
                return []
        with ThreadPoolExecutor(max_workers=6) as ex:
            alle = [e for lst in ex.map(hent, favs) for e in lst]
        if pm:   # Podme har sin egen strøm med nye episoder fra det du følger
            try:
                alle += pm.feed(n)
            except Exception:
                pass
        alle.sort(key=lambda e: -(e.get("ts") or 0))
        return alle[:n]

    def continue_list(self, n: int = 12) -> list[dict]:
        return self.progress.continue_list(n)


def routes(ctx):
    """ctx: play_url, lyr_cmd, lyr_info, data_dir, nrk (valgfri), fetch (tester)."""
    from aiohttp import web
    import asyncio

    pod = Pod(ctx.get("data_dir", "/var/lib/ki-amp"), fetch=ctx.get("fetch"), nrk=ctx.get("nrk"), settings=ctx.get("settings"))
    ctx["pod"] = pod
    playing: dict = {}

    async def run(fn, *a):
        try:
            return web.json_response(await asyncio.get_running_loop().run_in_executor(None, lambda: fn(*a)))
        except PodError as e:
            return web.json_response({"error": str(e)}, status=502)
        except Exception as e:
            return web.json_response({"error": f"podkast: {e}"}, status=502)

    async def h_genres(_r):
        return web.json_response({"genres": pod.genres()})

    async def h_top(r):
        try:
            g = int(r.query.get("genre") or 0)
        except ValueError:
            g = 0
        return await run(lambda: {"shows": pod.top(g)})

    async def h_search(r):
        return await run(lambda: {"shows": pod.search(r.query.get("q", ""))})

    async def h_show(r):
        return await run(pod.show, r.query.get("id", ""), r.query.get("fresh") == "1")

    async def h_favs(r):
        if r.method == "POST":
            try:
                b = await r.json()
            except Exception:
                b = {}
            try:
                if b.get("remove"):
                    await asyncio.get_running_loop().run_in_executor(None, lambda: pod.fav(remove=str(b["remove"])))
                elif isinstance(b.get("add"), dict):
                    await asyncio.get_running_loop().run_in_executor(None, lambda: pod.fav(add=b["add"]))
            except PodError as e:
                return web.json_response({"error": str(e)}, status=400)
        return await run(lambda: {"items": pod.all_favs()})

    async def h_podme(_r):
        return await run(pod.podme_status)

    async def h_new(_r):
        return await run(lambda: {"items": pod.new_episodes()})

    async def h_continue(_r):
        return web.json_response({"items": pod.continue_list()})

    def _play(b):
        url, eid = str(b.get("url") or ""), str(b.get("id") or "")
        src_url = url
        url = pod.resolve(url) if url.startswith("podme:") else url
        if not url.startswith(("http://", "https://")):
            raise PodError("episoden mangler lydadresse")
        eid = eid or ep_id(url)
        meta = {"title": b.get("title", ""), "series": b.get("show", ""), "image": b.get("image", ""), "dur": b.get("duration") or 0, "url": src_url, "pid": b.get("pid", "")}
        ctx["play_url"](url, b.get("show") or b.get("title") or "Podkast", b.get("image", ""), "Podkast",
                        {"track": b.get("title", ""), "artist": b.get("show", ""), "album": b.get("show", ""),
                         "duration": float(b.get("duration") or 0), "source": "Podkast"})
        playing.clear(); playing.update(id=eid, url=url, meta=meta, t=time.time(), podme_t=0.0)
        pod.progress.update(eid, 0 if b.get("restart") else pod.progress.get(eid).get("pos", 0), float(b.get("duration") or 0), meta)
        start = 0.0 if b.get("restart") else pod.progress.resume_at(eid)
        if start:
            def seek():
                for _ in range(10):
                    time.sleep(1.5)
                    if (ctx["lyr_info"]() or {}).get("mode") == "play":
                        break
                ctx["lyr_cmd"](["time", round(start)])
            threading.Thread(target=seek, daemon=True).start()
        return {"ok": True, "resume": start}

    async def h_play(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        return await run(_play, b)

    def watch():
        while True:
            time.sleep(10)
            try:
                if not playing:
                    continue
                i = ctx["lyr_info"]() or {}
                if i.get("url") and i.get("url") != playing["url"] and time.time() - playing.get("t", 0) > 30:
                    playing.clear(); continue
                if i.get("mode") == "play" and float(i.get("time") or 0) > 0:
                    pos = float(i.get("time") or 0)
                    pod.progress.update(playing["id"], pos, float(i.get("duration") or 0) or float(playing["meta"].get("dur") or 0))
                    # Podme: posisjonen tilbake til Podme hvert minutt, så du fortsetter der du slapp i Podme-appen også
                    if playing["id"].startswith("podme-") and time.time() - playing.get("podme_t", 0) > 60:
                        playing["podme_t"] = time.time()
                        pm = pod.podme()
                        if pm:
                            try:
                                pm.save_progress(int(playing["id"][6:]), pos)
                            except Exception:
                                pass
            except Exception:
                pass

    if not ctx.get("fetch"):
        threading.Thread(target=watch, daemon=True).start()
    return [web.get("/api/pod/genres", h_genres), web.get("/api/pod/top", h_top), web.get("/api/pod/search", h_search),
            web.get("/api/pod/show", h_show), web.get("/api/pod/favs", h_favs), web.post("/api/pod/favs", h_favs),
            web.get("/api/pod/new", h_new), web.get("/api/pod/continue", h_continue), web.post("/api/pod/play", h_play),
            web.get("/api/pod/podme", h_podme)]
