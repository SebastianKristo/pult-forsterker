#!/usr/bin/env python3
"""Tar skjermbilder av render3d.html (three.js) med headless Chromium -> ../render/*.png. Kjør render_textures.py først."""
import asyncio, os, sys, threading, functools, base64
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "render"); os.makedirs(OUT, exist_ok=True)
VIEWS = sys.argv[1:] or ["front34", "back34", "front", "back", "left", "bottom"]

async def main():
    # ES-moduler krever http: liten lokal server med rot i skjold-s1/ (teksturer ligger i ../render/tex)
    root = os.path.abspath(os.path.join(HERE, ".."))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(SimpleHTTPRequestHandler, directory=root))
    srv_log = SimpleHTTPRequestHandler.log_message; SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
    threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_address[1]
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        pg.on("console", lambda m: print("console:", m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: print("pageerror:", e))
        for v in VIEWS:
            await pg.goto(f"http://127.0.0.1:{port}/tools/render3d.html?view={v}&w=1920&h=1080")
            await pg.wait_for_function("document.title === 'ready'", timeout=120000)
            data = await pg.evaluate("document.querySelector('canvas').toDataURL('image/png')")
            import base64; open(os.path.join(OUT, f"pultforsterker_{v}.png"), "wb").write(base64.b64decode(data.split(",", 1)[1]))
            print("skrev", f"pultforsterker_{v}.png")
        await b.close()
    srv.shutdown()
asyncio.run(main())
