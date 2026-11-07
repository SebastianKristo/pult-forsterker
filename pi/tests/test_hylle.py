import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest  # noqa: E402
from skjold_hylle import Hylle  # noqa: E402


def lag(tmp_path, kjente=("AA11", "BB22")):
    log = []
    aktiv = {"uid": ""}

    def spill(uid, dev):
        log.append(("spill", uid, dev)); aktiv["uid"] = uid
        return {"ok": True}

    def stopp(uid):
        log.append(("stopp", uid)); aktiv["uid"] = ""
    h = Hylle({"spill": spill, "stopp": stopp, "kjent": lambda u: u in kjente, "aktiv": lambda: aktiv["uid"]},
              str(tmp_path / "hylle.json"))
    return h, log, aktiv


def test_ta_ut_spiller_og_sett_tilbake_stopper(tmp_path):
    h, log, _ = lag(tmp_path)
    h.event({"device": "hylle-1", "type": "hei", "antall": 3})
    h.event({"device": "hylle-1", "plass": 1, "uid": "aa:11", "type": "inn"})
    h.event({"device": "hylle-1", "plass": 2, "uid": "BB22", "type": "inn"})
    assert h.lys("hylle-1") == "iit"
    r = h.event({"device": "hylle-1", "plass": 1, "type": "ut"})      # tatt ut → spill (uid huskes fra plassen)
    assert r["spiller"] and log[-1] == ("spill", "AA11", "hylle-1")
    assert h.lys("hylle-1") == "sit"
    r = h.event({"device": "hylle-1", "plass": 3, "uid": "AA11", "type": "inn"})   # satt tilbake på en annen plass
    assert r["stoppet"] and log[-1] == ("stopp", "AA11")
    assert h.lys("hylle-1") == "tii"


def test_ukjent_brikke_spilles_ikke(tmp_path):
    h, log, _ = lag(tmp_path)
    h.event({"device": "h", "plass": 1, "uid": "CC33", "type": "inn", "antall": 2})
    assert h.lys("h") == "ut"
    h.event({"device": "h", "plass": 1, "type": "ut"})
    assert not log


def test_annen_avspilling_slipper_hylla(tmp_path):
    h, _, aktiv = lag(tmp_path)
    h.event({"device": "h", "plass": 1, "uid": "AA11", "type": "inn", "antall": 2})
    h.event({"device": "h", "plass": 1, "type": "ut"})
    aktiv["uid"] = "BB22"                       # noe annet ble startet fra appen
    assert h.lys("h") == "tt"


def test_ugyldig(tmp_path):
    h, _, _ = lag(tmp_path)
    with pytest.raises(ValueError):
        h.event({"device": "h", "plass": 99, "type": "ut"})
    with pytest.raises(ValueError):
        h.event({"device": "h", "plass": 1, "type": "inn"})
    st = h.sett({"device": "h", "navn": "Stua", "antall": 6})
    assert st["hyller"][0]["navn"] == "Stua" and st["hyller"][0]["antall"] == 6
