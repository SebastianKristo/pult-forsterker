#!/bin/sh
# Eksporter alle STL-er (utskrift i stl/, montert stilling i asm/ for sjekk_modell.py), deretter 3MF og sjekk.
# Tastene ligger i taster.py: kjør  python3 taster.py  først hvis du har flyttet eller endret en tast.
cd "$(dirname "$0")"
mkdir -p stl asm
python3 taster.py > /dev/null || exit 1
for p in topp bunn logo ir_vindu knapper knapper_lys gull symboler_lyse symboler_morke farge_rod farge_gronn farge_gul farge_bla bryterbrett; do
  openscad -q -D "part=\"$p\"" -o "stl/$p.stl" skjold_fjernkontroll.scad &
done
for p in topp bunn logo vindu hetter symboler kort skjerm batteri mcu lader; do
  openscad -q -D "part=\"A_$p\"" -o "asm/$p.stl" skjold_fjernkontroll.scad &
done
wait
python3 sjekk_modell.py asm && python3 lag_3mf.py
