#!/bin/sh
# Skjold Dokk: STL-er (stl/), pogo-handelen på plass (asm/), sjekk, 3MF og bilder (uten skjerm: xvfb-run -a sh lag_dokk.sh).
# Fjernkontrollens STL-er (../asm, ../asm_full) lages av ../lag_stl.sh.
cd "$(dirname "$0")"
mkdir -p stl asm render
for p in vugge sokkel gull lokk; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_dokk.scad & done
openscad -q -D 'part="pogo_han"' -o asm/pogo_han.stl skjold_dokk.scad &
wait
python3 sjekk_dokk.py || exit 1
python3 lag_3mf_dokk.py
r() { openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera="$3" -D "part=\"$2\"" -D "farge=\"$4\"" -D "variant=\"${5:-kort}\"" -o "render/$1.png" skjold_dokk.scad & }
r 01_dokk_bone samlet 0,22,40,62,0,-35,300 bone
r 02_dokk_mork samlet 0,22,40,62,0,-35,300 mork
r 03_dokk_bak samlet 0,22,30,62,0,145,300 bone
r 04_med_fjernkontroll_bone med_fjernkontroll 0,40,85,68,0,-35,520 bone
r 05_med_fjernkontroll_mork med_fjernkontroll 0,40,85,68,0,-35,520 mork
r 06_side_full med_fjernkontroll 0,60,100,90,0,-90,560 bone full
wait
