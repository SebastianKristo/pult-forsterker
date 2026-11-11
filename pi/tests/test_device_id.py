"""Enhets-ID-en (mDNS «id», /api/status, Home Assistant, Homey): ny installasjon med et vertsnavn som allerede er i bruk
på nettet skal få en unik ID, mens en enhet som har kjørt før beholder vertsnavnet.

Kjør:  python3 -m unittest pi.tests.test_device_id -v
"""
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import ki_amp_daemon as d  # noqa: E402


class DeviceId(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ki-id-")
        self.fil = os.path.join(self.dir, "device_id")
        self.p = [mock.patch.object(d, "DEVICE_ID_FILE", self.fil), mock.patch.object(d, "_device_id", "")]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_ny_installasjon_navn_tatt_far_suffiks(self):
        with mock.patch.object(d, "_FRESH_INSTALL", True), mock.patch.object(d, "_id_taken_on_lan", return_value=True):
            ident = d.resolve_device_id()
        self.assertTrue(ident.startswith(socket.gethostname() + "-"))
        self.assertEqual(len(ident), len(socket.gethostname()) + 5)
        self.assertEqual(open(self.fil).read().strip(), ident)
        self.assertEqual(d.device_id(), ident)

    def test_ny_installasjon_ledig_navn_beholder_vertsnavn(self):
        with mock.patch.object(d, "_FRESH_INSTALL", True), mock.patch.object(d, "_id_taken_on_lan", return_value=False):
            self.assertEqual(d.resolve_device_id(), socket.gethostname())

    def test_eksisterende_enhet_beholder_vertsnavn_selv_om_det_er_tatt(self):
        with mock.patch.object(d, "_FRESH_INSTALL", False), mock.patch.object(d, "_id_taken_on_lan", return_value=True) as sjekk:
            self.assertEqual(d.resolve_device_id(), socket.gethostname())
            sjekk.assert_not_called()

    def test_lagret_id_brukes(self):
        with open(self.fil, "w") as fh:
            fh.write("stue-ab12\n")
        with mock.patch.object(d, "_id_taken_on_lan") as sjekk:
            self.assertEqual(d.resolve_device_id(), "stue-ab12")
            sjekk.assert_not_called()

    def test_avahi_tolking(self):
        ut = ('=;eth0;IPv4;Skjold\\032Node;_kipultamp._tcp;local;pultamp.local;10.69.1.97;8765;"path=/api/status" "id=pultamp"\n'
              '=;eth0;IPv4;Skjold\\032S1;_kipultamp._tcp;local;s1.local;10.69.2.189;8765;"id=skjold-s1"\n')
        def run(cmd, **kw):
            return mock.Mock(stdout="10.69.2.189 fe80::1" if cmd[0] == "hostname" else ut)
        with mock.patch.object(d.subprocess, "run", side_effect=run):
            self.assertTrue(d._id_taken_on_lan("pultamp"))
            self.assertFalse(d._id_taken_on_lan("skjold-s1"))   # bare vår egen adresse
            self.assertFalse(d._id_taken_on_lan("kjokken"))


if __name__ == "__main__":
    unittest.main()
