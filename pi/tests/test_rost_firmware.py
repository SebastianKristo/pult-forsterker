"""Sjekker Skjold-oppsettet som bakes inn i fastvaren for Skjold Røst (firmware/rost/lag_firmware.py)."""
import csv
import importlib.util
import io
import json
import os
import re

import skjold_rost

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
spec = importlib.util.spec_from_file_location("lag_firmware", os.path.join(ROOT, "firmware", "rost", "lag_firmware.py"))
fw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw)

# ESP32-S3 N16R8: oppstartspinner, USB, flash og oktal PSRAM skal ikke brukes
FORBUDT = {0, 3, 45, 46, 19, 20, *range(26, 33), 33, 34, 35, 36, 37}
ACTIONS = {"ACTRLS_POWER", "ACTRLS_TOGGLE", "ACTRLS_VOLUP", "ACTRLS_VOLDOWN", "BCTRLS_PS1", "BCTRLS_PS2", "BCTRLS_PS3", "BCTRLS_PS4", "BCTRLS_PS5"}


def koblingstabell():
    """GPIO-ene i kabinett/rost/LES_MEG.md (koblingstabellen er fasiten for maskinvaren)."""
    t = open(os.path.join(ROOT, "kabinett", "rost", "LES_MEG.md"), encoding="utf-8").read()
    rader = {}
    for line in t.splitlines():
        if line.startswith("|") and "GPIO" in line:
            celler = [c.strip() for c in line.strip("|").split("|")]
            rader[celler[0]] = [int(x) for x in re.findall(r"GPIO(\d+)", celler[-1])]
    return rader


def test_nokler_og_lengder():
    cfg = fw.config()
    for k, v in cfg.items():
        assert len(k) <= 15, k                 # NVS-nøkler er maks 15 tegn
        assert len(v.encode()) < 4000, k       # NVS-strenger er maks 4000 byte
    for k in ("dac_config", "set_GPIO", "i2c_config", "display_config", "rotary_config", "actrls_config", "autoexec1"):
        assert cfg[k]


def test_knapper_er_gyldig_json_med_kjente_handlinger():
    cfg = fw.config()
    knapper = json.loads(cfg[cfg["actrls_config"]])
    assert len(knapper) == 5
    for b in knapper:
        assert b["type"] == "BUTTON_LOW" and b["pull"] is True
        assert b["normal"]["pressed"] in ACTIONS
    assert [b["normal"]["pressed"] for b in knapper] == ["ACTRLS_POWER", "BCTRLS_PS1", "BCTRLS_PS2", "BCTRLS_PS3", "BCTRLS_PS4"]
    # dusj-modus: langt trykk på ⏻ sender preset 5 (squeezelite-esp32: «long_press» ms + «longpress»-handling)
    assert knapper[0]["longpress"]["pressed"] == "BCTRLS_PS5" and 500 <= knapper[0]["long_press"] <= 3000
    for b in knapper[1:]:
        assert "longpress" not in b


def test_ingen_heksadesimal_i_verdier():
    # squeezelite-esp32 leser tall med atoi(): «0x3C» blir 0
    for k, v in fw.config().items():
        if k not in ("knapper", "cspot_config"):
            assert not re.search(r"=0x", v), (k, v)


def test_gpio_stemmer_med_koblingstabellen_og_er_lovlige():
    p = fw.PINS
    brukt = list(p.values())
    assert len(brukt) == len(set(brukt)), "samme GPIO brukt to ganger"
    assert not (set(brukt) & FORBUDT), set(brukt) & FORBUDT
    tab = koblingstabell()
    finn = lambda nokkel: next(v for k, v in tab.items() if nokkel in k)
    assert finn("BCK") == [p["i2s_bck"], p["i2s_ws"], p["i2s_do"]]
    assert finn("SDZ") == [p["amp"]]
    assert finn("Skjerm SDA") == [p["oled_sda"], p["oled_scl"]]
    assert finn("Knapp av/på") == [p["btn_power"], p["btn_1"], p["btn_2"], p["btn_3"], p["btn_4"]]
    assert finn("EC11") == [p["enc_a"], p["enc_b"], p["enc_sw"]]
    cfg = fw.config()
    assert cfg["dac_config"] == "model=I2S,bck=4,ws=5,do=6"
    assert cfg["rotary_config"].startswith("A=15,B=16,SW=17")
    assert cfg["set_GPIO"] == "7=amp"


def test_nvs_csv_kan_leses_tilbake():
    rows = list(csv.DictReader(io.StringIO(fw.nvs_csv(fw.config()))))
    assert rows[0]["key"] == "config" and rows[0]["type"] == "namespace"
    back = {r["key"]: r["value"] for r in rows[1:]}
    assert back == fw.config()           # komma og anførselstegn i JSON overlever CSV


def test_spillernavnet_gjenkjennes_av_skjold():
    navn = fw.config()["autoexec1"].split("-n ", 1)[1]
    assert skjold_rost.is_mini({"name": navn, "model": "squeezelite", "modelname": "Squeezelite"})
