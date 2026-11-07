#!/bin/sh
# Eksporter alle STL-er (utskrift i stl/, montert stilling i asm/ for sjekk_modell.py), deretter 3MF og sjekk.
cd "$(dirname "$0")"
mkdir -p stl asm
for p in kropp kammer lokk grill bunn brakett knott volum knapp; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_radio.scad & done
for p in kropp kammer lokk grill bunn brakett knapper knott volum; do openscad -q -D "part=\"A_$p\"" -o "asm/$p.stl" skjold_radio.scad & done
wait
python3 sjekk_modell.py asm && python3 lag_3mf.py
