#!/bin/sh
# Enkel utgave (XIAO ESP32S3 + MCP23017 på et bærekort): toppen og bunnen (stl_en/), montert stilling (asm_en/), sjekk og bilder.
# Kortdataene (enkel/enkel_data.scad) lages av enkel/lag_enkel.py. Uten skjerm: xvfb-run -a sh lag_en.sh
cd "$(dirname "$0")"
mkdir -p stl_en asm_en
E='elektronikk="enkel"'
for p in topp bunn; do openscad -q -D "part=\"$p\"" -D "$E" -o "stl_en/$p.stl" skjold_fjernkontroll.scad & done
openscad -q -D 'part="bunn"' -D dokk_kontakt=true -D "$E" -o stl_en/bunn_dokk.stl skjold_fjernkontroll.scad &
for p in topp bunn logo vindu hetter symboler kort skjerm batteri ir flex ledninger hkdeler usbc pogo; do
  openscad -q -D "part=\"A_$p\"" -D "$E" -o "asm_en/$p.stl" skjold_fjernkontroll.scad &
done
wait
python3 sjekk_modell.py asm_en enkel || exit 1
openscad -q --colorscheme=Tomorrow --imgsize=1600,900 --projection=p --camera=27.5,63,7,145,0,90,215 -D 'part="hk_3d"' -D "$E" -o enkel/render_3d.png skjold_fjernkontroll.scad
openscad -q --colorscheme=Tomorrow --imgsize=1600,1100 --projection=p --camera=27.5,98.75,7,15,0,-90,418 -D 'part="inni"' -D "$E" -o enkel/render_inni.png skjold_fjernkontroll.scad
