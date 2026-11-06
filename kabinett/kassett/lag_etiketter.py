#!/usr/bin/env python3
"""Etikettark for Skjold Kassett (A4): SVG + DXF (kuttlinjer på eget lag «Kutt») + PDF (via Chromium/Playwright hvis tilgjengelig).
Etikett 43,2 × 51,2 mm (litt mindre enn den 44 × 52 mm forsenkningen), hjørneradius 2 mm, 3 kolonner × 5 rader."""
import math, os, subprocess, sys

W, H = 210.0, 297.0
LW, LH, R = 43.2, 51.2, 2.0
COLS, ROWS = 3, 5
GX, GY = 8.0, 4.0
MX = (W - COLS * LW - (COLS - 1) * GX) / 2
MY = (H - ROWS * LH - (ROWS - 1) * GY) / 2
OUT = os.path.dirname(os.path.abspath(__file__))

def cells():
    for r in range(ROWS):
        for c in range(COLS):
            yield MX + c * (LW + GX), MY + r * (LH + GY)

def svg():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
         '<style>.k{fill:none;stroke:#e0451b;stroke-width:.2}.b{fill:#f6f3ee}.t{font-family:Sora,Helvetica,Arial,sans-serif}</style>',
         f'<text x="{MX}" y="{MY-4}" font-size="3" fill="#8b8b86" class="t">SKJOLD KASSETT · etiketter 43,2 × 51,2 mm · rød linje = kutt (eget lag)</text>']
    for x, y in cells():
        p.append(f'<g transform="translate({x:.2f},{y:.2f})">'
                 f'<rect class="b" width="{LW}" height="{LH}" rx="{R}"/>'
                 f'<rect x="3" y="3" width="{LW-6}" height="{LW-6}" rx="1.2" fill="#e4e1db"/>'
                 f'<text x="3" y="{LW+1.6}" font-size="3.2" font-weight="600" class="t" fill="#1b1b1c">Tittel</text>'
                 f'<text x="3" y="{LW+5.4}" font-size="2.4" class="t" fill="#6a6a65">Artist · kilde</text>'
                 f'<text x="{LW-3}" y="{LH-2}" font-size="1.8" class="t" fill="#b0aca4" text-anchor="end" letter-spacing=".4">SKJOLD</text>'
                 f'<rect class="k" width="{LW}" height="{LH}" rx="{R}"/></g>')
    p.append('</svg>')
    open(os.path.join(OUT, 'etiketter_a4.svg'), 'w').write('\n'.join(p))

def dxf():
    def poly(x, y):
        # avrundet rektangel som LWPOLYLINE med bulge (tan(90°/4)) på hjørnene
        b = math.tan(math.pi / 8)
        pts = [(x+R, y, 0), (x+LW-R, y, b), (x+LW, y+R, 0), (x+LW, y+LH-R, b), (x+LW-R, y+LH, 0), (x+R, y+LH, b), (x, y+LH-R, 0), (x, y+R, b)]
        s = ['0', 'LWPOLYLINE', '8', 'Kutt', '62', '1', '90', str(len(pts)), '70', '1']
        for px, py, bb in pts:
            s += ['10', f'{px:.3f}', '20', f'{H-py:.3f}'] + (['42', f'{bb:.6f}'] if bb else [])
        return s
    out = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC',
           '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER', '70', '1',
           '0', 'LAYER', '2', 'Kutt', '70', '0', '62', '1', '6', 'CONTINUOUS', '0', 'ENDTAB', '0', 'ENDSEC',
           '0', 'SECTION', '2', 'ENTITIES']
    for x, y in cells():
        out += poly(x, y)
    out += ['0', 'ENDSEC', '0', 'EOF']
    open(os.path.join(OUT, 'etiketter_a4.dxf'), 'w').write('\n'.join(out) + '\n')

def pdf():
    svgp = os.path.join(OUT, 'etiketter_a4.svg')
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print('Playwright mangler – hopper over PDF'); return
    html = f'<html><head><style>@page{{size:A4;margin:0}}body{{margin:0}}</style></head><body>{open(svgp).read()}</body></html>'
    with sync_playwright() as p:
        exe = '/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None
        try: b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        except Exception as e: print('Chromium mangler – hopper over PDF:', e); return
        pg = b.new_page(); pg.set_content(html)
        pg.pdf(path=os.path.join(OUT, 'etiketter_a4.pdf'), width='210mm', height='297mm', print_background=True)
        b.close()

if __name__ == '__main__':
    svg(); dxf(); pdf(); print('etiketter_a4.svg/.dxf/.pdf skrevet')
