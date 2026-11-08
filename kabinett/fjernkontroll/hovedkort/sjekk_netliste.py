"""Nettlistesjekk for hovedkortet (KiCad 7 har ingen ERC på kommandolinja, og det finnes ikke noe skjema her:
nettlista er kilden). Sjekker:

  1. hver strømpinne på hver IC er koblet til riktig forsyning (fra en tabell over pinnene i databladene)
  2. ingen nett med bare én pinne (unntatt testpunkter, som skal ha et nett med minst én annen pinne)
  3. ingen forsyninger kortsluttet mot hverandre (ingen pinne med to nett, ingen 0 Ω mellom ulike forsyninger)
  4. alle pinnene på hver IC er enten koblet eller står på lista over pinner som skal stå åpne (med grunn)
  5. strappinnene på ESP32-S3: GPIO0 har pull-up og BOOT-knapp; GPIO3, 45 og 46 står åpne (interne verdier)
  6. I²C har pull-up på SDA og SCL (berøringens egen buss til 3V3_SW), og INT-linjene (åpen drain) har pull-up
  7. hver forsyningspinne har en avkoblingskondensator mot GND innen 6 mm (målt på kortet)
  8. etter ruting: alle nett er ferdig rutet (pcbnew-konnektivitet) og nettene på kortet er de samme som i nettlista

Bruk:  python3 hovedkort/sjekk_netliste.py [skjold-hovedkort.kicad_pcb]"""
import math
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import kretser  # noqa: E402

ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


K = {r: (fp, v, side, x, n, rot, p) for r, fp, v, side, x, n, rot, p in kretser.KOMP}
N = kretser.netter()
FORSYNING = {"GND", "3V3", "3V3_SW", "VSYS", "VBAT", "VBUS"}

# (ref-prefiks eller ref, pinne, forventet nett) fra databladene
STROM = [("U1", "1", "GND"), ("U1", "40", "GND"), ("U1", "41", "GND"), ("U1", "2", "3V3"),
         ("U2", "2", "GND"), ("U2", "5", "VBUS"),
         ("U3", "3", "GND"), ("U3", "9", "GND"), ("U3", "4", "VBUS"), ("U3", "8", "VBUS"), ("U3", "1", "GND"),
         ("U4", "1", "VSYS"), ("U4", "2", "GND"), ("U4", "5", "3V3"), ("U4", "3", "VSYS")]
for u in ("U5", "U6", "U7"):
    STROM += [(u, "24", "3V3"), (u, "12", "GND")]
feil = [f"{r}.{p} = {K[r][6].get(p)} (skal være {n})" for r, p, n in STROM if K[r][6].get(p) != n]
melding(not feil, f"strømpinnene på alle IC-ene ({len(STROM)} pinner) går til riktig forsyning" if not feil else "; ".join(feil))

enslige = [(n, p) for n, p in N.items() if len(p) < 2]
melding(not enslige, "ingen nett med bare én pinne" if not enslige else f"nett med én pinne: {enslige}")

dobbel = []
for r, (fp, v, side, x, n, rot, p) in K.items():
    if v in ("0R",) and len({p.get("1"), p.get("2")} & FORSYNING) == 2:
        dobbel.append(r)
melding(not dobbel, "ingen forsyninger kortsluttet (ingen 0 Ω mellom to forsyninger; hver pinne har ett nett)" if not dobbel else f"kortslutning: {dobbel}")

# pinner som skal stå åpne
APNE = {"U1": {"15": "IO3 strappinne (JTAG-kilde) – står åpen", "16": "IO46 strappinne – intern pull-down",
               "24": "IO47 ledig", "25": "IO48 ledig", "26": "IO45 strappinne (VDD_SPI) – intern pull-down",
               **{str(i): "IO35–IO42 ledig (35–37 brukes av PSRAM på R8)" for i in range(28, 36) if i != 31}},
        "U3": {"6": "STDBY ikke brukt"}, "U7": {str(i): "P13–P17 ledig (intern pull-up)" for i in range(16, 21)}, "J3": {"7": "SDO/MISO ikke brukt", "17": "NC (antatt)"}}
PINNER = {"U1": [str(i) for i in range(1, 42)], "U2": list("123456"), "U3": [str(i) for i in range(1, 10)], "U4": ["1", "2", "3", "5"],
          **{u: [str(i) for i in range(1, 25)] for u in ("U5", "U6", "U7")}, "J3": [str(i) for i in range(1, 19)]}
mangler = []
for r, pins in PINNER.items():
    for p in pins:
        if p not in K[r][6] and p not in APNE.get(r, {}):
            mangler.append(f"{r}.{p}")
melding(not mangler, f"alle IC-pinner er koblet eller står bevisst åpne ({sum(len(v) for v in APNE.values())} åpne med grunn)"
        if not mangler else f"ukoblede pinner uten grunn: {mangler}")

esp = K["U1"][6]
boot_pu = any(K[r][1] == "10k" and set(K[r][6].values()) == {"3V3", "BOOT"} for r in K if r.startswith("R"))
boot_sw = any(set(K[r][6].values()) == {"BOOT", "GND"} for r in K if r.startswith("SW"))
melding(esp.get("27") == "BOOT" and boot_pu and boot_sw and all(p not in esp for p in ("15", "16", "26")),
        "strappinner: GPIO0 har 10 kΩ pull-up og BOOT-knapp; GPIO3, GPIO45 og GPIO46 står åpne")
en_ok = any(K[r][1] == "10k" and set(K[r][6].values()) == {"3V3", "EN"} for r in K) and any(K[r][1] == "1uF" and set(K[r][6].values()) == {"EN", "GND"} for r in K)
melding(en_ok, "EN har 10 kΩ til 3V3 og 1 µF til GND (Espressifs referanse)")


def pull_up(nett, til="3V3"):
    return [r for r in K if r.startswith("R") and set(K[r][6].values()) == {til, nett}]


pu = {n: pull_up(n) for n in ("SDA", "SCL", "TCA_INT", "CHRG")}
pu.update({n: pull_up(n, "3V3_SW") for n in ("T_SDA", "T_SCL", "T_INT")})   # berøringens buss følger berøringens forsyning
melding(all(pu.values()), "pull-up på " + ", ".join(f"{n} ({', '.join(v)})" for n, v in pu.items()))
cc = all(any(set(K[r][6].values()) == {c, "GND"} and K[r][1] == "5.1k" for r in K) for c in ("CC1", "CC2"))
melding(cc, "USB-C: 5,1 kΩ fra CC1 og CC2 til GND (strøm fra vanlige USB-C-ladere)")

# avkobling: målt på kortet
pcb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HER, "skjold-hovedkort.kicad_pcb")
try:
    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    pos = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            pos.setdefault((f.GetReference(), p.GetNumber()), (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
    kond = [(r, K[r][6]) for r in K if r.startswith("C")]
    langt = []
    for r, p, n in STROM:
        if n == "GND":
            continue
        x, y = pos[(r, p)]
        nær = [c for c, pp in kond if set(pp.values()) == {n, "GND"} and
               min(math.hypot(x - pos[(c, q)][0], y - pos[(c, q)][1]) for q in ("1", "2")) < 6.0]
        if not nær:
            langt.append(f"{r}.{p} ({n})")
    melding(not langt, "hver forsyningspinne har avkobling mot GND innen 6 mm" if not langt else f"mangler avkobling nær: {langt}")
    # kortet mot nettlista
    avvik = []
    for f in b.GetFootprints():
        r = f.GetReference()
        for p in f.Pads():
            vil = K[r][6].get(p.GetNumber(), "") if r in K else ""
            har = p.GetNetname()
            if (vil or har) and vil != har:
                avvik.append(f"{r}.{p.GetNumber()}: kort {har!r}, nettliste {vil!r}")
    melding(not avvik, "nettene på kortet er de samme som i nettlista" if not avvik else f"avvik: {avvik[:8]}")
    ikke = b.GetConnectivity().GetUnconnectedCount(True) if hasattr(b.GetConnectivity(), "GetUnconnectedCount") else None
    rutet = len(b.GetTracks())
    melding(ikke == 0 and rutet > 0, f"alle nett er rutet ({rutet} spor/viaer, {ikke} ukoblede)")
except ImportError:
    melding(False, "pcbnew mangler: kan ikke sjekke kortet")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
