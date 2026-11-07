"""Køhistorikk: «Hva spilte i stua i går kveld?»

Bygger på lyttehistorikken (history.json – pluginen «Lyttehistorikk» må være på). Hver oppføring har nå også rom
(enhetens navn), kilde og strøm-URL når den finnes, så den kan spilles igjen.

GET  /api/qhist?dag=YYYY-MM-DD&fra=HH:MM&til=HH:MM&rom=&alle=1   → {rom: [...], økter: [{rom, start, slutt, spor: [...]}]}
     alle=1 henter også fra de andre Skjold-enhetene i huset (samme API på hver enhet, uten alle=1).
POST /api/qhist/spill {spor: [{…}], rom?}  → spill sporene igjen som kø (her, eller på et annet rom)
"""
import time

OKT_PAUSE_S = 45 * 60      # mer enn 45 min mellom to spor = ny økt


def _hm(s, default):
    try:
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return default


def filtrer(items, dag=None, fra=None, til=None, rom=None, tz_offset_s=None):
    """Filtrer historikk på dato (lokal tid), tidsrom (fra/til kan gå over midnatt, f.eks. 18:00–02:00) og rom."""
    lo, hi = _hm(fra, 0), _hm(til, 24 * 60)
    out = []
    for e in items:
        t = float(e.get("t") or 0)
        lt = time.localtime(t) if tz_offset_s is None else time.gmtime(t + tz_offset_s)
        mins = lt.tm_hour * 60 + lt.tm_min
        day = "%04d-%02d-%02d" % (lt.tm_year, lt.tm_mon, lt.tm_mday)
        if rom and str(e.get("rom") or "") != rom:
            continue
        if lo <= hi:
            if not (lo <= mins < hi):
                continue
            if dag and day != dag:
                continue
        else:   # kveld over midnatt: fra 18:00 på dagen til 02:00 dagen etter
            if dag:
                prev = time.strftime("%Y-%m-%d", time.localtime(t - 86400) if tz_offset_s is None else time.gmtime(t - 86400 + tz_offset_s))
                if not ((day == dag and mins >= lo) or (prev == dag and mins < hi)):
                    continue
            elif not (mins >= lo or mins < hi):
                continue
        out.append(e)
    return sorted(out, key=lambda e: float(e.get("t") or 0))


def okter(items, pause_s=OKT_PAUSE_S):
    """Del i økter per rom: sammenhengende lytting uten lengre pauser."""
    per_rom = {}
    for e in sorted(items, key=lambda e: float(e.get("t") or 0)):
        per_rom.setdefault(str(e.get("rom") or ""), []).append(e)
    res = []
    for rom, lst in per_rom.items():
        cur = None
        for e in lst:
            t = float(e.get("t") or 0)
            if cur and t - cur["slutt"] <= pause_s:
                cur["spor"].append(e); cur["slutt"] = t
            else:
                cur = {"rom": rom, "start": t, "slutt": t, "spor": [e]}
                res.append(cur)
    return sorted(res, key=lambda o: o["start"])


def spillbar(e):
    """Hva som trengs for å spille oppføringen igjen: {url} for strøm/kanal, ellers {artist, tittel} for søk."""
    if e.get("input") != "radio" and e.get("title") and e.get("artist"):
        return {"type": "sok", "artist": e.get("artist") or "", "tittel": e.get("title") or "", "album": e.get("album") or "",
                "url": e.get("url") or ""}
    if e.get("url") and str(e["url"]).startswith(("http://", "https://")):
        return {"type": "url", "url": e["url"], "tittel": e.get("station") or e.get("title") or "", "cover": e.get("cover") or ""}
    if e.get("title"):
        return {"type": "sok", "artist": e.get("artist") or "", "tittel": e.get("title") or "", "album": e.get("album") or ""}
    return None


def unike_spor(spor):
    """Fjern direkte gjentakelser (samme radiokanal logget flere ganger på rad)."""
    out, last = [], None
    for e in spor:
        # radio: samme kanal = én oppføring (låtene på kanalen kan ikke spilles igjen enkeltvis)
        k = ("radio", e.get("url")) if e.get("input") == "radio" and e.get("url") else (e.get("url") or "", e.get("title") or "", e.get("artist") or "")
        if k != last:
            out.append(e)
        last = k
    return out
