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
  6. IR i den stående og den flate dokka (stl_ir/, stl_flat_ir/): tette deler, delene får plass, frie ledningskanaler,
     lysdiodene ≥ 0,5 mm fra bunnplata, fri sikt bakover, romslige lommer, ingen støtte; USB-C-åpningene i den flate går gjennom

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

# 6. IR i dokkene (stl_ir/, stl_flat_ir/ og asm/*ir_*.stl fra lag_dokk.sh): tette deler, de kjøpte delene får plass,
#    ledningskanalene er frie, flensen på lysdiodene står ≥ 0,5 mm fra bunnplata, fri sikt bakover (kjegle ±17° som
#    TSAL6200), romslige lommer (C3: ≥ 4 mm til pinneradene og over loddepunktene, driverkammer ≥ 20 × 12 × 7,5 mm),
#    og print uten støtte (toppdelen står på delingsflaten i z = 2)
def bro(m):
    """bredeste flate bro (2 × største innskrevne radius i takflatene, sett ovenfra) og skrått overheng i mm²"""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    z0 = m.bounds[0][2]
    nz = m.face_normals[:, 2]
    hoy = m.triangles_center[:, 2] > z0 + 0.3
    skraa = m.area_faces[(nz < -np.cos(np.radians(45))) & (nz > -0.996) & hoy].sum()
    tri = m.triangles[(nz <= -0.996) & hoy]
    spenn = 0.0
    for z in np.unique(np.round(tri[:, 0, 2], 1)):
        tak = unary_union([Polygon(t[:, :2]).buffer(0.01) for t in tri if abs(t[0, 2] - z) < 0.06])
        lo, hi = 0.0, 50.0
        for _ in range(20):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not tak.buffer(-mid).is_empty else (lo, mid)
        spenn = max(spenn, 2 * lo)
    return skraa, spenn


def kjegle(starter, hinder, halv=17):
    treff = n = 0
    for start, akse in starter:
        u = np.cross(akse, [0, 0, 1]); u /= np.linalg.norm(u); w = np.cross(akse, u)
        for a in np.radians([0, 6, 12, halv]):
            for b in np.radians(np.arange(0, 360, 30)):
                r = np.cos(a) * akse + np.sin(a) * (np.cos(b) * u + np.sin(b) * w)
                n += 1
                treff += len(hinder.ray.intersects_location([start], [r])[0]) > 0
    return treff, n


def ir_sjekk(navn, topp, bunn, deler, kanaler, leds, hinder_ekstra, fil):
    m = trimesh.load(topp)
    bunn = trimesh.load(bunn)
    biter = [b for b in m.split(only_watertight=False) if abs(b.volume) >= 0.01]
    melding(m.is_watertight and len(biter) == 1, f"IR {navn}: {os.path.basename(topp)} er tett og ett legeme")
    d_alle = trimesh.load(deler)
    feil, flens = [], 99.0
    for d in d_alle.split(only_watertight=False):
        if d.volume < 0.05:
            continue
        v = max(overlapp(d, m), overlapp(d, bunn))
        if v > 0.6:   # USB-C-kontaktene stikker litt inn i åpningen (0,1–0,5 mm³)
            feil.append(f"del ved {np.round(d.centroid, 1)}: {v:.2f} mm³")
    for p0, akse in leds:   # lysdiodene: delene nær hullet i ytterflaten
        nær = [d for d in d_alle.split(only_watertight=False) if np.linalg.norm(d.centroid - p0) < 9]
        for d in nær:
            flens = min(flens, trimesh.proximity.closest_point(bunn, d.vertices)[1].min())
    melding(not feil, f"IR {navn}: C3, lysdiodene, VS1838B, driverkortet og USB-C-brikken får plass" + ("" if not feil else ": " + "; ".join(feil)))
    melding(flens >= 0.5, f"IR {navn}: lysdiodene står {flens:.2f} mm fra bunnplata (krav ≥ 0,5)")
    k = trimesh.load(kanaler)
    vk = overlapp(k, m) + overlapp(k, d_alle)
    melding(vk < 0.05, f"IR {navn}: ledningskanalene ({tall(fil, 'ir_kanal_b')} mm, avrundet) er frie hele veien ({vk:.3f} mm³ i veien)")
    t, n = kjegle([(p0 + akse * 0.4, akse) for p0, akse in leds], trimesh.util.concatenate([m] + hinder_ekstra))
    melding(t == 0, f"IR {navn}: fri sikt fra lysdiodene (±17°): {t} av {n} stråler treffer dokka")
    skraa, spenn = bro(m)
    melding(skraa < 30 and spenn <= 32, f"IR {navn}: {skraa:.0f} mm² skrått overheng (krav < 30), lengste bro {spenn:.0f} mm (krav ≤ 32)")


def akse(yaw, vinkel):
    y, v = np.radians(yaw), np.radians(vinkel)
    return np.array([np.sin(y) * np.cos(v), -np.cos(y) * np.cos(v), np.sin(v)])


if os.path.isdir(os.path.join(HER, "stl_ir")):
    vk, sp, irX, irz = (tall(SC, n) for n in ("ir_vinkel", "ir_spre", "ir_X", "ir_z"))
    SY1, SB, sideY = tall(SC, "SY1"), tall(SC, "SB"), tall(SC, "ir_side_Y")
    bak = [(np.array([-irX, SY1, irz]), akse(180 + sp, vk)), (np.array([irX, SY1, irz]), akse(180 - sp, vk))]
    for v, ekstra in (("", []), ("_side", [(np.array([SB / 2, sideY, irz]), akse(90, vk))])):
        ir_sjekk("stående" + (" (side)" if v else ""), os.path.join(HER, "stl_ir", f"sokkel_topp{v}.stl"), os.path.join(HER, "stl_ir", "sokkel_bunn.stl"),
                 os.path.join(HER, "asm", f"ir_deler{v}.stl"), os.path.join(HER, "asm", f"ir_kanaler{v}.stl"), bak + ekstra, [D["vugge"]], SC)
    tak, dz, c3b, lomme = tall(SC, "ir_tak"), tall(SC, "delt_z"), 18.0, 26.0
    kx0, ky0, kx1, ky1 = (float(x) for x in re.search(r"ir_kam = \[([-\d., ]+)\]", open(SC).read()).group(1).split(","))
    melding(tak - dz - 1.0 >= 4 and (lomme - c3b) / 2 >= 4 and kx1 - kx0 >= 20 and ky1 - ky0 >= 12 and tak - dz >= 7.5,
            f"IR stående: C3-lomma har {(lomme - c3b) / 2:.1f} mm langs pinneradene og {tak - dz - 1.0:.1f} mm over loddepunktene; "
            f"driverkammeret er {kx1 - kx0:.0f} × {ky1 - ky0:.0f} × {tak - dz:.0f} mm")
FL_SC = os.path.join(HER, "skjold_dokk_flat.scad")
if os.path.isdir(os.path.join(HER, "stl_flat_ir")):
    kant = tall(FL_SC, "kant")
    vk, sp, irz = (tall(FL_SC, n) for n in ("ir_vinkel", "ir_spre", "ir_z"))
    xs = [float(x) for x in re.search(r"ir_x = \[([-\d., ]+)\]", open(FL_SC).read()).group(1).split(",")]
    hale = [(np.array([xs[0], -2 * kant, irz]), akse(-sp, vk)), (np.array([xs[1], -2 * kant, irz]), akse(sp, vk))]
    ir_sjekk("flat", os.path.join(HER, "stl_flat_ir", "brett.stl"), os.path.join(HER, "stl_flat_ir", "bunnplate.stl"),
             os.path.join(HER, "asm", "flat_ir_deler.stl"), os.path.join(HER, "asm", "flat_ir_kanaler.stl"), hale, [], FL_SC)
    # USB-C-åpningene går gjennom endeveggen (brikken i dokka og sporet for fjernkontrollens plugg)
    for d in ("stl_flat", "stl_flat_ir"):
        b = trimesh.load(os.path.join(HER, d, "brett.stl"))
        gulv = 11.0 if d == "stl_flat_ir" else 9.0
        apen = not b.contains([[10, -2 * kant + 0.3, 5.5], [27.5, -2 * kant + 0.3, gulv + 4.7]]).any()
        melding(apen, f"{d}: USB-C-åpningene går gjennom endeveggen")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
