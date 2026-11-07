"""Tastene på Skjold Fjernkontroll – én kilde for kabinettet, tastekortet, fastvaren og dokumentasjonen.

To varianter: «kort» (standard, uten talltastene og smarthus-raden: 21 taster, 184 mm) og «full» (valgfri, 37 taster, 227 mm).
Kjør:  python3 taster.py
  skriver  taster.scad                      (hettene og bryterne for begge variantene til skjold_fjernkontroll.scad)
           tastekort/ og tastekort_full/     (plassering.csv og koblinger.csv: bryter- og brikkeplassering og
                                              hver bryter → TCA9555-brikke og pinne)
           ../../esphome/skjold-fjernkontroll.yaml       (standard/kort: blokkene mellom «# >>> navneliste/hendelser/taster» og «# <<< …»)
           ../../esphome/skjold-fjernkontroll-full.yaml  (laget fra den over, med full variants taster og 3 × TCA9555)
  og skriver koblingstabellen for standard (kort) til stdout, til LES_MEG.md (python3 taster.py full for full).

Koordinater: x = tvers (0 … W, venstre kant = 0), n = avstand fra nesen (IR-enden) målt langs fjernkontrollen.
Former:  rund (d) · pille (b × h, h langs fjernkontrollen) · vippe (to brytere) · ring (D-pad med fire brytere) · ok."""
import csv
import math
import os
import re

W, L = 55.0, 230.0          # ytre mål (må stemme med skjold_fjernkontroll.scad); L byttes av bruk("kort")
L_FULL, L_KORT = 227.0, 184.0
DN = 22.0                   # alt under skjermen flyttet 22 mm mot halen for 2,8″-skjermen (DN i .scad)
CX = W / 2
SPILL = 0.35                # klaring rundt hetta i hullet (hver side)
MIN_STEG = 1.4              # minste materiale mellom to hull i toppen
PCB_N0, PCB_N1 = 57.5 + DN, 198.5 + DN  # tastekortet strekker seg fra n = 57,5 til 198,5 (under skjermen og ned mot halen)

# ---------- hettene ----------
# (id, navn, form, x, n, b, h, ikon, farge, [bryter-id …])
HETTER = [
    # rad 1 rett under skjermen
    ("av", "Av-på", "rund", CX - 14, 61, 7, 7, "av", "mork", ["av"]),
    ("hjem", "Skjold (aktiviteter)", "rund", CX, 61, 7.6, 7.6, "skjold", "gull", ["hjem"]),
    ("meny", "Meny", "rund", CX + 14, 61, 7, 7, "meny", "mork", ["meny"]),
    # to hjørnetaster over D-paden (tilbake og avslutt)
    ("tilbake", "Tilbake", "rund", 7.6, 70, 6.6, 6.6, "tilbake", "mork", ["tilbake"]),
    ("avslutt", "Avslutt", "rund", W - 7.6, 70, 6.6, 6.6, "avslutt", "mork", ["avslutt"]),
    # D-pad: gullring med fire brytere og OK i midten
    ("dpad", "D-pad", "ring", CX, 84, 32, 14.6, "pil", "gull", ["opp", "ned", "venstre", "hoyre"]),
    ("ok", "OK", "ok", CX, 84, 12.6, 12.6, "OK", "mork", ["ok"]),
    # stor volumvippe i midten, demp til venstre og guide til høyre
    ("vol", "Volum", "vippe", CX, 117.5, 11.5, 28, "vol", "mork", ["vol_opp", "vol_ned"]),
    ("demp", "Demp", "rund", CX - 15, 117.5, 9, 9, "demp", "mork", ["demp"]),
    ("guide", "Guide", "rund", CX + 15, 117.5, 9, 9, "guide", "mork", ["guide"]),
    # avspilling
    ("spol_tilbake", "Spol tilbake", "pille", 12, 137.5, 12, 7.2, "spol_tilbake", "mork", ["spol_tilbake"]),
    ("spill_pause", "Spill-pause", "pille", CX, 137.5, 12, 7.2, "spill_pause", "mork", ["spill_pause"]),
    ("spol_frem", "Spol frem", "pille", W - 12, 137.5, 12, 7.2, "spol_frem", "mork", ["spol_frem"]),
    # fire fargetaster
    ("rod", "Rød", "pille", CX - 18, 146.5, 9, 4.4, "", "rod", ["rod"]),
    ("gronn", "Grønn", "pille", CX - 6, 146.5, 9, 4.4, "", "gronn", ["gronn"]),
    ("gul", "Gul", "pille", CX + 6, 146.5, 9, 4.4, "", "gul", ["gul"]),
    ("bla", "Blå", "pille", CX + 18, 146.5, 9, 4.4, "", "bla", ["bla"]),
] + [
    # talltaster 1–9, så − 0 ↵
    (f"tall_{d}", f"Tall {d}", "pille", (CX - 14, CX, CX + 14)[(d - 1) % 3], 154.3 + 8.4 * ((d - 1) // 3), 11.6, 6.0, str(d), "mork", [f"tall_{d}"])
    for d in range(1, 10)
] + [
    ("strek", "Strek", "pille", CX - 14, 179.5, 11.6, 6.0, "strek", "mork", ["strek"]),
    ("tall_0", "Tall 0", "pille", CX, 179.5, 11.6, 6.0, "0", "mork", ["tall_0"]),
    ("enter", "Enter", "pille", CX + 14, 179.5, 11.6, 6.0, "enter", "mork", ["enter"]),
    # smarthus-raden: lys, stikkontakt, − og +
    ("lys", "Lys", "pille", CX - 18, 189.1, 9.6, 6.0, "lys", "lys", ["lys"]),
    ("stikk", "Stikkontakt", "pille", CX - 6, 189.1, 9.6, 6.0, "stikk", "lys", ["stikk"]),
    ("minus", "Minus (dempe lys)", "pille", CX + 6, 189.1, 9.6, 6.0, "minus", "lys", ["minus"]),
    ("pluss", "Pluss (mer lys)", "pille", CX + 18, 189.1, 9.6, 6.0, "pluss", "lys", ["pluss"]),
]

# alt under skjermen ligger DN mm lenger bak enn i første utgave (2,0″-skjerm)
HETTER = [h[:4] + (h[4] + DN,) + h[5:] for h in HETTER]
HETTER_FULL = HETTER
# kort variant: uten talltastene (1–9, −, 0, ↵) og smarthus-raden (lys, stikk, −, +); fargetastene blir nederste rad
KORT_UTEN = {f"tall_{d}" for d in range(10)} | {"strek", "enter", "lys", "stikk", "minus", "pluss"}
HETTER_KORT = [h for h in HETTER_FULL if h[0] not in KORT_UTEN]
VARIANT = "full"
TCA_POS = [(CX - 13, 135.0 + DN), (CX, 135.0 + DN), (CX + 13, 135.0 + DN)]

BRYTER_NAVN = {
    "opp": "Opp", "ned": "Ned", "venstre": "Venstre", "hoyre": "Høyre", "vol_opp": "Volum +", "vol_ned": "Volum −",
    "kan_opp": "Kanal +", "kan_ned": "Kanal −",
}
DPAD_R = 12.0      # bryterne under gullringen (radius fra senter)
VIPPE_D = 9.0      # bryterne under volumvippa: ± fra midten


def brytere():
    """[(bryter-id, navn, x, n, hette-id)] i fast rekkefølge (= TCA9555-pinnene)."""
    ut = []
    for hid, navn, form, x, n, b, h, ikon, farge, ids in HETTER:
        if form == "ring":
            for bid, (dx, dn) in zip(ids, [(0, -DPAD_R), (0, DPAD_R), (-DPAD_R, 0), (DPAD_R, 0)]):
                ut.append((bid, BRYTER_NAVN[bid], x + dx, n + dn, hid))
        elif form == "vippe":
            for bid, dn in zip(ids, [-VIPPE_D, VIPPE_D]):
                ut.append((bid, BRYTER_NAVN[bid], x, n + dn, hid))
        else:
            ut.append((ids[0], navn, x, n, hid))
    return ut


def tca(i):
    """Bryter nr. i → (brikke, adresse, pinne 0–15, «P0_3»)."""
    chip = i // 16
    pin = i % 16
    return "ABC"[chip], 0x20 + chip, pin, f"P{pin // 8}_{pin % 8}"


# fire ledige pinner på siste brikke (pinne 12–15) brukes til styring: C i full variant, B i kort
def ekstra():
    c = "ABC"[len(TCA_POS) - 1]
    return [("vibrator", c, 12, "P1_4", "utgang: vibrasjonsmotor (via AO3400)"),
            ("strom_skjerm", c, 13, "P1_5", "utgang: 3V3 til skjerm og IR-mottaker (lav = på, AO3401)"),
            ("lader", c, 14, "P1_6", "inngang: TP4056 CHRG (lav = lader)"),
            ("ledig", c, 15, "P1_7", "ledig")]


def bruk(variant):
    """Velg variant («full» eller «kort») for funksjonene under."""
    global HETTER, L, PCB_N1, VARIANT, TCA_POS
    VARIANT = variant
    if variant == "kort":
        HETTER, L, TCA_POS = HETTER_KORT, L_KORT, [(CX - 13, 157.0), (CX, 157.0)]
    else:
        HETTER, L, TCA_POS = HETTER_FULL, L_FULL, [(CX - 13, 135.0 + DN), (CX, 135.0 + DN), (CX + 13, 135.0 + DN)]
    PCB_N1 = max(b[3] for b in brytere()) + 6.3   # 6,3 mm bak siste bryterrad


# ---------- 2D-former for sjekk av materialet mellom hullene ----------
def hull_form(h):
    hid, navn, form, x, n, b, hh, *_ = h
    s = SPILL
    if form in ("rund", "ok"):
        return ("sirkel", x, n, b / 2 + s)
    if form == "ring":
        return ("sirkel", x, n, b / 2 + s)
    if form in ("pille", "vippe"):
        return ("pille", x, n, b / 2 + s, hh / 2 + s)
    raise ValueError(form)


def pille_punkter(x, n, a, c, k=48):
    """Rand av en pille (rundet rektangel med radius = halve korteste side)."""
    r = min(a, c)
    pts = []
    for cx, cy, a0 in [(x + a - r, n + c - r, 0), (x - a + r, n + c - r, 90), (x - a + r, n - c + r, 180), (x + a - r, n - c + r, 270)]:
        for i in range(k // 4 + 1):
            t = math.radians(a0 + 90 * i / (k // 4))
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def rand(f, k=96):
    if f[0] == "sirkel":
        _, x, n, r = f
        return [(x + r * math.cos(2 * math.pi * i / k), n + r * math.sin(2 * math.pi * i / k)) for i in range(k)]
    return pille_punkter(*f[1:])


def inni(f, p):
    if f[0] == "sirkel":
        return math.hypot(p[0] - f[1], p[1] - f[2]) < f[3]
    _, x, n, a, c = f
    r = min(a, c)
    dx, dy = max(abs(p[0] - x) - (a - r), 0), max(abs(p[1] - n) - (c - r), 0)
    return math.hypot(dx, dy) < r


def avstand(fa, fb):
    """Korteste avstand mellom randene til to hull (negativ = overlapp)."""
    pa, pb = rand(fa), rand(fb)
    if any(inni(fb, p) for p in pa) or any(inni(fa, p) for p in pb):
        return -1.0
    return min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in pa for b in pb)


def sjekk_steg():
    """[(hette a, hette b, avstand)] for alle par nærmere enn MIN_STEG (ring og OK er ett hull sammen)."""
    hs = [h for h in HETTER if h[2] != "ok"]
    feil = []
    for i, a in enumerate(hs):
        for b in hs[i + 1:]:
            fa, fb = hull_form(a), hull_form(b)
            if abs(fa[1] - fb[1]) > 40 or abs(fa[2] - fb[2]) > 40:
                continue
            d = avstand(fa, fb)
            if d < MIN_STEG:
                feil.append((a[0], b[0], round(d, 2)))
    return feil


# ---------- utdata ----------
def scad():
    """taster.scad: lister som skjold_fjernkontroll.scad leser (n måles fra nesen, y = L − n i modellen)."""
    rows = []
    for hid, navn, form, x, n, b, h, ikon, farge, ids in HETTER:
        rows.append(f'  ["{hid}", "{form}", {x:.2f}, {n:.2f}, {b:.2f}, {h:.2f}, "{ikon}", "{farge}"]')
    br = [f'  ["{bid}", {x:.2f}, {n:.2f}]' for bid, _, x, n, _ in brytere()]
    v = VARIANT.upper()
    return (f"// variant «{VARIANT}»: {len(brytere())} brytere, {len(HETTER)} hetter, L = {L}\n"
            f"HETTER_{v} = [\n{(',' + chr(10)).join(rows)}\n];\n"
            f"BRYTERE_{v} = [\n{(',' + chr(10)).join(br)}\n];\n"
            f"PCB_N1_{v} = {PCB_N1:.2f};\nL_{v} = {L};\n")


def plassering():
    """Bryterne og brikkene på tastekortet. Origo = kortets nedre venstre hjørne sett ovenfra (halen ned):
    kortet går fra x = 3,2 til W − 3,2 og n = PCB_N0 … PCB_N1, så kort-x = x − 3,2 og kort-y = PCB_N1 − n."""
    rows = [("ref", "verdi", "fotavtrykk", "x_mm", "y_mm", "rot", "side")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        rows.append((f"SW{i + 1}", f"{bid}", "SW-SMD_4x4x1.5", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "0", "topp"))
    for i, (x, n) in enumerate(TCA_POS):
        rows.append((f"U{i + 1}", f"TCA9555PWR 0x{0x20 + i:02X}", "TSSOP-24", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "90", "bunn"))
    fpc_n = 8.4 + 69.2 + 4.5   # fpcN i skjold_fjernkontroll.scad: rett bak skjermmodulen
    rows.append(("J1", "FPC 18p 0,8 mm (skjerm)", "FPC-18P-0.8mm bunnkontakt", f"{CX - 3.2:.2f}", f"{PCB_N1 - fpc_n:.2f}", "0", "bunn"))
    rows.append(("U9", "XPT2046 (bare budsjett-skjerm)", "TSSOP-16", f"{CX + 14 - 3.2:.2f}", f"{PCB_N1 - fpc_n:.2f}", "90", "bunn"))
    return rows


def koblinger():
    rows = [("bryter", "navn", "brikke", "adresse", "pinne", "esphome_nummer")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        c, a, p, pn = tca(i)
        rows.append((bid, navn, c, f"0x{a:02X}", pn, str(p)))
    for bid, c, p, pn, m in ekstra():
        rows.append((bid, m, c, f"0x{0x20 + len(TCA_POS) - 1:02X}", pn, str(p)))
    return rows


REPETER = {"vol_opp", "vol_ned", "opp", "ned", "venstre", "hoyre", "minus", "pluss"}   # gjentas når de holdes


def yaml_blokker():
    """Tre blokker i esphome/skjold-fjernkontroll.yaml: navnelista (globals), hendelsestypene (event) og en
    binary_sensor for hver tast. Vanlige taster: kort trykk og langt trykk (≥ 0,6 s). Volum, kanal, D-pad og ± gjentas
    så lenge de holdes inne. Alle kaller script «tast» med bryter-id og om trykket var langt."""
    hub = {"A": "tca_a", "B": "tca_b", "C": "tca_c"}
    ids = [b[0] for b in brytere()]
    navn = ["# >>> navneliste (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
            "  - id: taster_navn",
            "    type: std::vector<std::string>",
            "    initial_value: '{" + ", ".join(f'"{i}"' for i in ids) + "}'",
            "# <<< navneliste"]
    hend = ["# >>> hendelser (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
            "    event_types:"] + [f"      - {i}" for i in ids] + [f"      - {i}_lang" for i in ids if i not in REPETER] + ["# <<< hendelser"]
    ut = ["# >>> taster (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)"]
    for i, (bid, nv, x, n, hid) in enumerate(brytere()):
        c, a, p, pn = tca(i)
        ut += [f"  - platform: gpio",
               f"    id: t_{bid}",
               f"    name: \"Tast {nv}\"",
               f"    internal: true",
               f"    pin: {{ tca9555: {hub[c]}, number: {p}, mode: {{ input: true }}, inverted: true }}",
               f"    filters: [ {{ delayed_on: 15ms }}, {{ delayed_off: 15ms }} ]"]
        if bid in REPETER:
            ut += [f"    on_press:",
                   f"      - script.execute: {{ id: tast, navn: \"{bid}\", lang: false }}",
                   f"      - delay: 450ms",
                   f"      - while:",
                   f"          condition: {{ binary_sensor.is_on: t_{bid} }}",
                   f"          then:",
                   f"            - script.execute: {{ id: tast, navn: \"{bid}\", lang: false }}",
                   f"            - delay: 160ms"]
        else:
            ut += [f"    on_multi_click:",
                   f"      - timing: [ \"ON for at least 0.6s\" ]",
                   f"        then: [ {{ script.execute: {{ id: tast, navn: \"{bid}\", lang: true }} }} ]",
                   f"      - timing: [ \"ON for at most 0.59s\", \"OFF for at least 0.01s\" ]",
                   f"        then: [ {{ script.execute: {{ id: tast, navn: \"{bid}\", lang: false }} }} ]"]
    ut.append("# <<< taster")
    return {"navneliste": "\n".join(navn), "hendelser": "\n".join(hend), "taster": "\n".join(ut)}


def tabell():
    lines = ["| Tast | Bryter-id | Brikke | Adresse | Pinne |", "|---|---|---|---|---|"]
    for row in koblinger()[1:]:
        bid, navn, c, a, pn, _ = row
        lines.append(f"| {navn} | `{bid}` | {c} | {a} | {pn} |")
    return "\n".join(lines)


def full_yaml(kort):
    """esphome/skjold-fjernkontroll-full.yaml: samme fil som standard (kort), men med talltastene og
    smarthus-raden (37 taster) og 3 × TCA9555."""
    k = kort
    for a, b in [("  name: skjold-fjernkontroll\n", "  name: skjold-fjernkontroll-full\n"),
                 ("  friendly_name: Skjold Fjernkontroll\n", "  friendly_name: Skjold Fjernkontroll Full\n"),
                 ("  ekstra_hub: tca_b ", "  ekstra_hub: tca_c "),
                 ("  - { id: tca_b, i2c_id: bus_a, address: 0x21 }\n",
                  "  - { id: tca_b, i2c_id: bus_a, address: 0x21 }\n  - { id: tca_c, i2c_id: bus_a, address: 0x22 }\n"),
                 ("  ap: { ssid: \"Skjold Fjernkontroll\" }", "  ap: { ssid: \"Skjold Fjernkontroll Full\" }"),
                 ("# Dette er standardvarianten (uten talltastene og smarthus-raden). Full variant med talltaster og smarthus-rad:\n"
                  "# skjold-fjernkontroll-full.yaml, laget av kabinett/fjernkontroll/taster.py fra denne fila.\n", ""),
                 ("21 taster, IR og Wi-Fi", "37 taster, IR og Wi-Fi"),
                 ("2 × TCA9555 på tastekortet (21 taster", "3 × TCA9555 på tastekortet (37 taster")]:
        assert a in k, a
        k = k.replace(a, b)
    hode = ("# FULL VARIANT (valgfri) – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger\n"
            "# her: endre skjold-fjernkontroll.yaml og kjør python3 taster.py. Med talltastene og smarthus-raden (37 taster,\n"
            "# 3 × TCA9555).\n")
    for kk, v in yaml_blokker().items():
        k = re.sub(rf"# >>> {kk}.*?# <<< {kk}", lambda _m, v=v: v, k, flags=re.S)
    return hode + k


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    deler, yml = [], os.path.join(here, "..", "..", "esphome", "skjold-fjernkontroll.yaml")
    for v, antall in (("kort", 21), ("full", 37)):
        bruk(v)
        assert len(brytere()) == antall, (v, len(brytere()))
        feil = sjekk_steg()
        if feil:
            raise SystemExit(f"{v}: for lite materiale mellom hullene: {feil}")
        deler.append(scad())
        mappe = os.path.join(here, "tastekort" if v == "kort" else "tastekort_full")
        os.makedirs(mappe, exist_ok=True)
        for fn, rows in (("plassering.csv", plassering()), ("koblinger.csv", koblinger())):
            with open(os.path.join(mappe, fn), "w", newline="") as f:
                csv.writer(f).writerows(rows)
    with open(os.path.join(here, "taster.scad"), "w") as f:
        f.write("// Laget av taster.py – ikke rediger for hånd.\n"
                "// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge] · bryter: [id, x, n]\n"
                f"DPAD_R = {DPAD_R};\nVIPPE_D = {VIPPE_D};\nPCB_N0 = {PCB_N0};\n" + "".join(deler))
    # standard (kort) er hovedfila; full lages fra den
    bruk("kort")
    s = open(yml).read()
    ny = s
    for k, v in yaml_blokker().items():
        ny = re.sub(rf"# >>> {k}.*?# <<< {k}", lambda _m, v=v: v, ny, flags=re.S)
    if ny != s:
        open(yml, "w").write(ny)
    bruk("full")
    open(yml.replace(".yaml", "-full.yaml"), "w").write(full_yaml(ny))
    bruk("kort")
    import sys
    if len(sys.argv) > 1:
        bruk(sys.argv[1])
    print(tabell())


if __name__ == "__main__":
    main()
