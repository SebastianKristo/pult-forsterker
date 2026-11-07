#!/bin/sh
# Eksporter alle STL-er (utskrift i stl/, montert stilling i asm/ for sjekk_modell.py), deretter 3MF og sjekk.
cd "$(dirname "$0")"
mkdir -p stl asm
for p in kropp bak kammer lokk grill list brakett knott volum knapp knapp_symbol knott_symbol volum_symbol; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_radio.scad & done
for p in kropp bak kammer lokk grill list brakett knapper knapp_symboler knott knott_symbol volum volum_symbol stoff; do openscad -q -D "part=\"A_$p\"" -o "asm/$p.stl" skjold_radio.scad & done
wait
python3 sjekk_modell.py asm && python3 lag_3mf.py
