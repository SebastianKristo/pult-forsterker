"""Lag 3MF-platene for Skjold Fjernkontroll (Creality K2 / K2 Pro / K2 Plus, 250 × 250 mm):

  skjold-fjernkontroll-k2.3mf         topp (forsiden ned) med SKJOLD i gull, og bunn          filament 1 lys · 2 mørk · 3 gull
  skjold-fjernkontroll-k2-taster.3mf  alle hetter (flensen ned) med symbolene felt inn, gullring
                                      og Skjold-tast, smarthus-tastene i lys farge, og IR-vinduet  1 lys · 2 mørk · 3 gull · 4 klar
  skjold-fjernkontroll-k2-taster-uten-gull.3mf  alle de mørke tastene i oppsett A på én plate (power, meny, OK og
                                      tilbake/exit, spill/pause, demp, volum) – uten gullringen og Skjold-tasten  1 lys · 2 mørk

Standard er kort variant (uten talltastene og smarthus-raden), fra stl/. Full variant: samme tre plater med «-full»
i navnet, fra stl_full/.
Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py   (eller ./lag_stl.sh, som gjør alt)
Hver del får filamentnummer i Metadata/model_settings.config (Creality Print / OrcaSlicer).
Mørk variant: bytt filament 1 og 2 i sliceren (mørk topp, lys bunn og lyse taster med mørke symboler).
Hettene ligger i samme mønster som på fjernkontrollen (spredt litt ut), så de er lette å finne igjen."""
import itertools
import math
import zipfile

import trimesh

import taster
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)   # trimesh: tomme snitt gir 0/0 i tyngdepunktet

BED = 250
# fil, navn, filament, min-hjørne (x, y) eller None, «samme flytt som»
PLATES = {
    "skjold-fjernkontroll-k2.3mf": ("Skjold Fjernkontroll – topp og bunn (PLA/PETG)", [
        ("topp", "Topp (forsiden ned)", 1, (172, 12), None),   # til høyre, unna sideviften på K2
        ("logo", "SKJOLD (gull, felt inn i toppen)", 3, None, "topp"),
        ("orer", "Museører (holder halen nede, vris av etter print)", 1, None, "topp"),
        ("bunn", "Bunn", 2, (95, 12), None),
    ], {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40"}),
    "skjold-fjernkontroll-k2-taster.3mf": ("Skjold Fjernkontroll – taster og IR-vindu", [
        ("knapper", "Taster (mørke, flensen ned)", 2, (40, 30), None),
        ("symboler_lyse", "Symboler på de mørke tastene", 1, None, "knapper"),
        ("knapper_lys", "Smarthus-taster (lyse)", 1, None, "knapper"),
        ("symboler_morke", "Symboler på de lyse tastene og Skjold-tasten", 2, None, "knapper"),
        ("gull", "Gullring (D-pad) og Skjold-tast", 3, None, "knapper"),
        ("ir_vindu", "IR-vindu (klar eller natur PETG, forsiden ned)", 4, (160, 30), None),
    ], {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40", 4: "#DDE6EA"}),
}


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def place(parts):
    out, moved = [], {}
    for f, name, fil, pos, same in parts:
        m = trimesh.load(f"{STL}/{f}.stl")
        if same:
            T = moved[same]
        elif pos == "diag":   # for lang for plata: 45° og midt på (lengre enn plata)
            T = trimesh.transformations.rotation_matrix(math.radians(45), [0, 0, 1])
            b = m.copy().apply_transform(T).bounds
            T = trimesh.transformations.translation_matrix([BED/2 - (b[0][0] + b[1][0])/2, BED/2 - (b[0][1] + b[1][1])/2, -b[0][2]]) @ T
        else:
            b = m.bounds
            T = trimesh.transformations.translation_matrix([pos[0] - b[0][0], pos[1] - b[0][1], -b[0][2]])
        m.apply_transform(T)
        moved[f] = T
        assert m.bounds[1][0] <= BED and m.bounds[1][1] <= BED and m.bounds[0][0] >= 0 and m.bounds[0][1] >= 0, (f, m.bounds)
        out.append((f, name, fil, m))
    # ingen deler overlapper på plata (symbolene og logoen ligger i lommene sine og berører bare)
    for (fa, _, _, a), (fb, _, _, b) in itertools.combinations(out, 2):
        (a0, a1), (b0, b1) = a.bounds, b.bounds
        if a1[0] <= b0[0] or b1[0] <= a0[0] or a1[1] <= b0[1] or b1[1] <= a0[1]:
            continue
        v = a.intersection(b, engine="manifold").volume
        assert v < 0.05, (fa, fb, v)
    return out


OBJ_INNST = {}   # {delnavn: {innstilling: verdi}} – ekstra objektinnstillinger (brukes av andre produkter, f.eks. Røst Rund)
TOPP_INNST = {"brim_type": "outer_only", "brim_width": "5", "brim_object_gap": "0",
              "initial_layer_speed": "25", "initial_layer_infill_speed": "25"}


def write(fn, title, parts, colors, sammen=False):
    """sammen=True: deler med «samme som» (innfelte logoer, symboler) blir deler av samme objekt som den de ligger i,
    med egen filamentfarge. Da behandler sliceren dem som én modell: ingen støtte eller brim på logoen for seg,
    og ingen overlappende objekter."""
    if sammen:
        return write_sammen(fn, title, parts, colors)
    objs, items, cfg = [], [], []
    for i, (f, name, fil, m) in enumerate(place(parts), 1):
        objs.append(f'<object id="{i}" name="{name}" type="model">{mesh_xml(m)}</object>')
        items.append(f'<item objectid="{i}"/>')
        # toppen er lang og flat og løfter seg ved halen: brim og sakte første lag som egne objektinnstillinger
        # (Creality Print / OrcaSlicer leser dem fra model_settings.config; platetemperatur og vifter er filament-
        # innstillinger og kan ikke legges på et objekt)
        innst = TOPP_INNST if f == "topp" or f.endswith("/topp") else OBJ_INNST.get(f, {})
        ekstra = "".join(f'<metadata key="{k}" value="{v}"/>' for k, v in innst.items())
        cfg.append(f'<object id="{i}"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/>{ekstra}'
                   f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{name}"/><metadata key="extruder" value="{fil}"/></part></object>')
    farger = ";".join(f"{k}={v}" for k, v in sorted(colors.items()))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><metadata name="Designer">Skjold</metadata>'
             f'<metadata name="Description">Filamenter: {farger}</metadata>'
             '<metadata name="License">CC BY-NC-SA 4.0</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    conf = '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfg) + "</config>"
    with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", conf)
    print("skrev", fn)


def _pakk(fn, title, objs, items, cfg, colors):
    farger = ";".join(f"{k}={v}" for k, v in sorted(colors.items()))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata><metadata name="Designer">Skjold</metadata>'
             f'<metadata name="Description">Filamenter: {farger}</metadata>'
             '<metadata name="License">CC BY-NC-SA 4.0</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    conf = '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfg) + "</config>"
    with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", conf)
    print("skrev", fn)


def write_sammen(fn, title, parts, colors):
    plassert = place(parts)
    grupper = {}   # hoveddel → [(indeks i plassert)]
    for k, (f, name, fil, m) in enumerate(plassert):
        same = parts[k][4]
        grupper.setdefault(same or f, []).append(k)
    objs, items, cfg, nid = [], [], [], 0
    for hoved, ledd in grupper.items():
        del_id = []
        for k in ledd:
            nid += 1
            f, name, fil, m = plassert[k]
            objs.append(f'<object id="{nid}" name="{name}" type="model">{mesh_xml(m)}</object>')
            del_id.append((nid, name, fil))
        nid += 1
        f0, name0, fil0, _ = plassert[ledd[0]]
        comps = "".join(f'<component objectid="{i}"/>' for i, _, _ in del_id)
        objs.append(f'<object id="{nid}" name="{name0}" type="model"><components>{comps}</components></object>')
        items.append(f'<item objectid="{nid}"/>')
        innst = TOPP_INNST if f0 == "topp" or f0.endswith("/topp") else OBJ_INNST.get(f0, {})
        ekstra = "".join(f'<metadata key="{k}" value="{v}"/>' for k, v in innst.items())
        deler = "".join(f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{n}"/><metadata key="extruder" value="{fl}"/></part>'
                        for i, n, fl in del_id)
        cfg.append(f'<object id="{nid}"><metadata key="name" value="{name0}"/><metadata key="extruder" value="{fil0}"/>{ekstra}{deler}</object>')
    _pakk(fn, title, objs, items, cfg, colors)


STL = "stl"


# hvert tasteoppsett: hele toppen (med SKJOLD) og oppsettets hetter. A er også med i de vanlige platene.
BOKSTAV = {"rutenett": "A", "vannrett": "B", "stor": "C"}
OPPSETT_PLATER = {o: [
    (f"Skjold Fjernkontroll – topp {navn}", [
        (f"oppsett_{o}/topp", "Topp (forsiden ned)", 1, (100, 12), None),
        ("logo", "SKJOLD (gull, felt inn i toppen)", 3, None, f"oppsett_{o}/topp"),
        ("orer", "Museører (holder halen nede, vris av etter print)", 1, None, f"oppsett_{o}/topp")], {1: "#ECE9E3", 3: "#D99E40"}),
    (f"Skjold Fjernkontroll – taster {navn}", [
        (f"oppsett_{o}/front_knapper", "Taster til oppsettet (flensen ned)", 2, (40, 30), None),
        (f"oppsett_{o}/front_symboler", "Symboler", 1, None, f"oppsett_{o}/front_knapper")], {1: "#ECE9E3", 2: "#2E2D2C"})]
    for o, navn in taster.OPPSETT_NAVN.items()}


def uten_gull(front="oppsett_rutenett/"):
    """Alle mørke taster i oppsett A med symbolene, uten gulldelene (D-pad-ringen og Skjold-tasten).
    front: mappen (under STL) med oppsettets hetter – hullkort/enkel eksporterer sine egne (tappene følger bryterne)."""
    return ("Skjold Fjernkontroll – alle taster uten gull", [
        ("knapper", "Power, meny og OK (flensen ned)", 2, (60, 40), None),
        ("symboler_lyse", "Symboler på power, meny og OK", 1, None, "knapper"),
        (f"{front}front_knapper", "Tilbake/exit, spill/pause, demp og volum (forsiden ned)", 2, (70, 110), None),
        (f"{front}front_symboler", "Symboler på media-tastene", 1, None, f"{front}front_knapper"),
    ], {1: "#ECE9E3", 2: "#2E2D2C"})


def gull():
    """Bare gulldelene: ringen rundt D-paden og Skjold-tasten, med de mørke symbolene (piler og Skjold-merket)."""
    return ("Skjold Fjernkontroll – gulldelene", [
        ("gull", "Gullring (D-pad) og Skjold-tast (flensen ned)", 3, (60, 40), None),
        ("symboler_morke", "Symboler på gulldelene (piler og Skjold-merke)", 2, None, "gull"),
    ], {2: "#2E2D2C", 3: "#D99E40"})


def plater(variant):
    """{filnavn: (tittel, deler, farger)} for varianten. Full variant er 254,5 mm, lengre enn plata (250 mm):
    toppen og bunnen ligger da på hver sin plate, på skrå (45°)."""
    ut = {}
    for fn, (title, parts, colors) in PLATES.items():
        if variant == "kort":
            ut[fn] = (title, [p for p in parts if p[0] != "knapper_lys"], colors)   # standard har ikke smarthus-raden
            continue
        fn = fn.replace("skjold-fjernkontroll-", "skjold-fjernkontroll-full-")
        title = title.replace("Skjold Fjernkontroll", "Skjold Fjernkontroll Full")
        if fn.endswith("-k2.3mf") and taster.L_FULL > BED - 4:
            diag = [(f, n, fil, "diag" if pos else None, same) for f, n, fil, pos, same in parts]
            ut[fn.replace("-k2.3mf", "-k2-topp.3mf")] = (title.replace("topp og bunn", "topp"), [p for p in diag if p[0] != "bunn"], colors)
            ut[fn.replace("-k2.3mf", "-k2-bunn.3mf")] = (title.replace("topp og bunn", "bunn"), [p for p in diag if p[0] == "bunn"], colors)
        else:
            ut[fn] = (title, parts, colors)
    if variant != "kort":   # full variant er for lang til museørene på plata (254,5 mm): bruk brim i sliceren i stedet
        flytt = {"topp": (20, 2), "bunn": (100, 2)}   # og trenger hele lengden av plata
        ut = {fn: (t, [(p[0], p[1], p[2], flytt.get(p[0], p[3]) if p[3] and p[3] != "diag" else p[3], p[4]) for p in ps if p[0] != "orer"], c)
              for fn, (t, ps, c) in ut.items()}
    for o, ((t1, p1, c1), (t2, p2, c2)) in OPPSETT_PLATER.items():
        b = BOKSTAV[o]
        pre = "skjold-fjernkontroll-k2" if variant == "kort" else "skjold-fjernkontroll-full-k2"
        tt = (lambda t: t) if variant == "kort" else (lambda t: t.replace("Skjold Fjernkontroll", "Skjold Fjernkontroll Full"))
        ut[f"{pre}-topp-{b}.3mf"] = (tt(t1), p1 if variant == "kort" else
                                     [(p[0], p[1], p[2], (20, 2) if p[3] else None, p[4]) for p in p1 if p[0] != "orer"], c1)
        ut[f"{pre}-taster-{b}.3mf"] = (tt(t2), p2, c2)
    if variant == "kort":
        ut["skjold-fjernkontroll-k2-taster-uten-gull.3mf"] = uten_gull()
        ut["skjold-fjernkontroll-k2-taster-gull.3mf"] = gull()
    return ut


def main():
    """Standard (kort) fra stl/, full variant fra stl_full/ (filene heter skjold-fjernkontroll-full-…)."""
    global STL
    for variant in ("kort", "full"):
        STL = "stl" if variant == "kort" else "stl_full"
        for fn, (title, parts, colors) in plater(variant).items():
            write(fn, title, parts, colors)


if __name__ == "__main__":
    main()
