"""Skjold Synk: utgangsforsinkelsen måles fra ALSA og CamillaDSP, og lederen setter Lyrions playDelay."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_synk as S  # noqa: E402


def pcm(root, card, cid, dev, pid, delay, rate=48000, running=True):
    d = os.path.join(root, f"card{card}", f"pcm{dev}p", "sub0")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(root, f"card{card}", "id"), "w") as f:
        f.write(cid + "\n")
    with open(os.path.join(d, "status"), "w") as f:
        f.write(f"state: {'RUNNING' if running else 'SETUP'}\nowner_pid   : {pid}\ntrigger_time: 1.0\ndelay       : {delay}\navail       : 100\n")
    with open(os.path.join(d, "hw_params"), "w") as f:
        f.write(f"access: MMAP_INTERLEAVED\nformat: S16_LE\nchannels: 2\nrate: {rate} ({rate}/1)\n")


class TestMaaling(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        pcm(self.root, 0, "Loopback", 0, pid=111, delay=4800)          # squeezelite → loopback: 100 ms
        pcm(self.root, 1, "Headphones", 0, pid=222, delay=22050, rate=44100)   # camilladsp → 3,5 mm: 500 ms
        pcm(self.root, 2, "Annet", 0, pid=999, delay=48000, running=False)    # går ikke: teller ikke

    def test_les_status(self):
        st = sorted(S.pcm_status(self.root), key=lambda x: x["card"])
        self.assertEqual([(x["card"], x["pid"], x["delay"], x["rate"]) for x in st],
                         [("Headphones", 222, 22050, 44100), ("Loopback", 111, 4800, 48000)])

    def test_regn_summerer_kjeden(self):
        r = S.regn(S.pcm_status(self.root), {111}, {222}, dsp_buffer=2048, chunk=1024)
        self.assertTrue(r["running"])
        self.assertEqual(r["deler"], {"squeezelite": 100.0, "camilladsp": 64.0, "lydkort": 500.0, "trim": 0.0})
        self.assertEqual(r["ms"], 664.0)
        self.assertEqual(S.regn(S.pcm_status(self.root), {111}, {222}, 2048, trim_ms=-40)["ms"], 624.0)

    def test_spiller_ikke(self):
        r = S.regn([], {111}, {222}, None)
        self.assertFalse(r["running"])

    def test_maaler_snitt_og_siste_verdi(self):
        m = S.Maaler("ws://ingen", root=self.root)
        orig = (S.pids, S.camilla_buffer)
        try:
            S.pids = lambda n: {111} if n == "squeezelite" else {222}
            S.camilla_buffer = lambda url, timeout=1.5: 1024
            a = m.maal()
            self.assertTrue(a["running"]); self.assertAlmostEqual(a["ms"], 100 + 1000 * 2048 / 48000 + 500, places=0)
            S.pids = lambda n: set()   # stoppet: siste kjente verdi, med ny trim
            b = m.maal(trim_ms=20)
            self.assertFalse(b["running"]); self.assertAlmostEqual(b["ms"], a["ms"] + 20, places=1)
        finally:
            S.pids, S.camilla_buffer = orig

    def test_endring(self):
        self.assertTrue(S.trenger_endring(None, 300))
        self.assertFalse(S.trenger_endring(300, 310))
        self.assertTrue(S.trenger_endring(300, 320))


if __name__ == "__main__":
    unittest.main()
