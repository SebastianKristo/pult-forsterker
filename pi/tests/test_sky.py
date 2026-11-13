"""Tester for sky-modulen i ki_amp_daemon.py (Skjold-hjem, docs/SKJOLD_HJEM.md).

Kjør:  python3 -m unittest discover -s pi/tests -v
Integrasjonstesten starter den ekte Workeren (skjold/sky) i Miniflare og krever `npm ci` i skjold/sky; ellers hoppes den over.
"""
import asyncio
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.dirname(os.path.dirname(HER))
SKY_DIR = os.path.join(ROT, "skjold", "sky")
_tmp = tempfile.mkdtemp(prefix="ki-sky-")
os.environ["KI_AMP_SKY_FILE"] = os.path.join(_tmp, "sky.json")   # før import: daemonens globale `sky` leser denne
sys.path.insert(0, os.path.join(ROT, "pi"))
import ki_amp_daemon as d  # noqa: E402
from aiohttp import web, ClientSession  # noqa: E402


class FalskLan:
    def __init__(self, peers):
        self.peers = peers


class TestSkyLokalt(unittest.TestCase):
    def test_konfig_0600_og_ingen_nokkel_i_status(self):
        sti = os.path.join(tempfile.mkdtemp(), "under", "sky.json")
        s = d.Sky(path=sti, lan=False, ident="pi-x")
        self.assertFalse(s.status()["koblet"])
        s._skriv({"url": "https://x", "sted": "st_abc", "id": "pi-x", "noekkel": "st_abc." + "f" * 64})
        self.assertEqual(stat.S_IMODE(os.stat(sti).st_mode), 0o600)
        s2 = d.Sky(path=sti, lan=False, ident="pi-x")
        self.assertTrue(s2.status()["koblet"])
        self.assertNotIn("f" * 64, json.dumps(s2.status()) + json.dumps(s2.kort()))
        self.assertEqual(s2.kort(), {"koblet": True, "sted": "st_abc", "erAktivHoved": False})
        s2.aktiv = "pi-x"
        self.assertTrue(s2.kort()["erAktivHoved"])

    def test_status_har_sky(self):
        self.assertEqual(d.read_status()["sky"], {"koblet": False, "sted": None, "erAktivHoved": False})

    def test_avahi_tolking(self):
        txt = ('+;eth0;IPv4;Stue;_kipultamp._tcp;local\n'
               '=;eth0;IPv4;Skjold\\032Stue;_kipultamp._tcp;local;stue.local;192.168.1.20;8765;"path=/api/status" "product=core" "name=Stue" "id=stue"\n'
               '=;eth0;IPv6;Skjold\\032Stue;_kipultamp._tcp;local;stue.local;fe80::1;8765;"id=stue"\n'
               '=;eth0;IPv4;Meg;_kipultamp._tcp;local;meg.local;192.168.1.21;8765;"id=meg"\n')
        p = d.LanPeers.parse_avahi(txt, "meg")
        self.assertEqual(p, {"stue": {"id": "stue", "navn": "Stue", "ip": "192.168.1.20", "port": 8765, "produkt": "core"}})

    def test_mal_og_stisperre(self):
        s = d.Sky(path=os.path.join(_tmp, "x.json"), lan=FalskLan({"b": {"id": "b", "ip": "10.0.0.5", "port": 8765}}),
                  ident="a", local="http://127.0.0.1:1")
        self.assertEqual(s._maal("a"), "http://127.0.0.1:1")
        self.assertEqual(s._maal(None), "http://127.0.0.1:1")
        self.assertEqual(s._maal("b"), "http://10.0.0.5:8765")
        self.assertIsNone(s._maal("ukjent"))
        self.assertIsNone(Sky_sjekk("GET", "/api/status"))
        self.assertIsNotNone(Sky_sjekk("GET", "/etc/passwd"))
        self.assertIsNotNone(Sky_sjekk("POST", "/api/sky"))
        self.assertIsNone(Sky_sjekk("GET", "/api/sky"))


def Sky_sjekk(m, p):
    return d.Sky._sjekk_sti(m, p)


async def falsk_enhet(navn):
    """Et lite «eget API» som svarer som daemonen: /api/status, /api/volume (ekko), /api/events (SSE)."""
    async def status(_r):
        return web.json_response({"id": navn, "name": navn})

    async def volume(r):
        return web.json_response({"id": navn, "fikk": await r.json()})

    async def events(r):
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await resp.prepare(r)
        await resp.write(b"retry: 2000\n\n")
        n = 0
        try:
            while True:
                await resp.write(b"data: " + json.dumps({"id": navn, "n": n}).encode() + b"\n\n")
                n += 1
                await asyncio.sleep(0.05)
        except (ConnectionResetError, asyncio.CancelledError, RuntimeError):
            pass
        return resp
    app = web.Application()
    app.add_routes([web.get("/api/status", status), web.post("/api/volume", volume), web.get("/api/events", events)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, port



async def falsk_nabo(koblet, mottatt, status=200):
    """En Skjold-enhet på LAN-et sett fra hovedenheten: GET /api/sky sier om den er med i et sted, POST tar imot koden."""
    async def hent(_r):
        return web.json_response({"koblet": koblet})

    async def post(r):
        mottatt.append(await r.json())
        return web.json_response({"koblet": True}, status=status)
    app = web.Application()
    app.add_routes([web.get("/api/sky", hent), web.post("/api/sky", post)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    return runner, site._server.sockets[0].getsockname()[1]


class TestAutomatiskInnmelding(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runners, self.skyer = [], []

    async def asyncTearDown(self):
        for s in self.skyer:
            await s.close()
        for r in self.runners:
            await r.cleanup()

    def hoved(self, peers):
        sti = os.path.join(tempfile.mkdtemp(), "sky.json")
        s = d.Sky(path=sti, lan=FalskLan(peers), ident="pi-a", local="http://127.0.0.1:1")
        s.cfg = {"url": "https://hjem.test", "sted": "st_x", "id": "pi-a", "noekkel": "st_x." + "0" * 64}
        self.skyer.append(s)
        return s

    async def test_leverer_koden_til_enhet_som_ikke_er_med(self):
        mottatt = []
        r, port = await falsk_nabo(False, mottatt)
        self.runners.append(r)
        s = self.hoved({"nabo": {"id": "nabo", "ip": "127.0.0.1", "port": port}})
        self.assertTrue(await s._inviter({"t": "inviter", "til": "nabo", "kode": "K7Q2XM"}))
        self.assertEqual(mottatt, [{"kode": "K7Q2XM", "auto": True, "url": "https://hjem.test"}])

    async def test_rorer_ikke_enhet_som_alt_er_med_i_et_sted(self):
        mottatt = []
        r, port = await falsk_nabo(True, mottatt)
        self.runners.append(r)
        s = self.hoved({"nabo": {"id": "nabo", "ip": "127.0.0.1", "port": port}})
        self.assertFalse(await s._inviter({"t": "inviter", "til": "nabo", "kode": "K7Q2XM"}))
        self.assertEqual(mottatt, [])

    async def test_bare_enheter_funnet_paa_lan_og_gyldig_kode(self):
        mottatt = []
        r, port = await falsk_nabo(False, mottatt)
        self.runners.append(r)
        s = self.hoved({"nabo": {"id": "nabo", "ip": "127.0.0.1", "port": port}})
        self.assertFalse(await s._inviter({"t": "inviter", "til": "ukjent", "kode": "K7Q2XM"}))
        self.assertFalse(await s._inviter({"t": "inviter", "til": "nabo", "kode": "../x"}))
        self.assertFalse(await s._inviter({"t": "inviter", "til": "pi-a", "kode": "K7Q2XM"}))   # aldri oss selv
        self.assertEqual(mottatt, [])

    async def test_nabo_som_ikke_svarer_eller_avslaar(self):
        s = self.hoved({"dod": {"id": "dod", "ip": "127.0.0.1", "port": 9}})
        self.assertFalse(await s._inviter({"t": "inviter", "til": "dod", "kode": "K7Q2XM"}))
        mottatt = []
        r, port = await falsk_nabo(False, mottatt, status=409)
        self.runners.append(r)
        s2 = self.hoved({"nabo": {"id": "nabo", "ip": "127.0.0.1", "port": port}})
        self.assertFalse(await s2._inviter({"t": "inviter", "til": "nabo", "kode": "K7Q2XM"}))


class FalskForesporsel:
    def __init__(self, kropp):
        self._k = kropp

    async def json(self):
        return self._k


class TestAutoPaaMottakeren(unittest.IsolatedAsyncioTestCase):
    """POST /api/sky {kode, auto}: en annen enhet melder oss inn. Bare når vi ikke er med i noe sted fra før."""
    async def asyncSetUp(self):
        self.gammel, self.gammel_auto = d.sky, d.SKY_AUTO
        self.kall = []

        class Sky:
            cfg = {}

            def status(self_):
                return {"koblet": bool(self_.cfg)}

            async def kobl(self_, kode, url=None):
                self.kall.append((kode, url))
                return {"koblet": True}
        d.sky = Sky()

    async def asyncTearDown(self):
        d.sky, d.SKY_AUTO = self.gammel, self.gammel_auto

    async def test_ledig_enhet_tar_imot(self):
        r = await d.h_sky_post(FalskForesporsel({"kode": "K7Q2XM", "auto": True, "url": "https://hjem.test"}))
        self.assertEqual(r.status, 200)
        self.assertEqual(self.kall, [("K7Q2XM", "https://hjem.test")])

    async def test_koblet_enhet_avslaar_auto_men_ikke_egen_kode(self):
        d.sky.cfg = {"sted": "st_annet"}
        r = await d.h_sky_post(FalskForesporsel({"kode": "K7Q2XM", "auto": True}))
        self.assertEqual(r.status, 409)
        self.assertEqual(self.kall, [])
        r = await d.h_sky_post(FalskForesporsel({"kode": "K7Q2XM"}))     # tastet inn av brukeren: flytter enheten
        self.assertEqual(r.status, 200)

    async def test_kan_slaas_av_paa_enheten(self):
        d.SKY_AUTO = False
        r = await d.h_sky_post(FalskForesporsel({"kode": "K7Q2XM", "auto": True}))
        self.assertEqual(r.status, 409)
        self.assertEqual(self.kall, [])


HAR_MINIFLARE = shutil.which("node") and os.path.isdir(os.path.join(SKY_DIR, "node_modules", "miniflare"))


@unittest.skipUnless(HAR_MINIFLARE, "krever node + `npm ci` i skjold/sky")
class TestSkyMotWorker(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.proc = await asyncio.create_subprocess_exec("node", os.path.join(SKY_DIR, "test", "server.mjs"), cwd=SKY_DIR,
                                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        linje = await asyncio.wait_for(self.proc.stdout.readline(), 60)
        self.sky_url = json.loads(linje)["url"]
        self.http = ClientSession()
        self.runners = []

    async def asyncTearDown(self):
        await self.http.close()
        for r in self.runners:
            await r.cleanup()
        self.proc.stdin.close()
        try:
            await asyncio.wait_for(self.proc.wait(), 15)
        except asyncio.TimeoutError:
            self.proc.kill()

    async def api(self, metode, sti, kropp=None):
        async with self.http.request(metode, self.sky_url + sti, json=kropp, headers={"X-Skjold-User": "eier@test.no"}) as r:
            tekst = await r.text()
            try:
                return r.status, json.loads(tekst)
            except ValueError:
                return r.status, tekst

    async def vent(self, pred, s=10):
        for _ in range(int(s * 20)):
            if pred():
                return
            await asyncio.sleep(0.05)
        self.fail("tidsavbrudd")

    async def test_kobling_rele_lan_og_sse(self):
        ra, port_a = await falsk_enhet("pi-a")
        rb, port_b = await falsk_enhet("lan-b")
        self.runners += [ra, rb]
        s, sted = await self.api("POST", "/api/hjem/steder", {"navn": "Hytta"})
        self.assertEqual(s, 201)
        sted = sted["id"]
        _, kode = await self.api("POST", f"/api/hjem/steder/{sted}/kobling")
        sti = os.path.join(tempfile.mkdtemp(), "sky.json")
        sky = d.Sky(path=sti, url=self.sky_url, local=f"http://127.0.0.1:{port_a}", ident="pi-a",
                    info=lambda: {"navn": "Stue", "produkt": "core", "versjon": "2.0"},
                    lan=FalskLan({"lan-b": {"id": "lan-b", "navn": "Kjøkken", "ip": "127.0.0.1", "port": port_b, "produkt": "node"}}))
        with self.assertRaises(d.SkyFeil):
            await sky.kobl("AAAAAA")   # ukjent kode
        st = await sky.kobl(kode["kode"])
        self.assertTrue(st["koblet"])
        self.assertEqual(st["sted"], sted)
        self.assertEqual(stat.S_IMODE(os.stat(sti).st_mode), 0o600)
        with open(sti) as fh:
            self.assertTrue(json.load(fh)["noekkel"].startswith(sted + "."))
        oppgave = asyncio.create_task(sky.run())
        try:
            await self.vent(lambda: sky.tilkoblet and sky.aktiv == "pi-a")
            self.assertTrue(sky.status()["erHoved"])

            s, svar = await self.api("GET", f"/api/hjem/steder/{sted}/enheter/pi-a/api/status")
            self.assertEqual((s, svar["id"]), (200, "pi-a"))
            s, svar = await self.api("POST", f"/api/hjem/steder/{sted}/enheter/pi-a/api/volume", {"volume": 25})
            self.assertEqual(svar, {"id": "pi-a", "fikk": {"volume": 25}})
            # LAN-enhet bak aktiv hovedenhet (til)
            await asyncio.sleep(0.3)
            s, svar = await self.api("GET", f"/api/hjem/steder/{sted}/enheter/lan-b/api/status")
            self.assertEqual((s, svar["id"]), (200, "lan-b"))
            # /api/sky kan ikke endres via skyen
            s, _ = await self.api("POST", f"/api/hjem/steder/{sted}/enheter/pi-a/api/sky", {"koble_fra": True})
            self.assertEqual(s, 403)
            self.assertTrue(sky.status()["koblet"])
            # enhetslista
            s, enheter = await self.api("GET", f"/api/hjem/steder/{sted}/enheter")
            self.assertEqual(enheter[0]["navn"], "Stue")
            self.assertTrue(enheter[0]["online"] and enheter[0]["aktivHoved"])
            # SSE via relé (både egen og LAN-enhet)
            for mal in ("pi-a", "lan-b"):
                async with self.http.get(f"{self.sky_url}/api/hjem/steder/{sted}/enheter/{mal}/api/events",
                                         headers={"X-Skjold-User": "eier@test.no"}) as r:
                    self.assertEqual(r.headers["content-type"], "text/event-stream")
                    data = []
                    while len(data) < 3:
                        linje = (await asyncio.wait_for(r.content.readline(), 10)).decode().strip()
                        if linje.startswith("data: "):
                            data.append(json.loads(linje[6:]))
                    self.assertEqual([x["id"] for x in data], [mal] * 3)
                    self.assertEqual(data[1]["n"], data[0]["n"] + 1)
            await self.vent(lambda: not sky._subs, 10)   # unsub kom frem og strømmen ble stoppet
            # koble fra
            sky.koble_fra()
            self.assertFalse(os.path.exists(sti))
            await self.vent(lambda: not sky.tilkoblet)
        finally:
            oppgave.cancel()
            try:
                await oppgave
            except asyncio.CancelledError:
                pass
            await sky.close()

    async def test_sky_utilgjengelig_krasjer_ikke(self):
        sti = os.path.join(tempfile.mkdtemp(), "sky.json")
        sky = d.Sky(path=sti, url="http://127.0.0.1:9", lan=False, ident="pi-z")
        with self.assertRaises(d.SkyFeil) as e:
            await sky.kobl("ABCDEF")
        self.assertEqual(e.exception.status, 502)
        sky._skriv({"url": "http://127.0.0.1:9", "sted": "st_x", "id": "pi-z", "noekkel": "st_x." + "0" * 64})
        sky.cfg = sky._les()
        oppgave = asyncio.create_task(sky.run())
        await asyncio.sleep(0.5)
        self.assertFalse(oppgave.done())   # løkka lever og prøver igjen med pause
        self.assertTrue(sky.status()["feil"])
        self.assertFalse(sky.tilkoblet)
        oppgave.cancel()
        try:
            await oppgave
        except asyncio.CancelledError:
            pass
        await sky.close()


if __name__ == "__main__":
    unittest.main()
