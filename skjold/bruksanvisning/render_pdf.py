#!/usr/bin/env python3
"""Renderer Bruksanvisning.dc.html (med innhold.json) til PDF med Playwright/Chromium.

Bruk (fra denne mappen, som i .github/workflows/skjold-release.yml):
    python render_pdf.py [utfil.pdf]
Standard utfil: Skjold_Byggeanvisning.pdf i denne mappen. Siden hentes over en lokal HTTP-server
fordi malen laster innhold.json med fetch(). Bruker python-playwright hvis det finnes, ellers
Node sin require('playwright') via subprocess.

Malens runtime (support.js) henter React og Babel fra unpkg.com. Uten nett: sett SKJOLD_CDN_SPEIL til en mappe
med samme stier (f.eks. <speil>/react@18.3.1/umd/react.production.min.js), så besvares de forespørslene derfra.
"""
import functools, http.server, json, os, shutil, subprocess, sys, threading

HER = os.path.dirname(os.path.abspath(__file__))
UT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HER, "Skjold_Byggeanvisning.pdf")
SIDE = "Bruksanvisning.dc.html"
ANTALL = len(json.load(open(os.path.join(HER, "innhold.json"), encoding="utf-8"))["pages"])
SPEIL = os.environ.get("SKJOLD_CDN_SPEIL", "")
VENT_JS = f"() => document.querySelectorAll('section.page').length >= {ANTALL}"


class Stille(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Stille, directory=HER))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/{SIDE}"


def med_python(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        if SPEIL:
            def svar(route):
                f = os.path.join(SPEIL, route.request.url.split("unpkg.com/", 1)[1].split("?")[0])
                route.fulfill(path=f) if os.path.isfile(f) else route.continue_()
            pg.route("https://unpkg.com/**", svar)
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_function(VENT_JS, timeout=30000)
        pg.evaluate("document.fonts.ready")
        pg.emulate_media(media="print")
        pg.pdf(path=UT, prefer_css_page_size=True, print_background=True)
        b.close()


def med_node(url):
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch(); const pg = await b.newPage();
  const speil = {json.dumps(SPEIL)}, fs = require('fs'), path = require('path');
  if (speil) await pg.route('https://unpkg.com/**', r => {{
    const f = path.join(speil, r.request().url().split('unpkg.com/')[1].split('?')[0]);
    return fs.existsSync(f) ? r.fulfill({{ path: f }}) : r.continue();
  }});
  await pg.goto({json.dumps(url)}, {{ waitUntil: 'networkidle' }});
  await pg.waitForFunction({json.dumps(VENT_JS)}.slice(6), null, {{ timeout: 30000 }});
  await pg.evaluate(() => document.fonts.ready); await pg.emulateMedia({{ media: 'print' }});
  await pg.pdf({{ path: {json.dumps(UT)}, preferCSSPageSize: true, printBackground: true }});
  await b.close();
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
    env = dict(os.environ)
    rot = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    env["NODE_PATH"] = os.pathsep.join(x for x in (env.get("NODE_PATH"), rot) if x)
    subprocess.run(["node", "-e", js], check=True, env=env)


def main():
    srv, url = server()
    try:
        try:
            med_python(url)
        except Exception as e:  # ikke installert, eller nettleseren mangler for denne versjonen
            if not shutil.which("node"):
                raise
            print(f"python-playwright feilet ({type(e).__name__}), prøver node …", file=sys.stderr)
            med_node(url)
    finally:
        srv.shutdown()
    print(f"{UT} ({ANTALL} sider forventet)")


if __name__ == "__main__":
    main()
