"""Kjør DRC på hovedkortet og skriv sammendrag (feil og advarsler per type)."""
import collections
import re
import sys

import pcbnew


def kjør(pcb, rapport, fyll=True):
    b = pcbnew.LoadBoard(pcb)
    if fyll:
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.WriteDRCReport(b, rapport, pcbnew.EDA_UNITS_MILLIMETRES, True)
    t = open(rapport).read()
    blokker = re.findall(r"^\[(\w+)\]: (.*?)\n(.*?)(?=^\[|\Z)", t, re.M | re.S)
    feil = collections.Counter()
    adv = collections.Counter()
    eks = {}
    for typ, tekst, rest in blokker:
        sev = re.search(r"Severity: (\w+)", rest)
        sev = sev.group(1) if sev else "error"
        (feil if sev == "error" else adv)[typ] += 1
        eks.setdefault(typ, rest.strip()[:400])
    return feil, adv, eks, b


if __name__ == "__main__":
    f, a, e, _ = kjør(sys.argv[1], sys.argv[2])
    print("FEIL:", dict(f))
    print("ADVARSLER:", dict(a))
    for typ in f:
        print(f"--- {typ}\n{e[typ]}")
