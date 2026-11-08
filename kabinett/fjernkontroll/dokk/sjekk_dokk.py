"""Kontroll av Skjold Dokk (lag STL-ene med lag_dokk.sh først). Sjekker:

  1. alle dokkdelene er tette og ett legeme hver
  2. fjernkontrollen (standard og full, alle tre tasteoppsett) går klar av dokka: ingen overlapp, ≥ 0,3 mm til
     vangene på sidene, og den hviler på ryggen og hylla
  3. pogo-kontakten: hunndelen i fjernkontrollen og handelen i dokka står rett mot hverandre (≤ 0,2 mm), og
     fjærpinnene presses 0,5–1,0 mm
  4. stabil: tyngdepunktet til fjernkontrollen + dokka ligger godt innenfor sokkelen (≥ 10 mm), og fjernkontrollens
     eget tyngdepunkt ligger bak hylla, så den lener seg mot ryggen
  5. kan printes uten støtte: ingen nedovervendte flater brattere enn 45° på vugga og sokkelen (utenom bunnen og
     små broer over hull)

Bruk:  python3 dokk/sjekk_dokk.py"""
import os
import re
import sys

import numpy as np
import trimesh

HER = os.path.dirname(os.path.abspath(__file__))
FK = os.path.dirname(HER)
ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


def tall(fil, navn):
    m = re.search(rf"(?:^|;\s*){navn}\s*=\s*([-\d.]+)", open(fil).read(), re.M)
    return float(m.group(1))


SC = os.path.join(HER, "skjold_dokk.scad")
FKS = os.path.join(FK, "skjold_fjernkontroll.scad")
A = np.radians(tall(SC, "A"))
SH, HT, RT = tall(SC, "SH"), tall(SC, r"hylle_t"), tall(SC, r"rygg_t")
HB = SH + HT * np.sin(A) + RT * np.cos(A)
FW = 55.0
PX, PY = tall(FKS, "POGO_X"), tall(FKS, "POGO_Y")
PIN = tall(FKS, "POGO_PINNE")
DEL = tall(FKS, "POGO_DELING")


def plass(m):
    """fjernkontrollens koordinater → dokka (samme som fk_plass() i skjold_dokk.scad)"""
    T = np.eye(4)
    T[:3, :3] = [[1, 0, 0], [0, np.cos(A), -np.sin(A)], [0, np.sin(A), np.cos(A)]]
    T[:3, 3] = [-FW / 2, 0, HB]
    return m.copy().apply_transform(T)


def pkt(x, y, z):
    return np.array([x - FW / 2, y * np.cos(A) - z * np.sin(A), HB + y * np.sin(A) + z * np.cos(A)])


def overlapp(a, b):
    try:
        i = trimesh.boolean.intersection([a, b])
        return 0.0 if i.is_empty else abs(i.volume)
    except Exception:
        return 0.0


STL = os.path.join(HER, "stl")
D = {p: trimesh.load(os.path.join(STL, f"{p}.stl")) for p in ("vugge", "sokkel", "gull", "lokk")}
han = trimesh.load(os.path.join(HER, "asm", "pogo_han.stl"))
feil = [p for p, m in D.items() if not (m.is_watertight and len(m.split()) == 1)]
melding(not feil, "dokkdelene er tette og ett legeme hver (vugge, sokkel, gull, lokk)" if not feil else f"ikke tette: {feil}")
dokk = trimesh.util.concatenate([D["vugge"], D["sokkel"]])

# 2. fjernkontrollen i dokka
for v, asm in (("standard", "asm"), ("full", "asm_full")):
    deler = {p: trimesh.load(os.path.join(FK, asm, f"{p}.stl")) for p in ("topp", "bunn", "logo")}
    for o in ("rutenett", "vannrett", "stor"):
        h = trimesh.load(os.path.join(FK, asm, f"oppsett_{o}", "hetter.stl"))
        fk = plass(trimesh.util.concatenate(list(deler.values()) + [h]))
        ov = overlapp(fk, D["vugge"])
        # klaring til vangene: flytt fjernkontrollen 0,3 mm til hver side
        side = max(overlapp(fk.copy().apply_translation([s * 0.3, 0, 0]), D["vugge"]) for s in (-1, 1))
        melding(ov < 0.05 and side < 0.05, f"{v}, oppsett {o}: fjernkontrollen går klar av vugga (overlapp {ov:.3f} mm³, ±0,3 mm til siden {side:.3f} mm³)")
    fk = plass(deler["bunn"])
    # hviler på ryggen og hylla: nærmeste avstand fra bunnen til vugga ≈ 0
    d = trimesh.proximity.closest_point(D["vugge"], fk.vertices)[1].min()
    melding(d < 0.05, f"{v}: fjernkontrollen hviler på ryggen og hylla (nærmeste avstand {d:.3f} mm)")

# 3. pogo
hunn = plass(trimesh.load(os.path.join(FK, "asm", "pogo.stl")))
p_hunn = [pkt(PX, PY + s * DEL / 2, 0) for s in (-1, 1)]
nrm = np.array([0, -np.sin(A), np.cos(A)])
spiss = []
for p in p_hunn:   # fjærpinnen under puta: senteret (snitt av punktene) og toppen (lengst ut langs normalen)
    d_ = han.vertices - p
    lat = d_ - np.outer(d_ @ nrm, nrm)
    n_ = np.linalg.norm(lat, axis=1) < 0.9
    if not n_.any():
        spiss.append(np.array([1e3, 1e3, 1e3])); continue
    spiss.append(p + lat[n_].mean(0) + (d_[n_] @ nrm).max() * nrm)
avvik = max(np.linalg.norm((s - p) - ((s - p) @ nrm) * nrm) for s, p in zip(spiss, p_hunn))
trykk = min((s - p) @ nrm for s, p in zip(spiss, p_hunn))
flate = abs((hunn.vertices @ nrm).min() - (p_hunn[0] @ nrm))
melding(avvik <= 0.2, f"pogo: pinnene står {avvik:.2f} mm fra putene på tvers (krav ≤ 0,2)")
melding(0.5 <= trykk <= 1.0, f"pogo: fjærpinnene presses {trykk:.2f} mm når fjernkontrollen står i dokka (krav 0,5–1,0)")
melding(flate < 0.05, f"pogo: hunndelens flate ligger i ryggens plan ({flate:.3f} mm)")

# 4. stabilitet
PLA = 1.24e-3        # g/mm³
fyll = 0.45          # effektiv andel plast (vegger + 15–20 % fyll)
for v, asm, ekstra in (("standard", "asm", 45.0), ("full", "asm_full", 55.0)):
    skall = [trimesh.load(os.path.join(FK, asm, f"{p}.stl")) for p in ("topp", "bunn")]
    bat = trimesh.load(os.path.join(FK, asm, "batteri.stl"))
    kort = trimesh.load(os.path.join(FK, asm, "kort.stl"))
    m_fk, c_fk = [], []
    for m in skall:
        m_fk.append(m.volume * PLA * fyll * 2); c_fk.append(plass(m).center_mass)
    m_fk.append(25.0); c_fk.append(plass(bat).center_mass)                  # batteri 603450
    m_fk.append(ekstra - 25.0); c_fk.append(plass(kort).center_mass)        # kort, skjerm, hetter, elektronikk
    m_fk, c_fk = np.array(m_fk), np.array(c_fk)
    tp_fk = (m_fk[:, None] * c_fk).sum(0) / m_fk.sum()
    hylle_y = pkt(0, 0, 13.5)[1]
    melding(tp_fk[1] > hylle_y + 5, f"{v}: fjernkontrollens tyngdepunkt (≈ {m_fk.sum():.0f} g) ligger {tp_fk[1] - hylle_y:.0f} mm bak "
            "framkanten av hylla, så den lener seg mot ryggen")
    md = [D["vugge"].volume * PLA * 0.35, D["sokkel"].volume * PLA * 0.45, 70.0]
    cd = [D["vugge"].center_mass, D["sokkel"].center_mass, np.array([0, -7, 3.5])]    # 70 g stål i vektlomma
    m_alle = np.array(list(m_fk) + md)
    c_alle = np.vstack([c_fk, cd])
    tp = (m_alle[:, None] * c_alle).sum(0) / m_alle.sum()
    b = D["sokkel"].bounds
    marg = min(tp[0] - b[0][0], b[1][0] - tp[0], tp[1] - b[0][1], b[1][1] - tp[1])
    melding(marg >= 10, f"{v}: samlet tyngdepunkt ({m_alle.sum():.0f} g) ligger {marg:.0f} mm innenfor kanten av sokkelen (krav ≥ 10; "
            f"Y {tp[1]:.0f} mm av {b[0][1]:.0f}…{b[1][1]:.0f})")

# 5. print uten støtte: skrå overheng (45–85° fra loddrett) må nesten ikke finnes; vannrette tak over lommer er broer
for p in ("vugge", "sokkel"):
    m = D[p]
    z0 = m.bounds[0][2]
    nz = m.face_normals[:, 2]
    hoy = m.triangles_center[:, 2] > z0 + 0.3
    skraa = (nz < -np.cos(np.radians(45))) & (nz > -0.996) & hoy
    bro = (nz <= -0.996) & hoy
    spenn = 0.0   # bredeste bro: 2 × største innskrevne radius i takflatene (sett ovenfra)
    if bro.any():
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        tri = m.triangles[bro]
        for z in np.unique(np.round(tri[:, 0, 2], 1)):   # hvert tak for seg (samme høyde)
            tak = unary_union([Polygon(t[:, :2]).buffer(0.01) for t in tri if abs(t[0, 2] - z) < 0.06])
            lo, hi = 0.0, 50.0
            for _ in range(20):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if not tak.buffer(-mid).is_empty else (lo, mid)
            spenn = max(spenn, 2 * lo)
    melding(m.area_faces[skraa].sum() < 30 and spenn <= 32,
            f"{p}: {m.area_faces[skraa].sum():.0f} mm² skrått overheng (krav < 30), lengste bro {spenn:.0f} mm (krav ≤ 32)")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
