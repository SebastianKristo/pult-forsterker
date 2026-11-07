"""Rene hjelpere for Skjold-kortet i dashbordet (ingen Home Assistant-import, så de kan testes alene)."""
from __future__ import annotations

import re

# Samme forhåndsinnstillinger som web-appen (skjold/app/src/lib/settings.ts EQ.presets) – rekkefølgen er indeksen
# som lagres i settings.eq[kilde].preset.
EQ_PRESETS: list[tuple[str, list[int]]] = [
    ("Flat", [0, 0, 0, 0, 0]), ("Bass+", [5, 2, 0, 0, 1]), ("Vokal", [-2, -1, 2, 3, 1]),
    ("Kveld", [2, 1, 0, -2, -3]), ("Podkast", [-5, -1, 3, 3, -2]), ("Klassisk", [1, 0, 0, 1, 2]),
    ("Rock", [4, 1, -2, 2, 3]), ("Pop", [2, 0, 1, 2, 2]), ("Elektronisk", [6, 1, -1, 1, 3]),
    ("Hip-hop", [6, 3, -1, 1, 1]), ("Jazz", [2, 1, -1, 1, 2]), ("Akustisk", [1, 2, 0, 2, 2]),
    ("Små høyttalere", [-4, 2, 1, 1, 0]), ("Lavt volum", [4, 1, -1, 1, 3]),
]
# Inngang → EQ-profilnøkkel (som EQ_SRC i daemonen; hodetelefoner har egen profil «hp»)
EQ_SRC = {"airplay": "air", "bt": "bt", "radio": "radio", "aux": "aux", "aux2": "aux", "usb": "usb"}
_KEY = re.compile(r"^[0-9a-f]{16}$")
LOGO_URL = "/api/skjold_logo/{entry_id}?k={k}"


def eq_source(status: dict) -> str:
    if status.get("headphones"):
        return "hp"
    return EQ_SRC.get(str(status.get("input") or ""), "air")


def eq_state(settings: dict | None, status: dict) -> dict:
    """Aktiv EQ-profil for det som høres nå: {"source", "preset" (navn eller «Egen»), "bands", "profiles"}."""
    src = eq_source(status)
    prof = ((settings or {}).get("eq") or {}).get(src) or {}
    bands = prof.get("eq") if isinstance(prof.get("eq"), list) and len(prof.get("eq")) == 5 else [0, 0, 0, 0, 0]
    idx = prof.get("preset")
    name = EQ_PRESETS[idx][0] if isinstance(idx, int) and 0 <= idx < len(EQ_PRESETS) else ""
    if not name:   # ingen lagret indeks: gjenkjenn båndene
        name = next((n for n, b in EQ_PRESETS if [round(float(x)) for x in bands] == b), "Egen")
    return {"source": src, "preset": name, "bands": [float(x) for x in bands], "profiles": [n for n, _ in EQ_PRESETS]}


def eq_patch(profile: str, source: str) -> dict:
    """settings-patch som setter forhåndsinnstillingen «profile» for kilden (daemonen fletter per kilde)."""
    for i, (n, bands) in enumerate(EQ_PRESETS):
        if n.lower() == str(profile).strip().lower():
            return {"eq": {source: {"preset": i, "eq": list(bands)}}}
    raise ValueError(f"ukjent EQ-profil: {profile}")


def logo_key(path: str | None) -> str:
    """«/api/logo?k=abcd…» → «abcd…» (eller "" hvis ugyldig)."""
    m = re.search(r"[?&]k=([0-9a-f]{16})", str(path or ""))
    return m.group(1) if m else ""


def valid_key(k: str) -> bool:
    return bool(_KEY.match(k or ""))


def logo_url(entry_id: str, path: str | None) -> str:
    k = logo_key(path)
    return LOGO_URL.format(entry_id=entry_id, k=k) if k else ""


def card_presets(entry_id: str, presets: list, status_presets: list) -> list[dict]:
    """Favoritter for kortet med logo som går via Home Assistant (samme opphav som dashbordet – virker også over https)."""
    logos = {p.get("n"): p.get("logo") for p in status_presets or [] if isinstance(p, dict)}
    out = []
    for p in presets or []:
        if not isinstance(p, dict) or not p.get("n"):
            continue
        out.append({"n": p.get("n"), "title": p.get("title", ""), "image": p.get("image") or p.get("icon") or "",
                    "logo": logo_url(entry_id, p.get("logo") or logos.get(p.get("n")))})
    return out[:50]
