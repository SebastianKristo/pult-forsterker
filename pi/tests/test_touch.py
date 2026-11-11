"""Skjold Touch: smarthusfliser, vekkeklokke som ringer, nattmodus, stemme og skjermkommandoer (pi/skjold_touch.py).

Kjør:  python3 -m unittest pi.tests.test_touch -v
"""
import os
import sys
import tempfile
import time
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_touch as t  # noqa: E402


def tm(wday, h, m):
    return time.struct_time((2026, 11, 9 + wday, h, m, 0, wday, 313 + wday, 0))


class Fliser(unittest.TestCase):
    def test_lys(self):
        f = t.tile_of({"entity_id": "light.stue", "state": "on", "attributes": {"friendly_name": "Stue", "brightness": 204}})
        self.assertEqual((f["name"], f["on"], f["text"], f["tag"], f["kind"]), ("Stue", True, "På · 80 %", "LYS", "toggle"))
        self.assertEqual(t.tile_of({"entity_id": "light.stue", "state": "off", "attributes": {}})["text"], "Av")

    def test_varme(self):
        f = t.tile_of({"entity_id": "climate.stue", "state": "heat", "attributes": {"current_temperature": 21.2, "temperature": 21.5}})
        self.assertEqual((f["kind"], f["text"], f["target"]), ("climate", "Nå 21,2 °C", 21.5))

    def test_port_og_sensor(self):
        self.assertEqual(t.tile_of({"entity_id": "cover.garasje", "state": "closed", "attributes": {}})["tag"], "TRYKK FOR Å ÅPNE")
        f = t.tile_of({"entity_id": "sensor.strom", "state": "1.84", "attributes": {"unit_of_measurement": "kW", "device_class": "power"}})
        self.assertEqual((f["text"], f["tag"], f["kind"]), ("1,84 kW", "POWER", "info"))

    def test_utilgjengelig_og_laas(self):
        self.assertEqual(t.tile_of({"entity_id": "light.x", "state": "unavailable"})["text"], "Utilgjengelig")
        f = t.tile_of({"entity_id": "lock.inngang", "state": "locked", "attributes": {}})
        self.assertEqual((f["text"], f["kind"]), ("Låst", "info"))          # låsen åpnes ikke med et trykk på flisa

    def test_utvalg(self):
        st = [{"entity_id": f"light.l{i}", "state": "off"} for i in range(6)] + [{"entity_id": "climate.a", "state": "heat"},
              {"entity_id": "scene.kveld", "state": "x"}, {"entity_id": "light.dod", "state": "unavailable"}]
        fl, sc = t.auto_pick(st)
        self.assertEqual(len([e for e in fl if e.startswith("light.")]), 4)
        self.assertIn("climate.a", fl)
        self.assertNotIn("light.dod", fl)
        self.assertEqual(sc, ["scene.kveld"])


class Tjenester(unittest.TestCase):
    def test_trykk(self):
        self.assertEqual(t.service_for("light.stue", "toggle"), ("homeassistant", "toggle", {"entity_id": "light.stue"}))
        self.assertEqual(t.service_for("cover.port", "toggle")[:2], ("cover", "toggle"))
        self.assertEqual(t.service_for("scene.kveld", "scene")[:2], ("scene", "turn_on"))
        self.assertEqual(t.service_for("climate.stue", "up", 21.5)[2]["temperature"], 22.0)
        self.assertEqual(t.service_for("climate.stue", "up", 30, 5, 30)[2]["temperature"], 30)

    def test_laas_og_alarm_styres_ikke(self):
        for e in ("lock.inngang", "alarm_control_panel.hus", "sensor.x"):
            with self.assertRaises(ValueError):
                t.service_for(e, "toggle")

    def test_bare_valgte_fliser(self):
        with tempfile.TemporaryDirectory() as d:
            x = t.Touch({"changed": lambda: None, "ha": lambda: {"ha_url": "http://ha", "ha_token": "t"}, "alarms": lambda: []}, os.path.join(d, "t.json"))
            x.save({"tiles": ["light.stue"]})
            with self.assertRaises(ValueError):
                x.press("light.naboen", "toggle")

    def test_oppsett(self):
        self.assertEqual(t.clean(dict(t.DEFAULTS), {"tiles": ["light.a", "tull", 5], "ukjent": 1})["tiles"], ["light.a"])
        with self.assertRaises(ValueError):
            t.clean(dict(t.DEFAULTS), {"lock_entity": "inngang"})


class Natt(unittest.TestCase):
    def test_modus(self):
        self.assertFalse(t.in_night(0, 22, 7, 23, True))
        self.assertTrue(t.in_night(3, 22, 7, 12, False))
        self.assertTrue(t.in_night(1, 22, 7, 23, False))
        self.assertTrue(t.in_night(1, 22, 7, 6, False))
        self.assertFalse(t.in_night(1, 22, 7, 7, False))
        self.assertTrue(t.in_night(1, 1, 5, 3, False))
        self.assertFalse(t.in_night(1, 1, 5, 23, False))
        self.assertTrue(t.in_night(2, 22, 7, 12, True))
        self.assertFalse(t.in_night(2, 22, 7, 23, False))


class Vekking(unittest.TestCase):
    AL = [{"time": "06:45", "days": [0, 1, 2, 3, 4], "name": "Jobb", "on": True}, {"time": "09:00", "days": [5, 6], "name": "Helg", "on": True},
          {"time": "06:00", "days": [1, 3], "name": "Trening", "on": False}]

    def test_neste(self):
        self.assertEqual(t.next_alarm(self.AL, tm(0, 5, 0))["name"], "Jobb")
        n = t.next_alarm(self.AL, tm(4, 7, 0))            # fredag etter jobb-alarmen: lørdag 09:00
        self.assertEqual((n["name"], n["in_min"]), ("Helg", 26 * 60))
        self.assertEqual(t.next_alarm(self.AL, tm(6, 10, 0))["name"], "Jobb")
        self.assertIsNone(t.next_alarm([{"time": "07:00", "on": False}], tm(0, 5, 0)))
        self.assertEqual(t.next_alarm([{"time": "07:00", "days": []}], tm(0, 8, 0))["in_min"], 23 * 60)   # ingen dager = hver dag

    def test_ring_slumre_og_av(self):
        now = [1000.0]
        log = []
        r = t.AlarmRing({"changed": lambda: log.append("c"), "pause": lambda: log.append("pause"), "fire": lambda a: log.append(("fire", a["fade"]))},
                        clock=lambda: now[0])
        r.start({"name": "Jobb", "time": "06:45", "fade": 3})
        self.assertTrue(r.status()["ringing"])
        r.snooze()
        self.assertEqual((r.on, r.snoozed), (False, True))
        self.assertIn("pause", log)
        now[0] += 8 * 60; r.tick()
        self.assertFalse(r.on)
        now[0] += 61; r.tick()
        self.assertTrue(r.on and r.snoozed)
        self.assertIn(("fire", 0), log)                   # etter slumring starter lyden rett på, uten myk oppstart
        r.stop()
        self.assertEqual((r.on, r.snoozed, r.snooze_until, r.status()["name"]), (False, False, 0.0, ""))

    def test_gir_seg_selv(self):
        now = [0.0]
        r = t.AlarmRing({"changed": lambda: None, "pause": lambda: None, "fire": lambda a: None}, clock=lambda: now[0])
        r.start({"name": "x"})
        now[0] = t.RING_MAX_S + 1; r.tick()
        self.assertFalse(r.on)

    def test_test_stopper_ikke_musikken(self):
        log = []
        r = t.AlarmRing({"changed": lambda: None, "pause": lambda: log.append("pause"), "fire": lambda a: log.append("fire")})
        r.start({"name": "Test", "test": True}); r.stop()
        self.assertEqual(log, [])

    def test_morgen(self):
        w = {"state": "cloudy", "attributes": {"temperature": 6.2}}
        l = {"state": "on", "attributes": {"friendly_name": "Lyset på soverommet", "brightness": 102}}
        self.assertEqual(t.morning_text(w, l), "6 °C og overskyet · lyset på soverommet er på 40 %")
        self.assertEqual(t.morning_text(None, {"state": "off"}), "")


class Skjerm(unittest.TestCase):
    def ny(self, d):
        return t.Touch({"changed": lambda: None, "ha": lambda: {}, "alarms": lambda: []}, os.path.join(d, "t.json"))

    def test_kommandoer_og_stemme(self):
        with tempfile.TemporaryDirectory() as d:
            x = self.ny(d)
            self.assertEqual(x.command("page", "alarm")["seq"], 1)
            self.assertEqual(x.command("standby")["seq"], 2)
            for bad in (("page", "tull"), ("slett", "")):
                with self.assertRaises(ValueError):
                    x.command(*bad)
            x.set_voice("listen"); x.set_voice("think", "Skru på lyset")
            v = x.set_voice("reply", reply="Lyset er på.")
            self.assertEqual((v["text"], v["reply"]), ("Skru på lyset", "Lyset er på."))
            x.voice["t"] -= 60
            self.assertEqual(x.status()["touch"]["voice"]["state"], "idle")     # satellitten ble stille: overlegget lukkes
            self.assertFalse(x.smart()["ok"])                                   # uten HA: forklaring, ikke krasj
            self.assertIn("Home Assistant", x.smart()["error"])

    def test_bakgrunnslys(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, "10-0045"))
            open(os.path.join(d, "10-0045", "max_brightness"), "w").write("255\n")
            open(os.path.join(d, "10-0045", "brightness"), "w").write("255")
            self.assertTrue(t.set_backlight(20, d))
            self.assertEqual(open(os.path.join(d, "10-0045", "brightness")).read(), "51")
            self.assertFalse(t.set_backlight(20, os.path.join(d, "finnes-ikke")))

    def test_mqtt(self):
        ds = t.mqtt_discovery("skjold/x", "x", {"identifiers": ["x"]})
        self.assertEqual(len(ds), 5)
        self.assertTrue(all(c["unique_id"].startswith("x_") and c["device"] for _, c in ds))


if __name__ == "__main__":
    unittest.main()
