"""Skjold IR: pakken Skjold sender til dokka og IR-senderne er den samme som Skjold Stav sender."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


class TestIr(unittest.TestCase):
    def test_pakke(self):
        self.assertEqual(d.ir_pakke("Skap", "nec", "00ff02fd"), b"SKIR1 skap 1 00FF02FD 0")
        self.assertEqual(d.ir_pakke("", 3, 0xA90, 12), b"SKIR1 alle 3 00000A90 12")
        with self.assertRaises(ValueError):
            d.ir_pakke("dokk", 9, 1)


if __name__ == "__main__":
    unittest.main()
