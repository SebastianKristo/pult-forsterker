"""Wi-Fi over Bluetooth (Improv): RPC-pakkene inn og svaret ut."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skjold_improv as I  # noqa: E402


def pakke(cmd, *strenger):
    body = b"".join(bytes([len(x.encode())]) + x.encode() for x in strenger)
    p = bytes([cmd, len(body)]) + body
    return list(p + bytes([sum(p) & 0xFF]))


class TestImprov(unittest.TestCase):
    def test_wifi_pakke(self):
        self.assertEqual(I.wifi_rpc(pakke(1, "Hjemme", "hemmelig123")), ("Hjemme", "hemmelig123"))
        self.assertEqual(I.wifi_rpc(pakke(1, "Åpent nett æøå", "")), ("Åpent nett æøå", ""))

    def test_feil_sjekksum_og_ukjent_kommando(self):
        p = pakke(1, "A", "b"); p[-1] ^= 1
        with self.assertRaises(ValueError):
            I.wifi_rpc(p)
        with self.assertRaises(KeyError):
            I.wifi_rpc(pakke(2))
        with self.assertRaises(ValueError):
            I.wifi_rpc([1, 5, 3])

    def test_svar(self):
        r = I.build_result(1, ["http://10.0.0.7:8765/"])
        self.assertEqual(I.parse_rpc(r), (1, ["http://10.0.0.7:8765/"]))

    def test_kobler_til_og_rydder_ved_feil(self):
        kall = []
        class R:
            def __init__(self, code): self.returncode, self.stderr, self.stdout = code, "Secrets were required", ""
        def run(cmd, **kw):
            kall.append(cmd); return R(0 if "connect" not in cmd else 4)
        ok, err = I.connect_wifi("Hjemme", "feil-passord", run=run)
        self.assertFalse(ok)
        self.assertIn(["nmcli", "connection", "delete", "id", "Hjemme"], kall)


if __name__ == "__main__":
    unittest.main()
