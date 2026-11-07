#!/bin/sh
# Eksporter alle STL-er for begge variantene, kjør sjekken og lag 3MF:
#   standard (kort, 15 taster, 180 mm): utskrift i stl/, montert stilling i asm/
#   full (valgfri, 31 taster, 223 mm, med talltaster og smarthus-rad): stl_full/ og asm_full/
# Tastene ligger i taster.py; den kjøres først.
cd "$(dirname "$0")"
python3 taster.py > /dev/null || exit 1
for v in kort full; do
  S=stl; A=asm; [ $v = full ] && { S=stl_full; A=asm_full; }
  mkdir -p $S $A
  P="topp bunn logo ir_vindu knapper knapper_lys gull symboler_lyse symboler_morke bryterbrett"
  [ $v = kort ] && P=$(echo $P | sed 's/knapper_lys //')
  for p in $P; do
    openscad -q -D "part=\"$p\"" -D "variant=\"$v\"" -o "$S/$p.stl" skjold_fjernkontroll.scad &
  done
  for p in topp bunn logo vindu hetter symboler kort skjerm batteri mcu lader ir vib motor flex ledninger; do
    openscad -q -D "part=\"A_$p\"" -D "variant=\"$v\"" -o "$A/$p.stl" skjold_fjernkontroll.scad &
  done
done
openscad -q -D 'part="kort_omriss"' -D 'variant="kort"' -o tastekort/kort_omriss.dxf skjold_fjernkontroll.scad &
openscad -q -D 'part="kort_omriss"' -D 'variant="full"' -o tastekort_full/kort_omriss.dxf skjold_fjernkontroll.scad &
wait
python3 sjekk_modell.py asm kort && python3 sjekk_modell.py asm_full full && python3 lag_3mf.py
