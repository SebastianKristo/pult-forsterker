#!/usr/bin/env python3
"""Generate the Skjold logo SVG + PNG icons (PWA, Capacitor) from the design tokens.

Logo: five rounded bars, heights 22/33/42/33/22, width 4.6 (ratio), top-aligned.
Run: python3 tools/make_icons.py   (needs cairosvg)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'icons')
os.makedirs(OUT, exist_ok=True)

def bars(x0, y0, scale, color):
    hs = [22, 33, 42, 33, 22]; w = 4.6; gap = 3.4
    parts = []
    for i, h in enumerate(hs):
        x = x0 + i * (w + gap) * scale
        parts.append(f'<rect x="{x:.2f}" y="{y0:.2f}" width="{w*scale:.2f}" height="{h*scale:.2f}" rx="{w*scale/2:.2f}" fill="{color}"/>')
    return '\n'.join(parts)

def icon_svg(size=512, bg='#0b0b0c', fg='#f2f2ee', pad=0.22, maskable=False):
    # total logo width = 5*4.6 + 4*3.4 = 36.6 units, height 42 units
    r = 0 if maskable else size * 0.22
    scale = size * (1 - 2 * pad) / 42
    lw = 36.6 * scale; lh = 42 * scale
    x0 = (size - lw) / 2; y0 = (size - lh) / 2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{r:.1f}" fill="{bg}"/>' + bars(x0, y0, scale, fg) + '</svg>')

def main():
    import cairosvg
    with open(os.path.join(OUT, 'icon.svg'), 'w') as f: f.write(icon_svg())
    with open(os.path.join(OUT, 'icon-maskable.svg'), 'w') as f: f.write(icon_svg(pad=0.28, maskable=True))
    for n in (180, 192, 512):
        cairosvg.svg2png(bytestring=icon_svg(512).encode(), write_to=os.path.join(OUT, f'icon-{n}.png'), output_width=n, output_height=n)
    cairosvg.svg2png(bytestring=icon_svg(512, pad=0.28, maskable=True).encode(), write_to=os.path.join(OUT, 'icon-512-maskable.png'), output_width=512, output_height=512)
    cairosvg.svg2png(bytestring=icon_svg(1024, pad=0.28, maskable=True).encode(), write_to=os.path.join(OUT, 'icon-1024.png'), output_width=1024, output_height=1024)
    # favicon
    cairosvg.svg2png(bytestring=icon_svg(64).encode(), write_to=os.path.join(OUT, 'favicon-64.png'), output_width=64, output_height=64)
    print('icons written to', os.path.abspath(OUT))

if __name__ == '__main__':
    sys.exit(main())
