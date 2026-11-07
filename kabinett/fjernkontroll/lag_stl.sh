#!/bin/sh
# Eksporter alle STL-er for begge variantene, kjør sjekken og lag 3MF:
#   full (42 taster, 230 mm): utskrift i stl/, montert stilling i asm/
#   kort (26 taster, 187 mm, uten talltastene og smarthus-raden): stl_kort/ og asm_kort/
# Tastene ligger i taster.py; den kjøres først.
cd "$(dirname "$0")"
python3 taster.py > /dev/null || exit 1
for v in full kort; do
  S=stl; A=asm; [ $v = kort ] && { S=stl_kort; A=asm_kort; }
  mkdir -p $S $A
  P="topp bunn logo ir_vindu knapper knapper_lys gull symboler_lyse symboler_morke farge_rod farge_gronn farge_gul farge_bla bryterbrett"
  [ $v = kort ] && P=$(echo $P | sed 's/knapper_lys //')
  for p in $P; do
    openscad -q -D "part=\"$p\"" -D "variant=\"$v\"" -o "$S/$p.stl" skjold_fjernkontroll.scad &
  done
  for p in topp bunn logo vindu hetter symboler kort skjerm batteri mcu lader; do
    openscad -q -D "part=\"A_$p\"" -D "variant=\"$v\"" -o "$A/$p.stl" skjold_fjernkontroll.scad &
  done
done
openscad -q -D 'part="kort_omriss"' -o tastekort/kort_omriss.dxf skjold_fjernkontroll.scad &
openscad -q -D 'part="kort_omriss"' -D 'variant="kort"' -o tastekort_kort/kort_omriss.dxf skjold_fjernkontroll.scad &
wait
python3 sjekk_modell.py asm full && python3 sjekk_modell.py asm_kort kort && python3 lag_3mf.py
