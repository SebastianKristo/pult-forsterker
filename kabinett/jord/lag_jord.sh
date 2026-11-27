#!/bin/sh
# Skjold Jord: STL-er (stl/ for utskrift, asm/ montert), sjekk, 3MF og bilder. Uten skjerm: xvfb-run -a sh lag_jord.sh
cd "$(dirname "$0")"
mkdir -p stl asm render
for p in kropp lokk logo pakning mansjett plugg; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_jord.scad & done
for p in kropp lokk logo pakning mansjett plugg sensor xiao batteri; do openscad -q -D "part=\"A_$p\"" -o "asm/$p.stl" skjold_jord.scad & done
wait
python3 sjekk_jord.py || exit 1
python3 lag_3mf_jord.py
for v in samlet eksplodert; do
  openscad -q --colorscheme=Tomorrow --imgsize=1400,1400 --projection=p --camera=30,8,15,62,0,32,330 -D "part=\"$v\"" -o "render/$v.png" skjold_jord.scad
done
openscad -q --colorscheme=Tomorrow --imgsize=1400,1400 --projection=p --camera=30,8,15,62,0,212,330 -D 'part="samlet"' -o render/bak.png skjold_jord.scad
