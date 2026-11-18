#!/bin/sh
# Skjold Dokk: STL-er (stl/), pogo-handelen på plass (asm/), sjekk, 3MF og bilder (uten skjerm: xvfb-run -a sh lag_dokk.sh).
# Fjernkontrollens STL-er (../asm, ../asm_full) lages av ../lag_stl.sh.
cd "$(dirname "$0")"
mkdir -p stl asm render
for p in vugge sokkel gull lokk led_propp sokkel_topp sokkel_bunn; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_dokk.scad & done
openscad -q -D 'part="pogo_han"' -o asm/pogo_han.stl skjold_dokk.scad &
# IR-dokka (delt sokkel med ESP32-C3, IR-lysdioder og VS1838B): toppdelen med tredje lysdiode bak eller på siden, og
# de kjøpte delene i montert stilling til sjekken. Bunnplata og gullstripa er de samme som i stl/.
mkdir -p stl_ir
openscad -q -D 'part="sokkel_topp"' -D ir=true -o stl_ir/sokkel_topp.stl skjold_dokk.scad &
openscad -q -D 'part="sokkel_topp"' -D ir=true -D 'ir_tredje="side"' -o stl_ir/sokkel_topp_side.stl skjold_dokk.scad &
openscad -q -D 'part="ir_deler"' -D ir=true -o asm/ir_deler.stl skjold_dokk.scad &
openscad -q -D 'part="ir_deler"' -D ir=true -D 'ir_tredje="side"' -o asm/ir_deler_side.stl skjold_dokk.scad &
wait
python3 sjekk_dokk.py || exit 1
python3 lag_3mf_dokk.py
r() { openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D "farge=\"$4\"" -D "variant=\"${5:-kort}\"" -o "render/$1.png" skjold_dokk.scad & }
# med fjernkontrollen og skjermen på: modellen tegnes fra ../skjold_fjernkontroll.scad (part="i_dokk"), med det aktive
# området i magenta (skjerm="nokkel") og et eget bilde av kvadrantene (part="skjermflate_dokk"); skjerm_i_render.py legger
# dokk-skjermen (render/skjerm-9-dokk.png fra lag_skjermbilder.py) inn i perspektiv. Kameraet ser fronten litt fra høyre:
# OpenSCAD-lyset kommer fra den siden, så Bone White blir varmt hvitt og ikke grått.
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
[ -f ../render/skjerm-9-dokk.png ] || (cd .. && python3 lag_skjermbilder.py)
f() {   # navn kamera farge [variant]
  ( cd .. && openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$2" -D 'part="i_dokk"' -D "farge=\"$3\"" \
      -D "variant=\"${4:-kort}\"" -D 'skjerm="nokkel"' -o "dokk/render/$1.png" skjold_fjernkontroll.scad
    openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$2" -D 'part="skjermflate_dokk"' \
      -D "variant=\"${4:-kort}\"" -o "$TMP/$1.png" skjold_fjernkontroll.scad
    python3 skjerm_i_render.py "dokk/render/$1.png" "$TMP/$1.png" render/skjerm-9-dokk.png ) &
}
r 01_dokk_bone samlet 0,22,40,62,0,30,300 bone
r 02_dokk_mork samlet 0,22,40,62,0,30,300 mork
r 03_dokk_bak samlet 0,22,30,62,0,145,300 bone
# IR-dokka: forfra (lysdiodene og mottakervinduet), inni (sokkelen kuttet i z = 4,6 med C3, lysdiodene og
# USB-C-brikken på plass) og bakfra (tredje lysdiode og lyslederen)
ir() { openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D ir=true \
         -D "farge=\"$4\"" -o "render/$1.png" skjold_dokk.scad & }
ir 16_ir_foran samlet 0,5,22,76,0,22,250 bone
ir 17_ir_inni ir_inni 0,22,0,42,0,20,215 mork
ir 18_ir_bak samlet 0,40,25,70,0,155,330 bone
f 00_hero 0,45,108,68,0,30,650 bone
f 04_med_fjernkontroll_bone 0,45,105,64,0,35,660 bone
f 05_med_fjernkontroll_mork 0,45,105,64,0,35,660 mork
f 06_side_full 0,55,125,80,0,62,760 bone full
wait
# Høyere vugge for Hullkort-utgaven (16,0 mm tykk)
mkdir -p stl_hu
for p in vugge sokkel gull lokk; do openscad -q -D "part=\"$p\"" -D FH=16.0 -o "stl_hu/$p.stl" skjold_dokk.scad & done
openscad -q -D 'part="vugge"' -D FH=16.0 -D usb_spor=true -o stl_hu/vugge_usb.stl skjold_dokk.scad &
wait
python3 - <<'PY'
import sys; sys.path.insert(0, ".."); import lag_3mf
lag_3mf.STL = "stl_hu"
lag_3mf.write("skjold-dokk-hullkort-k2.3mf", "Skjold Dokk for Hullkort-utgaven (16,0 mm) – vugge, sokkel og lokk", [
    ("vugge", "Vugge (Bone White)", 1, (12, 20), None), ("sokkel", "Sokkel (mørk)", 2, (95, 20), None),
    ("gull", "Gullstripe (felt inn i sokkelen)", 3, None, "sokkel"), ("lokk", "Lokk til vektlomma (mørk)", 2, (12, 150), None),
], {1: "#CEC6B4", 2: "#2E2D2C", 3: "#D99E40"})
lag_3mf.write("skjold-dokk-hullkort-k2-vugge-usb.3mf", "Skjold Dokk for Hullkort-utgaven – vugge med spor for vinklet USB-C-plugg", [
    ("vugge_usb", "Vugge med USB-spor (Bone White)", 1, (90, 80), None)], {1: "#CEC6B4"})
lag_3mf.write("skjold-dokk-hullkort-k2-vugge.3mf", "Skjold Dokk for Hullkort-utgaven – bare vugga (passer på sokkelen)", [
    ("vugge", "Vugge (Bone White)", 1, (90, 80), None)], {1: "#CEC6B4"})
PY
