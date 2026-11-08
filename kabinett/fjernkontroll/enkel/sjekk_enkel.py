"""Nettlistesjekk for Skjold Fjernkontroll Enkel (bærekortet med XIAO ESP32S3 og MCP23017). Nettlista i kretser_en.py er
kilden; denne sjekker den mot databladene, fastvaren og det rutede kortet:

  1. strømpinnene på XIAO-en og MCP23017 går til riktig forsyning; MCP-adressen er 0x20 (A0–A2 til GND)
  2. ingen nett med bare én pinne, ingen pinne med to nett
  3. alle MCP23017-pinner er koblet eller står bevisst åpne (med grunn)
  4. hver av de 14 tastene har sin egen MCP-pinne mellom pinnen og GND, samme pinne som i fastvaren
  5. XIAO-pinnene stemmer med GPIO-ene i esphome/skjold-fjernkontroll-enkel.yaml
  6. pull-up på SDA, SCL, INT og RESET; Q1 av ved oppstart (100 kΩ gate til 3V3), Q2/Q3 av (100 kΩ gate til GND)
  7. batterimålingen (1 MΩ / 1 MΩ, maks 2,1 V inn på ADC) og dokkdeleren (maks < 3,3 V inn på MCP-en)
  8. D1 peker riktig vei (anode på POGO, katode på XIAO-ens 5V)
  9. avkobling nær MCP23017 (innen 6 mm, målt på kortet)
 10. tastene på kortet står nøyaktig der taster.py (tasteoppsett A) har dem
 11. etter ruting: nettene på kortet er de samme som i nettlista, og alt er rutet

Skriver også enkel/pinner.csv (XIAO-pinne, GPIO, nett, funksjon).

Bruk:  python3 enkel/sjekk_enkel.py [skjold-enkel.kicad_pcb]"""
import csv
import math
import os
import re
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
sys.path.insert(0, os.path.dirname(HER))
import kretser_en  # noqa: E402
import taster  # noqa: E402

ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


K = {r: (fp, v, side, x, n, rot, p) for r, fp, v, side, x, n, rot, p in kretser_en.KOMP}
N = kretser_en.netter()
P = lambda r: K[r][6]   # noqa: E731

# 1. strøm
STROM = [("U1", "12", "3V3"), ("U1", "13", "GND"), ("U1", "14", "VBUS"),
         ("U2", "9", "3V3"), ("U2", "10", "GND"), ("U2", "15", "GND"), ("U2", "16", "GND"), ("U2", "17", "GND"),
         ("J1", "1", "VBAT"), ("J1", "2", "GND"), ("TP1", "1", "VBAT"), ("TP2", "1", "GND")]
feil = [f"{r}.{p} = {P(r).get(p)} (skal være {n})" for r, p, n in STROM if P(r).get(p) != n]
melding(not feil, "XIAO 3V3/GND/5V, MCP23017 VDD/VSS og adresse 0x20 (A0–A2 = GND), batteriet: riktige nett" if not feil else "; ".join(feil))

# 2. nett
enslige = [(n, p) for n, p in N.items() if len(p) < 2]
melding(not enslige, f"ingen nett med bare én pinne ({len(N)} nett)" if not enslige else f"nett med én pinne: {enslige}")

# 3. MCP23017-pinnene
APNE = {"11": "NC i databladet", "14": "NC i databladet", "19": "INTB ikke brukt (INTA dekker begge portene, MIRROR)"}
mangler = [p for p in map(str, range(1, 29)) if p not in P("U2") and p not in APNE]
melding(not mangler, "alle 28 MCP23017-pinner er koblet eller står bevisst åpne (11, 14 NC; 19 INTB)" if not mangler else f"ukoblet: {mangler}")

# 4. tastene og fastvaren
yml = open(os.path.join(HER, "..", "..", "..", "esphome", "skjold-fjernkontroll-enkel.yaml"), encoding="utf-8").read()
fw = {}
for m in re.finditer(r"id: t_(\w+)\n(?:.*\n){0,3}?\s*pin: \{ mcp23xxx: tca_a, number: (\d+)", yml):
    fw[m.group(1)] = int(m.group(2))
avvik, brukt = [], set()
for f, x, n, p in kretser_en.TASTER:
    sw = P(f"SW{p + 1}")
    nett = f"K_{f.upper()}"
    mp = [q for q, v in P("U2").items() if v == nett]
    if sw.get("1") != nett or sw.get("2") != "GND" or len(mp) != 1:
        avvik.append(f"SW{p + 1} {f}")
        continue
    brukt.add(mp[0])
    gp = int(mp[0]) - 21 if int(mp[0]) >= 21 else int(mp[0]) + 7
    if fw.get(f) is not None and fw[f] != gp:
        avvik.append(f"{f}: kort GP{gp}, fastvare {fw[f]}")
melding(not avvik and len(brukt) == 14 and len(fw) == 14, f"14 taster, hver på sin MCP-pinne mot GND ({len(fw)} av dem funnet i fastvaren, samme pinner)"
        if not avvik else f"avvik: {avvik}")
melding("number: 14, mode: { output: true }" in yml and P("U2").get("7") == "SKJ" and "number: 15" in yml and P("U2").get("8") == "DOKK",
        "fastvaren: GPB6 (pinne 7) = skjermstrøm, GPB7 (pinne 8) = dokken")

# 5. XIAO mot fastvaren
GP = kretser_en.GPIO
FW_NETT = {"VBAT_ADC": r"pin: GPIO(\d+)\s+# VBAT", "INT": r"wakeup_pin: \{ number: GPIO(\d+)", "LCD_DC": r"dc_pin: GPIO(\d+)",
           "LCD_RES": r"reset_pin: GPIO(\d+)", "SDA": r"sda: GPIO(\d+)", "SCL": r"scl: GPIO(\d+)", "IR_TX": r"pin: GPIO(\d+)\s+# → 100 Ω → AO3400 \(Q3\)",
           "IR_RX": r"pin: \{ number: GPIO(\d+), inverted: true \}\s+# VS1838B", "LCD_SCK": r"clk_pin: GPIO(\d+)",
           "LCD_BL": r"pin: GPIO(\d+)\s+# → 100 Ω → AO3400 \(Q2\)", "LCD_MOSI": r"mosi_pin: GPIO(\d+)"}
avvik = []
for nett, rx in FW_NETT.items():
    m = re.search(rx, yml)
    if not m or int(m.group(1)) != GP[nett]:
        avvik.append(f"{nett}: kort GPIO{GP[nett]}, fastvare {m.group(1) if m else '?'}")
    if nett not in P("U1").values():
        avvik.append(f"{nett} ikke på XIAO-en")
melding(not avvik, f"alle {len(FW_NETT)} XIAO-signalene har samme GPIO i fastvaren som på kortet" if not avvik else f"avvik: {avvik}")
XIAO_GPIO = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 43, "8": 44, "9": 7, "10": 8, "11": 9}   # Seeeds pinout D0–D10
feil = [p for p, g in XIAO_GPIO.items() if GP.get(P("U1").get(p)) != g]
melding(not feil, "XIAO-putene D0–D10 har GPIO-ene fra Seeeds pinout" if not feil else f"feil pute/GPIO: {feil}")


# 6. pull-up/-down
def mellom(a, b, verdi=None):
    return [r for r in K if r[0] == "R" and set(P(r).values()) == {a, b} and (verdi is None or K[r][1] == verdi)]


pu = {n: mellom(n, "3V3") for n in ("SDA", "SCL", "INT", "MCP_RST", "SKJ", "LCD_RES")}
pd = {n: mellom(n, "GND", "100k") for n in ("BL_G", "IR_G")}
melding(all(pu.values()) and all(pd.values()),
        "pull-up: " + ", ".join(f"{n} {v}" for n, v in pu.items()) + "; gate til GND: " + ", ".join(f"{n} {v}" for n, v in pd.items()))
melding(P("Q1") == {"1": "SKJ", "2": "3V3", "3": "3V3_SW"} and P("Q2")["2"] == "GND" and P("Q3")["2"] == "GND",
        "Q1 AO3401A: S = 3V3, D = 3V3_SW (P-kanal på høysiden); Q2/Q3 AO3400A: S = GND")


# 7. delere
def ohm(v):
    v = v.replace("R", "")
    return float(v[:-1]) * {"k": 1e3, "M": 1e6}[v[-1]] if v[-1] in "kM" else float(v)


r9, r10 = ohm(K["R9"][1]), ohm(K["R10"][1])
r11, r12 = ohm(K["R11"][1]), ohm(K["R12"][1])
vadc, vdokk = 4.2 * r10 / (r9 + r10), (5.25 - 0.3) * r12 / (r11 + r12)
melding(P("R9") == {"1": "VBAT", "2": "VBAT_ADC"} and P("R10") == {"1": "VBAT_ADC", "2": "GND"} and vadc < 2.5,
        f"batterimålingen: 4,2 V gir {vadc:.2f} V på D0 (under 2,5 V, ADC med 12 dB demping)")
melding(P("R11") == {"1": "POGO", "2": "DOKK"} and P("R12") == {"1": "DOKK", "2": "GND"} and 1.6 < vdokk < 3.3,
        f"dokkdeleren: 5,25 V gir {vdokk:.2f} V på GPB7 (høy, under 3,3 V)")
# 8. dioden (SOD-123: pinne 1 = katode)
melding(P("D1") == {"1": "VBUS", "2": "POGO"}, "D1 B5819W: anode = POGO, katode = VBUS (XIAO 5V): batteriet mater ikke pogo-pinnene")

# pinnetabellen
FUNK = {"VBAT_ADC": "batterispenning via 1 MΩ / 1 MΩ", "INT": "MCP23017 INTA (åpen drain, 10 kΩ), vekker fra dyp søvn",
        "LCD_DC": "skjerm D/C", "LCD_RES": "skjerm RESET og berøringens RST", "SDA": "I²C SDA (MCP23017 0x20, berøring 0x38)",
        "SCL": "I²C SCL", "IR_TX": "IR-sender → 100 Ω → Q3", "IR_RX": "IR-mottaker VS1838B (aktiv lav)", "LCD_SCK": "skjerm SPI SCK",
        "LCD_BL": "baklys PWM → 100 Ω → Q2", "LCD_MOSI": "skjerm SPI MOSI", "3V3": "3,3 V fra XIAO-ens regulator", "GND": "jord",
        "VBUS": "5V-puten: 5 V fra dokken via D1 (lader batteriet)"}
with open(os.path.join(HER, "pinner.csv"), "w", newline="", encoding="utf-8") as fil:
    w = csv.writer(fil)
    w.writerow(["XIAO-pute", "GPIO", "nett", "funksjon"])
    for p in map(str, range(1, 15)):
        n = P("U1")[p]
        navn = f"D{int(p) - 1}" if int(p) <= 11 else {"12": "3V3", "13": "GND", "14": "5V"}[p]
        w.writerow([navn, f"GPIO{GP[n]}" if n in GP else "", n, FUNK.get(n, "")])
    w.writerow(["BAT+ (bak)", "", "VBAT", "batteriet + (fra J1 via TP1)"])
    w.writerow(["BAT− (bak)", "", "GND", "batteriet − (fra J1 via TP2)"])
    for p in map(str, range(1, 29)):
        n = P("U2").get(p, "")
        g = f"GPA{int(p) - 21}" if int(p) >= 21 else (f"GPB{int(p) - 1}" if int(p) <= 8 else "")
        w.writerow([f"MCP23017 pinne {p}", g, n or "(åpen)", APNE.get(p, "tast" if n.startswith("K_") else "")])

# kortet
pcb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HER, "skjold-enkel.kicad_pcb")
try:
    import pcbnew
except ImportError:
    pcbnew = None
    melding(False, "pcbnew mangler: kan ikke sjekke kortet")
if pcbnew:
    b = pcbnew.LoadBoard(pcb)
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    pos = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            pos.setdefault((f.GetReference(), p.GetNumber()), (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))
    x, y = pos[("U2", "9")]
    nær = [c for c in K if c[0] == "C" and set(P(c).values()) == {"3V3", "GND"} and
           min(math.hypot(x - pos[(c, q)][0], y - pos[(c, q)][1]) for q in ("1", "2")) < 6.0]
    melding(nær, f"MCP23017 VDD har avkobling innen 6 mm ({', '.join(nær)})")
    # tastene mot taster.py
    W = taster.W if hasattr(taster, "W") else None
    avvik = []
    for f, tx, tn, p in taster.tastekort_a():
        fp = fps.get(f"SW{p + 1}")
        if fp is None:
            avvik.append(f"SW{p + 1} mangler")
            continue
        bx, by = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
        if abs(bx - tx) > 0.005 or abs(by - tn) > 0.005 or fp.GetLayer() != pcbnew.F_Cu:
            avvik.append(f"SW{p + 1} {f}: kort ({bx:.2f}, {by:.2f}), taster.py ({tx:.2f}, {tn:.2f})")
    melding(not avvik, "de 14 tastene står nøyaktig der taster.py (oppsett A) har dem, på oppsiden" if not avvik else f"avvik: {avvik}")
    avvik = []
    for f in b.GetFootprints():
        r = f.GetReference()
        for p in f.Pads():
            vil = P(r).get(p.GetNumber(), "") if r in K else ""
            har = p.GetNetname()
            if (vil or har) and vil != har:
                avvik.append(f"{r}.{p.GetNumber()}: kort {har!r}, nettliste {vil!r}")
    melding(not avvik and set(fps) == set(K), f"nettene på kortet er de samme som i nettlista ({len(fps)} deler)" if not avvik else f"avvik: {avvik[:8]}")
    b.BuildConnectivity()
    ikke = b.GetConnectivity().GetUnconnectedCount(True)
    rutet = len(b.GetTracks())
    melding(ikke == 0 and rutet > 0, f"alt er rutet ({rutet} spor/viaer, {ikke} ukoblede)")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
