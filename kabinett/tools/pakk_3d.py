#!/usr/bin/env python3
"""Pakker alle 3D-print-filene i én ryddig zip for utgivelsen: «skjold-3d-print.zip».

Én mappe per produkt, med samme oppbygging overalt:

    Skjold 3D-print/
      LES MEG.txt                      hva som ligger hvor, og hvordan du printer
      Skjold Røst Rund/
        LES_MEG.md                     deler, montering og utskriftsinnstillinger
        1 Ferdige plater (3MF)/        åpne i Creality Print / OrcaSlicer og trykk print
        2 Enkeltdeler (STL)/           hvis du vil sette opp plata selv
        3 Kilde (OpenSCAD)/            .scad og byggeskript, for å endre mål
        Bilder/                        renderne LES_MEG viser til
        Programvare/                   ESPHome-oppsett eller fastvare, der produktet har det
        Kretskort/                     gerber, skjema og KiCad, der produktet har det
      Felles kilde/                    fonter, elementmaler og 3MF-skriveren som kildene bruker

    python3 kabinett/tools/pakk_3d.py [ut-mappe]      (standard: ut/)
"""
import os
import sys
import zipfile

ROT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAB = os.path.join(ROT, "kabinett")
TOPP = "Skjold 3D-print"
HOPP = ("__pycache__", "/asm", "/stl_asm", ".kicad_prl", ".ses", ".dsn")

# (mappenavn i zip-en, kilde under kabinett/, undermapper som er egne produkter og derfor hoppes over, ekstra filer fra repoet)
PRODUKTER = [
    ("Skjold S1 (frontplate)", "skjold-s1/print", [], []),
    ("Skjold Røst Rund", "rost_rund", [], ["firmware/rost"]),
    ("Skjold Røst (baderom)", "rost", [], ["firmware/rost"]),
    ("Skjold Stav (fjernkontroll)", "fjernkontroll", ["dokk"],
     [f"esphome/skjold-fjernkontroll{s}.yaml" for s in ("", "-full", "-hovedkort", "-tastekort-a", "-enkel", "-hullkort", "-budsjett", "-gt911")]
     + ["esphome/skjold_ui.h", "esphome/blueprints/skjold_fjernkontroll.yaml"]),
    ("Skjold Dokk", "fjernkontroll/dokk", [], []),
    ("Skjold Kassett", "kassett", [], ["esphome/skjold-kassett.yaml"]),
    ("Skjold Kassetthylle", "hylle", [], ["esphome/skjold-hylle.yaml"]),
    ("Skjold Hjul", "hjul", [], ["esphome/skjold-hjul.yaml"]),
    ("Skjold Hjul S", "hjul-s", [], ["esphome/skjold-hjul-s.yaml"]),
    ("Skjold Radio", "radio", [], ["pi/skjold_radio_knapper.py", "pi/skjold-radio-knapper.service", "pi/config/radio_pins.yaml"]),
    ("Skjold Sans", "sans", ["konsepter"], ["esphome/skjold-sans.yaml"]),
]
KRETS = ("enkel", "hovedkort", "hullkort", "tastekort", "tastekort_a", "tastekort_full")   # under fjernkontroll/

LES_MEG = """Skjold – filer til 3D-printer
=============================

Én mappe per produkt. I hver mappe:

  LES_MEG.md                 Deler, montering og utskriftsinnstillinger for produktet. Les denne først.
  1 Ferdige plater (3MF)     Åpne fila i Creality Print eller OrcaSlicer og trykk print. Platene er satt opp for
                             Creality K2 (250 x 250 mm). Farger, brim og støtte ligger i fila.
  2 Enkeltdeler (STL)        Hver del for seg, hvis du har en annen printer eller vil sette opp plata selv.
  3 Kilde (OpenSCAD)         Modellene som kildekode. Endre mål øverst i .scad-fila og kjør byggeskriptet.
  Bilder                     Bildene LES_MEG viser til.
  Programvare                ESPHome-oppsett eller fastvare, for produktene som har det.
  Kretskort                  Gerber, skjema og KiCad-filer, for produktene som har det.

«Felles kilde» inneholder fonter, elementmaler og 3MF-skriveren som flere av kildene bruker. La mappa ligge ved
siden av produktmappene hvis du skal bygge fra kilde.

Materiale: PETG eller ASA anbefales (PLA blir mykt i varme og fuktige rom). Ingen av de ferdige platene trenger
støtte, bortsett fra der LES_MEG sier det (lokket til Røst Rund).

Mer: https://skjold.smarthjemexperten.no/stotte/   Kilde: https://github.com/SebastianKristo/pult-forsterker
Lisens for 3D-modellene: CC BY-NC-SA 4.0 (bygg selv, ikke for salg).
"""


def hopp(sti):
    s = "/" + sti.replace(os.sep, "/")
    return any(h in s for h in HOPP)


def plasser(rel):
    """Hvor en fil (relativ til produktmappa) havner i zip-en, eller None hvis den ikke skal med."""
    deler = rel.split("/")
    navn = deler[-1]
    ext = navn.rsplit(".", 1)[-1].lower() if "." in navn else ""
    if deler[0] in KRETS:
        return "Kretskort/" + rel
    if deler[0] == "render" or (len(deler) > 1 and deler[-2] == "render"):
        return "Bilder/" + "/".join(d for d in deler if d != "render") if ext in ("png", "jpg", "webp") else None
    if ext == "3mf":
        return "1 Ferdige plater (3MF)/" + ("/".join(deler[:-1]) + "/" if len(deler) > 1 and not deler[0].startswith("stl") else "") + navn
    if ext == "stl" or deler[0].startswith(("stl", "oppsett_")):
        return "2 Enkeltdeler (STL)/" + rel
    if navn == "LES_MEG.md" and len(deler) == 1:
        return navn
    if ext in ("scad", "py", "sh", "js", "md", "txt", "dxf", "svg", "pdf", "json", "csv"):
        return "3 Kilde (OpenSCAD)/" + rel
    return None


def main(ut="ut"):
    os.makedirs(ut, exist_ok=True)
    mal = os.path.join(ut, "skjold-3d-print.zip")
    n = {}
    with zipfile.ZipFile(mal, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(f"{TOPP}/LES MEG.txt", LES_MEG)
        for navn, kilde, egne, ekstra in PRODUKTER:
            rot = os.path.join(KAB, kilde)
            assert os.path.isdir(rot), rot
            for d, mapper, filer in os.walk(rot):
                rel_d = os.path.relpath(d, rot).replace(os.sep, "/")
                mapper[:] = sorted(m for m in mapper if not (rel_d == "." and m in egne))
                for f in sorted(filer):
                    rel = f if rel_d == "." else f"{rel_d}/{f}"
                    if hopp(rel):
                        continue
                    hvor = plasser(rel)
                    if hvor:
                        z.write(os.path.join(d, f), f"{TOPP}/{navn}/{hvor}")
                        n[navn] = n.get(navn, 0) + 1
            for e in ekstra:
                sti = os.path.join(ROT, e)
                if os.path.isdir(sti):
                    for d, _, filer in os.walk(sti):
                        for f in sorted(filer):
                            if not hopp(os.path.join(d, f)):
                                z.write(os.path.join(d, f), f"{TOPP}/{navn}/Programvare/{os.path.relpath(os.path.join(d, f), os.path.dirname(sti))}")
                elif os.path.isfile(sti):
                    z.write(sti, f"{TOPP}/{navn}/Programvare/{os.path.basename(e)}")
                else:
                    print("ADVARSEL: mangler", e, file=sys.stderr)
        # det kildene deler: fonter, elementmaler og 3MF-skriveren (fjernkontroll/lag_3mf.py, kassett/lag_3mf.py)
        for felles in ("fonter", "elementer"):
            for d, _, filer in os.walk(os.path.join(KAB, felles)):
                for f in sorted(filer):
                    if not hopp(os.path.join(d, f)):
                        z.write(os.path.join(d, f), f"{TOPP}/Felles kilde/{os.path.relpath(os.path.join(d, f), KAB)}")
        for f in ("fjernkontroll/lag_3mf.py", "kassett/lag_3mf.py"):
            z.write(os.path.join(KAB, f), f"{TOPP}/Felles kilde/{f}")
    for navn, antall in n.items():
        print(f"  {navn}: {antall} filer")
    print(f"skrev {mal}  ({os.path.getsize(mal) / 1e6:.1f} MB)")
    return mal


if __name__ == "__main__":
    main(*sys.argv[1:2])
