#!/bin/sh
# Hullkort-utgaven (XIAO ESP32S3, MCP23017-modul og 6 × 6-brytere på hullkort): toppen og bunnen (stl_hu/), montert stilling (asm_hu/), sjekk og bilder.
# Dataene (hullkort/hullkort_data.scad) lages av hullkort/lag_hullkort.py. Uten skjerm: xvfb-run -a sh lag_hu.sh
cd "$(dirname "$0")"
mkdir -p stl_hu asm_hu
E='elektronikk="hullkort"'
for p in topp bunn; do openscad -q -D "part=\"$p\"" -D "$E" -o "stl_hu/$p.stl" skjold_fjernkontroll.scad & done
openscad -q -D 'part="bunn"' -D dokk_kontakt=true -D "$E" -o stl_hu/bunn_dokk.stl skjold_fjernkontroll.scad &
for p in topp bunn logo vindu hetter symboler kort skjerm batteri ir flex ledninger hkdeler usbc pogo; do
  openscad -q -D "part=\"A_$p\"" -D "$E" -o "asm_hu/$p.stl" skjold_fjernkontroll.scad &
done
wait
python3 sjekk_modell.py asm_hu hullkort || exit 1
openscad -q --colorscheme=Tomorrow --imgsize=1600,900 --projection=p --camera=27.5,63,7,145,0,90,215 -D 'part="hu_3d"' -D "$E" -o hullkort/render_3d.png skjold_fjernkontroll.scad
openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera=27.5,98.75,7,15,0,-90,418 -D 'part="inni"' -D "$E" -o hullkort/render_inni.png skjold_fjernkontroll.scad
