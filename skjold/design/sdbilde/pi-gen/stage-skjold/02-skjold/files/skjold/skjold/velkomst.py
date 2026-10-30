"""Engangs velkomsthilsen (aktiveres med `sudo skjold-velkomst` over SSH).

Bruk i skjold-ui:
    from skjold import velkomst
    v = velkomst.hent()            # None hvis ikke aktiv
    if v: vis_animasjon(v["tittel"], v["navn"], v["hint"])  # til en knapp trykkes
          velkomst.brukt()        # skjer først når knappen er trykket
Lyd og knappefunksjoner er blokkert mens hilsenen vises. Første trykk lukker den
og utløser ikke funksjonen. Går strømmen før hilsenen er trykket vekk, vises den igjen.
"""
import json, os

FIL = "/var/lib/skjold/velkomst.json"

def hent():
    try:
        with open(FIL, encoding="utf-8") as f:
            v = json.load(f)
        return v if v.get("aktiv") else None
    except (OSError, ValueError):
        return None

def brukt():
    try:
        os.remove(FIL)
    except OSError:
        pass
