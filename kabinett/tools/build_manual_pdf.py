#!/usr/bin/env python3
"""Bygger en designet, utskriftsklar PDF (A4) av byggeveiledningen fra eksportert markdown."""
import re, sys, base64, html, asyncio, markdown
from pathlib import Path

md_path, out_pdf = sys.argv[1], sys.argv[2]
KAB = Path("/home/claude/pultforsterker/kabinett")
IMGS = ["guide_01_deler.png", "guide_02_bak.png", "guide_03_front.png", "guide_04_inni.png"]
CAPS = ["Delene: kasse, frontplate og lokk", "Bakvegg sett bakfra, nummererte hull", "Front med nummererte posisjoner", "Innvendig plassering sett ovenfra"]

src = Path(md_path).read_text()
src = re.sub(r"^# .*\n", "", src, count=1)
src = re.sub(r"^Oct 28, 2026 · @Sebastian\n", "", src, flags=re.M)
intro, rest = src.split("## ", 1); rest = "## " + rest
i = iter(range(4))
def img(m):
    k = next(i); b = base64.b64encode((KAB / IMGS[k]).read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b}" alt=""><figcaption>Fig. {k+1} · {CAPS[k]}</figcaption></figure>'
rest = re.sub(r"&#91;image: [^\]]*\\\]", img, rest)
body = markdown.markdown(rest, extensions=["tables"])
intro_html = markdown.markdown(intro)
# steg-nummer som store tall
body = re.sub(r"<h2>Steg (\d) – (.*?)</h2>", r'<h2 class="steg"><span class="n">\1</span><span>\2</span></h2>', body)
body = body.replace("<h2>Før du starter</h2>", '<h2 class="steg"><span class="n">0</span><span>Før du starter</span></h2>')
body = body.replace("<h2>Daglig bruk</h2>", '<h2 class="steg"><span class="n">✓</span><span>Daglig bruk og feilsøking</span></h2>')
# fjern lenkeavsnittet til 3D-modellen (ikke relevant på papir) -> QR-lignende note
body = re.sub(r"<p><strong>Interaktiv 3D-modell.*?</p>", "", body, flags=re.S)

css = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
:root{--ink:#1b1c20;--mute:#6b6a66;--line:#d9d7d1;--acc:#e8562a;--soft:#f4f3ef}
*{box-sizing:border-box} body{font-family:Inter,"Liberation Sans",sans-serif;color:var(--ink);font-size:10.3pt;line-height:1.45;margin:0}
code{font-family:"DejaVu Sans Mono",monospace;font-size:8.8pt;background:var(--soft);padding:0 3px;border-radius:3px}
.cover{height:257mm;display:flex;flex-direction:column;justify-content:space-between;page-break-after:always;border-left:6px solid var(--acc);padding-left:12mm}
.cover .kicker{font-size:10pt;letter-spacing:.14em;text-transform:uppercase;color:var(--mute)}
.cover h1{font-size:40pt;line-height:1.02;margin:6mm 0 4mm;font-weight:700;letter-spacing:-.02em}
.cover .sub{font-size:14pt;color:var(--mute);max-width:120mm}
.cover .spec{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm;border-top:1px solid var(--line);padding-top:6mm;font-size:9.5pt}
.cover .spec b{display:block;font-size:8pt;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin-bottom:1mm}
.cover img{width:120mm;margin:6mm 0;display:block}
.intro{page-break-after:always}
.intro p{max-width:150mm}
h2.steg{page-break-before:always;display:flex;align-items:baseline;gap:5mm;margin:0 0 5mm;font-size:22pt;letter-spacing:-.01em;border-bottom:2px solid var(--ink);padding-bottom:3mm}
h2.steg .n{font-size:30pt;color:var(--acc);font-weight:800;min-width:14mm}
h2:not(.steg){font-size:16pt;margin:8mm 0 3mm}
p{margin:0 0 3mm} ul,ol{margin:0 0 3mm;padding-left:6mm} li{margin-bottom:1.6mm} li::marker{color:var(--acc);font-weight:700}
ol li strong:first-child{color:var(--ink)}
strong{font-weight:700}
table{border-collapse:collapse;width:100%;margin:2mm 0 5mm;font-size:9.3pt;page-break-inside:avoid}
th{text-align:left;font-size:8pt;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);border-bottom:1.5px solid var(--ink);padding:1.5mm 2mm}
td{padding:1.6mm 2mm;border-bottom:1px solid var(--line);vertical-align:top}
tr:nth-child(even) td{background:var(--soft)}
figure{margin:4mm 0 6mm;page-break-inside:avoid} figure img{max-width:100%;max-height:72mm;display:block;margin:0 auto;border:1px solid var(--line);border-radius:3px}
figcaption{font-size:8.5pt;color:var(--mute);margin-top:1.5mm}
.note{border-left:3px solid var(--acc);background:var(--soft);padding:3mm 4mm;margin:3mm 0 5mm;page-break-inside:avoid}
"""
cover_img = base64.b64encode((KAB / "preview_v2.png").read_bytes()).decode() if (KAB/"preview_v2.png").exists() else ""
page = f"""<!doctype html><html lang="nb"><head><meta charset="utf-8"><title>Pultforsterker – Byggeveiledning</title><style>{css}</style></head><body>
<section class="cover">
 <div><div class="kicker">Byggeveiledning · v2</div><h1>Pultforsterker</h1>
 <p class="sub">AirPlay 2 · Bluetooth · AUX · USB · 2 × 50 W. Fra deler i posen til ferdig forsterker under pulten, steg for steg.</p>
 {'<img src="data:image/png;base64,'+cover_img+'" alt="">' if cover_img else ''}</div>
 <div class="spec"><div><b>Kabinett</b>200 × 120 × 48 mm, 3D-printet, tre deler</div><div><b>Hjerne</b>Raspberry Pi Zero 2 W + PCM5102A</div><div><b>Forsterker</b>XH-M562 TPA3116D2, 24 V</div>
 <div><b>Styring</b>5 LED-knapper, encoder, 2,42" OLED</div><div><b>Integrasjoner</b>Home Assistant · Homey</div><div><b>Dato</b>28. oktober 2026 · Sebastian Kristo</div></div>
</section>
<section class="intro"><h2>Om denne veiledningen</h2>{intro_html}
<div class="note"><strong>Slik leser du den.</strong> Hvert steg har et mål øverst. Fet tekst er handlinger; tall i bildene henviser til nummererte punkter i teksten. Mål er i millimeter fra kassens senter (x), høyde fra bunnen (z). Deleliste, koblingsskjema og kode står i hoveddokumentet «Pultforsterker – AirPlay + PC/Mac».</div>
<h2>Innhold</h2><ol><li>Før du starter</li><li>Steg 1 – Elektronikken på bordet</li><li>Steg 2 – Print og klargjør kabinettet</li><li>Steg 3 – Bakveggen</li><li>Steg 4 – Fronten</li><li>Steg 5 – Kort og moduler inni</li><li>Steg 6 – Ledninger</li><li>Steg 7 – Test, lokk og montering</li><li>Daglig bruk og feilsøking</li></ol></section>
{body}
</body></html>"""
Path(out_pdf).with_suffix(".html").write_text(page)

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.set_content(page); await pg.emulate_media(media="print")
        await pg.pdf(path=out_pdf, format="A4", print_background=True, display_header_footer=True,
            header_template="<div></div>",
            footer_template='<div style="width:100%;font-family:Inter,sans-serif;font-size:7.5pt;color:#6b6a66;padding:0 16mm;display:flex;justify-content:space-between"><span>Pultforsterker – Byggeveiledning</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
            margin={"top":"18mm","bottom":"20mm","left":"16mm","right":"16mm"})
        await b.close()
asyncio.run(main()); print("ok")
