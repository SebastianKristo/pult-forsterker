#!/bin/sh
# Renders av Skjold Røst til render/ (OpenSCAD, fargeskjema Tomorrow, 1200 × 1200).
# Skjermen viser et OLED-bilde (render/oled.png, 128 × 64, laget av lag_oled.py): OpenSCAD tegner det aktive området i
# magenta (skjerm="nokkel"), og skjerm_i_render.py legger bildet inn i perspektiv.
# Uten skjerm (CI/server): xvfb-run -a ./lag_render.sh   (hvert bilde tar rundt et minutt)
cd "$(dirname "$0")"
mkdir -p render
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
python3 lag_oled.py
[ -f asm/kropp.stl ] || { echo "kjør ./lag_stl.sh først (renderne bruker nettene i asm/)"; exit 1; }
O="-q -D fra_stl=true --colorscheme=Tomorrow --imgsize=1200,1200 --projection=p"
# Bakbildene tas rett bakfra og fra venstre bak: OpenSCAD-lyset står fast, og bakveggen blir nesten svart sett fra høyre bak.
# r <navn> <part> <kamera>: med skjermbilde
r() {
  ( openscad $O --camera="$3" -D "part=\"$2\"" -D 'skjerm="nokkel"' -o "render/$1.png" skjold_rost.scad
    openscad $O --camera="$3" -D 'part="skjermflate"' -o "$TMP/$1.png" skjold_rost.scad
    python3 skjerm_i_render.py "render/$1.png" "$TMP/$1.png" render/oled.png ) &
}
# g <navn> <part> <kamera>: uten skjermbilde (glassruta)
g() { openscad $O --camera="$3" -D "part=\"$2\"" -o "render/$1.png" skjold_rost.scad & }
r 01_rost        samlet     -390,-510,358,0,52,64
g 02_eksplodert  eksplodert -494,-625,410,0,45,62
g 03_bak         samlet     -230,660,330,0,55,64
g 07_bak_skra    samlet     -405,629,356,0,55,62
g 04_side        samlet     580,36,98,0,52,66
g 05_skjot       samlet     -150,-190,230,0,5,118
r 06_knapper_skjerm samlet  0,-149,408,0,40,134
wait
