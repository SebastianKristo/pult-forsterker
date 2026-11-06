"""«Spill noe til …» – fritekst → strukturert musikksøk → kø via smart radio.

Tolkning: valgfri LLM (lokal Ollama eller Anthropic API, strukturert svar via tool use) med en regelbasert
fallback som alltid virker uten nett. Resultatet er {genres, moods, energy, decade, language, artists_like,
duration_min, kilder}. Oppslag: lydtaggene (skjold_libtag) → Navidrome → Music Assistant → nettradio.

API:  POST /api/ask {text, room}       GET/POST /api/ai (LLM-oppsett, nøkkelen vises aldri)
"""
import json
import os
import re
import threading
import urllib.request

MOODS = ("glad", "rolig", "trist", "energisk", "mørk", "drømmende")
KILDER = ("tags", "navidrome", "ma", "radio")
SCHEMA = {
    "type": "object",
    "properties": {
        "genres": {"type": "array", "items": {"type": "string"}},
        "moods": {"type": "array", "items": {"type": "string", "enum": list(MOODS)}},
        "energy": {"type": "string", "enum": ["lav", "middels", "høy", ""]},
        "decade": {"type": ["integer", "null"]},
        "language": {"type": "string"},
        "artists_like": {"type": "array", "items": {"type": "string"}},
        "duration_min": {"type": ["integer", "null"]},
        "kilder": {"type": "array", "items": {"type": "string", "enum": list(KILDER)}},
    },
    "required": ["genres", "moods", "energy"],
}
SYSTEM = ("Du gjør om et ønske om musikk (norsk eller engelsk) til et strukturert søk for en hjemmeforsterker. "
          "Stemninger må være blant: " + ", ".join(MOODS) + ". Energi er lav/middels/høy eller tom. "
          "decade er f.eks. 1980 for «80-tallet». language er «norsk», «engelsk» eller tom. "
          "Sjangre på engelsk med små bokstaver (jazz, rock, classical …). Svar bare via verktøyet.")
DEFAULT_MODEL = "claude-haiku-5-5"

# ---------------------------------------------------------------- regelbasert tolkning

_GENRES = {
    "jazz": "jazz", "blues": "blues", "rock": "rock", "pop": "pop", "klassisk": "classical", "classical": "classical",
    "hip hop": "hip-hop", "hiphop": "hip-hop", "rap": "hip-hop", "metal": "metal", "country": "country", "folk": "folk",
    "visesang": "folk", "viser": "folk", "elektronisk": "electronic", "electronic": "electronic", "techno": "techno",
    "house": "house", "soul": "soul", "funk": "funk", "reggae": "reggae", "disco": "disco", "punk": "punk",
    "indie": "indie", "ambient": "ambient", "lofi": "lo-fi", "lo-fi": "lo-fi", "r&b": "r&b", "gospel": "gospel",
    "latin": "latin", "salsa": "latin", "opera": "opera", "julesang": "christmas", "jul": "christmas",
    "christmas": "christmas", "barnesang": "children", "dans": "dance", "dance": "dance", "singer-songwriter": "singer-songwriter",
}
_MOOD_WORDS = {
    "rolig": ("rolig", "lav"), "avslapp": ("rolig", "lav"), "chill": ("rolig", "lav"), "middag": ("rolig", "lav"),
    "kos": ("rolig", "lav"), "sove": ("rolig", "lav"), "søvn": ("rolig", "lav"), "calm": ("rolig", "lav"),
    "relax": ("rolig", "lav"), "lese": ("rolig", "lav"), "fokus": ("rolig", "middels"), "jobbe": ("rolig", "middels"),
    "glad": ("glad", "middels"), "happy": ("glad", "middels"), "fest": ("glad", "høy"), "party": ("glad", "høy"),
    "sommer": ("glad", "middels"), "solskinn": ("glad", "middels"),
    "trist": ("trist", "lav"), "sad": ("trist", "lav"), "melankol": ("trist", "lav"), "regn": ("trist", "lav"),
    "energisk": ("energisk", "høy"), "trening": ("energisk", "høy"), "trene": ("energisk", "høy"),
    "løping": ("energisk", "høy"), "workout": ("energisk", "høy"), "pump": ("energisk", "høy"), "rask": ("energisk", "høy"),
    "mørk": ("mørk", "middels"), "dark": ("mørk", "middels"), "drøm": ("drømmende", "lav"), "dream": ("drømmende", "lav"),
    "romantisk": ("drømmende", "lav"), "romantic": ("drømmende", "lav"),
}


def _decade(t):
    m = re.search(r"\b(?:19|20)?([0-9])0[\s-]*(?:tallet|talls|s\b|'s)", t) or re.search(r"\b'([0-9])0s\b", t)
    if not m:
        m2 = re.search(r"\b(19[5-9]0|20[0-2]0)\b", t)
        return int(m2.group(1)) if m2 else None
    d = int(m.group(1))
    return 2000 + d * 10 if d <= 2 else 1900 + d * 10


def parse_rules(text):
    t = " " + (text or "").lower().strip() + " "
    out = {"genres": [], "moods": [], "energy": "", "decade": _decade(t), "language": "", "artists_like": [],
           "duration_min": None, "kilder": []}
    for k, g in _GENRES.items():
        if re.search(r"(?<![a-zæøå])" + re.escape(k), t) and g not in out["genres"]:
            out["genres"].append(g)
    for k, (mood, en) in _MOOD_WORDS.items():
        if k in t:
            if mood not in out["moods"]:
                out["moods"].append(mood)
            out["energy"] = out["energy"] or en
    if re.search(r"\b(norsk|norske|på norsk|norwegian)\b", t):
        out["language"] = "norsk"
    elif re.search(r"\b(engelsk|english)\b", t):
        out["language"] = "engelsk"
    m = re.search(r"(?:som|like|à la|a la)\s+([A-ZÆØÅa-zæøå0-9 .&'-]{2,40}?)(?:\s+(?:fra|i|på|til|for|og|from|in|for|and|with)\b|[,.!?]|$)", (text or "").strip())
    if m and not any(w in m.group(1).lower() for w in ("noe", "musikk")):
        out["artists_like"].append(m.group(1).strip())
    m = re.search(r"(\d+)\s*(?:min|minutter|minutes)", t)
    if m:
        out["duration_min"] = int(m.group(1))
    elif re.search(r"\b(en time|1 time|an hour)\b", t):
        out["duration_min"] = 60
    if re.search(r"\bradio\b", t):
        out["kilder"] = ["radio"]
    return out


# ---------------------------------------------------------------- LLM

def clean(d):
    """Valider/normaliser et (LLM-)svar til skjemaet. Ukjente felt kastes, feil typer blir tomme."""
    if isinstance(d, str):
        m = re.search(r"\{.*\}", d, re.S)
        try:
            d = json.loads(m.group(0)) if m else {}
        except Exception:
            d = {}
    d = d if isinstance(d, dict) else {}

    def strs(v):
        if isinstance(v, str):
            v = [v]
        return [str(x).strip() for x in v if str(x).strip()][:8] if isinstance(v, list) else []

    def num(v):
        try:
            return int(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None
    en = str(d.get("energy") or "").lower()
    en = {"low": "lav", "medium": "middels", "high": "høy"}.get(en, en)
    dec = num(d.get("decade"))
    if dec is not None and dec < 100:
        dec = 1900 + dec if dec >= 30 else 2000 + dec
    return {"genres": [g.lower() for g in strs(d.get("genres"))],
            "moods": [m for m in (x.lower() for x in strs(d.get("moods"))) if m in MOODS],
            "energy": en if en in ("lav", "middels", "høy") else "",
            "decade": dec - dec % 10 if dec else None,
            "language": str(d.get("language") or "").lower()[:20],
            "artists_like": strs(d.get("artists_like")),
            "duration_min": num(d.get("duration_min")),
            "kilder": [k for k in strs(d.get("kilder")) if k in KILDER]}


def _post(url, body, headers, timeout=30):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def anthropic_body(text, model):
    return {"model": model or DEFAULT_MODEL, "max_tokens": 400, "system": SYSTEM,
            "tools": [{"name": "musikksok", "description": "Strukturert musikksøk", "input_schema": SCHEMA}],
            "tool_choice": {"type": "tool", "name": "musikksok"},
            "messages": [{"role": "user", "content": text}]}


def parse_anthropic(res):
    for c in (res or {}).get("content") or []:
        if c.get("type") == "tool_use":
            return clean(c.get("input") or {})
    for c in (res or {}).get("content") or []:
        if c.get("type") == "text":
            return clean(c.get("text") or "")
    raise ValueError("tomt svar fra Anthropic")


def parse_ollama(res):
    return clean(((res or {}).get("message") or {}).get("content") or "")


class LLM:
    """Felles LLM-oppsett (brukes også av podkastsammendraget). Lagres i data_dir/ai.json."""

    def __init__(self, path, post=_post):
        self.path, self.post = path, post
        self.cfg = {"provider": "", "ollamaUrl": "http://localhost:11434", "ollamaModel": "llama3.2",
                    "anthropicKey": "", "anthropicModel": DEFAULT_MODEL}
        try:
            with open(path) as f:
                self.cfg.update(json.load(f))
        except Exception:
            pass

    def public(self):
        c = dict(self.cfg)
        c["anthropicKey"] = ("•••• " + c["anthropicKey"][-4:]) if c.get("anthropicKey") else ""
        c["hasKey"] = bool(self.cfg.get("anthropicKey"))
        return c

    def set(self, b):
        for k in ("provider", "ollamaUrl", "ollamaModel", "anthropicModel"):
            if k in b:
                self.cfg[k] = str(b[k] or "").strip()
        if b.get("anthropicKey") and "•" not in str(b["anthropicKey"]):
            self.cfg["anthropicKey"] = str(b["anthropicKey"]).strip()
        if b.get("clearKey"):
            self.cfg["anthropicKey"] = ""
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.cfg, f)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except OSError:
            pass
        return self.public()

    @property
    def enabled(self):
        p = self.cfg.get("provider")
        return p == "ollama" or (p == "anthropic" and bool(self.cfg.get("anthropicKey")))

    def chat(self, system, user, max_tokens=600, timeout=60):
        """Fritt tekstsvar (brukt til sammendrag)."""
        p = self.cfg.get("provider")
        if p == "anthropic" and self.cfg.get("anthropicKey"):
            res = self.post("https://api.anthropic.com/v1/messages",
                            {"model": self.cfg.get("anthropicModel") or DEFAULT_MODEL, "max_tokens": max_tokens,
                             "system": system, "messages": [{"role": "user", "content": user}]},
                            {"x-api-key": self.cfg["anthropicKey"], "anthropic-version": "2023-06-01"}, timeout)
            return "".join(c.get("text", "") for c in res.get("content") or [] if c.get("type") == "text").strip()
        if p == "ollama":
            res = self.post(self.cfg["ollamaUrl"].rstrip("/") + "/api/chat",
                            {"model": self.cfg.get("ollamaModel"), "stream": False,
                             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                            {}, timeout)
            return ((res.get("message") or {}).get("content") or "").strip()
        raise RuntimeError("ingen LLM satt opp")

    def interpret(self, text, timeout=25):
        p = self.cfg.get("provider")
        if p == "anthropic" and self.cfg.get("anthropicKey"):
            return parse_anthropic(self.post("https://api.anthropic.com/v1/messages",
                                             anthropic_body(text, self.cfg.get("anthropicModel")),
                                             {"x-api-key": self.cfg["anthropicKey"], "anthropic-version": "2023-06-01"},
                                             timeout))
        if p == "ollama":
            return parse_ollama(self.post(self.cfg["ollamaUrl"].rstrip("/") + "/api/chat",
                                          {"model": self.cfg.get("ollamaModel"), "stream": False, "format": "json",
                                           "messages": [{"role": "system", "content": SYSTEM + " Svar med JSON med feltene "
                                                         + ", ".join(SCHEMA["properties"]) + "."},
                                                        {"role": "user", "content": text}]}, {}, timeout))
        raise RuntimeError("ingen LLM satt opp")


def interpret(text, llm=None):
    """→ (spørring, «llm»/«regler»). LLM-feil faller stille tilbake til reglene; tomme LLM-felt fylles fra reglene."""
    rules = parse_rules(text)
    if llm is not None and llm.enabled:
        try:
            q = llm.interpret(text)
            for k, v in rules.items():
                if not q.get(k) and v:
                    q[k] = v
            return q, "llm"
        except Exception:
            pass
    return rules, "regler"


# ---------------------------------------------------------------- oppslag

def resolve(q, ctx):
    """Finn noe å spille. → {kind: smartradio|queue|radio, seed?, tracks?, station?, source} eller None."""
    kilder = q.get("kilder") or list(KILDER)
    lt = ctx.get("libtag")
    nd = ctx["subsonic"]() if ctx.get("subsonic") else None
    if "tags" in kilder and lt is not None and (q.get("moods") or q.get("energy") or q.get("decade")):
        try:
            hits = lt.store.search(mood=",".join(q["moods"]) or None, energy=q.get("energy") or None,
                                   genre=(q.get("genres") or [None])[0], decade=q.get("decade"), limit=40)
            if not hits and q.get("genres"):
                hits = lt.store.search(mood=",".join(q["moods"]) or None, energy=q.get("energy") or None, limit=40)
            if hits:
                h = hits[0]
                return {"kind": "smartradio", "source": "tags", "tracks": hits,
                        "seed": {"id": h.get("id"), "artist": h.get("artist"), "genre": h.get("genre"), "title": h.get("title")}}
        except Exception:
            pass
    if "navidrome" in kilder and nd:
        try:
            for a in q.get("artists_like") or []:
                r = nd._call("search3", query=a, artistCount=1, songCount=1, albumCount=0)
                arts = ((r or {}).get("searchResult3") or {}).get("artist") or []
                if arts:
                    return {"kind": "smartradio", "source": "navidrome", "seed": {"artist": arts[0].get("name")}}
            genres = {g.get("value", "").lower(): g.get("value") for g in
                      ((nd._call("getGenres") or {}).get("genres") or {}).get("genre") or []}
            for g in q.get("genres") or []:
                hit = genres.get(g) or next((v for k, v in genres.items() if g in k), None)
                if hit:
                    return {"kind": "smartradio", "source": "navidrome", "seed": {"genre": hit}}
        except Exception:
            pass
    if "ma" in kilder and ctx.get("ma") is not None and (q.get("artists_like") or q.get("genres")):
        return {"kind": "smartradio", "source": "ma",
                "seed": {"source": "ma", "artist": (q.get("artists_like") or [""])[0], "genre": (q.get("genres") or [""])[0]}}
    if "radio" in kilder and ctx.get("rb_list"):
        tag = (q.get("genres") or [None])[0] or {"rolig": "chillout", "glad": "pop", "trist": "ballads",
                                                  "energisk": "dance", "mørk": "darkwave", "drømmende": "ambient"}.get(
            (q.get("moods") or [""])[0])
        params = {"tag": tag} if tag else {}
        if q.get("language") == "norsk":
            params["countrycode"] = "NO"
        if q.get("decade"):
            params["tag"] = f"{str(q['decade'])[2:]}s" if not tag else tag
        try:
            st = ctx["rb_list"](params, 10) if params else []
            if st:
                return {"kind": "radio", "source": "radio", "station": st[0]}
        except Exception:
            pass
    return None


def describe(q):
    bits = q.get("moods", []) + q.get("genres", [])
    if q.get("energy"):
        bits.append(f"{q['energy']} energi")
    if q.get("decade"):
        bits.append(f"{str(q['decade'])[2:]}-tallet")
    if q.get("language"):
        bits.append(q["language"])
    if q.get("artists_like"):
        bits.append("som " + ", ".join(q["artists_like"]))
    return ", ".join(bits) or "noe tilfeldig"


def ask(text, ctx, llm=None, room=""):
    q, how = interpret(text, llm)
    r = resolve(q, ctx)
    out = {"ok": False, "query": q, "how": how, "summary": describe(q), "room": room}
    if not r:
        out["error"] = "Fant ikke noe som passet"
        return out
    out.update(ok=True, source=r["source"], kind=r["kind"])
    if r["kind"] == "radio":
        st = r["station"]
        ctx["play_url"](st["url"], st.get("name", ""), st.get("favicon", "") or st.get("image", ""), "")
        out["playing"] = st.get("name")
    else:
        sr = ctx.get("smartradio")
        try:
            if sr is None:
                raise RuntimeError("smart radio mangler")
            sr.start(r["seed"])
            out["playing"] = r["seed"].get("title") or r["seed"].get("artist") or r["seed"].get("genre")
        except Exception as e:
            # siste utvei: spill første tag-treff direkte
            tr = (r.get("tracks") or [None])[0]
            nd = ctx["subsonic"]() if ctx.get("subsonic") else None
            if tr and nd:
                from skjold_smartradio import nd_stream_url
                ctx["play_url"](nd_stream_url(nd, tr["id"]), f"{tr.get('artist', '')} – {tr.get('title', '')}", "", "")
                out["playing"] = tr.get("title")
            else:
                out.update(ok=False, error=str(e))
    return out


def routes(ctx):
    from aiohttp import web
    import asyncio
    llm = LLM(os.path.join(ctx.get("data_dir") or "/var/lib/ki-amp", "ai.json"))
    ctx["llm"] = llm
    lock = threading.Lock()

    async def h_ask(r):
        try:
            b = await r.json()
        except Exception:
            b = {}
        text = str(b.get("text") or "").strip()[:300]
        if not text:
            return web.json_response({"ok": False, "error": "skriv hva du vil høre"}, status=400)

        def run():
            with lock:
                return ask(text, ctx, llm, str(b.get("room") or ""))
        res = await asyncio.get_running_loop().run_in_executor(None, run)
        if res.get("ok") and ctx.get("toast"):
            try:
                ctx["toast"]("Spiller " + res["summary"], res.get("playing") or "")
            except Exception:
                pass
        return web.json_response(res)

    async def h_parse(r):
        b = await r.json()
        q, how = await asyncio.get_running_loop().run_in_executor(None, lambda: interpret(str(b.get("text") or ""), llm))
        return web.json_response({"query": q, "how": how, "summary": describe(q)})

    async def h_ai(r):
        if r.method == "POST":
            return web.json_response(llm.set(await r.json()))
        return web.json_response(llm.public())

    return [web.post("/api/ask", h_ask), web.post("/api/ask/parse", h_parse),
            web.get("/api/ai", h_ai), web.post("/api/ai", h_ai)]
