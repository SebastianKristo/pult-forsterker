"""Oppsett-nett: eget Wi-Fi med oppsettside når enheten ikke har nett (pi/skjold_setupnet.py).

Kjør:  python3 -m unittest pi.tests.test_setupnet -v
"""
import os
import sys
import unittest
from types import SimpleNamespace as NS
from unittest import mock

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_setupnet as sn  # noqa: E402


class Nm:
    """Falsk nmcli: husker kommandoene, og svarer med det testen har lagt inn."""

    def __init__(self):
        self.calls, self.devices, self.conns, self.fail = [], "wlan0:wifi:disconnected:\neth0:ethernet:unavailable:\n", "", set()

    def __call__(self, cmd, **kw):
        a = cmd[1:]; self.calls.append(a)
        if a[:3] == ["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION"]:
            return NS(returncode=0, stdout=self.devices, stderr="")
        if a[:3] == ["-t", "-f", "TYPE,NAME"]:
            return NS(returncode=0, stdout=self.conns, stderr="")
        key = " ".join(a[:3])
        if key in self.fail:
            return NS(returncode=10, stdout="", stderr="Error: Secrets were required, but not provided.")
        return NS(returncode=0, stdout="", stderr="")

    def har(self, *start):
        return any(c[:len(start)] == list(start) for c in self.calls)


def ny(nm, now):
    endret = []
    s = sn.SetupNet({"device_id": lambda: "skjold-s1-a1b2", "changed": lambda: endret.append(1), "scan": lambda: [{"ssid": "Hjemme", "signal": 70, "security": "wpa2"}],
                     "port": 8765}, run=nm, clock=lambda: now[0], sleep=lambda _s: None)
    return s, endret


class Navn(unittest.TestCase):
    def test_ssid_og_qr(self):
        self.assertEqual(sn.ssid_for("skjold-s1-a1b2"), "Skjold-oppsett-A1B2")
        self.assertEqual(sn.ssid_for(""), "Skjold-oppsett-0000")
        self.assertEqual(sn.wifi_qr("Skjold-oppsett-A1B2", "skjoldoppsett"), "WIFI:T:WPA;S:Skjold-oppsett-A1B2;P:skjoldoppsett;;")
        self.assertEqual(sn.wifi_qr("a;b", "p:1"), r"WIFI:T:WPA;S:a\;b;P:p\:1;;")

    def test_enheter(self):
        d = sn.parse_devices("wlan0:wifi:connected:Hjemme\\:5G\neth0:ethernet:unavailable:\nlo:loopback:unmanaged:\n")
        self.assertEqual(d[0], {"device": "wlan0", "type": "wifi", "state": "connected", "connection": "Hjemme:5G"})
        self.assertEqual(len(d), 3)


class Beslutning(unittest.TestCase):
    def test_ny_enhet_uten_nett_starter_etter_oppstartspausen(self):
        now = [1000.0]; s, _ = ny(Nm(), now)
        self.assertEqual(s.decide(1010, False, False), "")              # gi vanlig Wi-Fi tid etter oppstart
        self.assertEqual(s.decide(1000 + sn.BOOT_GRACE_S + 1, False, False), "start")

    def test_med_lagrede_nett_venter_den_tre_minutter(self):
        now = [0.0]; s, _ = ny(Nm(), now)
        t = sn.BOOT_GRACE_S + 1
        self.assertEqual(s.decide(t, False, True), "")
        self.assertEqual(s.decide(t + sn.OFFLINE_S - 1, False, True), "")
        self.assertEqual(s.decide(t + sn.OFFLINE_S, False, True), "start")

    def test_med_nett_skjer_ingenting_og_ventetiden_nullstilles(self):
        now = [0.0]; s, _ = ny(Nm(), now)
        s.decide(100, False, True)
        self.assertEqual(s.decide(200, True, True), "")
        self.assertEqual(s.t_offline, 0.0)

    def test_slaar_seg_av_naar_nettet_kommer(self):
        now = [0.0]; s, _ = ny(Nm(), now); s.active = True; s.t_start = 100
        self.assertEqual(s.decide(120, True, False), "stop")

    def test_proever_lagrede_nett_igjen_men_ikke_mens_siden_brukes(self):
        now = [0.0]; s, _ = ny(Nm(), now); s.active = True; s.t_start = 0
        self.assertEqual(s.decide(sn.RETRY_S + 1, False, True), "stop")
        s.t_hit = sn.RETRY_S                                            # noen har siden oppe
        self.assertEqual(s.decide(sn.RETRY_S + 1, False, True), "")
        self.assertEqual(s.decide(sn.RETRY_S + 1, False, False), "")    # uten lagrede nett står det på til det er satt opp


class Nettet(unittest.TestCase):
    def test_start_lager_aksesspunkt_og_status(self):
        nm = Nm(); now = [50.0]; s, endret = ny(nm, now)
        with mock.patch.object(sn, "DNS_CONF", os.path.join(self.tmp(), "d", "skjold.conf")):
            self.assertTrue(s.start())
            self.assertEqual(open(sn.DNS_CONF).read().splitlines()[-1], "address=/#/10.42.0.1")
        self.assertTrue(nm.har("device", "wifi", "hotspot", "ifname", "wlan0", "con-name", "skjold-oppsett", "ssid", "Skjold-oppsett-A1B2", "password", "skjoldoppsett"))
        self.assertTrue(nm.har("connection", "modify", "skjold-oppsett", "connection.autoconnect", "no"))
        st = s.status()
        self.assertEqual((st["active"], st["ssid"], st["url"]), (True, "Skjold-oppsett-A1B2", "http://10.42.0.1:8765/oppsett"))
        self.assertEqual(s.networks[0]["ssid"], "Hjemme")
        self.assertTrue(endret)

    def test_uten_wifi_kort_skjer_ingenting(self):
        nm = Nm(); nm.devices = "eth0:ethernet:unavailable:\n"; s, _ = ny(nm, [0.0])
        self.assertFalse(s.start()); self.assertFalse(s.active); self.assertIsNone(s.status())

    def test_koble_til_slaar_av_oppsettnettet_foerst(self):
        nm = Nm(); s, _ = ny(nm, [0.0]); s.active = True
        with mock.patch.object(sn, "DNS_CONF", os.path.join(self.tmp(), "x.conf")):
            self.assertTrue(s.connect("Hjemme", "hemmelig123"))
        ned = next(i for i, c in enumerate(nm.calls) if c[:2] == ["connection", "down"])
        opp = next(i for i, c in enumerate(nm.calls) if c[:3] == ["device", "wifi", "connect"])
        self.assertLess(ned, opp)
        self.assertEqual(nm.calls[opp], ["device", "wifi", "connect", "Hjemme", "password", "hemmelig123"])
        self.assertFalse(s.active); self.assertEqual(s.error, "")

    def test_feil_passord_gir_oppsettnettet_tilbake_med_melding(self):
        nm = Nm(); nm.fail.add("device wifi connect"); s, _ = ny(nm, [0.0]); s.active = True
        with mock.patch.object(sn, "DNS_CONF", os.path.join(self.tmp(), "x.conf")):
            self.assertFalse(s.connect("Hjemme", "feilfeil1"))
        self.assertTrue(s.active)                                       # oppsett-nettet er oppe igjen
        self.assertIn("Feil passord", s.status()["error"])
        self.assertTrue(nm.har("connection", "delete", "id", "Hjemme"))  # nettet med feil passord blir ikke liggende

    def test_er_paa_nett(self):
        nm = Nm(); s, _ = ny(nm, [0.0])
        self.assertFalse(s.online())
        nm.devices = "wlan0:wifi:connected:skjold-oppsett\n"
        self.assertFalse(s.online())                                    # vårt eget oppsett-nett teller ikke som nett
        nm.devices = "wlan0:wifi:connected:Hjemme\n"; self.assertTrue(s.online())
        nm.conns = "802-11-wireless:skjold-oppsett\n"; self.assertFalse(s.has_profiles())
        nm.conns += "802-11-wireless:Hjemme\n"; self.assertTrue(s.has_profiles())

    def test_siden(self):
        h = sn.page("skjold-s1-a1b2", "Skjold-oppsett-A1B2")
        self.assertIn("http://skjold-s1-a1b2.local:8765", h)
        self.assertNotIn("__", h)
        self.assertIn("<title>Sett opp Skjold</title>", h)

    def tmp(self):
        import tempfile
        d = tempfile.mkdtemp(); self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True)); return d


if __name__ == "__main__":
    unittest.main()
