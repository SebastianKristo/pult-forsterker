"""Skjold gir kassettspilleren adressen sin (pi/skjold_esphome.py): tom eller død adresse fylles inn, en annen Skjold
som svarer får beholde den, og eldre fastvare uten feltet røres ikke."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_esphome as E  # noqa: E402


def kjør(spillere, adresser, levende, min_ip="10.69.2.244"):
    satt = {}
    ut = E.pass_paa(min_ip, finn=lambda: spillere, hent=lambda ip: adresser.get(ip), svarer=lambda h: h in levende,
                    sett=lambda ip, v: satt.__setitem__(ip, v) or True, logg=lambda m: None)
    return ut, satt


def test_ny_spiller_uten_adresse_far_denne_skjold():
    ut, satt = kjør([{"navn": "skjold-kassett", "ip": "10.69.2.216"}], {"10.69.2.216": ""}, set())
    assert satt == {"10.69.2.216": "10.69.2.244"} and ut[0]["fra"] == ""


def test_dod_adresse_byttes_men_levende_annen_skjold_beholdes():
    _ut, satt = kjør([{"navn": "a", "ip": "1.1.1.1"}, {"navn": "b", "ip": "2.2.2.2"}],
                     {"1.1.1.1": "10.69.1.189", "2.2.2.2": "10.69.2.189"}, {"10.69.2.189"})
    assert satt == {"1.1.1.1": "10.69.2.244"}


def test_eldre_fastvare_og_riktig_adresse_rores_ikke():
    _ut, satt = kjør([{"navn": "a", "ip": "1.1.1.1"}, {"navn": "b", "ip": "2.2.2.2"}],
                     {"1.1.1.1": None, "2.2.2.2": "10.69.2.244"}, set())
    assert satt == {}


def test_les_og_skriv_mot_web_server():
    kall = []

    def opener(url):
        kall.append(url)
        if url.endswith("/text/skjold_adresse"):
            raise OSError("404")
        return b'{"id":"text-skjold_adresse","value":"10.0.0.5","state":"10.0.0.5"}'
    assert E.get_host("1.2.3.4", opener=opener) == "10.0.0.5"
    assert kall[-1] == "http://1.2.3.4/text/Skjold%20adresse"
    sendt = []
    assert E.set_host("1.2.3.4", "10.69.2.244", opener=lambda req: sendt.append((req.get_method(), req.full_url)))
    assert sendt == [("POST", "http://1.2.3.4/text/skjold_adresse/set?value=10.69.2.244")]
