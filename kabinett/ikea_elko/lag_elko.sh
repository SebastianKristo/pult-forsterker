#!/bin/sh
# STL-er, 3MF og bilder. Uten skjerm: xvfb-run -a sh lag_elko.sh. Endre ramme_b/ramme_h/ramme_d i ikea_elko.scad først.
cd "$(dirname "$0")"
mkdir -p stl render
for p in front bak; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" ikea_elko.scad & done
wait
python3 lag_3mf_elko.py
openscad -q --colorscheme=Tomorrow --imgsize=1200,900 --projection=p --camera=0,0,20,40,0,20,260 -D 'part="samlet"' -o render/samlet.png ikea_elko.scad
openscad -q --colorscheme=Tomorrow --imgsize=1200,900 --projection=p --camera=0,0,10,140,0,20,260 -D 'part="samlet"' -o render/bak.png ikea_elko.scad
