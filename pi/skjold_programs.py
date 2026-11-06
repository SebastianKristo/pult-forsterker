"""Planlagte radioprogrammer («ta opp Nitimen hver lørdag») og endringslogg fra GitHub Releases.

Rene hjelpere uten daemon-avhengigheter, slik at de kan testes:
- programmer: lagre episode (lokalt + SMB), behold N siste, indeks, RSS-feed for podkastdelen
- NRK-programguide (psapi /epg) → liste med tittel, start, varighet
- endringslogg: release-notater for en tag, cachet på disk (fungerer uten nett)
"""
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
from email.utils import formatdate
from xml.sax.saxutils import escape

UA = "Skjold/1.0 (+https://github.com/SebastianKristo/pult-forsterker)"
REPO = os.environ.get("SKJOLD_REPO", "SebastianKristo/pult-forsterker")
NRK_API = os.environ.get("KI_AMP_NRK_API", "https://psapi.nrk.no")

# NRK-kanaler: id i programguiden → direktestrøm
NRK_CHANNELS = {
    "p1": ("NRK P1", "https://lyd.nrk.no/nrk_radio_p1_ostlandssendingen_mp3_h"),
    "p2": ("NRK P2", "https://lyd.nrk.no/nrk_radio_p2_mp3_h"),
    "p3": ("NRK P3", "https://lyd.nrk.no/nrk_radio_p3_mp3_h"),
    "mp3": ("NRK mP3", "https://lyd.nrk.no/nrk_radio_mp3_mp3_h"),
    "alltid_nyheter": ("NRK Alltid Nyheter", "https://lyd.nrk.no/nrk_radio_alltid_nyheter_mp3_h"),
    "klassisk": ("NRK Klassisk", "https://lyd.nrk.no/nrk_radio_klassisk_mp3_h"),
    "jazz": ("NRK Jazz", "https://lyd.nrk.no/nrk_radio_jazz_mp3_h"),
    "folkemusikk": ("NRK Folkemusikk", "https://lyd.nrk.no/nrk_radio_folkemusikk_mp3_h"),
    "p1pluss": ("NRK P1+", "https://lyd.nrk.no/nrk_radio_p1pluss_mp3_h"),
}


def safe_name(s, n=60):
    s = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", str(s or "")).strip(" .")
    return re.sub(r"\s+", " ", s)[:n] or "Program"


def slug(s):
    s = str(s or "").lower().translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a"}))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50] or "program"


# ---------- programmer og episoder ----------

class Programs:
    """Indeks over programopptak i <root>/<slug>/<YYYY-MM-DD HHMM>.mp3 med index.json."""

    def __init__(self, root):
        self.root = root

    def _idx_path(self):
        return os.path.join(self.root, "index.json")

    def load(self):
        try:
            with open(self._idx_path()) as fh:
                d = json.load(fh)
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def save(self, d):
        os.makedirs(self.root, exist_ok=True)
        tmp = self._idx_path() + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self._idx_path())

    def add(self, src, name, t0, dur, channel="", image="", keep=8, extra_dirs=(), move=True):
        """Lagrer opptaket som ny episode av programmet `name`. extra_dirs: f.eks. SMB-mappen (kopi der også).
        Returnerer episoden. Eldste episoder utover `keep` slettes (lokalt og i extra_dirs)."""
        sl = slug(name)
        d = self.load()
        prog = d.setdefault(sl, {"name": name, "episodes": []})
        prog.update(name=name, channel=channel or prog.get("channel", ""), image=image or prog.get("image", ""))
        stamp = time.strftime("%Y-%m-%d %H%M", time.localtime(t0))
        fn = f"{stamp}.mp3"
        local_dir = os.path.join(self.root, sl)
        os.makedirs(local_dir, exist_ok=True)
        dest = os.path.join(local_dir, fn)
        (shutil.move if move else shutil.copy2)(src, dest)
        copies = []
        for xd in extra_dirs:
            if not xd:
                continue
            try:
                pd = os.path.join(xd, safe_name(name))
                os.makedirs(pd, exist_ok=True)
                shutil.copy2(dest, os.path.join(pd, f"{safe_name(name)} {stamp}.mp3"))
                copies.append(pd)
            except OSError:
                pass
        ep = {"file": fn, "t": int(t0), "dur": int(dur), "size": os.path.getsize(dest),
              "title": f"{name} {time.strftime('%d.%m.%Y', time.localtime(t0))}"}
        prog["episodes"] = [e for e in prog["episodes"] if e.get("file") != fn] + [ep]
        prog["episodes"].sort(key=lambda e: e["t"], reverse=True)
        self._prune(sl, prog, max(1, int(keep or 8)), copies)
        self.save(d)
        return ep

    def _prune(self, sl, prog, keep, copies=()):
        old = prog["episodes"][keep:]
        prog["episodes"] = prog["episodes"][:keep]
        for e in old:
            for p in [os.path.join(self.root, sl, e["file"])] + \
                     [os.path.join(c, f"{safe_name(prog['name'])} {e['file']}") for c in copies]:
                try:
                    os.remove(p)
                except OSError:
                    pass

    def remove_episode(self, sl, fn):
        d = self.load()
        prog = d.get(sl)
        if not prog or "/" in fn:
            raise ValueError("finnes ikke")
        prog["episodes"] = [e for e in prog["episodes"] if e["file"] != fn]
        try:
            os.remove(os.path.join(self.root, sl, fn))
        except OSError:
            pass
        if not prog["episodes"]:
            d.pop(sl, None)
        self.save(d)

    def path(self, sl, fn):
        if "/" in sl or "/" in fn or ".." in sl or ".." in fn or not fn.endswith(".mp3"):
            return None
        p = os.path.join(self.root, sl, fn)
        return p if os.path.isfile(p) else None

    def listing(self):
        return [{"id": sl, "name": p["name"], "channel": p.get("channel", ""), "image": p.get("image", ""),
                 "episodes": p.get("episodes", [])} for sl, p in sorted(self.load().items(), key=lambda kv: kv[1]["name"].lower())]


def build_feed(programs, base_url, only=None, title="Skjold – radioopptak"):
    """RSS 2.0 (podkast) for alle eller ett program. base_url: http://<ip>:8765"""
    items = []
    imgs = []
    for p in programs:
        if only and p["id"] != only:
            continue
        if p.get("image"):
            imgs.append(p["image"])
        for e in p["episodes"]:
            url = f"{base_url}/api/recordings/prog/{urllib.parse.quote(p['id'])}/{urllib.parse.quote(e['file'])}"
            items.append((e["t"], (
                "<item>"
                f"<title>{escape(e.get('title') or p['name'])}</title>"
                f"<guid isPermaLink=\"false\">skjold-{escape(p['id'])}-{e['t']}</guid>"
                f"<pubDate>{formatdate(e['t'], localtime=False, usegmt=True)}</pubDate>"
                f"<enclosure url=\"{escape(url)}\" length=\"{int(e.get('size', 0))}\" type=\"audio/mpeg\"/>"
                f"<itunes:duration>{int(e.get('dur', 0))}</itunes:duration>"
                f"<description>{escape(p.get('channel') or '')}</description>"
                "</item>")))
    items.sort(key=lambda x: x[0], reverse=True)
    name = title
    if only:
        name = next((p["name"] for p in programs if p["id"] == only), title)
    img = f"<itunes:image href=\"{escape(imgs[0])}\"/>" if imgs else ""
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\"><channel>"
            f"<title>{escape(name)}</title><link>{escape(base_url)}</link><language>no</language>"
            f"<description>Radioprogrammer tatt opp av Skjold</description>{img}"
            + "".join(x[1] for x in items) + "</channel></rss>\n")


# ---------- NRK-programguide ----------

def _parse_time(s):
    """ISO-tid eller /Date(ms+0100)/ → epoch."""
    if not s:
        return None
    m = re.match(r"/Date\((\d+)", str(s))
    if m:
        return int(m.group(1)) // 1000
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _iso_dur(s):
    if isinstance(s, (int, float)):
        return float(s)
    m = re.match(r"P(?:T)?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", str(s or ""))
    if not m:
        return 0.0
    h, mi, se = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)


def parse_epg(res):
    """Tolerant: finner sendinger (tittel + start + varighet/slutt) hvor enn de ligger i svaret."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            title = o.get("title") or o.get("programTitle")
            if not isinstance(title, str) and isinstance(o.get("titles"), dict):
                title = o["titles"].get("title")
            if not isinstance(title, str):
                title = None
            start = _parse_time(o.get("plannedStart") or o.get("actualStart") or o.get("startTime") or o.get("start"))
            if title and start:
                dur = _iso_dur(o.get("duration") or o.get("plannedDuration") or 0)
                end = _parse_time(o.get("plannedEnd") or o.get("endTime") or o.get("end"))
                if not dur and end:
                    dur = end - start
                out.append({"title": str(title).strip(), "start": start, "dur": int(dur or 0),
                            "id": str(o.get("programId") or o.get("id") or "")})
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(res)
    seen, uniq = set(), []
    for x in sorted(out, key=lambda x: x["start"]):
        k = (x["title"], x["start"])
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


def nrk_guide(channel, date=None, fetch=None):
    """Programguide for en NRK-kanal én dag. date: 'YYYY-MM-DD' (tom = i dag)."""
    date = date or time.strftime("%Y-%m-%d")
    url = f"{NRK_API}/epg/{urllib.parse.quote(channel)}?date={urllib.parse.quote(date)}"
    if fetch:
        res = fetch(url)
    else:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            res = json.loads(r.read().decode("utf-8", "replace"))
    return parse_epg(res)


def schedule_from_show(show, channel, keep=8):
    """Gjør en sending fra guiden til en ukentlig opptaksplan (samme ukedag og tid hver uke)."""
    tm = time.localtime(show["start"])
    return {"time": "%02d:%02d" % (tm.tm_hour, tm.tm_min), "days": [tm.tm_wday], "minutes": max(1, min(240, round(show["dur"] / 60) or 60)),
            "program": show["title"], "nrk": channel, "url": NRK_CHANNELS.get(channel, ("", ""))[1], "preset": 0,
            "keep": keep, "on": True}


# ---------- endringslogg ----------

def _vkey(tag):
    return tuple(int(x) for x in re.findall(r"\d+", str(tag or ""))) or (0,)


class Changelog:
    def __init__(self, cache_path, fetch=None):
        self.cache_path = cache_path
        self.fetch = fetch

    def _load(self):
        try:
            with open(self.cache_path) as fh:
                d = json.load(fh)
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _save(self, d):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path + ".tmp", "w") as fh:
                json.dump(d, fh, ensure_ascii=False)
            os.replace(self.cache_path + ".tmp", self.cache_path)
        except OSError:
            pass

    def _get(self, url):
        if self.fetch:
            return self.fetch(url)
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())

    def refresh(self, max_age=3600):
        d = self._load()
        if time.time() - d.get("t", 0) < max_age and d.get("releases"):
            return d
        try:
            rels = self._get(f"https://api.github.com/repos/{REPO}/releases?per_page=30")
            items = [{"tag": r["tag_name"], "name": r.get("name") or r["tag_name"], "body": clean_body(r.get("body") or ""),
                      "date": r.get("published_at") or r.get("created_at") or "", "url": r.get("html_url") or "",
                      "prerelease": bool(r.get("prerelease"))}
                     for r in rels if not r.get("draft") and str(r.get("tag_name", "")).startswith("skjold-v")]
            items.sort(key=lambda x: _vkey(x["tag"]), reverse=True)
            d = {"t": time.time(), "releases": items}
            self._save(d)
            d["offline"] = False
        except Exception as e:
            d = {**d, "offline": True, "error": str(e)[:200]}
        return d

    def payload(self, current, beta=False, n=15):
        d = self.refresh()
        rels = [r for r in d.get("releases", []) if beta or not r["prerelease"] or r["tag"] == current]
        cur = next((r for r in rels if r["tag"] == current), None)
        return {"current": current or None, "notes": cur, "history": rels[:n], "offline": bool(d.get("offline"))}


def clean_body(body):
    """GitHubs autogenererte notater: fjern «by @x in URL», «Full Changelog»-linjen og PR-lenker → lesbar liste."""
    out = []
    for line in body.replace("\r", "").split("\n"):
        if line.startswith("**Full Changelog**") or line.strip().startswith("<!--"):
            continue
        line = re.sub(r"\s+by @[\w-]+(\[bot\])? in https://github\.com/\S+", "", line)
        line = re.sub(r"\s+in https://github\.com/\S+/pull/\d+", "", line)
        line = line.replace("## What's Changed", "## Endringer").replace("## New Contributors", "## Nye bidragsytere")
        out.append(line)
    return "\n".join(out).strip()
