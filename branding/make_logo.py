#!/usr/bin/env python3
"""Logo og ikon for KI Pultforsterker (Homey-app, Home Assistant brands, README)."""
import cairosvg, os, shutil
F = 'font-family="Helvetica Neue,Helvetica,Arial,sans-serif"'
def mark(x, y, s, fg="#ffffff", accent="#e8562a"):
    # volumknott: 270° ring med markør, lydbølge-«K» inni
    cx, cy = x + s/2, y + s/2; r = s*0.36
    import math
    a0, a1 = math.radians(135), math.radians(405)
    p0 = (cx + r*math.cos(a0), cy + r*math.sin(a0)); p1 = (cx + r*math.cos(a1), cy + r*math.sin(a1))
    return (f'<path d="M {p0[0]} {p0[1]} A {r} {r} 0 1 1 {p1[0]} {p1[1]}" fill="none" stroke="{fg}" stroke-width="{s*0.085}" stroke-linecap="round"/>'
            f'<line x1="{cx}" y1="{cy - r*0.98}" x2="{cx}" y2="{cy - r*0.6}" stroke="{accent}" stroke-width="{s*0.085}" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{s*0.07}" fill="{fg}"/>')
def icon_svg(size=512, bg="#2c2d30"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{size*0.22}" fill="{bg}"/>{mark(0,0,size)}</svg>')
def logo_svg(w=1700, h=400, bg="none", fg="#2c2d30"):
    s = h
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>'
            f'<rect x="{h*0.05}" y="{h*0.05}" width="{h*0.9}" height="{h*0.9}" rx="{h*0.2}" fill="#2c2d30"/>{mark(h*0.05,h*0.05,h*0.9)}'
            f'<text x="{h*1.1}" y="{h*0.47}" font-size="{h*0.3}" font-weight="700" {F} fill="{fg}">Pultforsterker</text>'
            f'<text x="{h*1.1}" y="{h*0.72}" font-size="{h*0.14}" font-weight="400" letter-spacing="{h*0.01}" {F} fill="#a3a29d">AIRPLAY 2 · BLUETOOTH · AUX · USB · 2 × 50 W</text></svg>')
os.makedirs("out", exist_ok=True)
open("out/icon.svg", "w").write(icon_svg()); open("out/logo.svg", "w").write(logo_svg()); open("out/logo_dark.svg", "w").write(logo_svg(fg="#ecebe6"))
for n in (256, 512, 1024): cairosvg.svg2png(bytestring=icon_svg().encode(), write_to=f"out/icon@{n}.png", output_width=n, output_height=n)
cairosvg.svg2png(bytestring=logo_svg().encode(), write_to="out/logo.png", output_width=1700, output_height=400)
cairosvg.svg2png(bytestring=logo_svg(fg="#ecebe6").encode(), write_to="out/logo_dark.png", output_width=1700, output_height=400)
# Home Assistant brands (home-assistant/brands → custom_integrations/ki_pultforsterker/)
hb = "../homeassistant/brands/ki_pultforsterker"; os.makedirs(hb, exist_ok=True)
for n, nm in ((256, "icon.png"), (512, "icon@2x.png")): shutil.copy(f"out/icon@{n}.png", f"{hb}/{nm}")
cairosvg.svg2png(bytestring=logo_svg(bg="none").encode(), write_to=f"{hb}/logo.png", output_width=1700, output_height=400)
cairosvg.svg2png(bytestring=logo_svg(bg="none").encode(), write_to=f"{hb}/logo@2x.png", output_width=3400, output_height=800)
# Homey-app: app-ikonet er monokrom SVG (Homey fargelegger selv)
mono = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        + mark(0, 0, 512, fg="#000000", accent="#000000") + '</svg>')
open("../homey/no.kristo.ki-pultforsterker/assets/icon.svg", "w").write(mono)
print("ok")
