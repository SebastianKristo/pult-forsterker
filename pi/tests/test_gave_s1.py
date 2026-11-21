"""Gaveskriptet (pi/gave_s1.sh): «Ferdig installert» først, så bursdagshilsenen ved neste oppstart, med «Fra …»."""
import importlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))


@pytest.fixture
def sui(tmp_path, monkeypatch):
    monkeypatch.setenv("SKJOLD_GREETING", str(tmp_path / "greeting.json"))
    import skjold_ui.__main__ as m
    m = importlib.reload(m)
    got = []
    monkeypatch.setattr(m, "broadcast", got.append)
    return m, got, tmp_path / "greeting.json"


def test_ferdig_viser_melding_og_gjor_hilsenen_klar(sui):
    m, got, fil = sui
    fil.write_text(json.dumps({"name": "Pappa", "fra": "Sebastian og Cybele", "state": "ferdig"}), encoding="utf-8")
    assert m.greeting_read() == {"name": "Pappa", "fra": "Sebastian og Cybele", "state": "ferdig"}
    m.ferdig_na()                                   # skjold-ui starter (oppstarten etter installasjonen)
    assert m.FERDIG["vis"] and got[-1] == {"ev": "ferdig"}
    assert json.loads(fil.read_text(encoding="utf-8"))["state"] == "armed"   # neste oppstart: hilsenen
    assert m.handle_input({"ev": "press", "src": "knob"}) == {"consumed": True}   # knappene gjør ingenting nå
    assert json.loads(fil.read_text(encoding="utf-8"))["state"] == "armed"   # og lukker ikke hilsenen


def test_neste_oppstart_viser_hilsenen_til_et_trykk(sui):
    m, got, fil = sui
    fil.write_text(json.dumps({"name": "Pappa", "fra": "Sebastian og Cybele", "state": "armed"}), encoding="utf-8")
    assert not m.FERDIG["vis"]
    assert m.greeting_read()["fra"] == "Sebastian og Cybele"
    assert m.handle_input({"ev": "press", "src": "power"}) == {"consumed": True}
    assert got[-1] == {"ev": "dismiss_greeting"}
    assert json.loads(fil.read_text(encoding="utf-8"))["state"] == "shown"


def test_skriptet_er_gyldig_bash():
    subprocess.run(["bash", "-n", os.path.join(HERE, "..", "gave_s1.sh")], check=True)
