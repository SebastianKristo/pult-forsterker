"""Rekkefølge og synlighet for seksjonene på hjemskjermen (settings.homeLayout).

Lagres i innstillingene til hver Skjold-enhet, så oppsettet følger rommet (som «unik for hver kilde» i Plexamp)
og synkes mellom web-UI, iOS og Android på samme måte som andre innstillinger.
Format: [{"id": "<seksjon>", "visible": bool}, …] i ønsket rekkefølge. Ukjente id-er beholdes (nyere klienter kan
ha seksjoner denne versjonen ikke kjenner), duplikater fjernes, og klientene legger nye seksjoner til på slutten.
"""
import re

# Seksjonene klientene kjenner i dag, i standardrekkefølge (id, visningsnavn).
SECTIONS = [
    ("recent", "Nylig spilt"),
    ("favs", "Radiofavoritter"),
    ("sources", "Kilder"),
    ("routines", "Rutiner"),
    ("discover", "Oppdag"),
    ("ask", "Spill noe til …"),
    ("nrk", "Fortsett på NRK"),
    ("playlists", "Dine spillelister"),
    ("library", "Fra bibliotekene"),
    ("wrapped", "Skjold Wrapped"),
]
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
MAX_ITEMS = 40


def clean(v):
    """Validerer og normaliserer et homeLayout fra en klient. Ugyldig → [] (standardoppsett)."""
    if not isinstance(v, list):
        return []
    out, seen = [], set()
    for it in v[:MAX_ITEMS]:
        if isinstance(it, str):
            it = {"id": it, "visible": True}
        if not isinstance(it, dict):
            continue
        i = str(it.get("id") or "").strip().lower()
        if not _ID.match(i) or i in seen:
            continue
        seen.add(i)
        out.append({"id": i, "visible": it.get("visible", True) is not False})
    return out


def resolved(v, available=None):
    """Full liste i visningsrekkefølge: lagret rekkefølge først, så kjente seksjoner som mangler (synlige) på slutten.
    available: id-er klienten faktisk kan vise (None = alle kjente)."""
    known = [s for s, _ in SECTIONS] if available is None else list(available)
    lay = clean(v)
    out = [it for it in lay if it["id"] in known]
    have = {it["id"] for it in out}
    out += [{"id": s, "visible": True} for s in known if s not in have]
    return out
