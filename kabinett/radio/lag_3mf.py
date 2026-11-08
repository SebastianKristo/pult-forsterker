"""Lag 3MF-platene for Skjold Radio (Creality K2 / K2 Pro / K2 Plus, 250 × 250 mm):

  skjold-radio-k2.3mf          kropp (fronten ned), volumknott, knappehetter og gullist (PETG/ASA, 3 farger)
  skjold-radio-k2-kammer.3mf   lydkammer (baffelen ned) og lokk (PETG/ASA, 100 % fyll i baffelen gir best lyd)
  skjold-radio-k2-grill.3mf    grill (forsiden ned) og skjermbrakett med Pi-tårn (PETG/ASA, sort)
  skjold-radio-k2-bak.3mf      bakplate (baksiden ned) og navigasjonshjul

Kjør etter at STL-ene er eksportert:  python3 lag_3mf.py   (eller ./lag_stl.sh, som gjør alt)
Hver del får filamentnummer i Metadata/model_settings.config (Creality Print / OrcaSlicer):
1 = kroppsfarge (lys), 2 = sort/mørk, 3 = gull.

Symbolene er innfelt i flukt (0,6 mm, egne legemer i en lomme med samme form). Hver knappehette, volumknotten og hjulet
blir ett objekt med to deler (komponenter) – selve delen og symbolinnlegget – med hvert sitt filament, slik at CFS printer
symbolet i kontrastfarge i samme utskrift: hettene sort (2) med gull symbol (3), volumknotten og hjulet gull (3) med sort
symbol (2). Mørk variant (sort kropp, gullknapper): legg sort i spor 1, og bytt filament på hettene til 3 og symbolene til 2."""
import math
import os
import zipfile
from xml.sax.saxutils import escape

import trimesh

BED = 250
PLATES = {
    "skjold-radio-k2.3mf": ("Skjold Radio – kropp, volumknott, knapper og gullist (PETG/ASA)", [
        # fil, navn, filament, rotasjon om z, min-hjørne (x, y), «samme som»
        ("kropp", "Kropp (fronten ned)", 1, 0, (5, 0.5), None),
        ("knapp", "Knappehetter 1–6 og av/på (toppen ned)", 2, 0, (5, 158), None),
        ("knapp_symbol", "Symbol", 3, 0, None, "knapp"),        # innlegg: delt opp og lagt inn i hver sin hette
        ("volum", "Volumknott", 3, 0, (145, 158), None),
        ("volum_symbol", "Symbol høyttaler", 2, 0, None, "volum"),
        ("list", "Gullist (forsiden ned)", 3, 90, (5, 176), None),
    ]),
    "skjold-radio-k2-kammer.3mf": ("Skjold Radio – lydkammer og lokk (PETG/ASA)", [
        ("kammer", "Lydkammer (baffelen ned)", 2, 0, (10, 5), None),
        ("lokk", "Lokk for kammeret", 2, 0, (130, 5), None),
    ]),
    "skjold-radio-k2-grill.3mf": ("Skjold Radio – grill og skjermbrakett (PETG/ASA)", [
        ("grill", "Grill (forsiden ned)", 2, 0, (5, 5), None),
        ("brakett", "Skjermbrakett med Pi-tårn", 2, 0, (118, 5), None),
    ]),
    "skjold-radio-k2-bak.3mf": ("Skjold Radio – bakplate og navigasjonshjul (PETG/ASA)", [
        ("bak", "Bakplate (baksiden ned)", 1, 0, (8, 3), None),
        ("knott", "Navigasjonshjul", 3, 0, (10, 145), None),
        ("knott_symbol", "Symbol spill/pause", 2, 0, None, "knott"),
    ]),
}
COLORS = {1: "#ECE9E3", 2: "#232325", 3: "#D99E40"}
HETTER = ["Knapp 1", "Knapp 2", "Knapp 3", "Knapp 4", "Knapp 5", "Knapp 6", "Knapp av/på"]


def mesh_xml(m):
    v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
    t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return f"<mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh>"


def place(parts):
    out, moved = [], {}
    for f, name, fil, rot, pos, same in parts:
        m = trimesh.load(f"stl/{f}.stl")
        if rot:
            m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1]))
        if same:
            m.apply_translation(moved[same])
        else:
            b = m.bounds
            d = [pos[0] - b[0][0], pos[1] - b[0][1], -b[0][2]]
            m.apply_translation(d)
            moved[f] = d
        assert m.bounds[1][0] <= BED and m.bounds[1][1] <= BED and m.bounds[0][0] >= 0 and m.bounds[0][1] >= 0, (f, m.bounds)
        out.append((f, name, fil, m))
    return out


def objects(parts):
    """Grupper delene til objekter: [(navn, [(delnavn, filament, mesh), …])]. Et innlegg («samme som») blir en ekstra del
    i objektet det ligger i. Knappehettene (sju legemer i én fil) deles opp, så hver hette med symbolet blir ett objekt."""
    placed = place(parts)
    objs, by = [], {}
    for f, name, fil, m in placed:
        same = next(p[5] for p in parts if p[0] == f)
        if same is None:
            if f == "knapp":
                for k, b in enumerate(sorted(m.split(only_watertight=False), key=lambda b: b.bounds[0][0])):
                    objs.append([HETTER[k] + " (toppen ned)", [(HETTER[k], fil, b)]])
                by[f] = objs[-7:]
            else:
                objs.append([name, [(name, fil, m)]])
                by[f] = [objs[-1]]
        else:
            groups = by[same]
            bodies = m.split(only_watertight=False) if len(groups) > 1 else [m]
            for g in groups:
                gb = g[1][0][2].bounds
                mine = [b for b in bodies if all(gb[0][i] <= b.centroid[i] <= gb[1][i] for i in (0, 1))]
                assert mine, (f, g[0])
                g[1].append((f"{name} – {g[0].split(' (')[0]}" if len(groups) > 1 else name, fil, trimesh.util.concatenate(mine)))
            assert sum(len(b.faces) for b in bodies) == sum(len(p[2].faces) for g in groups for p in g[1][1:]), f
    # ingen overlapp mellom objektene på plata
    out = [(o[0], None, None, trimesh.util.concatenate([p[2] for p in o[1]])) for o in objs]
    for i, (fa, _, _, a) in enumerate(out):
        for fb, _, _, b in out[i + 1:]:
            (a0, a1), (b0, b1) = a.bounds, b.bounds
            assert a1[0] <= b0[0] or b1[0] <= a0[0] or a1[1] <= b0[1] or b1[1] <= a0[1], (fa, fb)
    return objs


def write(fn, title, parts):
    objs, items, cfg, nid = [], [], [], 0
    for name, dels in objects(parts):
        if len(dels) == 1:   # én del: et vanlig mesh-objekt
            nid += 1
            dn, fil, m = dels[0]
            objs.append(f'<object id="{nid}" name="{escape(name)}" type="model">{mesh_xml(m)}</object>')
            items.append(f'<item objectid="{nid}"/>')
            cfg.append(f'<object id="{nid}"><metadata key="name" value="{escape(name)}"/><metadata key="extruder" value="{fil}"/>'
                       f'<part id="{nid}" subtype="normal_part"><metadata key="name" value="{escape(name)}"/><metadata key="extruder" value="{fil}"/></part></object>')
            continue
        # flere deler: ett objekt med komponenter, hver del med sitt filament (flerfarget med CFS)
        ids = []
        for dn, fil, m in dels:
            nid += 1
            ids.append(nid)
            objs.append(f'<object id="{nid}" name="{escape(dn)}" type="model">{mesh_xml(m)}</object>')
        nid += 1
        objs.append(f'<object id="{nid}" name="{escape(name)}" type="model"><components>'
                    + "".join(f'<component objectid="{i}"/>' for i in ids) + '</components></object>')
        items.append(f'<item objectid="{nid}"/>')
        cfg.append(f'<object id="{nid}"><metadata key="name" value="{escape(name)}"/><metadata key="extruder" value="{dels[0][1]}"/>'
                   + "".join(f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{escape(dn)}"/>'
                             f'<metadata key="extruder" value="{fil}"/></part>' for i, (dn, fil, _) in zip(ids, dels)) + '</object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{escape(title)}</metadata><metadata name="Designer">Skjold</metadata>'
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


def main():
    if os.path.exists("skjold-radio-k2-bunn.3mf"):   # fra første utgave (bunnplata finnes ikke lenger)
        os.remove("skjold-radio-k2-bunn.3mf")
    for fn, (title, parts) in PLATES.items():
        write(fn, title, parts)


if __name__ == "__main__":
    main()
