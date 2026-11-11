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

    def test_dimming(self):
        self.assertEqual(t.service_for("light.stue", "brightness", value=40), ("light", "turn_on", {"entity_id": "light.stue", "brightness_pct": 40}))
        self.assertEqual(t.service_for("light.stue", "brightness", value=0)[1], "turn_off")
        self.assertEqual(t.service_for("light.stue", "brightness", value=250)[2]["brightness_pct"], 100)
        with self.assertRaises(ValueError):
            t.service_for("switch.lader", "brightness", value=40)
        dim = t.tile_of({"entity_id": "light.stue", "state": "on", "attributes": {"brightness": 128, "supported_color_modes": ["brightness"]}})
        self.assertEqual(dim["pct"], 50)
        self.assertEqual(t.tile_of({"entity_id": "light.a", "state": "off", "attributes": {"supported_color_modes": ["color_temp"]}})["pct"], 0)
        self.assertNotIn("pct", t.tile_of({"entity_id": "light.b", "state": "on", "attributes": {"supported_color_modes": ["onoff"]}}))

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


class Homey(unittest.TestCase):
    """Homey som smarthus-kilde: enhetene fra Homeys lokale API blir fliser i samme form som fra Home Assistant."""
    LYS = {"id": "a1", "name": "Stue", "class": "light", "available": True, "capabilitiesObj": {"onoff": {"value": True}, "dim": {"value": 0.8}}}
    VARME = {"id": "b2", "name": "Varme stue", "class": "thermostat", "capabilitiesObj": {"target_temperature": {"value": 21.5, "min": 5, "max": 30}, "measure_temperature": {"value": 21.2}}}
    PLUGG = {"id": "c3", "name": "Kaffe", "class": "socket", "virtualClass": "light", "capabilitiesObj": {"onoff": {"value": False}}}
    LAAS = {"id": "d4", "name": "Inngang", "class": "lock", "capabilitiesObj": {"locked": {"value": True}, "onoff": {"value": True}}}
    STROM = {"id": "e5", "name": "Strøm", "class": "sensor", "capabilitiesObj": {"measure_power": {"value": 1840.4}}}

    def test_fliser(self):
        f = t.homey_tile(self.LYS)
        self.assertEqual((f["id"], f["kind"], f["on"], f["text"], f["pct"], f["tag"]), ("homey:a1", "toggle", True, "På · 80 %", 80, "LYS"))
        v = t.homey_tile(self.VARME)
        self.assertEqual((v["kind"], v["text"], v["target"]), ("climate", "Nå 21,2 °C", 21.5))
        self.assertEqual(t.homey_tile(self.PLUGG)["domain"], "light")              # «vis som lys» i Homey følges
        l = t.homey_tile(self.LAAS)
        self.assertEqual((l["kind"], l["text"]), ("info", "Låst"))
        self.assertEqual(t.homey_tile(self.STROM)["text"], "1840,4 W")
        self.assertEqual(t.homey_tile({**self.LYS, "available": False})["text"], "Utilgjengelig")

    def test_handlinger(self):
        self.assertEqual(t.homey_action(self.LYS, "toggle"), ("onoff", False))
        self.assertEqual(t.homey_action(self.LYS, "brightness", 40), ("dim", 0.4))
        self.assertEqual(t.homey_action(self.LYS, "brightness", 0), ("onoff", False))
        self.assertEqual(t.homey_action(self.VARME, "up"), ("target_temperature", 22.0))
        for dev, act in ((self.LAAS, "toggle"), (self.STROM, "toggle"), (self.PLUGG, "brightness")):
            with self.assertRaises(ValueError):
                t.homey_action(dev, act, 50)

    def test_utvalg_og_oppsett(self):
        ids = t.homey_pick([self.LYS, self.VARME, self.PLUGG, self.LAAS, self.STROM, {**self.LYS, "id": "z", "available": False}])
        self.assertEqual(ids, ["c3", "a1", "b2"])                                   # lys (etter navn), så varme; lås og sensor velges ikke selv
        c = t.clean(dict(t.DEFAULTS), {"hub": "homey", "homey_url": "homey-abc.local/", "homey_token": "hemmelig", "homey_devices": ["a1", ""]})
        self.assertEqual((c["hub"], c["homey_url"], c["homey_devices"]), ("homey", "http://homey-abc.local", ["a1"]))
        self.assertEqual(t.clean(c, {"homey_token": "••••••"})["homey_token"], "hemmelig")
        with self.assertRaises(ValueError):
            t.clean(dict(t.DEFAULTS), {"hub": "annet"})

    def test_mot_falsk_homey(self):
        kall = []
        with tempfile.TemporaryDirectory() as d:
            x = t.Touch({"changed": lambda: None, "ha": lambda: {}, "alarms": lambda: []}, os.path.join(d, "t.json"))
            x.save({"hub": "homey"})
            self.assertIn("Koble til Homey", x.smart()["error"])
            x.save({"homey_url": "http://homey", "homey_token": "nøkkel"})
            self.assertEqual(x.public()["homey_token"], "••••••")                   # nøkkelen vises aldri igjen
            enheter = {"a1": dict(self.LYS), "b2": dict(self.VARME)}
            def falsk(path, method="GET", body=None, timeout=6.0):
                kall.append((method, path, body))
                return enheter if method == "GET" else None
            x._homey = falsk
            sm = x.smart(fresh=True)
            self.assertEqual((sm["ok"], sm["hub"], [f["id"] for f in sm["tiles"]]), (True, "Homey", ["homey:a1", "homey:b2"]))
            x.press("homey:a1", "brightness", 30)
            self.assertIn(("PUT", "/api/manager/devices/device/a1/capability/dim", {"value": 0.3}), kall)
            with self.assertRaises(ValueError):
                x.press("homey:ukjent", "toggle")


class Hjemmedata(unittest.TestCase):
    """Data til standby-stilene på S1: samme form som eksempeldataene i designet (WIDE_DEF)."""

    def setUp(self):
        from datetime import timedelta, timezone
        self.tz = timezone(timedelta(hours=1))

    def test_vaer(self):
        w = t.home_weather({"state": "rainy", "attributes": {"temperature": 4.4, "friendly_name": "Oslo"}},
                           [{"datetime": "2026-11-11T22:00:00+00:00", "temperature": 4.2}, {"datetime": "2026-11-11T23:00:00+00:00", "temperature": 3}], self.tz)
        self.assertEqual(w, {"t": 4, "c": "Regn · Oslo", "hours": [["23", 4], ["00", 3]]})
        self.assertEqual(t.home_weather({"state": "sunny", "attributes": {"temperature": 20, "friendly_name": "Forecast Home"}})["c"], "Sol")
        self.assertIsNone(t.home_weather({"state": "unavailable", "attributes": {}}))
        self.assertIsNone(t.home_weather(None))

    def test_sol(self):
        s = t.home_sun({"attributes": {"next_rising": "2026-11-12T07:04:00+00:00", "next_setting": "2026-11-11T15:06:00+00:00"}}, self.tz)
        self.assertEqual(s, ["08:04", "16:06"])
        self.assertIsNone(t.home_sun({"attributes": {}}))

    def test_kalender(self):
        from datetime import date
        ev = [{"summary": "Middag hos mormor", "start": {"dateTime": "2026-11-12T11:00:00+00:00"}},
              {"summary": "Fotballtrening", "start": {"dateTime": "2026-11-12T08:30:00+00:00"}},
              {"summary": "Ferie", "start": {"date": "2026-11-14"}}, {"summary": "", "start": {"date": "2026-11-11"}}]
        k = t.home_calendar(ev, date(2026, 11, 11), self.tz)
        self.assertEqual(k, {"day": "I MORGEN", "items": ["09:30 Fotballtrening", "12:00 Middag hos mormor"]})
        self.assertEqual(t.home_calendar(ev, date(2026, 11, 12), self.tz)["day"], "I DAG")
        self.assertEqual(t.home_calendar(ev[2:3], date(2026, 11, 11), self.tz), {"day": "LØRDAG", "items": ["Ferie"]})
        self.assertIsNone(t.home_calendar([], date(2026, 11, 11)))

    def test_uten_home_assistant_gir_bare_alarm(self):
        with tempfile.TemporaryDirectory() as d:
            x = t.Touch({"changed": lambda: None, "ha": lambda: {}, "alarms": lambda: [{"time": "06:30", "on": True, "days": []}]}, os.path.join(d, "t.json"))
            self.assertEqual(x.home(), {"alarm": "06:30"})


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
