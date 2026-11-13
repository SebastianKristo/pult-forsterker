"""Skjold Kassett – NFC-kassetter som spiller noe på Skjold.

En kassett (NTAG215-brikke i en 3D-printet kassett) leses av en ESP32-S3 med PN532 (esphome/skjold-kassett.yaml),
som sender UID-en til POST /api/nfc/scan. Her ligger kartoteket UID → hva som skal skje, lær-modus («koble
kassetten til det som spiller nå») og omsetting til rutinesteg, så kassetter kan styre andre rom akkurat som rutiner.
Ren logikk uten avhengigheter til daemonen (testes i pi/tests/test_nfc.py)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import urllib.parse

HANDLINGER = ("preset", "play_url", "nrk", "ma_uri", "navidrome_album", "navidrome_playlist", "routine", "album")
UTTAK = ("pause", "ingenting")


def norm_uid(uid: str) -> str:
    """«04:a1:B2 c3» / «04A1B2C3» → «04-A1-B2-C3» (samme kassett gir samme nøkkel uansett leser)."""
    h = re.sub(r"[^0-9a-fA-F]", "", str(uid or "")).upper()
    if not h or len(h) % 2:
        raise ValueError("ugyldig UID")
    return "-".join(h[i:i + 2] for i in range(0, len(h), 2))


def clean_card(c: dict) -> dict:
    out = {"uid": norm_uid(c["uid"]), "navn": str(c.get("navn") or "Kassett")[:80],
           "handling": c.get("handling") or "preset", "verdi": c.get("verdi"),
           "rom": c.get("rom") or [], "volum": c.get("volum"), "ved_uttak": c.get("ved_uttak") or "ingenting",
           "omslag": str(c.get("omslag") or "")[:500], "undertittel": str(c.get("undertittel") or "")[:120]}
    if c.get("fra"):   # delt av en venn
        out["fra"] = str(c["fra"])[:60]
    if out["handling"] not in HANDLINGER:
        raise ValueError(f"ukjent handling «{out['handling']}»")
    if out["ved_uttak"] not in UTTAK:
        out["ved_uttak"] = "ingenting"
    if isinstance(out["rom"], str):
        out["rom"] = [r.strip() for r in out["rom"].split(",") if r.strip()]
    if out["volum"] in ("", None):
        out["volum"] = None
    else:
        out["volum"] = max(0, min(100, int(out["volum"])))
    if out["handling"] == "album":
        v = out["verdi"] if isinstance(out["verdi"], dict) else parse_album_line(str(out["verdi"] or ""))
        if not v or not str(v.get("album") or "").strip():
            raise ValueError("album-kassetten trenger et albumnavn")
        out["verdi"] = {"artist": str(v.get("artist") or "").strip()[:120], "album": str(v.get("album")).strip()[:160]}
        if v.get("spor"):
            out["verdi"]["spor"] = str(v["spor"]).strip()[:160]
        if out["navn"] in ("", "Kassett"):
            out["navn"] = out["verdi"]["album"][:80]
        if not out["undertittel"]:
            out["undertittel"] = out["verdi"]["artist"][:120]
        if not out["omslag"]:
            out["omslag"] = cover_path(out["verdi"]["artist"], out["verdi"]["album"])
        if isinstance(c.get("losning"), dict):
            out["losning"] = c["losning"]
        return out
    if out["verdi"] in (None, "") and out["handling"] != "routine":
        raise ValueError("kassetten må ha noe å spille (verdi)")
    return out


# ---------- album-kassetter: Navidrome hvis du har albumet, ellers YouTube Music (via Music Assistant) ----------
_SUFFIKS = re.compile(r"\s*[\(\[][^\)\]]*(remaster|deluxe|edition|expanded|anniversary|bonus|version|live)[^\)\]]*[\)\]]\s*", re.I)


def norm_navn(s: str) -> str:
    """Sammenlignbar form: små bokstaver, uten «(Remastered)»/«[Deluxe]», feat., tegnsetting og Λ/&/and-varianter."""
    t = str(s or "").lower().replace("λ", " ").replace("&", " ").replace(" and ", " ")
    t = _SUFFIKS.sub(" ", t)
    t = re.sub(r"\b(feat|ft|featuring)\.?\b.*$", " ", t)
    t = t.replace("æ", "ae").replace("ø", "o").replace("å", "a")
    return re.sub(r"[^a-z0-9]+", "", t)


def _artist_ok(want: str, have: str) -> bool:
    w, h = norm_navn(want), norm_navn(have)
    if not w:
        return True
    return w in h or h in w or any(norm_navn(x) and norm_navn(x) in w for x in re.split(r",|/|;|λ|&| x ", have or "", flags=re.I))


def clean_album(v) -> dict | None:
    if isinstance(v, str):
        v = parse_album_line(v)
    if not isinstance(v, dict) or not str(v.get("album") or "").strip():
        return None
    return {"artist": str(v.get("artist") or "").strip()[:120], "album": str(v["album"]).strip()[:160]}


def parse_album_line(line: str) -> dict | None:
    """«Artist - Album» (samme format som kabinett/kassett/album-eksempel.txt). «| …» bak ignoreres her."""
    s = str(line or "").split("|", 1)[0].strip()
    if not s or s.startswith("#"):
        return None
    if " - " in s:
        a, b = [x.strip() for x in s.split(" - ", 1)]
        return {"artist": a, "album": b}
    return {"artist": "", "album": s}


def cover_path(artist: str, album: str) -> str:
    return "/api/nfc/cover?" + urllib.parse.urlencode({"artist": artist or "", "album": album or ""})


def best_album(albums: list[dict], artist: str, album: str, name_key="name", artist_key="artist") -> dict | None:
    """Beste treff blant søkeresultater: albumnavnet må stemme (normalisert), artisten må passe hvis oppgitt."""
    want = norm_navn(album)
    exact, loose = [], []
    for a in albums or []:
        n = norm_navn(a.get(name_key) or "")
        if not n or not _artist_ok(artist, a.get(artist_key) or ""):
            continue
        if n == want:
            exact.append(a)
        elif want and (n.startswith(want) or want.startswith(n)):
            loose.append(a)
    return (exact or loose or [None])[0]


def resolve_album(artist: str, album: str, nd_search=None, ma_search=None, ytm_find=None) -> dict | None:
    """Finn albumet: 1) Navidrome (search3) → {"kilde":"navidrome","id"}; 2) YouTube Music innebygd (skjold_ytm) →
    {"kilde":"ytmusic","ytm_id"}; 3) Music Assistant → {"kilde":"ytmusic"|"ma","uri"} (bare som reserve).
    None = finnes ingen steder. ytm_find(artist, album) → treff eller None.
    nd_search(q) → liste av Subsonic-album {id,name,artist,coverArt}; ma_search(q) → liste av MA-album {uri,name,artist,provider,image}."""
    q = f"{artist} {album}".strip()
    if nd_search:
        try:
            hit = best_album(nd_search(q) or [], artist, album) or best_album(nd_search(album) or [], artist, album)
        except Exception:
            hit = None
        if hit:
            return {"kilde": "navidrome", "id": str(hit["id"]), "navn": hit.get("name", album), "artist": hit.get("artist", artist),
                    "cover_id": hit.get("coverArt") or hit["id"]}
    if ytm_find:
        try:
            hit = ytm_find(artist, album)
        except Exception:
            hit = None
        if hit:
            return hit
    if ma_search:
        try:
            res = ma_search(q) or []
        except Exception:
            res = []
        yt = [x for x in res if "youtube" in str(x.get("provider", "")).lower() or "ytmusic" in str(x.get("uri", "")).lower()]
        hit = best_album(yt, artist, album) or best_album([x for x in res if "subsonic" not in str(x.get("provider", "")).lower()], artist, album)
        if hit and hit.get("uri"):
            prov = str(hit.get("provider") or "")
            return {"kilde": "ytmusic" if hit in yt else "ma", "uri": hit["uri"], "navn": hit.get("name", album),
                    "artist": hit.get("artist", artist), "leverandor": prov, "image": hit.get("image", "")}
    return None


KILDE_NAVN = {"navidrome": "Navidrome", "ytmusic": "YouTube Music", "ma": "Music Assistant"}


def trenger_ny_losning(card: dict, now: float | None = None) -> bool:
    """Album-kassetten må slås opp: aldri gjort, eller forrige treff var ikke Navidrome og er over et døgn gammelt
    (kanskje du har lastet ned albumet siden)."""
    lo = card.get("losning") or {}
    if not lo.get("kilde"):
        return True
    if lo["kilde"] == "navidrome":
        return False
    return (now or time.time()) - float(lo.get("t", 0)) > 86400


def steps_for(card: dict, standard_rom: str = "") -> list[dict]:
    """Kassett → rutinesteg (samme format som skjold_routines). Rom: stegene gjentas per rom. standard_rom: den
    parede Skjold-enheten (Touch/Node/S1) – brukes når kassetten selv ikke har rom."""
    h, v = card["handling"], card["verdi"]
    if h == "album":
        lo = card.get("losning") or {}
        if lo.get("kilde") == "navidrome":
            h, v = "navidrome_album", lo["id"]
        elif lo.get("ytm_id"):
            h, v = "ytm_samling", lo["ytm_id"]
        elif lo.get("uri"):
            h, v = "ma_uri", lo["uri"]
        else:
            raise ValueError(f"fant ikke «{(v or {}).get('album', '')}» i Navidrome eller YouTube Music")
    typ = {"preset": "preset", "play_url": "play_url", "nrk": "nrk", "ma_uri": "ma", "ytm_samling": "ytm",
           "navidrome_album": "nd_album", "navidrome_playlist": "nd_playlist"}[h]
    base: list[dict] = []
    if card.get("volum") is not None:
        base.append({"type": "volume", "verdi": card["volum"]})
    s = {"type": typ, "verdi": v}
    if h == "play_url":
        s["tittel"] = card.get("navn") or ""
    base.append(s)
    rom = card.get("rom") or ([standard_rom] if standard_rom else [])
    if not rom:
        return base
    return [{**x, "rom": r} for r in rom for x in base]


# ---------- Kassett-Wrapped: logg over innsettinger og statistikk ----------
KILDE_KORT = {"navidrome": "Navidrome", "ma": "YouTube Music", "ytmusic": "YouTube Music"}


def kilde_for(card: dict) -> str:
    """Kort kildenavn for loggen: Navidrome / YouTube Music / radio / NRK / Music Assistant / rutine."""
    lo = card.get("losning") or {}
    if card.get("handling") == "album":
        k = lo.get("kilde") or ""
        return KILDE_KORT.get(k, "YouTube Music" if lo.get("uri") or lo.get("ytm_id") else "ukjent")
    return {"preset": "radio", "play_url": "radio", "nrk": "NRK", "ma_uri": "Music Assistant", "navidrome_album": "Navidrome",
            "navidrome_playlist": "Navidrome", "routine": "rutine"}.get(card.get("handling"), "annet")


class KassettLogg:
    """Rullerende logg over innsettinger: {u: uid, t: tid, n: navn, k: kilde, d: sekunder kassetten sto i}."""
    MAKS = 5000
    MAKS_VARIGHET = 6 * 3600   # glemt i spilleren over natta teller ikke som 12 timer lytting

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()

    def _les(self) -> list:
        try:
            with open(self.path) as fh:
                d = json.load(fh)
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def _skriv(self, d: list) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(d[-self.MAKS:], fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, self.path)

    def inn(self, uid: str, navn: str = "", kilde: str = "", now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self.lock:
            d = self._les()
            d.append({"u": uid, "t": int(now), "n": str(navn)[:80], "k": str(kilde)[:30]})
            self._skriv(d)

    def ut(self, uid: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self.lock:
            d = self._les()
            for e in reversed(d):
                if e.get("u") == uid and "d" not in e:
                    e["d"] = int(max(0, min(self.MAKS_VARIGHET, now - e.get("t", now))))
                    self._skriv(d)
                    return

    def hendelser(self) -> list:
        return self._les()


PERIODER = {"uke": 7, "mnd": 30, "år": 365, "aar": 365, "alt": None}


def kassett_stats(cards: dict, logg: list, periode: str = "år", glemt_uker: int = 8, now: float | None = None) -> dict:
    """Kassett-Wrapped: mest spilt, lyttetid, sist brukt, glemte kassetter og spilt per måned."""
    now = time.time() if now is None else now
    dager = PERIODER.get(periode, 365)
    fra = now - dager * 86400 if dager else 0
    sist_alle: dict = {}
    for e in logg:
        sist_alle[e.get("u")] = max(sist_alle.get(e.get("u"), 0), int(e.get("t", 0)))
    per: dict = {}
    mnd: dict = {}
    kilder: dict = {}
    for e in logg:
        t = int(e.get("t", 0))
        if t < fra:
            continue
        u = e.get("u")
        x = per.setdefault(u, {"uid": u, "spilt": 0, "lyttetid": 0, "kilder": {}})
        x["spilt"] += 1
        x["lyttetid"] += int(e.get("d") or 0)
        k = e.get("k") or "ukjent"
        x["kilder"][k] = x["kilder"].get(k, 0) + 1
        kilder[k] = kilder.get(k, 0) + 1
        m = time.strftime("%Y-%m", time.localtime(t))
        mnd[m] = mnd.get(m, 0) + 1

    def info(uid):
        c = cards.get(uid) or {}
        sist = sist_alle.get(uid) or c.get("sist") or 0
        return {"uid": uid, "navn": c.get("navn") or "(slettet kassett)", "undertittel": c.get("undertittel", ""),
                "omslag": c.get("omslag", ""), "laget": c.get("laget") or 0, "sist": sist, "finnes": bool(c),
                "fra": c.get("fra", "")}

    rader = []
    for uid, x in per.items():
        rader.append({**info(uid), "spilt": x["spilt"], "lyttetid": x["lyttetid"],
                      "kilde": max(x["kilder"], key=x["kilder"].get) if x["kilder"] else ""})
    rader.sort(key=lambda r: (-r["spilt"], -r["lyttetid"], -(r["sist"] or 0)))
    grense = now - max(1, int(glemt_uker)) * 7 * 86400
    glemte = []
    for uid, c in cards.items():
        sist = sist_alle.get(uid) or c.get("sist") or 0
        if (sist and sist < grense) or (not sist and (c.get("laget") or now) < grense):
            glemte.append({**info(uid), "uker_siden": int((now - (sist or c.get("laget") or now)) / (7 * 86400)),
                           "aldri": not sist})
    glemte.sort(key=lambda r: (r["sist"] or 0, r["laget"] or 0))
    aldri_brukt = [info(u) for u, c in cards.items() if not (sist_alle.get(u) or c.get("sist"))]
    return {"periode": periode if periode in PERIODER else "år", "glemt_uker": int(glemt_uker),
            "totalt": {"spilt": sum(r["spilt"] for r in rader), "lyttetid": sum(r["lyttetid"] for r in rader),
                       "kassetter": len(cards), "brukt": len(rader)},
            "topp": rader[:10], "alle": rader, "glemte": glemte[:30], "aldri_brukt": len(aldri_brukt),
            "per_maned": [{"mnd": k, "spilt": mnd[k]} for k in sorted(mnd)][-12:],
            "kilder": [{"kilde": k, "spilt": v} for k, v in sorted(kilder.items(), key=lambda kv: -kv[1])],
            "favoritt": rader[0] if rader else None}


# ---------- Del en kassett: kompakt delingskode (QR/lenke) ----------
DEL_SKJEMA = "skjold://kassett/del?d="
DEL_WEB = "https://skjold-lab.com/kassett/del#"
DELBAR = ("album", "play_url", "nrk", "ma_uri", "navidrome_album")


def til_deling(card: dict) -> dict | None:
    """Det som kan deles av en kassett: aldri Navidrome-ID-er, rom, passord eller lokale favorittnummer.
    Navidrome-album deles som artist + album, så mottakeren slår opp i sitt eget bibliotek (eller YouTube Music)."""
    h, v = card.get("handling"), card.get("verdi")
    base = {"navn": str(card.get("navn") or "")[:80], "undertittel": str(card.get("undertittel") or "")[:120]}
    if h == "album" and isinstance(v, dict):
        a = {"artist": v.get("artist", ""), "album": v.get("album", "")}
        if v.get("spor"):
            a["spor"] = v["spor"]
        return {**base, "handling": "album", "verdi": a}
    if h == "navidrome_album" and base["navn"]:
        return {**base, "handling": "album", "verdi": {"artist": base["undertittel"], "album": base["navn"]}}
    if h == "play_url" and isinstance(v, str) and re.match(r"^https?://", v) and not re.search(r"(u|p|t|s|token|key|pass)=", v, re.I):
        return {**base, "handling": "play_url", "verdi": v[:500]}
    if h == "nrk" and isinstance(v, str):
        return {**base, "handling": "nrk", "verdi": v[:120]}
    if h == "ma_uri" and isinstance(v, str) and not v.startswith(("library://", "filesystem")):
        return {**base, "handling": "ma_uri", "verdi": v[:300]}
    return None


def _b64u(b: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64u(s: str) -> bytes:
    import base64
    s = re.sub(r"[^A-Za-z0-9_-]", "", s)
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def del_kode(cards: list[dict], fra: str = "") -> dict:
    """Kassetter → {kode, lenke, web, delt, hoppet_over}. Koden er base64url(zlib(JSON)), kort nok for QR."""
    import zlib
    delt = [x for x in (til_deling(c) for c in cards) if x]
    if not delt:
        raise ValueError("ingen av kassettene kan deles (radiofavoritter, rutiner og Navidrome-spillelister er lokale)")
    raw = json.dumps({"v": 1, "fra": str(fra)[:60], "k": delt[:40]}, ensure_ascii=False, separators=(",", ":")).encode()
    kode = "1" + _b64u(zlib.compress(raw, 9))
    return {"kode": kode, "lenke": DEL_SKJEMA + kode, "web": DEL_WEB + kode, "delt": len(delt[:40]),
            "hoppet_over": len(cards) - len(delt[:40])}


def les_kode(tekst: str) -> dict:
    """Delingskode eller lenke → {fra, kassetter}. Godtar skjold://…?d=, https://…#, og koden alene."""
    import zlib
    t = str(tekst or "").strip()
    m = re.search(r"[?&]d=([A-Za-z0-9_-]+)", t) or re.search(r"#([A-Za-z0-9_-]+)\s*$", t)
    kode = m.group(1) if m else t
    if not kode.startswith("1") or len(kode) < 8 or len(kode) > 20000:
        raise ValueError("ukjent delingskode")
    try:
        d = json.loads(zlib.decompress(_unb64u(kode[1:]), bufsize=65536))
    except Exception:
        raise ValueError("delingskoden er ødelagt eller ufullstendig")
    out = []
    for k in (d.get("k") or [])[:40]:
        try:
            c = clean_ventende(k)
        except Exception:
            c = None
        if c:
            out.append(c)
    return {"fra": str(d.get("fra") or "")[:60], "kassetter": out}


# ---------- deling via Skjold Cloud: kryptert «postkasse» med utløp ----------
# Innholdet krypteres på enheten med en tilfeldig nøkkel som bare står i delingskoden (S<id>.<nøkkel>). Skyen lagrer
# bare den krypterte blobben i 14 dager og kan ikke lese den – som resten av Skjold Cloud, men uten at sender og
# mottaker må dele konto eller frase. Koden er kort (fin i QR/melding) selv om innholdet er stort.
def sky_pakk(cards: list[dict], fra: str = "") -> tuple[str, bytes, int]:
    import base64, secrets
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    delt = [x for x in (til_deling(c) for c in cards) if x]
    if not delt:
        raise ValueError("ingen av kassettene kan deles (radiofavoritter, rutiner og Navidrome-spillelister er lokale)")
    raw = json.dumps({"v": 1, "fra": str(fra)[:60], "k": delt[:40]}, ensure_ascii=False, separators=(",", ":")).encode()
    key, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    blob = base64.b64encode(b"\x01" + nonce + AESGCM(key).encrypt(nonce, raw, b"skjold-kassett")).decode()
    return blob, key, len(delt[:40])


def sky_kode(del_id: str, key: bytes) -> dict:
    kode = "S" + del_id + "." + _b64u(key)
    return {"kode": kode, "lenke": DEL_SKJEMA + kode, "web": DEL_WEB + kode}


def er_sky_kode(tekst: str) -> str:
    """Returnerer «S<id>.<nøkkel>» hvis teksten er (eller inneholder) en Skjold Cloud-delingskode, ellers ""."""
    m = re.search(r"(?:^|[?&#=])(S[a-z0-9]{8,16}\.[A-Za-z0-9_-]{16,32})\s*$", str(tekst or "").strip())
    return m.group(1) if m else ""


def sky_les(kode: str, hent) -> dict:
    """S<id>.<nøkkel> → {fra, kassetter}. hent(id) → base64-blob fra skyen (GET /del/<id>)."""
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    m = re.match(r"^S([a-z0-9]{8,16})\.([A-Za-z0-9_-]{16,32})$", kode)
    if not m:
        raise ValueError("ukjent delingskode")
    raw = base64.b64decode(hent(m.group(1)))
    if raw[:1] != b"\x01":
        raise ValueError("ukjent format")
    try:
        d = json.loads(AESGCM(_unb64u(m.group(2))).decrypt(raw[1:13], raw[13:], b"skjold-kassett"))
    except Exception:
        raise ValueError("delingskoden passer ikke (feil nøkkel eller utløpt)")
    return {"fra": str(d.get("fra") or "")[:60], "kassetter": [x for x in (clean_ventende(k) for k in (d.get("k") or [])[:40]) if x]}


def clean_ventende(v) -> dict | None:
    """En ventende kassett: enten et album {artist, album} (import) eller en delt kassett {handling, verdi, navn …}."""
    if not isinstance(v, dict):
        return clean_album(v)
    if not v.get("handling"):
        return clean_album(v)
    if v["handling"] not in DELBAR:
        return None
    try:
        c = clean_card({**v, "uid": "00"})
    except Exception:
        return None
    out = {"handling": c["handling"], "verdi": c["verdi"], "navn": c["navn"], "undertittel": c["undertittel"]}
    if v.get("fra"):
        out["fra"] = str(v["fra"])[:60]
    if c.get("omslag") and c["handling"] == "album":
        out["omslag"] = c["omslag"]
    return out


def _ventende_nokkel(v: dict) -> tuple:
    if v.get("handling") in (None, "album"):
        a = v.get("verdi") if isinstance(v.get("verdi"), dict) else v
        return ("album", norm_navn(a.get("artist", "")), norm_navn(a.get("album", "")))
    return (v["handling"], str(v.get("verdi")))


class NfcStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.learn_until = 0.0
        self.learn_draft: dict | None = None
        self.last = {"uid": "", "t": 0.0, "known": False, "navn": ""}
        self.active_uid = ""
        self.ekstra_path = os.path.join(os.path.dirname(path) or ".", "kassett_oppsett.json")
        self.logg = KassettLogg(os.path.join(os.path.dirname(path) or ".", "kassett_logg.json"))

    # ---------- ventende album (import) og paring ----------
    def _ekstra(self) -> dict:
        try:
            with open(self.ekstra_path) as fh:
                d = json.load(fh)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _lagre_ekstra(self, d: dict) -> None:
        os.makedirs(os.path.dirname(self.ekstra_path) or ".", exist_ok=True)
        tmp = self.ekstra_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ekstra_path)

    def oppsett(self) -> dict:
        d = self._ekstra()
        return {"ventende": d.get("ventende") or [], "paret": d.get("paret") or "",
                "koble_ventende": d.get("koble_ventende", True)}

    def sett_oppsett(self, b: dict) -> dict:
        with self.lock:
            d = self._ekstra()
            if "paret" in b:
                d["paret"] = str(b.get("paret") or "")[:60]
            if "koble_ventende" in b:
                d["koble_ventende"] = bool(b["koble_ventende"])
            if "ventende" in b and isinstance(b["ventende"], list):
                d["ventende"] = [x for x in (clean_ventende(v) for v in b["ventende"]) if x][:200]
            self._lagre_ekstra(d)
        return self.oppsett()

    def importer(self, tekst: str) -> dict:
        """Linjer «Artist - Album» → ventende album-kassetter (kobles til de neste nye brikkene som settes inn)."""
        nye = [x for x in (parse_album_line(l) for l in str(tekst or "").splitlines()) if x and x.get("album")]
        with self.lock:
            d = self._ekstra()
            have = {_ventende_nokkel(v) for v in d.get("ventende") or []}
            have |= {_ventende_nokkel(c) for c in self.load().values() if c.get("handling") == "album"}
            lagt = []
            for v in nye:
                key = _ventende_nokkel(v)
                if key not in have:
                    have.add(key); lagt.append(v)
            d["ventende"] = (d.get("ventende") or []) + lagt
            self._lagre_ekstra(d)
        return {"lagt_til": len(lagt), "hoppet_over": len(nye) - len(lagt), **self.oppsett()}

    def importer_deling(self, tekst: str, fra: str = "") -> dict:
        """Delingskode/lenke (QR) eller innhold fra Skjold Cloud → ventende kassetter med «fra <navn>»."""
        if isinstance(tekst, dict):          # allerede dekodet (f.eks. fra Skjold Cloud)
            d = tekst
        elif isinstance(tekst, str):
            d = les_kode(tekst)
        else:
            d = {"fra": fra, "kassetter": [x for x in (clean_ventende(k) for k in tekst) if x]}
        avsender = (fra or d.get("fra") or "").strip()[:60]
        with self.lock:
            e = self._ekstra()
            have = {_ventende_nokkel(v) for v in e.get("ventende") or []}
            have |= {_ventende_nokkel(c) for c in self.load().values() if c.get("handling") in DELBAR}
            lagt = []
            for k in d["kassetter"]:
                if avsender:
                    k = {**k, "fra": avsender}
                key = _ventende_nokkel(k)
                if key not in have:
                    have.add(key); lagt.append(k)
            e["ventende"] = (e.get("ventende") or []) + lagt
            self._lagre_ekstra(e)
        return {"lagt_til": len(lagt), "hoppet_over": len(d["kassetter"]) - len(lagt), "fra": avsender,
                "nye": lagt, **self.oppsett()}

    def stats(self, periode: str = "år", glemt_uker: int = 8, now: float | None = None) -> dict:
        return kassett_stats(self.load(), self.logg.hendelser(), periode, glemt_uker, now)

    def _ta_ventende(self) -> dict | None:
        with self.lock:
            d = self._ekstra()
            if not d.get("koble_ventende", True) or not d.get("ventende"):
                return None
            v = d["ventende"].pop(0)
            self._lagre_ekstra(d)
            return v

    def load(self) -> dict:
        try:
            with open(self.path) as fh:
                d = json.load(fh)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def _save(self, cards: dict) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(cards, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def list(self) -> list[dict]:
        return sorted(self.load().values(), key=lambda c: c.get("navn", "").lower())

    def put(self, c: dict) -> dict:
        card = clean_card(c)
        with self.lock:
            cards = self.load()
            old = cards.get(card["uid"]) or {}
            card["laget"] = old.get("laget") or int(time.time())
            card["spilt"] = old.get("spilt", 0)
            cards[card["uid"]] = card
            self._save(cards)
        return card

    def delete(self, uid: str) -> bool:
        k = norm_uid(uid)
        with self.lock:
            cards = self.load()
            ok = cards.pop(k, None) is not None
            self._save(cards)
        return ok

    def get(self, uid: str) -> dict | None:
        return self.load().get(norm_uid(uid))

    # ---------- lær-modus ----------
    def learn(self, timeout: float = 30, draft: dict | None = None) -> dict:
        self.learn_until = time.time() + max(5.0, min(300.0, float(timeout or 30)))
        self.learn_draft = draft or None
        return {"learning": True, "until": self.learn_until}

    def learning(self) -> bool:
        return time.time() < self.learn_until

    def scan(self, uid: str, current=None, resolve=None, standard_rom: str = "") -> dict:
        """Kassett satt inn. Returnerer {known, card, learned, steps}. current(): det som spiller nå (for lær-modus).
        resolve(card) → card: slår opp album-kassetter (Navidrome/YouTube Music). standard_rom: paret Skjold-enhet.
        Ukjent brikke + ventende album (fra import) → brikken blir neste ventende album."""
        k = norm_uid(uid)
        if not self.learning() and not self.get(k):
            v = self._ta_ventende()
            if v and v.get("handling"):   # delt kassett (QR/lenke/Skjold Cloud)
                self.put({**v, "uid": k})
            elif v:
                self.put({"uid": k, "handling": "album", "verdi": v, "navn": v["album"], "undertittel": v["artist"]})
        if self.learning():
            draft = dict(self.learn_draft or {})
            src = draft
            if not draft.get("handling"):  # bare rom/volum/navn: resten hentes fra det som spiller nå
                cur = (current() if current else None) or {}
                src = {**cur, **draft} if cur else {}
            if not src:
                raise ValueError("ingenting spiller – start noe først, eller velg hva kassetten skal spille")
            src["uid"] = k
            card = self.put(src)
            self.learn_until = 0.0; self.learn_draft = None
            self.last = {"uid": k, "t": time.time(), "known": True, "navn": card["navn"]}
            return {"known": True, "learned": True, "card": card, "steps": []}
        card = self.get(k)
        self.last = {"uid": k, "t": time.time(), "known": bool(card), "navn": (card or {}).get("navn", "")}
        if not card:
            return {"known": False, "learned": False, "card": None, "steps": []}
        with self.lock:
            cards = self.load()
            if k in cards:
                cards[k]["spilt"] = int(cards[k].get("spilt", 0)) + 1
                cards[k]["sist"] = int(time.time())
                self._save(cards)
        self.active_uid = k
        if card["handling"] == "album" and resolve:
            card = resolve(card)
        try:
            self.logg.inn(k, card.get("navn", ""), kilde_for(card))
        except Exception:
            pass
        try:
            steps = [] if card["handling"] == "routine" else steps_for(card, standard_rom)
        except ValueError as e:   # album som ikke finnes noe sted: kassetten er kjent, men har ingenting å spille
            return {"known": True, "learned": False, "card": card, "steps": [], "feil": str(e)}
        return {"known": True, "learned": False, "card": card, "steps": steps}

    def lagre_losning(self, uid: str, losning: dict | None) -> dict | None:
        k = norm_uid(uid)
        with self.lock:
            cards = self.load()
            if k not in cards:
                return None
            if losning:
                cards[k]["losning"] = {**losning, "t": int(time.time())}
            else:
                cards[k].pop("losning", None)
            self._save(cards)
            return cards[k]

    def removed(self, uid: str) -> dict:
        """Kassett tatt ut. Pause bare hvis det er kassetten som startet det som spiller nå."""
        k = norm_uid(uid)
        card = self.get(k)
        pause = bool(card and card.get("ved_uttak") == "pause" and self.active_uid == k)
        try:
            self.logg.ut(k)
        except Exception:
            pass
        if self.active_uid == k:
            self.active_uid = ""
        return {"pause": pause}


def current_to_card(state: dict, radio_now: dict | None, last_play: dict | None) -> dict:
    """Det som spiller nå → kassettutkast (lær-modus)."""
    rn = radio_now or {}
    lp = last_play or {}
    if state.get("input") == "radio" and rn.get("n"):
        return {"navn": rn.get("name") or f"Radiofavoritt {rn['n']}", "handling": "preset", "verdi": int(rn["n"]),
                "omslag": rn.get("logo") or rn.get("image") or "", "undertittel": "Radio"}
    url = lp.get("url") or rn.get("url")
    if url:
        return {"navn": lp.get("album") or lp.get("title") or rn.get("name") or "Kassett", "handling": "play_url", "verdi": url,
                "omslag": lp.get("art") or rn.get("image") or "", "undertittel": lp.get("artist") or ""}
    return {}


def subsonic_tracks(url: str, user: str, pw: str, kind: str, item_id: str, opener) -> list[dict]:
    """Navidrome-album eller -spilleliste → låter med strøm-URL (Subsonic stream med token-innlogging)."""
    def q(**extra):
        salt = secrets.token_hex(6)
        p = {"u": user, "t": hashlib.md5((pw + salt).encode()).hexdigest(), "s": salt, "v": "1.16.1", "c": "skjold", "f": "json"}
        p.update(extra)
        return urllib.parse.urlencode(p)
    base = url.rstrip("/")
    method = "getAlbum" if kind == "album" else "getPlaylist"
    d = opener(f"{base}/rest/{method}.view?" + q(id=item_id)).get("subsonic-response") or {}
    if d.get("status") != "ok":
        raise RuntimeError("Navidrome: " + str((d.get("error") or {}).get("message") or "feil"))
    holder = d.get("album") or d.get("playlist") or {}
    songs = holder.get("song") or holder.get("entry") or []
    out = []
    for s in songs:
        out.append({"url": f"{base}/rest/stream.view?" + q(id=s["id"], format="mp3", maxBitRate=320),
                    "title": s.get("title", ""), "artist": s.get("artist", ""), "album": s.get("album", holder.get("name", "")),
                    "cover": f"{base}/rest/getCoverArt.view?" + q(id=s.get("coverArt") or s["id"], size=300)})
    return out


def subsonic_cover_url(url: str, user: str, pw: str, cover_id: str, size: int = 600) -> str:
    salt = secrets.token_hex(6)
    p = {"u": user, "t": hashlib.md5((pw + salt).encode()).hexdigest(), "s": salt, "v": "1.16.1", "c": "skjold", "f": "json",
         "id": cover_id, "size": size}
    return f"{url.rstrip('/')}/rest/getCoverArt.view?" + urllib.parse.urlencode(p)


# ---------- «Lag kassett»: NDEF-lenke og ferdige etiketter ----------
NDEF_PREFIX = "skjold://kassett/"
# Samme mål som kabinett/kassett/lag_etiketter.py (43,2 × 51,2 mm, 3 × 5 på A4) – kuttlinjene passer forsenkningen.
LBL_W, LBL_H, LBL_R, LBL_COLS, LBL_ROWS, LBL_GX, LBL_GY = 43.2, 51.2, 2.0, 3, 5, 8.0, 4.0
A4_W, A4_H = 210.0, 297.0


def ndef_url(uid: str) -> str:
    """URI-posten telefonen skriver på brikken. Leseren bruker bare UID-en; lenken lar en telefon som holdes mot
    kassetten åpne den i Skjold-appen."""
    return NDEF_PREFIX + norm_uid(uid)


def uid_from_ndef(text: str) -> str:
    t = str(text or "").strip()
    if t.lower().startswith(NDEF_PREFIX):
        t = t[len(NDEF_PREFIX):]
    return norm_uid(t)


def _esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _clip(s: str, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def label_sheet_svg(cards: list[dict], image=None, start: int = 0, cut: bool = True) -> str:
    """A4-ark med ferdige etiketter (cover, tittel, undertittel). image(url) → data-URI eller None (cover bakes inn,
    så arket kan skrives ut/deles uten nett). start: hopp over så mange ruter (for et delvis brukt ark)."""
    mx = (A4_W - LBL_COLS * LBL_W - (LBL_COLS - 1) * LBL_GX) / 2
    my = (A4_H - LBL_ROWS * LBL_H - (LBL_ROWS - 1) * LBL_GY) / 2
    per = LBL_COLS * LBL_ROWS
    start = max(0, min(per - 1, int(start or 0)))
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_W}mm" height="{A4_H}mm" viewBox="0 0 {A4_W} {A4_H}">',
         '<style>.k{fill:none;stroke:#e0451b;stroke-width:.2}.t{font-family:Sora,Helvetica,Arial,sans-serif}</style>',
         f'<text x="{mx}" y="{my-4}" font-size="3" fill="#8b8b86" class="t">SKJOLD KASSETT · {len(cards)} etikett'
         f'{"er" if len(cards) != 1 else ""} · rød linje = kutt</text>']
    sz = LBL_W - 6
    for i, c in enumerate(cards[: per - start]):
        r, k = divmod(i + start, LBL_COLS)
        x, y = mx + k * (LBL_W + LBL_GX), my + r * (LBL_H + LBL_GY)
        src = image(c.get("omslag")) if (image and c.get("omslag")) else None
        cid = f"c{i}"
        p.append(f'<g transform="translate({x:.2f},{y:.2f})">'
                 f'<rect width="{LBL_W}" height="{LBL_H}" rx="{LBL_R}" fill="#f6f3ee"/>'
                 f'<clipPath id="{cid}"><rect x="3" y="3" width="{sz}" height="{sz}" rx="1.2"/></clipPath>')
        if src:
            p.append(f'<image href="{_esc(src)}" x="3" y="3" width="{sz}" height="{sz}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')
        else:
            p.append(f'<rect x="3" y="3" width="{sz}" height="{sz}" rx="1.2" fill="#141415"/>'
                     f'<text x="{LBL_W/2}" y="{3+sz/2+1.5}" font-size="4.2" font-weight="700" letter-spacing="1.2" fill="#e8b04a" '
                     f'text-anchor="middle" class="t">{_esc(_clip(c.get("navn"), 14).upper())}</text>')
        p.append(f'<text x="3" y="{LBL_W+1.6}" font-size="3.2" font-weight="600" class="t" fill="#1b1b1c">{_esc(_clip(c.get("navn"), 24))}</text>'
                 f'<text x="3" y="{LBL_W+5.4}" font-size="2.4" class="t" fill="#6a6a65">{_esc(_clip(c.get("undertittel"), 34))}</text>'
                 f'<text x="{LBL_W-3}" y="{LBL_H-2}" font-size="1.8" class="t" fill="#b0aca4" text-anchor="end" letter-spacing=".4">SKJOLD</text>')
        if cut:
            p.append(f'<rect class="k" width="{LBL_W}" height="{LBL_H}" rx="{LBL_R}"/>')
        p.append('</g>')
    p.append('</svg>')
    return "\n".join(p)


class Spoler:
    """Spolene i Kassett-spillerens vindu: hva motoren skal gjøre, ut fra det som spilles.

    ESP-en (esphome/skjold-kassett.yaml) spør GET /api/nfc/spoler et par ganger i sekundet og får
    {"modus": "spill"|"spol"|"tilbake"|"stopp", "rps": omdreininger/s, "retning": 1|-1}. Den står selv for myk
    akselerasjon. Hopp i låten (posisjonen flytter seg mer enn forventet) og ny låt gir et kort «spol» fremover
    (eller «tilbake» ved hopp bakover), som på en ekte kassettspiller. Innstillingene lagres i en liten JSON-fil."""

    STD = {"på": True, "fart": 0.5, "spol": 1.6, "bare_kassett": True, "vent": 2.5}
    SPOL_TID = 1.4      # sekunder med spoling ved hopp eller ny låt
    HOPP = 4.0          # avvik (s) i posisjon som regnes som hopp

    def __init__(self, path: str | None = None):
        self.path = path
        self.cfg = dict(self.STD)
        self._last: tuple | None = None   # (tid, posisjon, tittel)
        self._spol_til = 0.0
        self._spol_retning = 1
        self._tvang_til = 0.0    # neste/forrige fra app/Touch: spol fysisk før låten byttes (også mens lyden står)
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.cfg.update({k: v for k, v in json.load(f).items() if k in self.STD})
            except Exception:
                pass

    def sett(self, b: dict) -> dict:
        if "på" in b:
            self.cfg["på"] = bool(b["på"])
        if "bare_kassett" in b:
            self.cfg["bare_kassett"] = bool(b["bare_kassett"])
        for k, lo, hi in (("fart", 0.1, 1.5), ("spol", 0.5, 3.0), ("vent", 0.0, 6.0)):
            if k in b and b[k] is not None:
                self.cfg[k] = round(max(lo, min(hi, float(b[k]))), 2)
        if self.path:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.cfg, f)
            os.replace(tmp, self.path)
        return dict(self.cfg)

    def hent_hopp(self):
        """(retning, sekunder hoppet) for et nytt hopp i låten, eller None. Nullstilles når den er hentet."""
        h, self._hopp = getattr(self, "_hopp", None), None
        return h

    def spoletid(self, hopp_s: float) -> float:
        """Hvor lenge spolene skal spole for et hopp: lengre hopp = lengre spoling, maks «vent»."""
        vent = float(self.cfg.get("vent", 0) or 0)
        return round(min(vent, max(1.0, vent * min(1.0, 0.35 + hopp_s / 120.0))), 2) if vent > 0 else 0.0

    def skal_vente(self, kassett_inne: bool) -> float:
        """Sekunder å spole fysisk ved neste/forrige (0 = ikke vent)."""
        if not self.cfg["på"] or (self.cfg["bare_kassett"] and not kassett_inne):
            return 0.0
        return float(self.cfg.get("vent", 0) or 0)

    def tving(self, retning: int, sek: float, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._tvang_til, self._spol_retning = now + sek, (1 if retning >= 0 else -1)
        self._spol_til = 0.0   # ikke legg på en ekstra auto-spoling når den nye låten starter

    def status(self, st: dict, kassett_inne: bool, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        if now < self._tvang_til and self.cfg["på"]:
            self._last = None
            return {"modus": "spol" if self._spol_retning > 0 else "tilbake", "rps": self.cfg["spol"],
                    "retning": self._spol_retning, **self.cfg}
        playing = bool(st.get("playing")) and not st.get("paused")
        pos = float(st.get("position") or 0)
        tittel = str(st.get("title") or "")
        last, self._last = self._last, (now, pos, tittel) if playing else None
        if not self.cfg["på"] or (self.cfg["bare_kassett"] and not kassett_inne) or not playing:
            self._spol_til = 0.0
            return {"modus": "stopp", "rps": 0.0, "retning": 1, **self.cfg}
        if last:
            t0, p0, tit0 = last
            forventet = p0 + (now - t0)
            if tit0 and tittel and tittel != tit0:
                self._spol_til, self._spol_retning = now + self.SPOL_TID, 1
            elif pos and abs(pos - forventet) > self.HOPP:
                self._spol_til, self._spol_retning = now + self.SPOL_TID, (1 if pos > forventet else -1)
                # Spoling i låten (f.eks. fra Touch/Lyrion: 0:10 → 1:22). Daemonen kan da sette lyden på pause og la
                # spolene spole fysisk før den spiller videre – se hent_hopp().
                if self.skal_vente(kassett_inne) > 0:
                    self._hopp = (self._spol_retning, abs(pos - forventet))
        if now < self._spol_til:
            return {"modus": "spol" if self._spol_retning > 0 else "tilbake", "rps": self.cfg["spol"],
                    "retning": self._spol_retning, **self.cfg}
        return {"modus": "spill", "rps": self.cfg["fart"], "retning": 1, **self.cfg}
