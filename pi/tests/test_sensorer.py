"""Skjold Sensor i Skjold: mDNS-oppføringer og hendelsesstrømmen fra ESPHome."""
import os
import sys
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_sensorer as S  # noqa: E402

AVAHI = (
    '+;eth0;IPv4;skjold-sensor;_esphomelib._tcp;local\n'
    '=;eth0;IPv4;skjold-sensor;_esphomelib._tcp;local;skjold-sensor.local;10.0.0.42;6053;'
    '"project_name=skjold.sensor" "friendly_name=Skjold Sensor" "mac=a4cf12aabbcc" "platform=ESP8266"\n'
    '=;eth0;IPv4;skjold-kassett;_esphomelib._tcp;local;skjold-kassett.local;10.0.0.43;6053;"project_name=" "mac=1"\n'
    '=;eth0;IPv6;skjold-sensor;_esphomelib._tcp;local;skjold-sensor.local;fe80::1;6053;"project_name=skjold.sensor" "mac=a4cf12aabbcc"\n'
)


class TestSensorer(unittest.TestCase):
    def test_avahi(self):
        f = S.parse_avahi(AVAHI)
        self.assertEqual(f, {"a4cf12aabbcc": {"navn": "Skjold Sensor", "ip": "10.0.0.42", "port": 80}})

    def test_sse(self):
        s = S.Sensorer()
        s.enheter["m"] = {"verdier": {}, "tilkoblet": True, "sist": 0}
        linjer = ['event: state\r', 'data: {"id":"sensor/Temperatur","name":"Temperatur","value":21.4,"state":"21.4 °C"}\r', '\r',
                  'event: ping\r', 'data: {}\r', '\r',
                  'event: state', 'data: {"id":"binary_sensor/Bevegelse","value":true,"state":"ON"}', '',
                  'event: state', 'data: {"id":"binary_sensor-mørkt","state":"OFF"}', '',
                  'event: state', 'data: {"id":"text_sensor/Komfort","value":"Behagelig","state":"Behagelig"}', '']
        S.les_sse(iter(linjer), lambda n, v: s._sett("m", n, v))
        self.assertEqual(s.status()["enheter"]["m"]["verdier"],
                         {"Temperatur": 21.4, "Bevegelse": True, "mørkt": False, "Komfort": "Behagelig"})


if __name__ == "__main__":
    unittest.main()


def test_sti_for_innstillinger():
    from skjold_sensorer import sti_for
    assert sti_for("Oppdateringsintervall", 60) == "/number/Oppdateringsintervall/set?value=60"
    assert sti_for("Tilstedeværelse av etter", "15") == "/number/Tilstedev%C3%A6relse%20av%20etter/set?value=15"
    assert sti_for("Status-LED", False) == "/switch/Status-LED/turn_off"
    assert sti_for("Status-LED", True) == "/switch/Status-LED/turn_on"
    try:
        sti_for("Temperatur", 1)
        assert False
    except ValueError:
        pass
