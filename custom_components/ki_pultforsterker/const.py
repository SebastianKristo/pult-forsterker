"""Konstanter for Pultforsterker."""
from __future__ import annotations
DOMAIN = "ki_pultforsterker"
DEFAULT_PORT = 8765
SCAN_INTERVAL_S = 5
CONF_HOST = "host"
CONF_PORT = "port"

# Kildenavn (nøkkel i API-et → visningsnavn). Rekkefølgen er standardrekkefølgen.
SOURCE_LABELS = {
    "radio": "Radio", "airplay": "AirPlay", "bt": "Bluetooth", "spotify": "Spotify",
    "aux": "AUX 1", "aux2": "AUX 2", "usb": "USB",
}
# Eldre daemoner (uten "inputs" i status) hadde alltid disse.
FALLBACK_INPUTS = ["radio", "airplay", "bt", "aux", "aux2", "usb"]
# Kort uten AUX/USB, hodetelefonjack, overtemperatur og USB-switch (Skjold Node).
NODE_BOARDS = ("node",)
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


def is_node(data: dict | None) -> bool:
    return (data or {}).get("board") in NODE_BOARDS


def all_known_sources(data: dict | None) -> list[str]:
    """Supersett av kilder (til ENUM-sensoren): alle kjente + det kortet rapporterer."""
    out = list(SOURCE_LABELS)
    for i in status_inputs(data):
        if i not in out:
            out.append(i)
    return out
