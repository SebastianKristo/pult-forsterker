#!/bin/sh
# Bambu Lab P3C (fem hoder): hettene med TPU-fjær (stl/p3c/) og platene skjold-fjernkontroll[-enkel]-p3c[-taster].3mf.
# Topp, bunn, logo og IR-vindu er de samme som til K2 (stl/ og stl_en/ – kjør lag_stl.sh og lag_en.sh først).
cd "$(dirname "$0")"
mkdir -p stl/p3c
for p in knapper gull symboler_lyse symboler_morke fjaer; do
  openscad -q -D "part=\"$p\"" -D tpu=true -o "stl/p3c/$p.stl" skjold_fjernkontroll.scad &
done
for p in front_knapper front_symboler front_tupper; do
  openscad -q -D "part=\"$p\"" -D tpu=true -D 'oppsett="rutenett"' -o "stl/p3c/$p.stl" skjold_fjernkontroll.scad &
done
wait
python3 lag_3mf.py p3c
