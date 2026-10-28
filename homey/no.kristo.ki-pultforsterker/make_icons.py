#!/usr/bin/env python3
"""Lager Homey-bildene (app + driver) og enhetsikonet fra forsterkerens front i designfargene."""
import cairosvg, os
def amp_svg(W=1000, H=700, bg="#1b1c20"):
    # frontplate 188x46 skalert; knapper/knott/OLED som på frontplaten
    s = W / 227
    def X(x): return W / 2 + x * s
    def Y(y): return H / 2 + y * s
    btn = lambda cx, cy, r, led: (f'<circle cx="{X(cx)}" cy="{Y(cy)}" r="{r*s}" fill="#1d1d20"/>'
        f'<circle cx="{X(cx)}" cy="{Y(cy)}" r="{(r-1.5)*s}" fill="none" stroke="{"#ffffff" if led else "#2a2a2e"}" stroke-width="{0.9*s}"/>'
        f'<circle cx="{X(cx)}" cy="{Y(cy)}" r="{(r-2.6)*s}" fill="#252528"/>')
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{bg}"/>',
         f'<rect x="{X(-100)}" y="{Y(-26)}" width="{200*s}" height="{52*s}" rx="{6*s}" fill="#2c2d30"/>',
         f'<rect x="{X(-94)}" y="{Y(-23)}" width="{188*s}" height="{46*s}" rx="{3*s}" fill="#37383c"/>',
         # OLED-vindu
         f'<rect x="{X(-65)}" y="{Y(-19)}" width="{70*s}" height="{38*s}" rx="{1.5*s}" fill="#060708"/>',
         f'<rect x="{X(-57.5)}" y="{Y(-13.75)}" width="{55*s}" height="{27.5*s}" fill="#000"/>']
    # OLED-innhold (1 px = 55/128 mm)
    px = 55 / 128 * s; sx, sy = X(-57.5), Y(-13.75)
    F = 'font-family="Helvetica Neue,Helvetica,Arial,sans-serif"'
    g += [f'<rect x="{sx+2*px}" y="{sy+1*px}" width="{22*px}" height="{9.5*px}" fill="#eef6ff"/>',
          f'<text x="{sx+13*px}" y="{sy+8.2*px}" font-size="{6.5*px}" font-weight="700" {F} fill="#000" text-anchor="middle">AIR</text>']
    for i, t in enumerate(["BT", "AUX", "USB"]):
        x0 = sx + (27 + i * 20) * px
        g += [f'<rect x="{x0}" y="{sy+1.3*px}" width="{17*px}" height="{8.9*px}" fill="none" stroke="#7d8a94" stroke-width="{0.6*px}"/>',
              f'<text x="{x0+8.5*px}" y="{sy+8.2*px}" font-size="{6.5*px}" font-weight="700" {F} fill="#7d8a94" text-anchor="middle">{t}</text>']
    g += [f'<text x="{sx+2*px}" y="{sy+25*px}" font-size="{11*px}" font-weight="700" {F} fill="#eef6ff">Midnight City</text>',
          f'<text x="{sx+2*px}" y="{sy+33.5*px}" font-size="{7*px}" {F} fill="#7d8a94">M83 · iPhone</text>',
          f'<rect x="{sx+11*px}" y="{sy+40*px}" width="{86*px}" height="{1.4*px}" fill="#2a3036"/>',
          f'<rect x="{sx+11*px}" y="{sy+40*px}" width="{36*px}" height="{1.4*px}" fill="#eef6ff"/>',
          f'<text x="{sx+2*px}" y="{sy+57.5*px}" font-size="{6*px}" font-weight="700" {F} fill="#7d8a94">VOL</text>',
          f'<text x="{sx+126*px}" y="{sy+58*px}" font-size="{12*px}" font-weight="700" {F} fill="#eef6ff" text-anchor="end">42</text>']
    for i in range(24):
        h = (3 + i * 0.25) * px
        g.append(f'<rect x="{sx+(17+i*3.5)*px}" y="{sy+59*px-h}" width="{2.5*px}" height="{h}" fill="{"#eef6ff" if i < 10 else "#2a3036"}"/>')
    # knapper
    g += [btn(20, -8.5, 7, True), btn(37, -8.5, 7, False), btn(20, 8.5, 7, False), btn(37, 8.5, 7, False), btn(-80, 0, 9.5, True)]
    # strømsymbol
    cx, cy, r = X(-80), Y(0), 3.2 * s
    g.append(f'<path d="M {cx-r*0.68} {cy-r*0.72} A {r} {r} 0 1 0 {cx+r*0.68} {cy-r*0.72}" fill="none" stroke="#fff" stroke-width="{1.1*s}" stroke-linecap="round"/>'
             f'<line x1="{cx}" y1="{cy-r-0.6*s}" x2="{cx}" y2="{cy-0.2*s}" stroke="#fff" stroke-width="{1.1*s}" stroke-linecap="round"/>')
    # knott
    g += [f'<circle cx="{X(70)}" cy="{Y(0)}" r="{17*s}" fill="#18181a"/>',
          f'<circle cx="{X(70)}" cy="{Y(0)}" r="{16.4*s}" fill="none" stroke="#2a2a2e" stroke-width="{0.6*s}"/>',
          f'<rect x="{X(70)-0.6*s}" y="{Y(-14.5)}" width="{1.2*s}" height="{5.5*s}" fill="#eeeeee" transform="rotate(-18 {X(70)} {Y(0)})"/>']
    # etiketter
    lab = lambda t, x, y, fs=2.1: f'<text x="{X(x)}" y="{Y(y)}" font-size="{fs*s}" font-weight="500" letter-spacing="{0.3*s}" {F} fill="#a3a29d" text-anchor="middle">{t}</text>'
    g += [lab("AIRPLAY", 20, -16.5), lab("BT", 37, -16.5), lab("AUX", 20, 0.5), lab("USB", 37, 0.5), lab("POWER", -80, 13.2), lab("VOL · PUSH MUTE", 70, 21.2, 2.4)]
    g.append('</svg>')
    return "\n".join(g)

os.makedirs("assets/images", exist_ok=True); os.makedirs("drivers/pultforsterker/assets/images", exist_ok=True)
for name, w in (("small", 250), ("large", 500), ("xlarge", 1000)):   # app: 250x175 / 500x350 / 1000x700
    cairosvg.svg2png(bytestring=amp_svg().encode(), write_to=f"assets/images/{name}.png", output_width=w, output_height=int(w * 0.7))
for name, w in (("small", 75), ("large", 500), ("xlarge", 1000)):    # driver: kvadratisk 75 / 500 / 1000
    cairosvg.svg2png(bytestring=amp_svg(1000, 1000).encode(), write_to=f"drivers/pultforsterker/assets/images/{name}.png", output_width=w, output_height=w)

# Enhetsikon (monokrom silhuett, Homey fargelegger den selv): front med skjerm, knapper og knott
icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">
<path fill-rule="evenodd" d="M90 330 h820 a50 50 0 0 1 50 50 v240 a50 50 0 0 1 -50 50 h-820 a50 50 0 0 1 -50 -50 v-240 a50 50 0 0 1 50 -50 z
 M300 410 h230 v180 h-230 z M580 430 a30 30 0 1 0 0.1 0 z M660 430 a30 30 0 1 0 0.1 0 z M580 510 a30 30 0 1 0 0.1 0 z M660 510 a30 30 0 1 0 0.1 0 z
 M790 420 a80 80 0 1 0 0.1 0 z M160 440 a40 40 0 1 0 0.1 0 z"/>
<path fill-rule="evenodd" d="M790 438 a62 62 0 1 0 0.1 0 z M784 448 h12 v26 h-12 z"/>
</svg>'''
open("assets/icon.svg", "w").write(icon)
open("drivers/pultforsterker/assets/icon.svg", "w").write(icon)
print("ok")
