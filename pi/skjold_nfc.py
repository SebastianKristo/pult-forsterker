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

HANDLINGER = ("preset", "play_url", "nrk", "ma_uri", "navidrome_album", "navidrome_playlist", "routine")
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
    if out["verdi"] in (None, "") and out["handling"] != "routine":
        raise ValueError("kassetten må ha noe å spille (verdi)")
    return out


def steps_for(card: dict) -> list[dict]:
    """Kassett → rutinesteg (samme format som skjold_routines). Rom: stegene gjentas per rom."""
    h, v = card["handling"], card["verdi"]
    typ = {"preset": "preset", "play_url": "play_url", "nrk": "nrk", "ma_uri": "ma",
           "navidrome_album": "nd_album", "navidrome_playlist": "nd_playlist"}[h]
    base: list[dict] = []
    if card.get("volum") is not None:
        base.append({"type": "volume", "verdi": card["volum"]})
    s = {"type": typ, "verdi": v}
    if h == "play_url":
        s["tittel"] = card.get("navn") or ""
    base.append(s)
    rom = card.get("rom") or []
    if not rom:
        return base
    return [{**x, "rom": r} for r in rom for x in base]


class NfcStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.learn_until = 0.0
        self.learn_draft: dict | None = None
        self.last = {"uid": "", "t": 0.0, "known": False, "navn": ""}
        self.active_uid = ""

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

    def scan(self, uid: str, current=None) -> dict:
        """Kassett satt inn. Returnerer {known, card, learned, steps}. current(): det som spiller nå (for lær-modus)."""
        k = norm_uid(uid)
        if self.learning():
            src = dict(self.learn_draft or {}) or (current() if current else {}) or {}
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
        return {"known": True, "learned": False, "card": card,
                "steps": [] if card["handling"] == "routine" else steps_for(card)}

    def removed(self, uid: str) -> dict:
        """Kassett tatt ut. Pause bare hvis det er kassetten som startet det som spiller nå."""
        k = norm_uid(uid)
        card = self.get(k)
        pause = bool(card and card.get("ved_uttak") == "pause" and self.active_uid == k)
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
