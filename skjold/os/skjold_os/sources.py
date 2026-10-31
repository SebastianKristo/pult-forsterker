"""Kilder: daemonens input-nøkler -> navn, farge, ikon (design/README.md «Kildefarger»)."""
from .gfx import hexc

SOURCES = {
    "radio":   {"k": "RADIO",   "n": "Radio",   "c": hexc("#e8893a"), "ico": "radio",   "sub": "Lyrion · favoritter",
                "art": ("#e8893a", "#8a3b12")},
    "airplay": {"k": "AIRPLAY", "n": "AirPlay", "c": hexc("#f2f2ee"), "ico": "air",     "sub": "Via Wi-Fi",
                "art": ("#6b6f7a", "#22252c")},
    "bt":      {"k": "BLÅTANN", "n": "Blåtann", "c": hexc("#4a8cff"), "ico": "bt",      "sub": "Blåtann",
                "art": ("#4a8cff", "#1a2f66")},
    "spotify": {"k": "SPOTIFY", "n": "Spotify", "c": hexc("#1ed760"), "ico": "spotify", "sub": "Spotify Connect",
                "art": ("#1ed760", "#0b5c2a")},
    "aux":     {"k": "AUX",     "n": "AUX",     "c": hexc("#d8cfb4"), "ico": "aux",     "sub": "Linjeinngang",
                "art": ("#d8cfb4", "#5c5540")},
    "aux2":    {"k": "AUX 2",   "n": "AUX 2",   "c": hexc("#d8cfb4"), "ico": "aux",     "sub": "Linjeinngang",
                "art": ("#d8cfb4", "#5c5540")},
    "usb":     {"k": "USB",     "n": "USB",     "c": hexc("#4a8cff"), "ico": "usb",     "sub": "USB-lyd fra PC",
                "art": ("#4a8cff", "#1a2f66")},
}
ORDER = ["radio", "airplay", "bt", "spotify", "aux", "aux2", "usb"]   # design: RADIO, AIRPLAY, BLÅTANN først

def src(key):
    return SOURCES.get(key) or {"k": (key or "?").upper(), "n": key or "?", "c": hexc("#f2f2ee"), "ico": "aux",
                                "sub": "", "art": ("#6b6f7a", "#22252c")}

def ring(inputs):
    """Rekkefølgen kildebytte-animasjonen viser ikonene i."""
    ins = [i for i in ORDER if i in (inputs or [])] + [i for i in (inputs or []) if i not in ORDER]
    return ins or ["radio", "airplay", "bt"]
