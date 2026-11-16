"""Home Assistant-hjelperne (pi/skjold_ha.py): adresser, entitetsliste og innloggings-URL."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skjold_ha as ha  # noqa: E402


class TestHa(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(ha._norm("homeassistant.local"), "http://homeassistant.local:8123")
        self.assertEqual(ha._norm("https://ha.example.no/"), "https://ha.example.no")
        self.assertEqual(ha._norm("http://10.0.0.5:8123/"), "http://10.0.0.5:8123")

    def test_entities_filter(self):
        states = [{"entity_id": "camera.inngang", "state": "idle", "attributes": {"friendly_name": "Inngang"}},
                  {"entity_id": "light.stue", "state": "on", "attributes": {"friendly_name": "Stue"}},
                  {"entity_id": "binary_sensor.ringeklokke", "state": "off", "attributes": {"friendly_name": "Ringeklokke", "device_class": "occupancy"}}]
        with mock.patch.object(ha, "_get", return_value=states):
            self.assertEqual([e["entity_id"] for e in ha.entities("ha", "t", "camera")], ["camera.inngang"])
            self.assertEqual(len(ha.entities("ha", "t")), 3)
            self.assertEqual([e["entity_id"] for e in ha.entities("ha", "t", "", "ringe")], ["binary_sensor.ringeklokke"])

    def test_login_url(self):
        u = ha.login_url("homeassistant.local", "http://10.0.0.9:8765", "http://10.0.0.9:8765/#innstillinger")
        self.assertTrue(u.startswith("http://homeassistant.local:8123/auth/authorize?"))
        self.assertIn("client_id=http%3A%2F%2F10.0.0.9%3A8765%2F", u)
        self.assertIn("redirect_uri=http%3A%2F%2F10.0.0.9%3A8765%2Fapi%2Fha%2Fcallback", u)
        with self.assertRaises(RuntimeError):
            ha.finish_login("ukjent", "kode")


if __name__ == "__main__":
    unittest.main()
