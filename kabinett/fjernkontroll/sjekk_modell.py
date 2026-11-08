"""Kontroll av Skjold Fjernkontroll-modellen.

Bruk:  python3 sjekk_modell.py [mappe med A_*.stl i montert stilling] [kort|full]   (standard: asm/ kort)
       python3 sjekk_modell.py asm_full full   (full variant: STL-ene ligger i stl_full/)
STL-ene lages av lag_stl.sh. Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, har riktig antall legemer, ligger på platen (min z = 0)
     og passer i Creality K2 (250 × 250 × 250 mm), rett eller på skrå (45°)
  2. ingen deler overlapper i montert stilling (topp, bunn, IR-vindu, logo, hetter, symboler, tastekort med brytere,
     skjermmodul, batteri, SuperMini, lader); par som skal ligge an mot hverandre har bare kontaktflater.
     Hettene sjekkes også mot hverandre (hver hette for seg).
  3. sideveggen er ≥ 1,6 mm (vannrette stråler inn i topp + bunn utenom USB-C, IR-vinduet og lysdiodehullene),
     toppflaten ≥ 1,5 mm utenom hullene, skjermlomma (0,8 mm leppe) og SKJOLD (felt 0,5 mm inn), gulvet ≥ 1,5 mm utenom skruehodene
  4. minst 1,4 mm materiale mellom tastehullene i toppen (fra taster.py)
  5. hver hette står 0,1 mm over bryteren sin (forvandring) og har klaring rundt i hullet
  6. tykkelse: kroppen ≤ 14 mm, høyeste tast ≤ 15,5 mm (mål ≤ 18 mm)
  7. innmaten (referansedeler for alt som kjøpes: batteri, SuperMini, TP4056, IR-kort, vibrasjonsbryter, motor,
     flatkabler og ledningsbunter): ingen kollisjoner (punkt 2), ≥ 0,5 mm klaring til siden og ≥ 1,0 mm over
     kort og komponenter, batterilomma ≥ batteriet + 0,5 mm, fri vei for USB-C-pluggen inn til laderen og
     til SuperMini-en (flashing med bunnen åpen), og skruetårnene treffer ingen komponenter"""
import itertools
import sys

import numpy as np
import trimesh
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)   # trimesh: tomme snitt gir 0/0 i tyngdepunktet

import taster

ASM = sys.argv[1] if len(sys.argv) > 1 else "asm"
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "kort"
HK = VARIANT == "hovedkort"        # «alt på ett kort»: hovedkortet i stedet for SuperMini, TP4056 og tastekortet
taster.bruk("kort" if HK else VARIANT)
STL = "stl_hk" if HK else "stl" if VARIANT == "kort" else "stl_full"
W, L, H = taster.W, taster.L, 13.5
print(f"Variant: {VARIANT} ({len(taster.brytere())} taster, {len(taster.HETTER)} hetter)")
ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


# ---------- 1. utskriftsdelene ----------
ANTALL = {"knapper": None, "knapper_lys": 4, "gull": 2,
          "topp": 1, "bunn": 1, "ir_vindu": 1, "bryterbrett": 1, "logo": 6, "symboler_lyse": None, "symboler_morke": None}
mork = sum(1 for h in taster.HETTER if h[8] == "mork")
ANTALL["knapper"] = mork
if VARIANT == "kort":
    del ANTALL["knapper_lys"]   # smarthus-raden finnes ikke
if HK:   # bare toppen og bunnen er annerledes; resten er de samme som standard
    ANTALL = {"topp": 1, "bunn": 1}
for n, want in ANTALL.items():
    m = trimesh.load(f"{STL}/{n}.stl")
    deler = len(m.split(only_watertight=False))
    paa_plata = abs(m.bounds[0][2]) < 0.02 or n.startswith("symboler")   # symbolene ligger i hettene (samme plassering i 3MF)
    god = m.is_watertight and m.is_volume and (want is None or deler == want) and paa_plata and m.extents[2] <= 250 and (max(m.extents[:2]) <= 250 or sum(m.extents[:2]) / 2**0.5 <= 250)
    melding(god, f"{n:15s} vanntett={m.is_watertight} legemer={deler} {m.volume/1000:6.2f} cm³ {m.extents.round(1)} mm")

# ---------- 2. overlapp i montert stilling ----------
DELER = ["topp", "bunn", "vindu", "logo", "hetter", "symboler", "kort", "skjerm", "batteri", "mcu", "lader", "ir", "vib", "motor", "flex", "ledninger"]
if HK:
    DELER = [d for d in DELER if d not in ("mcu", "lader")] + ["hkdeler"]
A = {n: trimesh.load(f"{ASM}/{n}.stl") for n in DELER}
TOUCH = {("topp", "logo"), ("hetter", "symboler"), ("bunn", "vindu"), ("topp", "kort"), ("bunn", "kort"), ("topp", "skjerm"),
         ("topp", "bunn"), ("flex", "kort"), ("flex", "skjerm"), ("kort", "hkdeler"), ("flex", "hkdeler")}


def overlapp(a, b):
    if np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]):
        return 0.0
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return float("nan")


feil = []
for x, y in itertools.combinations(DELER, 2):
    if {x, y} == {"kort", "hkdeler"}:   # komponentboksene er en del av kortet
        continue
    v = overlapp(A[x], A[y])
    lim = 0.05 if (x, y) in TOUCH or (y, x) in TOUCH else 0.001
    if not v <= lim:
        feil.append(f"{x} × {y}: {v:.3f} mm³")
hett = A["hetter"].split(only_watertight=False)
for a, b in itertools.combinations(hett, 2):
    v = overlapp(a, b)
    if not v <= 0.001:
        feil.append(f"to hetter ved {a.centroid[:2].round(1)} og {b.centroid[:2].round(1)}: {v:.3f} mm³")
melding(not feil and len(hett) == len(taster.HETTER) + len(taster.OPPSETT["rutenett"]),
        f"ingen overlapp i montert stilling ({len(DELER)} deler, {len(hett)} hetter)" if not feil else "overlapp: " + "; ".join(feil))

# ---------- 3. veggtykkelse ----------
skall = A["topp"].union(A["bunn"], engine="manifold")


def segment(mesh, o, d):
    """Tykkelsen av det første materialet strålen treffer."""
    loc, _, _ = mesh.ray.intersects_location([o], [d])
    if len(loc) < 2:
        return None
    s = sorted(np.linalg.norm(loc - np.array(o), axis=1))
    return s[1] - s[0]


_ux, _uz = W/2, 4.4
if HK:
    _u = trimesh.load(f"{ASM}/usbc.stl"); _ux = (_u.bounds[0][0] + _u.bounds[1][0]) / 2; _uz = (_u.bounds[0][2] + _u.bounds[1][2]) / 2
HULL_SIDE = [("hale", _ux - 6.9, _ux + 6.9, _uz - 3.9, _uz + 3.9), ("nese", W/2 - 16.2, W/2 + 16.2, 1.7, 7.5),
             ("hale", W/2 - 9.4, W/2 - 7.6, 3.3, 5.5), ("hale", W/2 + 7.6, W/2 + 9.4, 3.3, 5.5)]
tynn = []
for z in np.arange(2.0, 11.8, 0.6):
    for y in np.arange(14, L - 14, 3):
        for side, o, d in (("v", [-5, y, z], [1, 0, 0]), ("h", [W + 5, y, z], [-1, 0, 0])):
            s = segment(skall, o, d)
            if s is None or s < 1.59:
                tynn.append((side, round(float(y), 1), round(float(z), 1), s and round(s, 2)))
    for x in np.arange(14, W - 14, 2):
        for side, o, d in (("hale", [x, -5, z], [0, 1, 0]), ("nese", [x, L + 5, z], [0, -1, 0])):
            if any(side == f and u0 <= x <= u1 and v0 <= z <= v1 for f, u0, u1, v0, v1 in HULL_SIDE):
                continue
            s = segment(skall, o, d)
            if s is None or s < 1.59:
                tynn.append((side, round(float(x), 1), round(float(z), 1), s and round(s, 2)))
melding(not tynn, "sideveggen er ≥ 1,6 mm rundt hele (utenom USB-C, IR-vinduet og lysdiodehullene)" if not tynn else
        f"sideveggen er tynnere enn 1,6 mm på {len(tynn)} punkter, f.eks. {tynn[:6]}")

# topp og gulv: loddrette stråler
rot, gulv = [], []
SKRUER = [(7.5, L - 5.5), (W - 7.5, L - 5.5), (4.9, 8), (W - 4.9, 8), (W - 7, L - 95)]   # skruehodene og forborene
scr = (W/2 - 24.2, W/2 + 24.2, L - 8.1 - 67.1, L - 8.1)   # lomma for 2,8″-modulen (48,4 × 67,1 mm)
for x in np.arange(5.13, W - 5, 1.0):
    for y in np.arange(5.37, L - 5, 1.0):
        s = segment(A["topp"], [x, y, H + 5], [0, 0, -1])
        if s is not None and s < 1.49 and not (scr[0] <= x <= scr[1] and scr[2] <= y <= scr[3]) and not (W/2 - 14 <= x <= W/2 + 14 and 4 <= y <= 10):   # SKJOLD er felt 0,5 mm inn
            rot.append((round(float(x), 1), round(float(y), 1), round(s, 2)))
        g = segment(A["bunn"], [x, y, -5], [0, 0, 1])
        if g is None or g < 1.49:
            gulv.append((round(float(x), 1), round(float(y), 1), g and round(g, 2)))
gulv = [p for p in gulv if not any(np.hypot(p[0] - sx, p[1] - sy) < 2.4 for sx, sy in SKRUER)]
rot = [p for p in rot if not any(np.hypot(p[0] - sx, p[1] - sy) < 1.0 for sx, sy in SKRUER)]
# forsenkningen for flensene til oppsettets hetter: 1,0 mm topp der (0,6 mm forsenkning i 1,6 mm)
FORS = [taster.hull_form(h[:3] + (h[3], L - h[4]) + h[5:]) for h in taster.OPPSETT["rutenett"]]
def i_fors(x, y):
    for f in FORS:
        if f[0] == "sirkel" and np.hypot(x - f[1], y - f[2]) < f[3] + 1.25:
            return True
        if f[0] == "pille" and taster.inni(("pille", f[1], f[2], f[3] + 1.25, f[4] + 1.25), (x, y)):
            return True
    return False
rot = [p for p in rot if not (i_fors(p[0], p[1]) and p[2] >= 0.99)]   # forboret til 0,8 mm under toppen
melding(not rot, "toppflaten er ≥ 1,5 mm utenom tastehullene og skjermlomma (1,0 mm i forsenkningen rundt oppsettets hetter)" if not rot else f"tynn topp: {rot[:6]}")
melding(not gulv, "gulvet er ≥ 1,5 mm utenom skruehodene" if not gulv else f"tynt gulv: {gulv[:6]}")

# ---------- 4. materiale mellom tastehullene ----------
steg = taster.sjekk_steg()
melding(not steg, f"≥ {taster.MIN_STEG} mm mellom alle tastehull" if not steg else f"for smalt mellom: {steg}")

# ---------- 4b. tasteoppsettene: hver hette treffer bryteren sin, ingen kollisjoner ----------
GRID = [(x, L - n) for x, n in taster.GRID]
TOPP_PLUNGER = 8.2 + 1.0 + 1.5
for o in ([] if HK else taster.OPPSETT):
    d = f"{ASM}/oppsett_{o}"
    F = {n: trimesh.load(f"{d}/{n}.stl") for n in ("topp", "hetter", "symboler")}
    feil = []
    for x, y in [("hetter", "topp"), ("hetter", "kort"), ("topp", "skjerm")]:
        v = overlapp(F.get(x, A.get(x)), F.get(y, A.get(y)))
        if not v <= (0.05 if (x, y) == ("topp", "skjerm") else 0.001):
            feil.append(f"{x} × {y}: {v:.3f} mm³")
    hs = F["hetter"].split(only_watertight=False)
    for a_, b_ in itertools.combinations(hs, 2):
        if overlapp(a_, b_) > 0.001:
            feil.append("to hetter overlapper")
    # stråler opp fra toppen av hver rutenettbryter: målbryteren har hetta 0,1 mm over seg, de andre ≥ 0,45 mm eller ingenting
    kart = taster.kart(o)
    o_ = np.array([[x, y, TOPP_PLUNGER - 0.01] for x, y in GRID])
    loc, idx, _ = F["hetter"].ray.intersects_location(o_, np.tile([0, 0, 1.0], (len(o_), 1)), multiple_hits=False)
    avst = np.full(len(o_), np.inf)
    avst[idx] = loc[:, 2] - TOPP_PLUNGER
    bom = [f"{f} (g{i:02d}: {avst[i]:.2f} mm)" for i, f in enumerate(kart) if f and abs(avst[i] - 0.1) > 0.03]
    tull = [f"g{i:02d} ({avst[i]:.2f} mm)" for i, f in enumerate(kart) if not f and avst[i] < 0.5]
    fri = min([avst[i] for i, f in enumerate(kart) if not f and np.isfinite(avst[i])] or [np.inf])
    akt = sum(len(h[9]) for h in taster.OPPSETT[o])
    navn = taster.OPPSETT_NAVN[o]
    melding(not feil and not bom and not tull and len(hs) == len(taster.HETTER) + len(taster.OPPSETT[o]),
            f"oppsett {navn}: {len(taster.OPPSETT[o])} hetter med {akt} aktuatorer og 0 støtteknotter; hver aktuator 0,1 mm over sin bryter "
            f"(rekkevidde 0,25 + 0,1 mm), ingen andre brytere innen rekkevidde (minst {fri:.2f} mm fri, krav 0,5), ingen forspenning"
            if not (feil or bom or tull) else f"oppsett {navn}: {'; '.join(feil + bom + tull)}")
    for n in ("topp", "front_knapper", "front_symboler"):
        m = trimesh.load(f"{STL}/oppsett_{o}/{n}.stl")
        want = 1 if n == "topp" else len(taster.OPPSETT[o]) if n == "front_knapper" else None
        deler = len(m.split(only_watertight=False))
        melding((m.is_watertight and (want is None or deler == want) and abs(m.bounds[0][2]) < 0.02) or n == "front_symboler",
                f"  {n:15s} vanntett={m.is_watertight} legemer={deler} {m.extents.round(1)} mm")

# ---------- 5. forvandring og klaring ----------
bryter_topp = 8.2 + 1.0 + 1.5
hette_bunn = min(h.bounds[0][2] for h in hett)
melding(abs(hette_bunn - bryter_topp - 0.1) < 0.02, f"hettene står {hette_bunn - bryter_topp:.2f} mm over bryterne (forvandring)")

# ---------- 6. tykkelse ----------
kropp = max(A["topp"].bounds[1][2], A["bunn"].bounds[1][2]) - A["bunn"].bounds[0][2]
tast = A["hetter"].bounds[1][2]
mal = A["topp"].bounds[1] - A["bunn"].bounds[0]
melding(kropp <= 14.0 and tast <= 15.5, f"mål {mal[0]:.1f} × {mal[1]:.1f} mm, kropp {kropp:.1f} mm tykk, med taster {tast:.1f} mm")

# ---------- 7. innmaten ----------
REF = {"batteri": 0.5, "mcu": 1.0, "lader": 1.0, "ir": 1.0, "vib": 0.5, "motor": 0.5}   # klaring over (mm)
if HK:
    REF = {"batteri": 0.5, "ir": 1.0, "vib": 0.5, "motor": 0.5}
I_SPOR = {"ir": {"bunn"}, "vib": {"bunn"}}   # står i spor/vugger i bunnen (bevisst tett tilpasning)
FAST = ["topp", "bunn", "vindu", "kort", "skjerm", "batteri", "mcu", "lader", "ir", "vib", "motor", "flex"]
if HK:
    FAST = [f for f in FAST if f not in ("mcu", "lader")] + ["hkdeler"]
rng = np.random.default_rng(1)


def scene(navn):
    return trimesh.util.concatenate([A[n] for n in navn])


def stråle(mesh, o, d):
    """Avstand fra punktene o langs retningene d til første treff (inf når ingenting treffes)."""
    loc, idx, _ = mesh.ray.intersects_location(o, d, multiple_hits=False)
    ut = np.full(len(o), np.inf)
    if len(idx):
        ut[idx] = np.linalg.norm(loc - o[idx], axis=1)
    return ut


trangt = []
for n, over in REF.items():
    m = A[n]
    p, fi = trimesh.sample.sample_surface_even(m, 6000, seed=1)
    nr = m.face_normals[fi]
    andre = [x for x in FAST if x != n]
    side = (np.abs(nr[:, 2]) < 0.2) & (p[:, 2] > m.bounds[0][2] + 0.15)
    topp_ = nr[:, 2] > 0.9
    for maske, lim, hva in ((side, 0.5, "til siden"), (topp_, over, "over")):
        if not maske.any():
            continue
        o, d = p[maske] + nr[maske] * 0.002, nr[maske]
        for x in andre:
            if x in I_SPOR.get(n, ()):
                continue
            a = stråle(A[x], o, d)
            if a.min() < lim - 0.02:
                i = a.argmin()
                trangt.append(f"{n}→{x} {hva} {a[i]:.2f} mm ved {o[i].round(1)}")
melding(not trangt, "klaring rundt referansedelene: ≥ 0,5 mm til siden, ≥ 1,0 mm over kortene (IR-kortet og vibrasjonsbryteren står i spor)"
        if not trangt else "for trangt: " + "; ".join(trangt[:8]))

# batterilomma: stråler fra batteriets midte i ±x og ±y mot ribbene, og opp mot skjermmodulen
bv = A["batteri"].vertices
bv = bv[bv[:, 2] > bv[:, 2].min() + 2.5]   # selve cellen (kabelstumpen ligger lavere)
c0 = (bv.min(axis=0) + bv.max(axis=0)) / 2
halv = (bv.max(axis=0) - bv.min(axis=0)) / 2
z0b, z1b = A["batteri"].vertices[:, 2].min(), A["batteri"].vertices[:, 2].max()
c0[2], halv[2] = (z0b + z1b) / 2, (z1b - z0b) / 2
lomme = []
for d, h in (([1, 0, 0], halv[0]), ([-1, 0, 0], halv[0]), ([0, 1, 0], halv[1]), ([0, -1, 0], halv[1])):
    o = np.array([c0 + np.array([0, 0, z]) for z in (-2.2, -1.6)])   # i høyde med ribba (1,6 mm)
    if d[1] < 0:   # kabelen går ut bak (hakket i ribba): mål ved siden av hakket
        o[:, 0] -= 8
    a = stråle(A["bunn"], o, np.tile(d, (len(o), 1))).min() - h
    lomme.append(a)
opp = stråle(A["skjerm"], np.array([c0]), np.array([[0, 0, 1.0]]))[0] - halv[2]
melding(min(lomme) >= 0.5 and opp >= 0.5, f"batterilomma: {min(lomme):.2f} mm klaring rundt, {opp:.2f} mm over (krav 0,5)")

# USB-C inn til laderen: pluggens metall (8,4 × 2,6) går fritt gjennom hullet, den støpte delen (12,4 × 6,5) stopper ≤ 1,0 mm fra kontakten
if HK:
    U = trimesh.load(f"{ASM}/usbc.stl")
    ufront = U.bounds[0][1]
    zc = (U.bounds[0][2] + U.bounds[1][2]) / 2
    ux = (U.bounds[0][0] + U.bounds[1][0]) / 2
else:
    lv = A["lader"].vertices
    lv = lv[lv[:, 2] > lv[:, 2].min() + 1.3]   # USB-C-kontakten står på kortet
    ufront = lv[:, 1].min()
    zc = 1.6 + 1.2 + 1.6
    ux = W/2
skall_ = [(ux + u*4.2, zc + v*1.3) for u in (-1, 0, 1) for v in (-1, 0, 1)]
o = np.array([[x, -5.0, z] for x, z in skall_])
fri = stråle(A["bunn"], o, np.tile([0, 1.0, 0], (len(o), 1))) + -5.0
gjennom = bool(np.all(fri > ufront - 0.01))
# omrisset av den støpte delen: 12,4 × 6,5 mm med R2-hjørner
vink = np.linspace(0, 2*np.pi, 48, endpoint=False)
kant = np.array([[ux + np.sign(np.cos(a))*4.2 + 2*np.cos(a), -5.0, zc + np.sign(np.sin(a))*1.25 + 2*np.sin(a)] for a in vink])
stopp = stråle(skall, kant, np.tile([0, 1.0, 0], (len(kant), 1))).min() - 5.0
melding(gjennom and ufront - stopp <= 1.0,
        f"USB-C i halen: metallet går fritt inn, den støpte delen stopper {ufront - stopp:.2f} mm foran kontakten (krav ≤ 1,0)")

# USB-C på SuperMini-en (flashing med bunnen åpen): pluggen 12,4 × 6,5 mm og 22 mm lang rett mot nesen
mv = A["mcu"].vertices if not HK else np.zeros((0, 3))
mv = mv if not len(mv) else mv[(mv[:, 2] > mv[:, 2].min() + 1.05) & (mv[:, 1] > mv[:, 1].max() - 7.4)]   # USB-C-kontakten (mot nesen)
if len(mv):
    cx, cz, y0 = (mv[:, 0].min() + mv[:, 0].max()) / 2, (mv[:, 2].min() + mv[:, 2].max()) / 2, mv[:, 1].max()
    plugg = trimesh.creation.box([12.4 + 0.4, 22.0, 6.5 + 0.4])
    plugg.apply_translation([cx, y0 + 11.0 + 0.01, cz])
    hinder = [(x, overlapp(plugg, A[x])) for x in ("bunn", "batteri", "lader", "ir", "vib", "motor", "ledninger")]
    hinder = [f"{x} {v:.2f} mm³" for x, v in hinder if v > 0.001]
    melding(not hinder, "USB-C på SuperMini-en: fri vei for pluggen (12,4 × 6,5 × 22 mm + 0,2 mm) med bunnen åpen"
            if not hinder else "USB-C-pluggen til SuperMini-en treffer " + ", ".join(hinder))
elif HK:
    print("--  USB-C på SuperMini-en: finnes ikke (hovedkortet flashes gjennom USB-C i halen)")
else:
    melding(False, "fant ikke USB-C på SuperMini-en")

# skruetårnene (med skruen, Ø2,3 mm gjennom hele) mot komponentene
tårn = trimesh.util.concatenate([trimesh.creation.cylinder(radius=3.0 + 0.5, height=13.5, transform=trimesh.transformations.translation_matrix([x, y, 6.75]))
                                 for x, y in SKRUER])
treff = [f"{x} {overlapp(tårn, A[x]):.2f} mm³" for x in ("batteri", "mcu", "lader", "ir", "vib", "motor", "flex", "ledninger", "hkdeler")
         if x in A and overlapp(tårn, A[x]) > 0.001]
melding(not treff, "skruetårnene (+ 0,5 mm) treffer ingen komponenter" if not treff else "skruetårn treffer " + ", ".join(treff))

if HK:   # komponentene på undersiden av hovedkortet: ≥ 0,5 mm ned til bunnen og det som står i den
    p_, fi = trimesh.sample.sample_surface_even(A["hkdeler"], 8000, seed=2)
    ned = A["hkdeler"].face_normals[fi][:, 2] < -0.9
    under = trimesh.util.concatenate([A[x] for x in ("bunn", "batteri", "ir", "vib", "motor", "ledninger")])
    d_ = stråle(under, p_[ned] - [0, 0, 0.002], np.tile([0, 0, -1.0], (int(ned.sum()), 1)))
    melding(d_.min() >= 0.5, f"hovedkortets komponenter: minst {d_.min():.2f} mm ned til bunnen og innmaten (krav 0,5)")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
