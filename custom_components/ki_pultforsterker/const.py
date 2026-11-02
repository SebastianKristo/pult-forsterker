"""Konstanter for Pultforsterker."""
from __future__ import annotations
DOMAIN = "ki_pultforsterker"
DEFAULT_PORT = 8765
SCAN_INTERVAL_S = 5
CONF_HOST = "host"
CONF_PORT = "port"

# Kildenavn (nøkkel i API-et → visningsnavn). Rekkefølgen er standardrekkefølgen.
SOURCE_LABELS = {
    "radio": "Radio", "airplay": "AirPlay", "bt": "Bluetooth", "spotify": "Spotify", "plex": "Plex",
    "aux": "AUX 1", "aux2": "AUX 2", "usb": "USB",
}
# Eldre daemoner (uten "inputs" i status) hadde alltid disse.
FALLBACK_INPUTS = ["radio", "airplay", "bt", "aux", "aux2", "usb"]
# Kort uten AUX/USB, hodetelefonjack, overtemperatur og USB-switch (Skjold Node).
NODE_BOARDS = ("node",)
# Produkter (status["product"]): Skjold S1 (hovedkortet), Skjold Node (knapper/potmeter/LED/OLED), Skjold Core (ren Pi).
PRODUCT_MODELS = {"s1": "Skjold S1", "node": "Skjold Node", "core": "Skjold Core"}
MANUFACTURER = "Skjold"
LED_MODES = ["press", "always", "off"]   # settings["ledMode"]: ved trykk / alltid / av
PRESETS_MAX = 50
# Lysstyrke på skjermen (settings["bright"], indeks) – samme som innstillingsmenyen på Node.
BRIGHT_OPTIONS = ["auto", "high", "medium", "low"]


def status_inputs(data: dict | None) -> list[str]:
    """Kildene dette kortet har, i daemonens rekkefølge (fallback for eldre daemoner)."""
    inputs = (data or {}).get("inputs")
    if isinstance(inputs, list) and inputs:
        return [str(i) for i in inputs]
    return list(FALLBACK_INPUTS)


def source_label(key: str) -> str:
    return SOURCE_LABELS.get(key, key.capitalize())


def product(data: dict | None) -> str:
    """s1 | node | core. Eldre daemoner uten "product": board=node → node, ellers s1."""
    d = data or {}
    p = d.get("product")
    if p in PRODUCT_MODELS:
        return p
    return "node" if d.get("board") in NODE_BOARDS else "s1"


def is_node(data: dict | None) -> bool:
    """Node-kortfamilien (Skjold Node og Skjold Core): ingen AUX/USB, hodetelefoner, overtemperatur eller USB-switch."""
    return product(data) in ("node", "core")


def has_display(data: dict | None) -> bool:
    return product(data) in ("s1", "node")


def has_leds(data: dict | None) -> bool:
    """LED-ringer med ledLevel/ledMode i innstillingene (Skjold Node)."""
    return product(data) == "node"


def setting(data: dict | None, key: str, default):
    """status["settings"] har bare endrede nøkler – ellers standardverdien."""
    v = ((data or {}).get("settings") or {}).get(key)
    return default if v is None else v


def all_known_sources(data: dict | None) -> list[str]:
    """Supersett av kilder (til ENUM-sensoren): alle kjente + det kortet rapporterer."""
    out = list(SOURCE_LABELS)
    for i in status_inputs(data):
        if i not in out:
            out.append(i)
    return out
