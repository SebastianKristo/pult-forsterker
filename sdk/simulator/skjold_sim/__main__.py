"""python -m skjold_sim [--port 8765] [--rom 1] [--vert 127.0.0.1]

Starter én eller flere falske Skjold-høyttalere (port, port+1, …) med samme API som den ekte daemonen:
status, SSE (/api/events), av/på, volum, demp, kilde, radiofavoritter, avspilling, transport, innstillinger og
rom-liste. «Spiller nå» bytter låt hvert 20. sekund. Som KI_AMP_LMS=0 på en ekte Skjold: ingen Lyrion bak.
Ruter som ikke er simulert svarer 501 med {"error": "...", "sim": true}.
"""
import argparse
import asyncio
import json
import os
import time

from aiohttp import web

os.environ.setdefault("KI_AMP_LMS", "0")

INPUTS = ["airplay", "spotify", "bt", "radio", "usb", "aux1"]
ROMNAVN = ["Stue", "Kjøkken", "Soverom", "Bad", "Kontor", "Hytta"]
LATER = [("Kygo", "Firestone", "Cloud Nine"), ("a-ha", "Take On Me", "Hunting High and Low"), ("Sigrid", "Strangers", "Sucker Punch"),
         ("Röyksopp", "Eple", "Melody A.M."), ("Aurora", "Runaway", "All My Demons Greeting Me as a Friend")]
PRESETS = [{"name": "NRK P1", "url": "https://lyd.nrk.no/nrk_radio_p1_ostlandssendingen_mp3_h"}, {"name": "NRK P2", "url": "https://lyd.nrk.no/nrk_radio_p2_mp3_h"},
           {"name": "NRK P3", "url": "https://lyd.nrk.no/nrk_radio_p3_mp3_h"}, {"name": "NRK mP3", "url": "https://lyd.nrk.no/nrk_radio_mp3_mp3_h"},
           {"name": "NRK Klassisk", "url": "https://lyd.nrk.no/nrk_radio_klassisk_mp3_h"}, {"name": "NRK Jazz", "url": "https://lyd.nrk.no/nrk_radio_jazz_mp3_h"}]


class Hoyttaler:
    def __init__(self, i, port, alle):
        self.port, self.alle = port, alle
        self.s = {"power": True, "volume": 30, "mute": False, "input": "radio", "inputs": list(INPUTS), "preset": 1, "playing": True,
                  "name": ROMNAVN[i % len(ROMNAVN)], "id": f"skjold-sim-{i + 1}", "product": "s1", "version": "sim-1.0.0", "sim": True,
                  "station": PRESETS[0]["name"], "title": "", "artist": "", "album": ""}
        self.settings = {"name": self.s["name"], "vmax": 100, "vstart": 30, "eq": {}}
        self.presets = [dict(p) for p in PRESETS]
        self.historikk = []
        self.lytt = set()
        self._lat(0)

    def _lat(self, n):
        a, t, al = LATER[n % len(LATER)]
        self.s.update(artist=a, title=t, album=al, started=int(time.time()))
        self.historikk = ([{"t": int(time.time()), "artist": a, "title": t, "source": self.s["input"]}] + self.historikk)[:50]

    def endret(self):
        data = ("data: " + json.dumps(self.s, ensure_ascii=False) + "\n\n").encode()
        for q in list(self.lytt):
            q.put_nowait(data)

    async def body(self, r):
        try:
            return await r.json()
        except Exception:
            return {}

    # --- handlere ---
    async def status(self, _r):
        return web.json_response(self.s)

    async def events(self, r):
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"})
        await resp.prepare(r)
        q = asyncio.Queue()
        self.lytt.add(q)
        try:
            await resp.write(b"retry: 2000\n\n" + ("data: " + json.dumps(self.s, ensure_ascii=False) + "\n\n").encode())
            while True:
                try:
                    await resp.write(await asyncio.wait_for(q.get(), 15))
                except asyncio.TimeoutError:
                    await resp.write(b": ping\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self.lytt.discard(q)
        return resp

    def _ok(self):
        self.endret()
        return web.json_response(self.s)

    async def power(self, r):
        self.s["power"] = bool((await self.body(r)).get("on", True)); self.s["playing"] = self.s["power"]; return self._ok()

    async def toggle(self, _r):
        self.s["power"] = not self.s["power"]; return self._ok()

    async def volume(self, r):
        b = await self.body(r)
        v = self.s["volume"] + int(b["delta"]) if "delta" in b else int(b.get("volume", self.s["volume"]))
        self.s["volume"] = max(0, min(int(self.settings["vmax"]), v)); return self._ok()

    async def mute(self, r):
        self.s["mute"] = bool((await self.body(r)).get("mute", True)); return self._ok()

    async def input(self, r):
        k = (await self.body(r)).get("input", "")
        if k not in INPUTS:
            return web.json_response({"error": f"input må være en av {INPUTS}"}, status=400)
        self.s.update(input=k, preset=0 if k != "radio" else self.s["preset"]); return self._ok()

    async def preset(self, r):
        b = await self.body(r)
        n = int(b.get("n", 0) or 0)
        if not 1 <= n <= len(self.presets):
            return web.json_response({"error": f"n må være 1–{len(self.presets)}"}, status=400)
        self.s.update(power=True, input="radio", preset=n, station=self.presets[n - 1]["name"], playing=True); return self._ok()

    async def presets_get(self, _r):
        return web.json_response({"presets": self.presets})

    async def play(self, r):
        b = await self.body(r)
        if not b.get("url"):
            return web.json_response({"error": "url mangler"}, status=400)
        self.s.update(power=True, playing=True, title=b.get("title") or b["url"].rsplit("/", 1)[-1], artist=b.get("artist") or "", preset=0); return self._ok()

    async def transport(self, r):
        a = (await self.body(r)).get("action", "")
        if a in ("pause", "stop"):
            self.s["playing"] = False
        elif a in ("play",):
            self.s["playing"] = True
        elif a == "playpause":
            self.s["playing"] = not self.s["playing"]
        elif a in ("next", "previous"):
            n = next((i for i, x in enumerate(LATER) if x[1] == self.s["title"]), 0)
            self._lat(n + (1 if a == "next" else -1))
        else:
            return web.json_response({"error": "ukjent action"}, status=400)
        return self._ok()

    async def settings_get(self, _r):
        return web.json_response(self.settings)

    async def settings_post(self, r):
        self.settings.update({k: v for k, v in (await self.body(r)).items() if "pass" not in k.lower()})
        if "name" in self.settings:
            self.s["name"] = self.settings["name"]
        self.endret()
        return web.json_response(self.settings)

    async def history(self, _r):
        return web.json_response({"history": self.historikk})

    async def rooms(self, _r):
        return web.json_response({"rooms": [{"id": h.s["id"], "name": h.s["name"], "host": "127.0.0.1", "port": h.port, "power": h.s["power"],
                                             "volume": h.s["volume"], "self": h is self} for h in self.alle]})

    async def ikke_simulert(self, r):
        return web.json_response({"error": f"{r.method} {r.path} er ikke simulert", "sim": True}, status=501)

    def app(self):
        @web.middleware
        async def cors(request, handler):
            r, h = request, handler
            if r.method == "OPTIONS":
                resp = web.Response()
            else:
                resp = await h(r)
            if not resp.prepared:
                resp.headers.update({"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
            return resp
        a = web.Application(middlewares=[cors])
        a.add_routes([web.get("/api/status", self.status), web.get("/api/events", self.events), web.post("/api/power", self.power),
                      web.post("/api/toggle", self.toggle), web.post("/api/volume", self.volume), web.post("/api/mute", self.mute),
                      web.post("/api/input", self.input), web.post("/api/preset", self.preset), web.get("/api/presets", self.presets_get),
                      web.post("/api/play", self.play), web.post("/api/transport", self.transport), web.get("/api/settings", self.settings_get),
                      web.post("/api/settings", self.settings_post), web.get("/api/history", self.history), web.get("/api/rooms", self.rooms),
                      web.route("*", "/{tail:.*}", self.ikke_simulert)])
        return a


async def spill(hoyttalere, sek=20):
    n = 0
    while True:
        await asyncio.sleep(sek)
        n += 1
        for h in hoyttalere:
            if h.s["power"] and h.s["playing"]:
                h._lat(n); h.endret()


async def kjor(vert, port, rom, sek=20):
    alle = []
    alle.extend(Hoyttaler(i, port + i, alle) for i in range(rom))
    runners = []
    for h in alle:
        run = web.AppRunner(h.app())
        await run.setup()
        await web.TCPSite(run, vert, h.port).start()
        runners.append(run)
        print(f"Skjold-simulator «{h.s['name']}» på http://{vert}:{h.port}/api/status", flush=True)
    await spill(alle, sek)


def main(argv=None):
    p = argparse.ArgumentParser(prog="skjold_sim", description=__doc__.split("\n")[0])
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--rom", type=int, default=1, help="antall simulerte høyttalere (port, port+1, …)")
    p.add_argument("--vert", default="127.0.0.1")
    a = p.parse_args(argv)
    try:
        asyncio.run(kjor(a.vert, a.port, max(1, min(6, a.rom))))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
