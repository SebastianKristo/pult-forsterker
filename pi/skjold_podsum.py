"""Daglig podkastsammendrag: nye episoder fra fulgte podkaster (RSS, NRK, Music Assistant) siden sist,
oppsummert (LLM hvis satt opp, ellers tittel + første setning), lest opp med piper – og tilbud om å spille episoden.

Oppsett i data_dir/podsum.json: {follow:[{kind:rss|nrk|ma, id, title}], time:"07:15", enabled, llm, voiceVol, maxEps, seen:{}}
API: GET/POST /api/podsum   POST /api/podsum/preview   POST /api/podsum/run   POST /api/podsum/play {i}
"""
import datetime as _dt
import email.utils
import html
import json
import os
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast": "https://podcastindex.org/namespace/1.0",
      "content": "http://purl.org/rss/1.0/modules/content/"}
SYSTEM = ("Du lager korte, muntlige sammendrag av podkastepisoder på norsk bokmål, til opplesning med talesyntese. "
          "2–3 setninger per episode, ingen lister, ingen markdown, ingen lenker.")


def _fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Skjold/1.0 podkast"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<(br|p|/p|li)[^>]*>", " ", s or "", flags=re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def _ts(s):
    if not s:
        return 0
    try:
        return email.utils.parsedate_to_datetime(s).timestamp()
    except Exception:
        pass
    try:
        return _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def parse_rss(data):
    """RSS-bytes → {title, image, episodes:[{id, title, desc, date, ts, url, transcript}]} (nyeste først)."""
    root = ET.fromstring(data)
    ch = root.find("channel")
    if ch is None:
        raise ValueError("ikke en RSS-feed")
    img = ch.find("itunes:image", NS)
    out = {"title": (ch.findtext("title") or "").strip(),
           "image": (img.get("href") if img is not None else "") or (ch.findtext("image/url") or ""), "episodes": []}
    for it in ch.findall("item"):
        enc = it.find("enclosure")
        tr = it.find("podcast:transcript", NS)
        desc = it.findtext("content:encoded", namespaces=NS) or it.findtext("description") or it.findtext("itunes:summary", namespaces=NS) or ""
        pub = it.findtext("pubDate") or ""
        out["episodes"].append({"id": (it.findtext("guid") or (enc.get("url") if enc is not None else "") or it.findtext("title") or "").strip(),
                                "title": (it.findtext("title") or "").strip(), "desc": strip_html(desc)[:4000],
                                "date": pub, "ts": _ts(pub), "url": enc.get("url") if enc is not None else "",
                                "transcript": tr.get("url") if tr is not None else ""})
    out["episodes"].sort(key=lambda e: -e["ts"])
    return out


def transcript_text(url, fetch=_fetch):
    """podcast:transcript (SRT/VTT/HTML/tekst/JSON) → ren tekst (maks ~6000 tegn)."""
    try:
        raw = fetch(url).decode("utf-8", "replace")
    except Exception:
        return ""
    if raw.lstrip().startswith("{"):
        try:
            segs = json.loads(raw).get("segments") or []
            return " ".join(s.get("body", "") for s in segs)[:6000]
        except Exception:
            return ""
    lines = [ln for ln in raw.splitlines() if ln.strip() and not re.match(r"^(\d+|WEBVTT.*|[\d:.,]+\s*-->\s*[\d:.,]+.*)$", ln.strip())]
    return strip_html(" ".join(lines))[:6000]


def first_sentence(text, n=220):
    t = strip_html(text)
    m = re.match(r"(.{20,}?[.!?])(\s|$)", t)
    s = m.group(1) if m else t
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def simple_summary(show, ep):
    fs = first_sentence(ep.get("desc") or "")
    return f"{show}: {ep['title']}." + (f" {fs}" if fs and fs.lower() not in ep["title"].lower() else "")


def summarize(items, llm=None, fetch=_fetch):
    """items: [(show, ep)] → [tekst]. LLM hvis tilgjengelig, ellers tittel + første setning."""
    out = []
    for show, ep in items:
        text = None
        if llm is not None and llm.enabled:
            body = ep.get("desc") or ""
            if ep.get("transcript"):
                body = (transcript_text(ep["transcript"], fetch) or body)
            try:
                text = llm.chat(SYSTEM, f"Podkast: {show}\nEpisode: {ep['title']}\n\n{body[:6000]}", max_tokens=300)
                text = re.sub(r"[*#_`]", "", text or "").strip()
                if text and show.lower() not in text.lower()[:80]:
                    text = f"{show}: {text}"
            except Exception:
                text = None
        out.append(text or simple_summary(show, ep))
    return out


def chunks(text, n=380):
    """Del i biter på setningsgrenser (piper-oppsettet tar maks 400 tegn om gangen)."""
    out, cur = [], ""
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        while len(s) > n:
            out.append(s[:n]); s = s[n:]
        if len(cur) + len(s) + 1 > n and cur:
            out.append(cur); cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        out.append(cur)
    return out


class PodSum:
    def __init__(self, ctx, path=None, fetch=_fetch):
        self.ctx, self.fetch = ctx, fetch
        self.path = path or os.path.join(ctx.get("data_dir") or "/var/lib/ki-amp", "podsum.json")
        self.cfg = {"follow": [], "time": "07:15", "enabled": False, "llm": True, "voiceVol": 0.9, "maxEps": 5,
                    "seen": {}, "lastRun": ""}
        try:
            with open(self.path) as f:
                self.cfg.update(json.load(f))
        except Exception:
            pass
        self.last = {"text": "", "items": [], "at": 0}
        self.lock = threading.Lock()

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.cfg, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def public(self):
        c = {k: v for k, v in self.cfg.items() if k != "seen"}
        c["llmReady"] = bool(self.ctx.get("llm") is not None and self.ctx["llm"].enabled)
        c["last"] = self.last
        return c

    def set(self, b):
        if "follow" in b and isinstance(b["follow"], list):
            fl = []
            for f in b["follow"][:50]:
                if isinstance(f, dict) and f.get("id") and f.get("kind") in ("rss", "nrk", "ma"):
                    fl.append({"kind": f["kind"], "id": str(f["id"])[:500], "title": str(f.get("title") or "")[:120]})
            self.cfg["follow"] = fl
        if re.match(r"^\d{1,2}:\d{2}$", str(b.get("time") or "")):
            self.cfg["time"] = b["time"]
        for k in ("enabled", "llm"):
            if k in b:
                self.cfg[k] = bool(b[k])
        if "voiceVol" in b:
            self.cfg["voiceVol"] = max(0.1, min(2.0, float(b["voiceVol"])))
        if "maxEps" in b:
            self.cfg["maxEps"] = max(1, min(15, int(b["maxEps"])))
        self.save()
        return self.public()

    # ---- kilder
    def _feed(self, f):
        if f["kind"] == "rss":
            return parse_rss(self.fetch(f["id"]))
        if f["kind"] == "nrk":
            nrk = self.ctx.get("nrk")
            s = nrk.series(f["id"], "podcast") if nrk else {"title": f.get("title"), "episodes": []}
            return {"title": s.get("title") or f.get("title"), "image": s.get("image", ""),
                    "episodes": [{"id": e["id"], "title": e.get("title", ""), "desc": e.get("subtitle", ""), "date": e.get("date", ""),
                                  "ts": _ts(e.get("date")), "nrk": e["id"], "url": "", "transcript": ""} for e in s.get("episodes", [])]}
        if f["kind"] == "ma":
            ma = self.ctx.get("ma")
            eps = []
            try:
                eps = ma.podcast_episodes(f["id"]) if ma is not None and hasattr(ma, "podcast_episodes") else []
            except Exception:
                eps = []
            return {"title": f.get("title") or "Podkast", "image": "",
                    "episodes": [{"id": e.get("uri") or e.get("id"), "title": e.get("name") or e.get("title", ""),
                                  "desc": e.get("description", ""), "date": "", "ts": _ts(e.get("date")),
                                  "ma": e.get("uri"), "url": "", "transcript": ""} for e in eps]}
        raise ValueError("ukjent kilde")

    def collect(self, mark=False):
        """→ [(show, ep)] – nye episoder siden sist (første gang: siste episode per podkast)."""
        out = []
        seen = self.cfg.setdefault("seen", {})
        for f in self.cfg["follow"]:
            key = f"{f['kind']}:{f['id']}"
            try:
                feed = self._feed(f)
            except Exception as e:
                print("podkastsammendrag:", key, e, flush=True)
                continue
            eps = feed["episodes"]
            prev = seen.get(key)
            new = [e for e in eps if prev is None or e["id"] not in prev][: (1 if prev is None else 3)]
            show = feed.get("title") or f.get("title") or "Podkast"
            out += [(show, dict(e, show=show, image=feed.get("image", ""))) for e in new]
            if mark:
                seen[key] = [e["id"] for e in eps[:60]]
        if mark:
            self.save()
        return out[: self.cfg.get("maxEps", 5)]

    def build(self, mark=False):
        items = self.collect(mark)
        if not items:
            return {"text": "Ingen nye podkastepisoder siden sist.", "items": [], "at": time.time()}
        llm = self.ctx.get("llm") if self.cfg.get("llm") else None
        texts = summarize(items, llm, self.fetch)
        n = len(items)
        intro = f"God morgen. Her er {'én ny podkastepisode' if n == 1 else f'{n} nye podkastepisoder'}."
        return {"text": " ".join([intro] + texts + ["Vil du høre en av dem, trykk Spill i Skjold-appen."]),
                "items": [{"show": s, "title": e["title"], "summary": t, "url": e.get("url"), "nrk": e.get("nrk"),
                           "ma": e.get("ma"), "image": e.get("image")} for (s, e), t in zip(items, texts)],
                "at": time.time()}

    def speak(self, text):
        tts, ann = self.ctx.get("tts"), self.ctx.get("announce")
        if not tts or not ann:
            raise RuntimeError("tale er ikke tilgjengelig")
        for c in chunks(text):
            wav = tts(c)
            if wav:
                ann(wav, self.cfg.get("voiceVol", 0.9))

    def run(self, speak=True):
        with self.lock:
            res = self.build(mark=True)
            self.last = res
            self.cfg["lastRun"] = _dt.date.today().isoformat()
            self.save()
        if speak:
            self.speak(res["text"])
        if res["items"] and self.ctx.get("toast"):
            try:
                self.ctx["toast"]("Podkastsammendrag", f"{len(res['items'])} nye episoder – trykk for å spille")
            except Exception:
                pass
        return res

    def play(self, i):
        it = self.last["items"][int(i)]
        if it.get("nrk") and self.ctx.get("nrk"):
            url = self.ctx["nrk"].stream(it["nrk"], True)
        elif it.get("url"):
            url = it["url"]
        elif it.get("ma") and self.ctx.get("ma") is not None:
            self.ctx["ma"].play(it["ma"])
            return it
        else:
            raise ValueError("episoden har ingen lydfil")
        if self.ctx.get("power_set"):
            self.ctx["power_set"](True)
        self.ctx["play_url"](url, f"{it['show']} – {it['title']}", it.get("image") or "", "")
        return it

    def due(self, now=None):
        now = now or _dt.datetime.now()
        if not self.cfg.get("enabled") or not self.cfg["follow"] or self.cfg.get("lastRun") == now.date().isoformat():
            return False
        h, m = map(int, self.cfg["time"].split(":"))
        return (now.hour, now.minute) >= (h, m)

    def add_to_morning(self):
        rt = self.ctx.get("routines")
        if rt is None:
            raise RuntimeError("rutiner er ikke tilgjengelig")
        r = rt.find("morgen") or rt.find("Morgen")
        if not r:
            raise KeyError("fant ingen Morgen-rutine")
        if not any(s.get("type") == "podsum" for s in r.get("steg") or []):
            r = dict(r, steg=list(r.get("steg") or []) + [{"type": "podsum", "verdi": True}])
            rt.save(r)
        return r


def routes(ctx):
    from aiohttp import web
    import asyncio
    ps = PodSum(ctx)
    ctx["podsum"] = ps

    def loop():
        while True:
            time.sleep(30)
            try:
                if ps.due():
                    ps.run()
            except Exception as e:
                print("podkastsammendrag:", e, flush=True)
    threading.Thread(target=loop, daemon=True).start()

    async def h_cfg(r):
        if r.method == "POST":
            b = await r.json()
            try:
                if b.get("action") == "morgen":
                    await asyncio.get_running_loop().run_in_executor(None, ps.add_to_morning)
                    return web.json_response(dict(ps.public(), morgen=True))
            except Exception as e:
                return web.json_response({"error": str(e)}, status=400)
            return web.json_response(ps.set(b))
        return web.json_response(ps.public())

    async def h_preview(_r):
        res = await asyncio.get_running_loop().run_in_executor(None, lambda: ps.build(mark=False))
        ps.last = res
        return web.json_response(res)

    async def h_run(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        threading.Thread(target=lambda: ps.run(speak=b.get("speak", True)), daemon=True).start()
        return web.json_response({"ok": True})

    async def h_play(r):
        b = await r.json()
        try:
            it = await asyncio.get_running_loop().run_in_executor(None, lambda: ps.play(b.get("i", 0)))
            return web.json_response({"ok": True, "playing": it["title"]})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=400)

    return [web.get("/api/podsum", h_cfg), web.post("/api/podsum", h_cfg), web.post("/api/podsum/preview", h_preview),
            web.post("/api/podsum/run", h_run), web.post("/api/podsum/play", h_play)]
