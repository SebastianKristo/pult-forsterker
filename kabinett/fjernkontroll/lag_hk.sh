#!/bin/sh
# Hovedkort-utgaven («alt på ett kort»): eksporter toppen og bunnen (stl_hk/) og montert stilling (asm_hk/), og sjekk.
# Kortdataene (hovedkort/hovedkort_data.scad) lages av hovedkort/lag_hovedkort.py.
cd "$(dirname "$0")"
mkdir -p stl_hk asm_hk
for p in topp bunn; do
  openscad -q -D "part=\"$p\"" -D 'elektronikk="hovedkort"' -o "stl_hk/$p.stl" skjold_fjernkontroll.scad &
done
openscad -q -D 'part="bunn"' -D dokk_kontakt=true -D 'elektronikk="hovedkort"' -o stl_hk/bunn_dokk.stl skjold_fjernkontroll.scad &
for p in topp bunn logo vindu hetter symboler kort skjerm batteri ir vib motor flex ledninger hkdeler usbc pogo; do
  openscad -q -D "part=\"A_$p\"" -D 'elektronikk="hovedkort"' -o "asm_hk/$p.stl" skjold_fjernkontroll.scad &
done
wait
python3 sjekk_modell.py asm_hk hovedkort || exit 1
# bilder: hovedkortet sett fra undersiden, og innmaten med hovedkortet (uten skjerm: xvfb-run -a sh lag_hk.sh)
openscad -q --colorscheme=Tomorrow --imgsize=1600,900 --projection=p --camera=27.5,63,7,145,0,90,215 -D 'part="hk_3d"' \
  -D 'elektronikk="hovedkort"' -o hovedkort/render_3d.png skjold_fjernkontroll.scad
openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera=27.5,98.75,7,15,0,-90,418 -D 'part="inni"' \
  -D 'elektronikk="hovedkort"' -o hovedkort/render_inni.png skjold_fjernkontroll.scad
