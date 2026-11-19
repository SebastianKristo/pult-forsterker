"""Skjold S1 rev F: pinne-editoren i web-UI-et – validering (samme regler som test_s1f) og skriving av s1f_pins.yaml."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_s1f as s1  # noqa: E402

STD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "s1f_pins.yaml")


def std_tekst():
    with open(STD) as fh:
        return fh.read()


def std_pinner():
    return s1.pin_bruk(s1.parse_yaml(std_tekst()))


@pytest.fixture(params=["pyyaml", "egen"])
def parser(request, monkeypatch):
    """Kjør testene både med PyYAML og med den enkle leseren (Pi-en har ikke nødvendigvis PyYAML)."""
    if request.param == "egen":
        monkeypatch.setitem(sys.modules, "yaml", None)   # import yaml → ImportError
    else:
        pytest.importorskip("yaml")
    return request.param


def test_header_og_fysisk_stemmer_med_testens_tabell():
    phys = {2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 5: 29, 6: 31, 13: 33, 19: 35, 26: 37, 14: 8, 15: 10,
            18: 12, 23: 16, 24: 18, 25: 22, 8: 24, 7: 26, 12: 32, 16: 36, 20: 38, 21: 40}
    for g, p in phys.items():
        assert s1.FYSISK[g] == p
    assert s1.FYSISK[0] == 27 and s1.FYSISK[1] == 28 and len(s1.HEADER) == 40
    assert sorted(s1.FYSISK) == list(range(28))
    typer = [v for v in s1.HEADER.values() if isinstance(v, str)]
    assert typer.count("GND") == 8 and typer.count("5V") == 2 and typer.count("3V3") == 2


def test_standardpinnene_er_gyldige(parser):
    res = s1.valider_pinner(std_pinner())
    assert res["ok"], res["feil"]
    adv = " ".join(res["advarsler"])
    assert "GPIO2" in adv and "I²C" in adv and "GPIO14" in adv and "UART" in adv and "GPIO9" in adv and "SPI" in adv


@pytest.mark.parametrize("g", [0, 1, 18, 19, 21])
def test_reserverte_pinner_avvises(g):
    res = s1.valider_pinner({**std_pinner(), "buttons.bt": g})
    assert not res["ok"] and any("reservert" in f for f in res["feil"])


@pytest.mark.parametrize("g", [6, 12, 13, 16, 20, 26])
def test_pinne_31_til_40_er_for_lydkortet(g):
    res = s1.valider_pinner({**std_pinner(), "leds.bt": g})
    assert not res["ok"] and any("31–40" in f for f in res["feil"])


def test_dobbelbruk_avvises():
    res = s1.valider_pinner({**std_pinner(), "relay": 5})       # 5 = BT-knappen
    assert not res["ok"] and any("GPIO5 er brukt to ganger" in f for f in res["feil"])


def test_ugyldige_verdier():
    assert not s1.valider_pinner({"buttons.bt": 28})["ok"]
    assert not s1.valider_pinner({"buttons.bt": "tull"})["ok"]
    assert not s1.valider_pinner({"buttons.bt": True})["ok"]
    assert not s1.valider_pinner({"knapp.ukjent": 4})["ok"]
    res = s1.valider_pinner({"buttons.bt": "GPIO4", "leds.bt": "", "relay": "27"})
    assert res["ok"] and res["pinner"] == {"buttons.bt": 4, "leds.bt": None, "relay": 27}


def test_viktig_funksjon_uten_pinne_gir_advarsel():
    res = s1.valider_pinner({**std_pinner(), "relay": None})
    assert res["ok"] and any("Relé" in a and "ingen pinne" in a for a in res["advarsler"])


def test_skriv_beholder_resten_av_fila(parser):
    tekst = std_tekst()
    ny = s1.skriv_pinner(tekst, {**std_pinner(), "buttons.bt": 4, "buttons.usb": None, "dac_xsmt": 5})
    cfg = s1.parse_yaml(ny)
    assert cfg["buttons"]["bt"] == 4 and cfg["buttons"]["usb"] is None and cfg["dac_xsmt"] == 5
    assert cfg["leds"]["power"] == 3 and cfg["usb_switch"]["sense_pc1"] == "low" and cfg["timing"]["click_window"] == 0.38
    assert cfg["audio"]["aux1"] == "plughw:UCA_AUX1" and cfg["led_hz"] == 400
    gamle, nye = tekst.splitlines(), ny.splitlines()
    assert nye[0] == s1.MERKE
    # uendrede linjer (med kommentarene sine) står som før; bare de tre endrede linjene + merket er nye
    assert len(set(nye) - set(gamle)) == 4
    assert "  bt: 4          # Knapp BT/AirPlay (pinne 7)" in nye
    assert any(x.startswith("dac_xsmt: 5") and "pinne 29" in x for x in nye)
    assert "  aux: 7         # AUX (pinne 26)" in nye


def test_skriv_legger_til_det_som_mangler(parser):
    gammel = "# gammel fil\nbuttons:\n  bt: 5\n\nleds:\n  bt: 22\nrelay: 27\n"
    ny = s1.skriv_pinner(gammel, std_pinner())
    assert s1.pin_bruk(s1.parse_yaml(ny)) == std_pinner()
    assert "usb_switch:" in ny and "dac_xsmt: null" in ny


def test_skriv_er_idempotent():
    tekst = s1.skriv_pinner(std_tekst(), {**std_pinner(), "buttons.bt": 4})
    assert s1.skriv_pinner(tekst, {**std_pinner(), "buttons.bt": 4}) == tekst


def test_lagre_og_tilbakestill(tmp_path, parser):
    ut = str(tmp_path / "skjold" / "s1f_pins.yaml")
    # bytt BT-knappen og av/på-knappen (5 ↔ 17)
    res = s1.lagre_pinner({"buttons.bt": 17, "buttons.power": 5}, ut=ut, kilde=STD)
    assert res["ok"] and res["fil"] == ut and os.path.exists(ut)
    cfg = s1.load_pins(ut)
    assert cfg["buttons"]["bt"] == 17 and cfg["buttons"]["power"] == 5 and cfg["encoder"]["a"] == 9
    assert cfg["timing"]["hold_reset"] == 10.0
    # neste lagring tar utgangspunkt i fila i /etc (egne endringer der beholdes)
    with open(ut, "a") as fh:
        fh.write("# min egen kommentar\n")
    s1.lagre_pinner({"leds.bt": 4}, ut=ut)
    tekst = open(ut).read()
    assert "# min egen kommentar" in tekst and s1.load_pins(ut)["leds"]["bt"] == 4 and tekst.count(s1.MERKE) == 1
    assert not os.path.exists(ut + ".tmp")
    assert s1.tilbakestill_pinner(ut) is True and not os.path.exists(ut)
    assert s1.tilbakestill_pinner(ut) is False


def test_lagre_ugyldig_skriver_ingenting(tmp_path):
    ut = str(tmp_path / "s1f_pins.yaml")
    with pytest.raises(ValueError) as e:
        s1.lagre_pinner({"buttons.bt": 18}, ut=ut, kilde=STD)
    assert not os.path.exists(ut)
    assert e.value.args[1]["ok"] is False and e.value.args[1]["feil"]
    with pytest.raises(ValueError):
        s1.lagre_pinner({"buttons.bt": 7}, ut=ut, kilde=STD)        # 7 = AUX-knappen
    assert not os.path.exists(ut)


def test_regler_til_web_ui():
    r = s1.pinne_regler()
    assert len(r["header"]) == 40 and r["header"][0] == {"fys": 1, "type": "3V3", "gpio": None}
    assert r["header"][26] == {"fys": 27, "type": "id", "gpio": 0}
    assert r["header"][11] == {"fys": 12, "type": "gpio", "gpio": 18}
    assert set(r["reservert"]) == {"0", "1", "18", "19", "21"} and r["lydkort_fys"] == [31, 40]
    assert [f["id"] for f in r["funksjoner"]] == s1.FUNK_IDS
    assert set(s1.FUNK_IDS) >= {"buttons.bt", "leds.power", "encoder.sw", "relay", "headphone_detect", "usb_switch.pulse", "dac_xsmt"}


# --- API-et i daemonen: GET/POST /api/s1f/pins og /api/s1f/pins/reset ---
class Req:
    def __init__(self, method="GET", body=None, origin=None):
        self.method, self._body, self.host, self.path = method, body, "skjold.local:8765", "/api/s1f/pins"
        self.headers = {"Origin": origin} if origin else {}

    async def json(self):
        return self._body


@pytest.fixture
def daemon(tmp_path, monkeypatch):
    import ki_amp_daemon as d
    etc = str(tmp_path / "etc" / "s1f_pins.yaml")
    monkeypatch.setattr(s1, "ETC_PINS", etc)
    monkeypatch.setattr(s1, "PIN_FILES", [etc, STD])
    monkeypatch.setattr(d, "S1F", True)
    omstart = []
    monkeypatch.setattr(d, "_s1f_restart_snart", lambda *a: omstart.append(True))
    return d, etc, omstart


def kjor(handler, req):
    import asyncio
    import json as _json
    resp = asyncio.run(handler(req))
    return resp.status, _json.loads(resp.text)


def test_api_get_post_reset(daemon):
    d, etc, omstart = daemon
    st, b = kjor(d.h_s1f_pins, Req())
    assert st == 200 and b["overstyrt"] is False and b["pinner"] == b["standard"] == std_pinner()
    assert b["egen_fil"] == etc and len(b["regler"]["header"]) == 40
    st, b = kjor(d.h_s1f_pins, Req("POST", {"pinner": {"buttons.bt": 4}, "dry_run": True}))
    assert st == 200 and b["ok"] and not os.path.exists(etc) and not omstart
    st, b = kjor(d.h_s1f_pins, Req("POST", {"pinner": {"buttons.bt": 4, "buttons.power": 5}}))
    assert st == 200 and b["ok"] and b["restart"] is True and omstart == [True]
    assert s1.load_pins(etc)["buttons"]["bt"] == 4
    st, b = kjor(d.h_s1f_pins, Req())
    assert b["overstyrt"] is True and b["fil"] == etc and b["pinner"]["buttons.power"] == 5
    st, b = kjor(d.h_s1f_pins_reset, Req("POST", {}))
    assert st == 200 and b["slettet"] is True and not os.path.exists(etc) and len(omstart) == 2


def test_api_avviser_ugyldig_og_fremmed(daemon):
    d, etc, omstart = daemon
    st, b = kjor(d.h_s1f_pins, Req("POST", {"pinner": {"buttons.bt": 21}}))
    assert st == 400 and b["feil"] and not os.path.exists(etc) and not omstart
    st, b = kjor(d.h_s1f_pins, Req("POST", {"pinner": [1, 2]}))
    assert st == 400
    st, _ = kjor(d.h_s1f_pins, Req("POST", {"pinner": {"buttons.bt": 4}}, origin="https://ond.example.com"))
    assert st == 403 and not os.path.exists(etc)
    st, _ = kjor(d.h_s1f_pins, Req("GET", origin="http://192.168.1.20"))
    assert st == 200


def test_api_bare_paa_s1f(daemon, monkeypatch):
    d = daemon[0]
    monkeypatch.setattr(d, "S1F", False)
    st, b = kjor(d.h_s1f_pins, Req())
    assert st == 404 and "S1 rev F" in b["error"]
    st, _ = kjor(d.h_s1f_pins_reset, Req("POST", {}))
    assert st == 404
