#!/usr/bin/env python3
"""KI Pultforsterker rev B – lager KiCad 7-skjemaet `ki_pultforsterker_main.kicad_sch` fra kortet.

Fasit er `ki_pultforsterker_main.kicad_pcb` (lest med pcbnew): hver footprint gir referanse, verdi, footprint og pad -> nett.
`bom.csv` gir LCSC-kode og beskrivelse. Skjemaet tegnes «label-stil»: hvert symbol får en kort ledningsstubb fra hver pinne til
en global etikett med nettnavnet, så nettlisten fra skjemaet blir identisk med kortets. Pinner uten nett får «no connect».
Delene grupperes i blokker (se BLOCKS) med overskrift og ramme, på ett ark (A2 eller A1, velges etter plass).

Symboler kommer fra KiCads standardbiblioteker (/usr/share/kicad/symbols). Deler som mangler der (TPA3116D2, PCM1808, PGA2311,
LM2662, TS3USB221, PCM2900C, Raspberry Pi-header med pinnenavn) tegnes som egne symboler i `ki_pultforsterker.kicad_sym`.
Alle brukte symboler legges også inn i `lib_symbols` i skjemaet, så fila er selvstendig.

Kjør:  python3 build_schematic.py            (bygger skjema, symbolbibliotek, sym-lib-table, eksporterer netliste og
                                               sammenligner pinne-for-pinne mot kortet, kjører ERC, lager produksjon/skjema.pdf/.svg)
       python3 build_schematic.py --check    (bare sammenligning + ERC på eksisterende skjema)

ERC: `kicad-cli sch erc` finnes fra KiCad 8 og brukes da; med KiCad 7 kjøres en innebygd kontroll (pinnematrise, strøminngang uten
driver, inngang uten driver, pinner uten nett/«no connect», dupliserte referanser). Rapport: produksjon/skjema_erc.txt.
"""
import os, sys, re, csv, copy, uuid, math, subprocess, datetime
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BASENAME = "ki_pultforsterker_main"
PCB = os.path.join(HERE, BASENAME + ".kicad_pcb")
SCH = os.path.join(HERE, BASENAME + ".kicad_sch")
BOM = os.path.join(HERE, "bom.csv")
PROJLIB_NAME = "ki_pultforsterker"
PROJLIB = os.path.join(HERE, PROJLIB_NAME + ".kicad_sym")
SYMDIR = os.environ.get("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols")
PROD = os.path.join(HERE, "produksjon")
TITLE = "KI Pultforsterker rev B"

# ---------------------------------------------------------------- s-uttrykk
class A(str):
    """Bart atom (ikke sitert) i s-uttrykket."""

def parse(text):
    tok = re.findall(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()"]+', text)
    st = [[]]
    for t in tok:
        if t == "(":
            st.append([])
        elif t == ")":
            x = st.pop(); st[-1].append(x)
        else:
            st[-1].append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\") if t.startswith('"') else A(t))
    return st[0]

def ser(x, ind=0):
    """Serialiserer med rekkefølgen bevart (KiCad er følsom for rekkefølgen i noen uttrykk)."""
    if isinstance(x, list):
        flat = "(" + " ".join(ser(y, ind + 1) for y in x) + ")"
        if len(flat) <= 90 or not any(isinstance(y, list) for y in x):
            return flat
        out, line = [], "("
        for y in x:
            if isinstance(y, list):
                out.append(line.rstrip()); line = "  " * (ind + 1) + ser(y, ind + 1)
            else:
                line += (" " if line.strip() and not line.endswith("(") else "") + ser(y)
        out.append(line.rstrip())
        return "\n".join(out) + "\n" + "  " * ind + ")"
    if isinstance(x, A):
        return str(x)
    return '"' + str(x).replace("\\", "\\\\").replace('"', '\\"') + '"'

def N(v):
    """Tall som atom, uten unødige desimaler."""
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return A(s if s not in ("-0", "") else "0")
    return A(str(v))

def L(*args):
    return [A(args[0])] + list(args[1:])

def sub(node, key):
    for y in node:
        if isinstance(y, list) and y and y[0] == key:
            return y
    return None

def subs(node, key):
    return [y for y in node if isinstance(y, list) and y and y[0] == key]

def U():
    return str(uuid.uuid4())

def font(size=1.27, hide=False, bold=False, justify=None):
    f = L("font", L("size", N(size), N(size)))
    if bold:
        f.append(A("bold"))
    e = L("effects", f)
    if justify:
        e.append(L("justify", *[A(j) for j in justify.split()]))
    if hide:
        e.append(A("hide"))
    return e

# ---------------------------------------------------------------- kortet (fasit)
def read_board():
    """ref -> dict(value, fp, pads{padnavn: nett}) for alle footprints unntatt festehull."""
    board = pcbnew.LoadBoard(PCB)
    parts = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("H"):
            continue
        pads = {}
        for p in fp.Pads():
            name = p.GetPadName()
            if not name:
                continue                                     # pasta-/maskepads uten nummer
            net = p.GetNetname()
            if name in pads and pads[name] != net and net:
                raise SystemExit(f"{ref}: pad {name} ligger på to nett ({pads[name]} / {net})")
            pads[name] = pads.get(name) or net
        parts[ref] = dict(value=fp.GetValue(), fp=str(fp.GetFPID().GetLibItemName()), pads=pads)
    return parts

def read_bom():
    out = {}
    with open(BOM, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["Designator"]] = row
    return out

def refkey(ref):
    m = re.match(r"([A-Za-z#]+)(\d*)", ref)
    return (m.group(1), int(m.group(2) or 0))

# footprint-bibliotek (kicad_pcb mangler bibliotek-nick)
FP_LIB = {
    "R_": "Resistor_SMD", "C_": "Capacitor_SMD", "CP_Elec": "Capacitor_SMD", "CP_Radial": "Capacitor_THT", "L_": "Inductor_SMD",
    "SOT-": "Package_TO_SOT_SMD", "TO-": "Package_TO_SOT_SMD", "SOIC": "Package_SO", "SSOP": "Package_SO", "TSSOP": "Package_SO",
    "HSOP": "Package_SO", "HTSSOP": "Package_SO", "Texas_RTE": "Package_DFN_QFN", "Texas_UQFN": "Package_DFN_QFN", "Texas_HSOP": "Package_SO", "UQFN": "Package_DFN_QFN", "JST_XH": "Connector_JST",
    "PinHeader": "Connector_PinHeader_2.54mm", "USB_": "Connector_USB", "TerminalBlock": "TerminalBlock", "Fuse": "Fuse",
    "Crystal": "Crystal", "Oscillator": "Oscillator", "D_": "Diode_SMD", "Relay": "Relay_THT",
}
def fp_full(fp):
    for pre, lib in FP_LIB.items():
        if fp.startswith(pre):
            return f"{lib}:{fp}"
    raise SystemExit(f"ukjent footprint-bibliotek for {fp}")

# ---------------------------------------------------------------- blokker (gruppering i skjemaet)
def rng(pre, a, b):
    return [f"{pre}{i}" for i in range(a, b + 1)]

BLOCKS = [
    ("24 V inn, vern og smart relé", ["J1", "F1", "Q11", "D5", "R79", "D1", "C1", "C110", "K1", "Q7", "D4", "R52", "R53", "Q8", "R54", "R55"]),
    ("Buck 5 V / 5 A (TPS54560) og 5 V til Pi", ["U1", "L1", "D2", "C2", "C3", "C4", "C5", "R1", "R2", "R3", "R4", "R5", "R6", "C6", "C7", "C8", "C9", "C10", "C11", "J6"]),
    ("3,3 V (alltid), −5 V (LM2662), 3,3 V_SW", ["U2", "C12", "C13", "C14", "U3", "C15", "C109", "C16", "U9", "C75", "C76"]),
    ("Raspberry Pi 40-pin", ["J5"]),
    ("DAC PCM5102A + utgangsfilter", ["U4"] + rng("C", 17, 22) + ["R7", "R8", "R9", "C23", "C24"]),
    ("Volum PGA2311 (±5 V)", ["U5", "C25", "C26", "R12", "R13"] + rng("C", 27, 31) + ["FB1", "R14", "R83"]),
    ("Hodetelefonforsterker TPA6132A2", ["U13"] + rng("C", 100, 107) + ["J23", "C108", "R76", "R77"]),
    ("Forsterker TPA3116D2 + utgangsfilter og snubber", ["U6"] + rng("C", 32, 44) + rng("R", 15, 20) + rng("C", 45, 48)
     + ["L2", "L3", "L4", "L5"] + rng("C", 49, 52) + ["R21", "C53", "R22", "C54", "R23", "C55", "R24", "C56", "J2", "J3"]),
    ("ADC PCM1808 (AUX 1) + 12,288 MHz-oscillator", ["U10", "X1"] + rng("C", 77, 82) + ["J4", "R57", "R58", "R59", "R60", "C83", "C84", "R61", "R62", "C85", "C86"]),
    ("USB-kodek PCM2900C (AUX 2)", ["U11", "Y2", "C87", "C88", "R63"] + rng("C", 89, 96) + ["R64", "R65", "R66", "J19", "J20", "R67", "R68", "R69", "R70", "C97", "C98"]),
    ("USB-delingsswitch: FE1.1s-hub, TS3USB221-mux, USB-C inn, USB-A ut",
     ["U7", "Y1", "C67", "C69", "R75", "R46", "C66", "C73", "C68", "U8", "C70", "R47", "J11", "J12", "R48", "R49", "R50", "R51", "D10", "D11",
      "J15", "D6", "J16", "D7", "J17", "D8", "J18", "D9", "F2", "C71", "C72"]),
    ("MCP23017 I/O-ekspander, knapper, encoder, knapp bak, EXP",
     ["U12", "R56", "C74", "R43", "R44", "J7"] + rng("C", 57, 61) + ["J8", "R40", "C62", "R41", "C63", "R42", "C64", "J21", "R45", "C65", "J22"]),
    ("LED-ringer (low-side AO3400)", ["J10", "Q2", "R25", "R30", "Q3", "R26", "R31", "Q4", "R27", "R32", "Q5", "R28", "R33", "Q6", "R29", "R34"]),
    ("Skjerm: OLED (I2C) og TFT (SPI + touch) med baklysdriver", ["J9", "C99", "J13", "R78", "Q9", "R71", "R72", "Q10", "R73", "R74"]),
    ("Overtemperaturvakt (NTC på kjøleribben)", ["J24", "R81", "C112", "U14", "C111", "R82"]),
]

# ---------------------------------------------------------------- symbolvalg
# ref -> (bibliotek, symbolnavn). Egne symboler ligger i PROJLIB_NAME.
def choose_symbol(ref, value):
    pfx = refkey(ref)[0]
    if ref in ("C1", "C110", "C40", "C41", "C72"):
        return ("Device", "C_Polarized")
    if pfx == "C":
        return ("Device", "C")
    if pfx == "R":
        return ("Device", "R")
    if pfx == "L":
        return ("Device", "L")
    if ref == "FB1":
        return ("Device", "FerriteBead")
    if ref == "F1":
        return ("Device", "Fuse")
    if ref == "F2":
        return ("Device", "Polyfuse")
    if ref == "D1":
        return ("Device", "D_TVS")
    if ref == "D2":
        return ("Device", "D_Schottky")
    if ref == "D4":
        return ("Device", "D")
    if ref == "D5":
        return ("Device", "D_Zener")
    if value == "USBLC6-2SC6":
        return ("Power_Protection", "USBLC6-2SC6")
    if value == "AO3400A":
        return ("Transistor_FET", "AO3400A")
    if value == "AO3401A":
        return ("Transistor_FET", "AO3401A")
    if ref == "Q11":
        return ("Device", "Q_PMOS_GDS")
    if ref == "K1":
        return ("Relay", "SANYOU_SRD_Form_C")
    if ref == "X1":
        return ("Oscillator", "ASE-xxxMHz")
    if pfx == "Y":
        return ("Device", "Crystal_GND24")
    table = {
        "U1": ("Regulator_Switching", "TPS54560BDDA"), "U2": ("Regulator_Linear", "AMS1117-3.3"), "U9": ("Regulator_Linear", "AMS1117-3.3"),
        "U3": (PROJLIB_NAME, "LM2662"), "U4": ("Audio", "PCM5102A"), "U5": (PROJLIB_NAME, "PGA2311"), "U6": (PROJLIB_NAME, "TPA3116D2DAD"),
        "U7": ("Interface_USB", "FE1.1s"), "U8": (PROJLIB_NAME, "TS3USB221"), "U10": (PROJLIB_NAME, "PCM1808"), "U11": (PROJLIB_NAME, "PCM2900C"),
        "U12": ("Interface_Expansion", "MCP23017_SS"), "U13": ("Amplifier_Audio", "TPA6132A2RTE"), "U14": ("74xGxx", "SN74LVC1G14DBV"),
        "J1": ("Connector", "Screw_Terminal_01x02"), "J2": ("Connector", "Screw_Terminal_01x02"), "J3": ("Connector", "Screw_Terminal_01x02"),
        "J6": ("Connector", "Screw_Terminal_01x02"), "J5": (PROJLIB_NAME, "RaspberryPi_40pin"),
        "J11": (PROJLIB_NAME, "USB_C_Receptacle_16P"), "J12": (PROJLIB_NAME, "USB_C_Receptacle_16P"),
        "J15": ("Connector", "USB_A"), "J16": ("Connector", "USB_A"), "J17": ("Connector", "USB_A"), "J18": ("Connector", "USB_A"),
        "J13": ("Connector_Generic", "Conn_01x14"),
    }
    if ref in table:
        return table[ref]
    if pfx == "J":
        return None  # JST XH: Conn_01xN etter antall pinner (settes av kalleren)
    raise SystemExit(f"ingen symbolregel for {ref} ({value})")

# ---------------------------------------------------------------- egne symboler
# (nummer, navn, type, side)  side: L/R/T/B
def ic(name, desc, fp, pins, width=None, keywords=""):
    sides = {"L": [], "R": [], "T": [], "B": []}
    for p in pins:
        sides[p[3]].append(p)
    cw = 1.1  # mm per tegn ved 1,27 mm tekst
    if width is None:
        wl = max([len(p[1]) for p in sides["L"]] + [0]); wr = max([len(p[1]) for p in sides["R"]] + [0])
        width = 5.08 * math.ceil(((wl + wr) * cw + 7.62) / 5.08)
    # ekstra rader øverst/nederst så loddrette pinnenavn (topp/bunn) ikke går inn i sidepinnenes navn
    mt = (math.ceil(max(len(p[1]) for p in sides["T"]) * cw / 2.54) + 1) if sides["T"] else 1
    mb = (math.ceil(max(len(p[1]) for p in sides["B"]) * cw / 2.54) + 1) if sides["B"] else 1
    nrows = max(len(sides["L"]), len(sides["R"])) + mt + mb - 1
    height = 5.08 * math.ceil(nrows * 2.54 / 5.08)
    width = max(width, 5.08 * math.ceil((max(len(sides["T"]), len(sides["B"])) + 1) * 2.54 / 5.08))
    hw, hh = width / 2, height / 2
    sym = L("symbol", name, L("pin_names", L("offset", N(1.016))), L("in_bom", A("yes")), L("on_board", A("yes")),
            L("property", "Reference", "U", L("at", N(-hw), N(hh + 1.27), N(0)), font(justify="left")),
            L("property", "Value", name, L("at", N(hw), N(-hh - 1.27), N(0)), font(justify="right")),
            L("property", "Footprint", fp, L("at", N(0), N(0), N(0)), font(hide=True)),
            L("property", "Datasheet", "~", L("at", N(0), N(0), N(0)), font(hide=True)),
            L("property", "ki_keywords", keywords, L("at", N(0), N(0), N(0)), font(hide=True)),
            L("property", "ki_description", desc, L("at", N(0), N(0), N(0)), font(hide=True)))
    body = L("symbol", f"{name}_0_1", L("rectangle", L("start", N(-hw), N(hh)), L("end", N(hw), N(-hh)),
                                        L("stroke", L("width", N(0.254)), L("type", A("default"))), L("fill", L("type", A("background")))))
    unit = L("symbol", f"{name}_1_1")
    def pin(num, nm, typ, x, y, ang):
        return L("pin", A(typ), A("line"), L("at", N(x), N(y), N(ang)), L("length", N(2.54)),
                 L("name", nm, font()), L("number", num, font()))
    for i, p in enumerate(sides["L"]):
        unit.append(pin(p[0], p[1], p[2], -hw - 2.54, hh - 2.54 * (i + mt), 0))
    for i, p in enumerate(sides["R"]):
        unit.append(pin(p[0], p[1], p[2], hw + 2.54, hh - 2.54 * (i + mt), 180))
    for i, p in enumerate(sides["T"]):
        x = -2.54 * (len(sides["T"]) - 1) / 2 + 2.54 * i
        unit.append(pin(p[0], p[1], p[2], x, hh + 2.54, 270))
    for i, p in enumerate(sides["B"]):
        x = -2.54 * (len(sides["B"]) - 1) / 2 + 2.54 * i
        unit.append(pin(p[0], p[1], p[2], x, -hh - 2.54, 90))
    sym += [body, unit]
    return sym

def custom_symbols():
    S = {}
    S["TPA3116D2DAD"] = ic("TPA3116D2DAD", "TPA3116D2 2x50 W klasse D-forsterker, HTSSOP-32 (DAD, kjøleflate på toppen)",
        "Package_SO:HTSSOP-32-1EP_6.1x11mm_P0.65mm_EP5.2x11mm_Mask4.11x4.36mm", [
        ("17", "PVCC", "power_in", "T"), ("18", "PVCC", "power_in", "T"), ("19", "PVCC", "power_in", "T"), ("31", "PVCC", "power_in", "T"), ("32", "PVCC", "power_in", "T"),
        ("7", "GVDD", "power_out", "T"),
        ("10", "LINP", "input", "L"), ("11", "LINN", "input", "L"), ("4", "RINP", "input", "L"), ("5", "RINN", "input", "L"),
        ("8", "GAIN/SLV", "input", "L"), ("6", "PLIMIT", "input", "L"), ("2", "SDZ", "input", "L"), ("12", "MUTE", "input", "L"),
        ("1", "MODSEL", "input", "L"), ("13", "AM0", "input", "L"), ("14", "AM1", "input", "L"), ("15", "AM2", "input", "L"),
        ("16", "SYNC", "bidirectional", "L"), ("3", "FAULTZ", "open_collector", "L"),
        ("20", "BSNL", "passive", "R"), ("21", "OUTNL", "output", "R"), ("24", "BSPL", "passive", "R"), ("23", "OUTPL", "output", "R"),
        ("26", "BSNR", "passive", "R"), ("27", "OUTNR", "output", "R"), ("30", "BSPR", "passive", "R"), ("29", "OUTPR", "output", "R"),
        ("9", "AGND", "power_in", "B"), ("22", "PGND", "power_in", "B"), ("25", "PGND", "power_in", "B"), ("28", "PGND", "power_in", "B"), ("33", "PAD", "passive", "B")],
        keywords="class-d audio amplifier")
    S["PCM1808"] = ic("PCM1808", "PCM1808 24-bit 96 kHz stereo I2S-ADC, TSSOP-14", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm", [
        ("3", "VCC", "power_in", "T"), ("4", "VDD", "power_in", "T"),
        ("13", "VINL", "input", "L"), ("14", "VINR", "input", "L"), ("1", "VREF", "passive", "L"), ("6", "SCKI", "input", "L"),
        ("10", "MD1", "input", "L"), ("11", "MD0", "input", "L"), ("12", "FMT", "input", "L"),
        ("8", "BCK", "bidirectional", "R"), ("7", "LRCK", "bidirectional", "R"), ("9", "DOUT", "output", "R"),
        ("2", "AGND", "power_in", "B"), ("5", "DGND", "power_in", "B")], keywords="adc audio i2s")
    S["PGA2311"] = ic("PGA2311", "PGA2311 stereo volumkontroll ±5 V, SOIC-16W", "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", [
        ("4", "VD+", "power_in", "T"), ("12", "VA+", "power_in", "T"), ("13", "VA-", "power_in", "T"),
        ("16", "VINL", "input", "L"), ("9", "VINR", "input", "L"), ("2", "~{CS}", "input", "L"), ("3", "SDI", "input", "L"),
        ("6", "SCLK", "input", "L"), ("7", "SDO", "output", "L"), ("8", "~{MUTE}", "input", "L"), ("1", "ZCEN", "input", "L"),
        ("14", "VOUTL", "output", "R"), ("11", "VOUTR", "output", "R"),
        ("5", "DGND", "power_in", "B"), ("15", "AGNDL", "power_in", "B"), ("10", "AGNDR", "power_in", "B")], keywords="volume control audio")
    S["LM2662"] = ic("LM2662", "LM2662 ladepumpe-spenningsinverter 200 mA, SOIC-8", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", [
        ("8", "V+", "power_in", "T"), ("1", "FC", "input", "L"), ("2", "CAP+", "passive", "L"), ("4", "CAP-", "passive", "L"),
        ("6", "LV", "passive", "L"), ("7", "OSC", "passive", "L"), ("5", "VOUT", "power_out", "R"), ("3", "GND", "power_in", "B")],
        keywords="charge pump inverter")
    S["TS3USB221"] = ic("TS3USB221", "TS3USB221 USB 2.0 høyhastighets 2:1-mux, UQFN-10", "Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm", [
        ("10", "VCC", "power_in", "T"), ("1", "D1+", "bidirectional", "L"), ("2", "D1-", "bidirectional", "L"), ("3", "D2+", "bidirectional", "L"),
        ("4", "D2-", "bidirectional", "L"), ("9", "S", "input", "L"), ("6", "~{OE}", "input", "L"),
        ("8", "D+", "bidirectional", "R"), ("7", "D-", "bidirectional", "R"), ("5", "GND", "power_in", "B")], keywords="usb mux switch")
    S["PCM2900C"] = ic("PCM2900C", "PCM2900C USB-lydkodek (stereo ADC/DAC, bus-powered), SSOP-28", "Package_SO:SSOP-28_5.3x10.2mm_P0.65mm", [
        ("3", "VBUS", "power_in", "T"), ("10", "VCCCI", "power_out", "T"), ("17", "VCCP1I", "power_out", "T"), ("19", "VCCP2I", "power_out", "T"),
        ("23", "VCCXI", "power_out", "T"), ("27", "VDDI", "power_out", "T"),
        ("1", "D+", "bidirectional", "L"), ("2", "D-", "bidirectional", "L"), ("5", "HID0", "input", "L"), ("6", "HID1", "input", "L"),
        ("7", "HID2", "input", "L"), ("8", "SEL0", "input", "L"), ("9", "SEL1", "input", "L"), ("21", "XTI", "input", "L"), ("20", "XTO", "output", "L"),
        ("24", "TEST0", "input", "L"), ("25", "TEST1", "no_connect", "L"), ("28", "~{SSPND}", "output", "L"),
        ("12", "VINL", "input", "R"), ("13", "VINR", "input", "R"), ("14", "VCOM", "passive", "R"), ("16", "VOUTL", "output", "R"), ("15", "VOUTR", "output", "R"),
        ("4", "DGNDU", "power_in", "B"), ("11", "AGNDC", "power_in", "B"), ("18", "AGNDP", "power_in", "B"), ("22", "AGNDX", "power_in", "B"), ("26", "DGND", "power_in", "B")],
        keywords="usb audio codec")
    # KiCads USB_C_Receptacle_USB2.0_16P stabler A4/B9/A9/B4 (VBUS) oppå hverandre, så de blir ett nett i skjemaet – kortet
    # har to nett (A4+B9 og A9+B4 er fysisk samme pad). Eget symbol med alle 16 pinner + skjerm på hver sin plass.
    S["USB_C_Receptacle_16P"] = ic("USB_C_Receptacle_16P", "USB-C-hunnkontakt 16-pinners (USB 2.0, HRO TYPE-C-31-M-12)", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", [
        ("A4", "VBUS", "passive", "L"), ("B9", "VBUS", "passive", "L"), ("A9", "VBUS", "passive", "L"), ("B4", "VBUS", "passive", "L"),
        ("A5", "CC1", "passive", "L"), ("B5", "CC2", "passive", "L"), ("A8", "SBU1", "passive", "L"), ("B8", "SBU2", "passive", "L"),
        ("A6", "D+", "passive", "R"), ("B6", "D+", "passive", "R"), ("A7", "D-", "passive", "R"), ("B7", "D-", "passive", "R"),
        ("A1", "GND", "passive", "B"), ("B1", "GND", "passive", "B"), ("A12", "GND", "passive", "B"), ("B12", "GND", "passive", "B"), ("S1", "SHIELD", "passive", "B")],
        keywords="usb-c receptacle")
    rpi = ["3V3", "5V", "GPIO2/SDA1", "5V", "GPIO3/SCL1", "GND", "GPIO4/GPCLK0", "GPIO14/TXD", "GND", "GPIO15/RXD", "GPIO17", "GPIO18/PCM_CLK",
           "GPIO27", "GND", "GPIO22", "GPIO23", "3V3", "GPIO24", "GPIO10/MOSI", "GND", "GPIO9/MISO", "GPIO25", "GPIO11/SCLK", "GPIO8/CE0",
           "GND", "GPIO7/CE1", "GPIO0/ID_SD", "GPIO1/ID_SC", "GPIO5", "GND", "GPIO6", "GPIO12/PWM0", "GPIO13/PWM1", "GND", "GPIO19/PCM_FS",
           "GPIO16", "GPIO26", "GPIO20/PCM_DIN", "GND", "GPIO21/PCM_DOUT"]
    S["RaspberryPi_40pin"] = ic("RaspberryPi_40pin", "Raspberry Pi 40-pinners GPIO-header (2x20, flatkabel) med BCM-pinnenavn",
        "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
        [(str(i + 1), rpi[i], "passive", "L" if i % 2 == 0 else "R") for i in range(40)], keywords="raspberry pi gpio header")
    return S

# ---------------------------------------------------------------- symbolbibliotek
_libcache = {}
def lib_symbols_of(lib):
    if lib not in _libcache:
        path = os.path.join(SYMDIR, lib + ".kicad_sym")
        if not os.path.exists(path):
            raise SystemExit(f"finner ikke symbolbibliotek {path}")
        doc = parse(open(path, encoding="utf-8").read())[0]
        _libcache[lib] = {x[1]: x for x in doc if isinstance(x, list) and x[0] == "symbol"}
    return _libcache[lib]

def flatten(lib, name):
    """Hent symbol fra biblioteket, slå sammen `extends`-kjeden til ett selvstendig symbol med navnet `lib:name`."""
    syms = lib_symbols_of(lib)
    if name not in syms:
        raise SystemExit(f"finner ikke symbol {lib}:{name}")
    chain = [syms[name]]
    while sub(chain[-1], "extends"):
        chain.append(syms[sub(chain[-1], "extends")[1]])
    base = copy.deepcopy(chain[-1])
    basename = base[1]
    for child in reversed(chain[:-1]):
        props = {p[1]: p for p in subs(base, "property")}
        for p in subs(child, "property"):
            if p[1] in props:
                base[base.index(props[p[1]])] = copy.deepcopy(p)
            else:
                base.append(copy.deepcopy(p))
    base = [x for x in base if not (isinstance(x, list) and x[0] == "extends")]
    base[1] = f"{lib}:{name}"
    for u in subs(base, "symbol"):
        u[1] = name + u[1][len(basename):]
    return base

def symbol_pins(sym):
    """[(nummer, navn, type, x, y, vinkel, lengde)] i bibliotekkoordinater (y opp), enhet 1."""
    out = []
    for u in subs(sym, "symbol"):
        if not re.search(r"_[01]_\d+$", u[1]):
            continue
        for p in subs(u, "pin"):
            at = sub(p, "at")
            out.append((sub(p, "number")[1], sub(p, "name")[1], str(p[1]), float(at[1]), float(at[2]), int(float(at[3])), float(sub(p, "length")[1])))
    return out

def symbol_bbox(sym):
    xs, ys = [], []
    for u in subs(sym, "symbol"):
        if not re.search(r"_[01]_\d+$", u[1]):
            continue
        for g in u:
            if not isinstance(g, list):
                continue
            if g[0] == "rectangle":
                for k in ("start", "end"):
                    xs.append(float(sub(g, k)[1])); ys.append(float(sub(g, k)[2]))
            elif g[0] in ("polyline", "bezier"):
                for xy in subs(sub(g, "pts"), "xy"):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif g[0] == "circle":
                c = sub(g, "center"); r = float(sub(g, "radius")[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif g[0] == "arc":
                for k in ("start", "mid", "end"):
                    xs.append(float(sub(g, k)[1])); ys.append(float(sub(g, k)[2]))
            elif g[0] == "pin":
                at = sub(g, "at"); ln = float(sub(g, "length")[1]); x, y, a = float(at[1]), float(at[2]), int(float(at[3]))
                dx, dy = {0: (1, 0), 180: (-1, 0), 90: (0, 1), 270: (0, -1)}[a]
                xs += [x, x + dx * ln]; ys += [y, y + dy * ln]
    return min(xs), min(ys), max(xs), max(ys)

def xform(px, py, rot):
    """Bibliotekpunkt (y opp) -> skjemaforskyvning (y ned) for rotasjon 0/90/180/270."""
    return {0: (px, -py), 90: (-py, -px), 180: (-px, py), 270: (py, px)}[rot]

# ---------------------------------------------------------------- plassering
LABEL_CH = 1.05       # mm per tegn i etikett (1,27 mm tekst)
LABEL_PAD = 3.0       # ramme/pil på global etikett
STUB = 2.54           # ledningsstubb pinne -> etikett

def snap(v, g=1.27):
    return round(round(v / g) * g, 3)

class Item:
    """Et symbol med etiketter; cellestørrelse beregnes før plassering."""
    def __init__(self, ref, lib, name, sym, value, fp, lcsc, desc, pads, rot=0, dnp=False):
        self.ref, self.lib, self.name, self.sym, self.value, self.fp, self.lcsc, self.desc, self.pads, self.rot, self.dnp = ref, lib, name, sym, value, fp, lcsc, desc, pads, rot, dnp
        self.pins = symbol_pins(sym)
        bx0, by0, bx1, by1 = symbol_bbox(sym)
        pts = [xform(x, y, rot) for x, y in ((bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1))]
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        self.body = (x0, y0, x1, y1)
        self.ends = {}          # pinnenummer -> (x, y, utover-retning dx, dy)
        for num, nm, typ, px, py, ang, ln in self.pins:
            ox, oy = {0: (-1, 0), 180: (1, 0), 90: (0, -1), 270: (0, 1)}[ang]   # utover i bibliotekkoordinater
            ex, ey = xform(px, py, rot); dx, dy = xform(ox, oy, rot)
            self.ends[num] = (ex, ey, dx, dy)
            net = pads.get(num, "")
            if net:
                ln_lab = STUB + LABEL_PAD + len(net) * LABEL_CH
                lx, ly = ex + dx * ln_lab, ey + dy * ln_lab
                x0, x1 = min(x0, lx, ex), max(x1, lx, ex); y0, y1 = min(y0, ly - 1.3, ey), max(y1, ly + 1.3, ey)
                if dy:  # vertikal etikett: bredde ca. 2,6 mm
                    x0, x1 = min(x0, ex - 1.3), max(x1, ex + 1.3)
        # referanse over, verdi under
        tw = max(len(ref), len(value)) * 1.1
        self.ref_at = (0.0, y0 - 1.6); self.val_at = (0.0, y1 + 1.6)
        y0 -= 3.2; y1 += 3.2
        x0, x1 = min(x0, -tw / 2), max(x1, tw / 2)
        self.cell = (x0 - 1.27, y0 - 1.27, x1 + 1.27, y1 + 1.27)
        self.w = self.cell[2] - self.cell[0]; self.h = self.cell[3] - self.cell[1]

def shelf_pack(items, max_w, gap=2.54):
    """Hyllepakking: store symboler (IC-er, kontakter) legges i rader; små (R/C) stables i kolonner ved siden av dem
    til radhøyden er fylt, resten i egne rader. Returnerer [(item, x, y)] relativt til (0,0) og (bredde, høyde)."""
    big = [x for x in items if x.h > 20]; small = [x for x in items if x.h <= 20]
    rows = []                                   # [høyde, bredde brukt, [(item, x, y)]]
    for it in big:
        if rows and rows[-1][1] + it.w <= max_w:
            r = rows[-1]; r[2].append((it, r[1], 0)); r[1] += it.w + gap; r[0] = max(r[0], it.h)
        else:
            rows.append([it.h, it.w + gap, [(it, 0, 0)]])
    small = list(small)
    for r in rows:                              # fyll resten av bredden med kolonner av små
        x = r[1]
        while small and x + small[0].w <= max_w:
            y, colw, placed_any = 0.0, 0.0, False
            while small and y + small[0].h <= r[0] and x + small[0].w <= max_w:
                it = small.pop(0); r[2].append((it, x, y)); y += it.h + gap; colw = max(colw, it.w); placed_any = True
            if not placed_any:
                break
            x += colw + gap
        r[1] = x
    row, rw, rh = [], 0.0, 0.0                 # resten i vanlige rader
    for it in small:
        if row and rw + it.w > max_w:
            rows.append([rh, rw, row]); row, rw, rh = [], 0.0, 0.0
        row.append((it, rw, 0)); rw += it.w + gap; rh = max(rh, it.h)
    if row:
        rows.append([rh, rw, row])
    out, y, W = [], 0.0, 0.0
    for rh, rw, placed in rows:
        for it, x, iy in placed:
            out.append((it, x, y + iy)); W = max(W, x + it.w)
        y += rh + gap
    return out, W, y - gap

# ---------------------------------------------------------------- skjemaelementer
def el_symbol(it, X, Y, root_uuid, project):
    rot = it.rot
    lib_id = f"{it.lib}:{it.name}"
    fa = 90 if rot in (90, 270) else 0      # tekst skal stå vannrett også på roterte symboler
    s = L("symbol", L("lib_id", lib_id), L("at", N(X), N(Y), N(rot)), L("unit", N(1)),
          L("in_bom", A("yes")), L("on_board", A("yes")), L("dnp", A("yes" if it.dnp else "no")), L("uuid", U()))
    def prop(name, val, x, y, hide=False):
        return L("property", name, val, L("at", N(snap(X + x)), N(snap(Y + y)), N(fa)), font(hide=hide))
    s.append(prop("Reference", it.ref, *it.ref_at))
    s.append(prop("Value", it.value, *it.val_at))
    s.append(prop("Footprint", it.fp, 0, 0, hide=True))
    s.append(prop("Datasheet", "~", 0, 0, hide=True))
    s.append(prop("LCSC", it.lcsc, 0, 0, hide=True))
    if it.desc:
        s.append(prop("Beskrivelse", it.desc, 0, 0, hide=True))
    for num, *_ in it.pins:
        s.append(L("pin", num, L("uuid", U())))
    s.append(L("instances", L("project", project, L("path", "/" + root_uuid, L("reference", it.ref), L("unit", N(1))))))
    return s

def el_wire(x1, y1, x2, y2):
    return L("wire", L("pts", L("xy", N(x1), N(y1)), L("xy", N(x2), N(y2))), L("stroke", L("width", N(0)), L("type", A("default"))), L("uuid", U()))

def el_glabel(net, x, y, dx, dy):
    ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
    just = "left" if ang in (0, 90) else "right"
    return L("global_label", net, L("shape", A("passive")), L("at", N(x), N(y), N(ang)), font(justify=just), L("uuid", U()),
             L("property", "Intersheetrefs", "${INTERSHEET_REFS}", L("at", N(x), N(y), N(0)), font(hide=True)))

def el_nc(x, y):
    return L("no_connect", L("at", N(x), N(y)), L("uuid", U()))

def el_text(txt, x, y, size=2.5, bold=True):
    return L("text", txt, L("at", N(x), N(y), N(0)), font(size=size, bold=bold, justify="left bottom"), L("uuid", U()))

def el_rect(x0, y0, x1, y1):
    return L("rectangle", L("start", N(x0), N(y0)), L("end", N(x1), N(y1)), L("stroke", L("width", N(0.3)), L("type", A("dash"))),
             L("fill", L("type", A("none"))), L("uuid", U()))

# ---------------------------------------------------------------- bygg skjemaet
PAPERS = {"A2": (594.0, 420.0), "A1": (841.0, 594.0)}

def build():
    parts = read_board()
    bom = read_bom()
    custom = custom_symbols()
    used = {}                      # lib_id -> symboldefinisjon (for lib_symbols)
    items = {}
    for ref in sorted(parts, key=refkey):
        p = parts[ref]
        sel = choose_symbol(ref, p["value"])
        if sel is None:
            sel = ("Connector_Generic", f"Conn_01x{len(p['pads']):02d}")
        lib, name = sel
        if lib == PROJLIB_NAME:
            sym = copy.deepcopy(custom[name]); sym[1] = f"{lib}:{name}"
        else:
            sym = flatten(lib, name)
        used.setdefault(f"{lib}:{name}", sym)
        pins = symbol_pins(sym)
        pin_nums = {x[0] for x in pins}
        pad_nums = set(p["pads"])
        if pin_nums != pad_nums:
            raise SystemExit(f"{ref}: symbol {lib}:{name} har pinner {sorted(pin_nums)} men kortet har pads {sorted(pad_nums)}")
        rot = 0
        if len(pins) == 2 and all(x[5] in (90, 270) for x in pins):
            rot = 90          # stående topolte (R, C, L, sikring) legges vannrett med pinne 1 til venstre
        row = bom.get(ref, {})
        items[ref] = Item(ref, lib, name, sym, p["value"], fp_full(p["fp"]), row.get("LCSC", ""), row.get("Beskrivelse", ""), p["pads"], rot,
                          dnp=(p["value"] == "DNP"))

    # PWR_FLAG på nett som har power_in-pinner men ingen power_out-pinne (ellers ERC-feil «not driven»)
    drivers, needs = set(), set()
    for it in items.values():
        for num, nm, typ, *_ in it.pins:
            net = it.pads.get(num)
            if net and typ == "power_out":
                drivers.add(net)
            if net and typ == "power_in":
                needs.add(net)
    flag_nets = sorted(needs - drivers)
    flag_sym = flatten("power", "PWR_FLAG"); used["power:PWR_FLAG"] = flag_sym
    flags = []
    for i, net in enumerate(flag_nets):
        it = Item(f"#FLG{i + 1:02d}", "power", "PWR_FLAG", flag_sym, "PWR_FLAG", "", "", "", {"1": net}, 0)
        flags.append(it)

    # blokker
    assigned = set()
    blocks = []
    for title, refs in BLOCKS:
        lst = []
        for r in refs:
            if r not in items:
                raise SystemExit(f"blokk «{title}»: {r} finnes ikke på kortet")
            if r in assigned:
                raise SystemExit(f"{r} er med i to blokker")
            assigned.add(r); lst.append(items[r])
        blocks.append((title, lst))
    rest = [items[r] for r in sorted(items, key=refkey) if r not in assigned]
    if rest:
        blocks.append(("Diverse (ikke tilordnet blokk)", rest))
    blocks.append(("Strømflagg (PWR_FLAG) for ERC", flags))

    # pakk hver blokk, så blokkene på arket
    HEAD = 7.62
    packed = []
    for title, lst in blocks:
        area = sum(x.w * x.h for x in lst) * 1.6
        maxw = min(420.0, max(150.0, math.sqrt(area * 2.5), max([x.w for x in lst] + [0]) + 2.54))
        if title.startswith("Strømflagg"):
            maxw = 400.0
        placed, W, H = shelf_pack(lst, maxw)
        packed.append((title, placed, W + 5.08, H + HEAD + 5.08))

    project = BASENAME
    root_uuid = U()
    def skyline_pack(blocks_wh, width, gap=5.08):
        """Bunn-venstre skyline-pakking i gitt rekkefølge; returnerer posisjoner og total høyde."""
        sky = [(0.0, width, 0.0)]                    # (x, bredde, y)
        pos = []
        for W, H in blocks_wh:
            best = None
            for i, (sx, sw, sy) in enumerate(sky):
                if sx + W > width + 1e-6:
                    continue
                yy, x_end, j = sy, sx + W, i
                while j < len(sky) and sky[j][0] < x_end:
                    yy = max(yy, sky[j][2]); j += 1
                if best is None or yy < best[0] - 1e-6 or (abs(yy - best[0]) < 1e-6 and sx < best[1]):
                    best = (yy, sx)
            y, x = best
            pos.append((x, y))
            new = [(x, W, y + H + gap)]
            for sx, sw, sy in sky:
                if sx + sw <= x or sx >= x + W:
                    new.append((sx, sw, sy))
                else:
                    if sx < x:
                        new.append((sx, x - sx, sy))
                    if sx + sw > x + W:
                        new.append((x + W, sx + sw - x - W, sy))
            sky = sorted(new)
            sky = [(sx, sw, sy) for sx, sw, sy in sky if sw > 1e-6]
        return pos, max(sy for _, _, sy in sky) - gap

    for paper in ("A2", "A1"):
        PW, PH = PAPERS[paper]
        margin, top, bottom = 10.16, 15.24, 40.0     # bunn: plass til tittelblokk
        pos, total_h = skyline_pack([(W, H) for _, _, W, H in packed], PW - 2 * margin)
        if total_h <= PH - top - bottom:
            break
    else:
        raise SystemExit(f"får ikke plass på A1 (trenger {total_h:.0f} mm høyde)")

    els = []
    nsym = 0
    for (title, placed, W, H), (bx, by) in zip(packed, pos):
        X0, Y0 = snap(margin + bx, 2.54), snap(top + by, 2.54)
        els.append(el_rect(X0, Y0, X0 + W, Y0 + H))
        els.append(el_text(title, X0 + 2.54, Y0 + HEAD - 1.0))
        for it, ix, iy in placed:
            ox = snap(X0 + 2.54 + ix - it.cell[0], 2.54); oy = snap(Y0 + HEAD + iy - it.cell[1], 2.54)
            els.append(el_symbol(it, ox, oy, root_uuid, project)); nsym += 1
            for num, (ex, ey, dx, dy) in it.ends.items():
                px, py = snap(ox + ex), snap(oy + ey)
                net = it.pads.get(num, "")
                if not net:
                    els.append(el_nc(px, py)); continue
                lx, ly = snap(px + dx * STUB), snap(py + dy * STUB)
                if it.lib == "power":
                    els.append(el_glabel(net, px, py, 1, 0))        # PWR_FLAG: etikett rett på pinnen
                else:
                    els.append(el_wire(px, py, lx, ly)); els.append(el_glabel(net, lx, ly, dx, dy))

    lib_symbols = L("lib_symbols", *[used[k] for k in sorted(used)])
    today = datetime.date.today().isoformat()
    doc = L("kicad_sch", L("version", N(20230121)), L("generator", A("build_schematic")), L("uuid", root_uuid), L("paper", paper),
            L("title_block", L("title", TITLE), L("date", today), L("rev", "B"), L("company", "Sebastian Kristo"),
              L("comment", N(1), "Generert av build_schematic.py fra kicad_pcb – ikke rediger for hånd"),
              L("comment", N(2), "Globale etiketter = nettnavn på kortet (verifisert pinne for pinne)")),
            lib_symbols, *els, L("sheet_instances", L("path", "/", L("page", "1"))))
    with open(SCH, "w", encoding="utf-8") as f:
        f.write(ser(doc) + "\n")

    # prosjektbibliotek med de egne symbolene + sym-lib-table
    libdoc = L("kicad_symbol_lib", L("version", N(20220914)), L("generator", A("build_schematic")), *[custom[k] for k in sorted(custom)])
    with open(PROJLIB, "w", encoding="utf-8") as f:
        f.write(ser(libdoc) + "\n")
    with open(os.path.join(HERE, "sym-lib-table"), "w", encoding="utf-8") as f:
        f.write(f'(sym_lib_table\n  (version 7)\n  (lib (name "{PROJLIB_NAME}")(type "KiCad")(uri "${{KIPRJMOD}}/{PROJLIB_NAME}.kicad_sym")(options "")(descr "Egne symboler for KI Pultforsterker"))\n)\n')
    print(f"skjema: {nsym} symboler ({len(flags)} PWR_FLAG) i {len(blocks)} blokker på {paper}, egne symboler: {', '.join(sorted(custom))}")
    return nsym

# ---------------------------------------------------------------- verifisering
def export_netlist(path):
    r = subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", path, SCH], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"kicad-cli netlist feilet: {r.stdout}{r.stderr}")
    doc = parse(open(path, encoding="utf-8").read())[0]
    sch = {}
    for net in subs(sub(doc, "nets"), "net"):
        name = sub(net, "name")[1]
        for node in subs(net, "node"):
            sch[(sub(node, "ref")[1], sub(node, "pin")[1])] = name
    return sch

def compare_netlists():
    """Sammenligner (ref, pad) -> nett mellom kortet og skjemaet. Skriver ut avvik og feiler hvis det finnes noen."""
    parts = read_board()
    board = {(ref, pad): net for ref, p in parts.items() for pad, net in p["pads"].items()}
    sch = export_netlist(os.path.join(HERE, "produksjon", "skjema_netliste.net"))
    sch = {k: ("" if v.startswith("unconnected-") else v) for k, v in sch.items() if not k[0].startswith("#")}
    diffs = []
    for key in sorted(set(board) | set(sch), key=lambda k: (refkey(k[0]), k[1])):
        b, s = board.get(key), sch.get(key)
        if b is None:
            diffs.append(f"{key[0]} pinne {key[1]}: finnes i skjemaet (nett {s!r}) men ikke på kortet")
        elif s is None:
            diffs.append(f"{key[0]} pad {key[1]}: finnes på kortet (nett {b!r}) men ikke i skjemaet")
        elif b != s:
            diffs.append(f"{key[0]} pad {key[1]}: kort {b!r} ≠ skjema {s!r}")
    for ref in parts:
        if ref not in {k[0] for k in sch}:
            diffs.append(f"{ref}: mangler i skjemaets netliste")
    bn, sn = {v for v in board.values() if v}, {v for v in sch.values() if v}
    for n in sorted(bn - sn):
        diffs.append(f"nett {n!r} finnes bare på kortet")
    for n in sorted(sn - bn):
        diffs.append(f"nett {n!r} finnes bare i skjemaet")
    for d in diffs:
        print("AVVIK:", d)
    print(f"netlistesammenligning: {len(board)} pads på {len(parts)} deler, {len(bn)} nett – {len(diffs)} avvik")
    if diffs:
        raise SystemExit("skjemaet stemmer ikke med kortet")

# ERC. kicad-cli fikk `sch erc` først i KiCad 8; med KiCad 7 kjøres en innebygd kontroll med de samme reglene som betyr noe her:
# KiCads standard pinnematrise (konflikter mellom pinnetyper på samme nett), strøminngang uten driver (feil), inngang uten driver
# (advarsel), pinner uten nett og uten «no connect», dupliserte referanser, og nettnavn som bare skiller seg i store/små bokstaver.
PIN_TYPES = ["input", "output", "bidirectional", "tri_state", "passive", "unspecified", "power_in", "power_out", "open_collector", "open_emitter", "no_connect"]
_O, _W, _E = 0, 1, 2
PIN_MATRIX = [  # fra KiCad erc_settings.cpp (rad/kolonne i PIN_TYPES-rekkefølge)
    [_O, _O, _O, _O, _O, _W, _O, _O, _O, _O, _E],
    [_O, _E, _O, _W, _O, _W, _O, _E, _E, _E, _E],
    [_O, _O, _O, _O, _O, _W, _O, _W, _O, _W, _E],
    [_O, _W, _O, _O, _O, _W, _W, _E, _W, _W, _E],
    [_O, _O, _O, _O, _O, _W, _O, _O, _O, _O, _E],
    [_W, _W, _W, _W, _W, _W, _W, _W, _W, _W, _E],
    [_O, _O, _O, _W, _O, _W, _O, _O, _O, _O, _E],
    [_O, _E, _W, _E, _O, _W, _O, _E, _E, _E, _E],
    [_O, _E, _O, _W, _O, _W, _O, _E, _O, _O, _E],
    [_O, _E, _W, _W, _O, _W, _O, _E, _O, _O, _E],
    [_E, _E, _E, _E, _E, _E, _E, _E, _E, _E, _E],
]
DRIVERS = {"output", "bidirectional", "tri_state", "power_out", "open_collector", "open_emitter"}

def builtin_erc(rep):
    doc = parse(open(SCH, encoding="utf-8").read())[0]
    libs = {s[1]: s for s in subs(sub(doc, "lib_symbols"), "symbol")}
    pintype = {k: {p[0]: p[2] for p in symbol_pins(v)} for k, v in libs.items()}
    pinpos = {}       # (ref, pin) -> posisjon i skjemaet
    refs, refcount = {}, {}
    for s in subs(doc, "symbol"):
        ref = sub(sub(sub(sub(s, "instances"), "project"), "path"), "reference")[1]
        refcount[ref] = refcount.get(ref, 0) + 1
        at = sub(s, "at"); X, Y, rot = float(at[1]), float(at[2]), int(float(at[3]))
        for num, nm, typ, px, py, ang, ln in symbol_pins(libs[sub(s, "lib_id")[1]]):
            ex, ey = xform(px, py, rot)
            pinpos[(ref, num)] = (round(X + ex, 2), round(Y + ey, 2))
            refs[(ref, num)] = typ
    ncs = {(round(float(sub(n, "at")[1]), 2), round(float(sub(n, "at")[2]), 2)) for n in subs(doc, "no_connect")}
    sch = export_netlist(os.path.join(HERE, "produksjon", "skjema_netliste.net"))
    # strømsymboler (#FLG…) er ikke med i netlisten: finn nettet via den globale etiketten som står på pinnen
    labels = {(round(float(sub(g, "at")[1]), 2), round(float(sub(g, "at")[2]), 2)): g[1] for g in subs(doc, "global_label")}
    for (ref, pin), typ in refs.items():
        if ref.startswith("#") and pinpos[(ref, pin)] in labels:
            sch[(ref, pin)] = labels[pinpos[(ref, pin)]]
    nets = {}
    for (ref, pin), name in sch.items():
        if name.startswith("unconnected-"):
            continue
        nets.setdefault(name, []).append((ref, pin, refs.get((ref, pin), "passive")))
    errors, warnings = [], []
    for (ref, pin), typ in refs.items():
        if sch.get((ref, pin), "unconnected-").startswith("unconnected-") and pinpos[(ref, pin)] not in ncs and typ != "no_connect":
            errors.append(f"[pin_not_connected] {ref} pinne {pin} ({typ}) er ikke koblet og har ikke «no connect»")
        if typ == "no_connect" and not sch.get((ref, pin), "unconnected-").startswith("unconnected-"):
            errors.append(f"[nc_pin_connected] {ref} pinne {pin} er NC-pinne men ligger på nett {sch[(ref, pin)]}")
    for ref, n in refcount.items():
        if n > 1 and not ref.startswith("#"):
            errors.append(f"[duplicate_reference] {ref} forekommer {n} ganger")
    lower = {}
    for name in nets:
        lower.setdefault(name.lower(), []).append(name)
    for k, v in lower.items():
        if len(v) > 1:
            warnings.append(f"[similar_labels] nettnavn som bare skiller seg i store/små bokstaver: {', '.join(v)}")
    for name, pins in sorted(nets.items()):
        types = [t for _, _, t in pins]
        has_driver = any(t in DRIVERS for t in types) or any(r.startswith("#FLG") for r, _, _ in pins)
        if "power_in" in types and not has_driver:
            errors.append(f"[power_pin_not_driven] nett {name}: strøminngang uten driver (power_out/PWR_FLAG)")
        if "input" in types and not has_driver:
            warnings.append(f"[pin_not_driven] nett {name}: inngang(er) uten driver: " + ", ".join(f"{r}.{p}" for r, p, t in pins if t == "input"))
        for i in range(len(pins)):
            for j in range(i + 1, len(pins)):
                a, b = pins[i], pins[j]
                sev = PIN_MATRIX[PIN_TYPES.index(a[2])][PIN_TYPES.index(b[2])]
                if sev == _E:
                    errors.append(f"[pin_to_pin] nett {name}: {a[0]}.{a[1]} ({a[2]}) mot {b[0]}.{b[1]} ({b[2]})")
                elif sev == _W:
                    warnings.append(f"[pin_to_pin] nett {name}: {a[0]}.{a[1]} ({a[2]}) mot {b[0]}.{b[1]} ({b[2]})")
    with open(rep, "w", encoding="utf-8") as f:
        f.write(f"ERC report (innebygd kontroll i build_schematic.py – kicad-cli {kicad_version()} har ikke `sch erc`)\n")
        f.write(f"Source: {SCH}\n\n")
        for e in errors:
            f.write("ERROR " + e + "\n")
        for w in warnings:
            f.write("WARNING " + w + "\n")
        f.write(f"\n ** ERC messages: {len(errors) + len(warnings)}  Errors {len(errors)}  Warnings {len(warnings)}\n")
    return len(errors), len(warnings), errors, warnings

def kicad_version():
    r = subprocess.run(["kicad-cli", "version"], capture_output=True, text=True)
    return r.stdout.strip()

def run_erc():
    rep = os.path.join(HERE, "produksjon", "skjema_erc.txt")
    major = int(kicad_version().split(".")[0] or 0)
    if major >= 8:
        r = subprocess.run(["kicad-cli", "sch", "erc", "--format", "report", "--severity-all", "-o", rep, SCH], capture_output=True, text=True)
        txt = open(rep, encoding="utf-8").read() if os.path.exists(rep) else ""
        m = re.search(r"Errors (\d+).*?Warnings (\d+)", txt, re.S)
        err, warn = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
        print(f"ERC (kicad-cli): {err} feil, {warn} advarsler – rapport: {rep}")
        return err, warn
    err, warn, errors, warnings = builtin_erc(rep)
    kinds = {}
    for k in re.findall(r"\[(\w+)\]", "\n".join(errors + warnings)):
        kinds[k] = kinds.get(k, 0) + 1
    print(f"ERC (innebygd, KiCad {kicad_version()} mangler `sch erc`): {err} feil, {warn} advarsler"
          + (f" ({', '.join(f'{k}: {v}' for k, v in sorted(kinds.items()))})" if kinds else "") + f" – rapport: {rep}")
    for e in errors:
        print("  ERC-FEIL:", e)
    return err, warn

def export_drawings():
    os.makedirs(PROD, exist_ok=True)
    for fmt, out in (("pdf", os.path.join(PROD, "skjema.pdf")), ("svg", PROD)):
        r = subprocess.run(["kicad-cli", "sch", "export", fmt, "--no-background-color", "-o", out, SCH], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"kicad-cli export {fmt} feilet: {r.stdout}{r.stderr}")
    svg = os.path.join(PROD, BASENAME + ".svg")
    if os.path.exists(svg):
        os.replace(svg, os.path.join(PROD, "skjema.svg"))
    print(f"tegninger: {os.path.join(PROD, 'skjema.pdf')}, {os.path.join(PROD, 'skjema.svg')}")

if __name__ == "__main__":
    os.makedirs(PROD, exist_ok=True)
    if "--check" not in sys.argv:
        build()
    compare_netlists()
    run_erc()
    if "--check" not in sys.argv:
        export_drawings()
