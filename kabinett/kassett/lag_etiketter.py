#!/usr/bin/env python3
"""Etikettark for Skjold Kassett (A4): SVG + DXF (kuttlinjer på eget lag «Kutt») + PDF (via Chromium/Playwright hvis tilgjengelig).
Cover 44 × 49,6 mm med øvre hjørner avfaset 7 mm – legges inni kassetten bak etikettvinduet (ingen lim), 3 × 5 per ark.
Rammen dekker 2,4 mm langs kanten. Samme form som lag_cover.py og papW/papH/papC i skjold_kassett.scad."""
import math, os, subprocess, sys

W, H = 210.0, 297.0
LW, LH, C, RIM = 44.0, 49.6, 7.0, 2.4
COLS, ROWS = 3, 5
GX, GY = 8.0, 4.0
MX = (W - COLS * LW - (COLS - 1) * GX) / 2
MY = (H - ROWS * LH - (ROWS - 1) * GY) / 2
OUT = os.path.dirname(os.path.abspath(__file__))

def cells():
    for r in range(ROWS):
        for c in range(COLS):
            yield MX + c * (LW + GX), MY + r * (LH + GY)

def punkter(inset=0.0):
    c = C - inset * (math.sqrt(2) - 1)
    a, w, h = inset, LW - inset, LH - inset
    return [(a + c, a), (w - c, a), (w, a + c), (w, h), (a, h), (a, a + c)]


def omriss(inset=0.0):
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in punkter(inset)) + " Z"


def svg():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
         '<style>.k{fill:none;stroke:#e0451b;stroke-width:.2}.b{fill:#f6f3ee}.t{font-family:Sora,Helvetica,Arial,sans-serif}</style>',
         f'<text x="{MX}" y="{MY-4}" font-size="3" fill="#8b8b86" class="t">SKJOLD KASSETT · cover 44 × 49,6 mm · rød linje = kutt (eget lag) · grått felt = synlig i vinduet</text>']
    for x, y in cells():
        p.append(f'<g transform="translate({x:.2f},{y:.2f})">'
                 f'<path class="b" d="{omriss()}"/>'
                 f'<path d="{omriss(RIM)}" fill="#e4e1db"/>'
                 f'<text x="{RIM+1}" y="{LH-RIM-4}" font-size="3.0" font-weight="600" class="t" fill="#1b1b1c">Tittel</text>'
                 f'<text x="{RIM+1}" y="{LH-RIM-1}" font-size="2.3" class="t" fill="#6a6a65">Artist · kilde</text>'
                 f'<path class="k" d="{omriss()}"/></g>')
    p.append('</svg>')
    open(os.path.join(OUT, 'etiketter_a4.svg'), 'w').write('\n'.join(p))

def dxf():
    def poly(x, y):
        pts = [(x + px, y + py, 0) for px, py in punkter()]   # papirformen (avfasede øvre hjørner) som lukket LWPOLYLINE
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
