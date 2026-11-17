"""Kassettspilleren: hvilken Skjold den har kontakt med (vises på Kassetter-siden) og den delte ESPHome-nøkkelen."""
import base64
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


def test_spiller_spores_fra_spoler_og_scan():
    d.nfc_spillere.clear()
    d._nfc_spiller_sett("10.69.2.216")
    d._nfc_spiller_sett("10.69.2.216", "skjold-kassett", "04-A9-F2")
    d._nfc_spiller_sett("127.0.0.1")   # Skjold selv (Home Assistant/Homey «spill kassett») teller ikke
    sp = d._nfc_spillere_her()
    assert len(sp) == 1 and sp[0]["aktiv"] and sp[0]["navn"] == "skjold-kassett" and sp[0]["sist_uid"] == "04-A9-F2"
    d.nfc_spillere["10.69.2.216"]["sist"] = time.time() - 60
    assert not d._nfc_spillere_her()[0]["aktiv"]
    d.nfc_spillere.clear()


def test_esphome_nokkel_valideres_og_deles():
    old = dict(d.state.get("settings") or {})
    try:
        god = base64.b64encode(os.urandom(32)).decode()
        d.update_settings({"esphomeKey": god})
        assert d.settings()["esphomeKey"] == god
        d.update_settings({"esphomeKey": "ikke-en-nokkel"})
        d.update_settings({"esphomeKey": base64.b64encode(b"for kort").decode()})
        assert d.settings()["esphomeKey"] == god
        assert "esphomeKey" in d.SHARED_SETTINGS
    finally:
        d.state["settings"] = old


def test_airplay_volum_speiles_uten_sloyfe():
    """Skjold-volum → AirPlay-dB → tilbake via pvol-formelen i oled_display gir samme volum (telefonen hopper ikke)."""
    for v in range(1, 101):
        av = d.airplay_db(v)
        assert -30 <= av <= 0
        assert round(100 * (av + 30) / 30) == v
    assert d.airplay_db(0) == -144.0
