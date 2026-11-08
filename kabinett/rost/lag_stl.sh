#!/bin/sh
# Eksporter alle STL-er for Skjold Røst (utskrift i stl/, montert stilling i asm/ for sjekk_modell.py), sjekk modellen og lag 3MF.
cd "$(dirname "$0")"
mkdir -p stl asm
P="kropp front logo grill bunn knott rute knapp pakning_front pakning_bunn krage dc_skive usb_propp"
for p in $P; do openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_rost.scad & done
for p in $P skjerm; do openscad -q -D "part=\"a_$p\"" -o "asm/$p.stl" skjold_rost.scad & done
openscad -q -D 'part="luft"' -o asm/luft.stl skjold_rost.scad &
wait
python3 sjekk_modell.py asm && python3 lag_3mf.py
