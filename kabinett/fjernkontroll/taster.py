"""Tastene på Skjold Fjernkontroll – én kilde for kabinettet, tastekortet, fastvaren og dokumentasjonen.

Kjør:  python3 taster.py
  skriver  taster.scad                      (hettene og bryterne til skjold_fjernkontroll.scad)
           tastekort/plassering.csv          (bryter- og brikkeplassering for tastekortet, mm fra kortets hjørne)
           tastekort/koblinger.csv           (hver bryter → TCA9555-brikke og pinne)
           ../../esphome/skjold-fjernkontroll.yaml  (blokkene mellom «# >>> navneliste/hendelser/taster» og «# <<< …»)
  og skriver koblingstabellen (Markdown) til stdout, til LES_MEG.md.

Koordinater: x = tvers (0 … W, venstre kant = 0), n = avstand fra nesen (IR-enden) målt langs fjernkontrollen.
Former:  rund (d) · pille (b × h, h langs fjernkontrollen) · vippe (to brytere) · ring (D-pad med fire brytere) · ok."""
import csv
import math
import os
import re

W, L = 55.0, 230.0          # ytre mål (må stemme med skjold_fjernkontroll.scad)
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
    # fire hjørnetaster rundt D-paden
    ("tilbake", "Tilbake", "rund", 7.6, 70, 6.6, 6.6, "tilbake", "mork", ["tilbake"]),
    ("info", "Info", "rund", W - 7.6, 70, 6.6, 6.6, "info", "mork", ["info"]),
    ("guide", "Guide", "rund", 7.6, 96, 6.6, 6.6, "guide", "mork", ["guide"]),
    ("avslutt", "Avslutt", "rund", W - 7.6, 96, 6.6, 6.6, "avslutt", "mork", ["avslutt"]),
    # D-pad: gullring med fire brytere og OK i midten
    ("dpad", "D-pad", "ring", CX, 83, 30, 14.6, "", "gull", ["opp", "ned", "venstre", "hoyre"]),
    ("ok", "OK", "ok", CX, 83, 12.6, 12.6, "OK", "mork", ["ok"]),
    # volum og kanal/side som loddrette vipper, demp og siste kanal mellom dem
    ("vol", "Volum", "vippe", 9.4, 113, 8.4, 22, "vol", "mork", ["vol_opp", "vol_ned"]),
    ("kan", "Kanal og side", "vippe", W - 9.4, 113, 8.4, 22, "kan", "mork", ["kan_opp", "kan_ned"]),
    ("demp", "Demp", "pille", CX, 106.5, 11, 6.4, "demp", "mork", ["demp"]),
    ("siste", "Siste kanal", "pille", CX, 119.5, 11, 6.4, "siste", "mork", ["siste"]),
    # avspilling
    ("spol_tilbake", "Spol tilbake", "pille", 12, 131.5, 12, 7.2, "spol_tilbake", "mork", ["spol_tilbake"]),
    ("spill_pause", "Spill-pause", "pille", CX, 131.5, 12, 7.2, "spill_pause", "mork", ["spill_pause"]),
    ("spol_frem", "Spol frem", "pille", W - 12, 131.5, 12, 7.2, "spol_frem", "mork", ["spol_frem"]),
    ("opptak", "Ta opp", "pille", 12, 141, 12, 6.6, "opptak", "mork", ["opptak"]),
    ("stopp", "Stopp", "pille", CX, 141, 12, 6.6, "stopp", "mork", ["stopp"]),
    ("dvr", "Opptak (liste)", "pille", W - 12, 141, 12, 6.6, "dvr", "mork", ["dvr"]),
    # fire fargetaster
    ("rod", "Rød", "pille", CX - 18, 149.6, 9, 4.4, "", "rod", ["rod"]),
    ("gronn", "Grønn", "pille", CX - 6, 149.6, 9, 4.4, "", "gronn", ["gronn"]),
    ("gul", "Gul", "pille", CX + 6, 149.6, 9, 4.4, "", "gul", ["gul"]),
    ("bla", "Blå", "pille", CX + 18, 149.6, 9, 4.4, "", "bla", ["bla"]),
] + [
    # talltaster 1–9, så − 0 ↵
    (f"tall_{d}", f"Tall {d}", "pille", (CX - 14, CX, CX + 14)[(d - 1) % 3], 157.4 + 8.4 * ((d - 1) // 3), 11.6, 6.0, str(d), "mork", [f"tall_{d}"])
    for d in range(1, 10)
] + [
    ("strek", "Strek", "pille", CX - 14, 182.6, 11.6, 6.0, "strek", "mork", ["strek"]),
    ("tall_0", "Tall 0", "pille", CX, 182.6, 11.6, 6.0, "0", "mork", ["tall_0"]),
    ("enter", "Enter", "pille", CX + 14, 182.6, 11.6, 6.0, "enter", "mork", ["enter"]),
    # smarthus-raden: lys, stikkontakt, − og +
    ("lys", "Lys", "pille", CX - 18, 192.2, 9.6, 6.0, "lys", "lys", ["lys"]),
    ("stikk", "Stikkontakt", "pille", CX - 6, 192.2, 9.6, 6.0, "stikk", "lys", ["stikk"]),
    ("minus", "Minus (dempe lys)", "pille", CX + 6, 192.2, 9.6, 6.0, "minus", "lys", ["minus"]),
    ("pluss", "Pluss (mer lys)", "pille", CX + 18, 192.2, 9.6, 6.0, "pluss", "lys", ["pluss"]),
]

# alt under skjermen ligger DN mm lenger bak enn i første utgave (2,0″-skjerm)
HETTER = [h[:4] + (h[4] + DN,) + h[5:] for h in HETTER]

BRYTER_NAVN = {
    "opp": "Opp", "ned": "Ned", "venstre": "Venstre", "hoyre": "Høyre", "vol_opp": "Volum +", "vol_ned": "Volum −",
    "kan_opp": "Kanal +", "kan_ned": "Kanal −",
}
DPAD_R = 11.2      # bryterne under gullringen (radius fra senter)
VIPPE_D = 7.4      # bryterne under en vippe: ± fra midten


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


# fire ledige pinner på brikke C (pinne 12–15) brukes til styring
EKSTRA = [("vibrator", "C", 12, "P1_4", "utgang: vibrasjonsmotor (via AO3400)"),
          ("strom_skjerm", "C", 13, "P1_5", "utgang: 3V3 til skjerm og IR-mottaker (lav = på, AO3401)"),
          ("lader", "C", 14, "P1_6", "inngang: TP4056 CHRG (lav = lader)"),
          ("ledig", "C", 15, "P1_7", "ledig")]


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
    return ("// Laget av taster.py – ikke rediger for hånd.\n"
            "// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge]\n"
            f"HETTER = [\n{(',' + chr(10)).join(rows)}\n];\n"
            "// bryter: [id, x, n]\n"
            f"BRYTERE = [\n{(',' + chr(10)).join(br)}\n];\n"
            f"DPAD_R = {DPAD_R};\nVIPPE_D = {VIPPE_D};\nPCB_N0 = {PCB_N0};\nPCB_N1 = {PCB_N1};\n")


def plassering():
    """Bryterne og brikkene på tastekortet. Origo = kortets nedre venstre hjørne sett ovenfra (halen ned):
    kortet går fra x = 3,2 til W − 3,2 og n = PCB_N0 … PCB_N1, så kort-x = x − 3,2 og kort-y = PCB_N1 − n."""
    rows = [("ref", "verdi", "fotavtrykk", "x_mm", "y_mm", "rot", "side")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        rows.append((f"SW{i + 1}", f"{bid}", "SW-SMD_4x4x1.5", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "0", "topp"))
    for i, (x, n) in enumerate([(CX - 13, 135.0 + DN), (CX, 135.0 + DN), (CX + 13, 135.0 + DN)]):
        rows.append((f"U{i + 1}", f"TCA9555PWR 0x{0x20 + i:02X}", "TSSOP-24", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "90", "bunn"))
    return rows


def koblinger():
    rows = [("bryter", "navn", "brikke", "adresse", "pinne", "esphome_nummer")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        c, a, p, pn = tca(i)
        rows.append((bid, navn, c, f"0x{a:02X}", pn, str(p)))
    for bid, c, p, pn, m in EKSTRA:
        rows.append((bid, m, c, "0x22", pn, str(p)))
    return rows


REPETER = {"vol_opp", "vol_ned", "kan_opp", "kan_ned", "opp", "ned", "venstre", "hoyre", "minus", "pluss"}   # gjentas når de holdes


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


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    feil = sjekk_steg()
    assert len(brytere()) == 44, len(brytere())
    if feil:
        raise SystemExit(f"for lite materiale mellom hullene: {feil}")
    with open(os.path.join(here, "taster.scad"), "w") as f:
        f.write(scad())
    os.makedirs(os.path.join(here, "tastekort"), exist_ok=True)
    for fn, rows in (("plassering.csv", plassering()), ("koblinger.csv", koblinger())):
        with open(os.path.join(here, "tastekort", fn), "w", newline="") as f:
            csv.writer(f).writerows(rows)
    yml = os.path.join(here, "..", "..", "esphome", "skjold-fjernkontroll.yaml")
    if os.path.exists(yml):
        s = open(yml).read()
        ny = s
        for k, v in yaml_blokker().items():
            ny = re.sub(rf"# >>> {k}.*?# <<< {k}", lambda _m, v=v: v, ny, flags=re.S)
        if ny != s:
            open(yml, "w").write(ny)
    print(tabell())


if __name__ == "__main__":
    main()
