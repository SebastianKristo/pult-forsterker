"""Alle modulene ki_amp_daemon.py importerer må kopieres til /usr/local/bin av update.sh og install.sh.
skjold_esphome.py manglet i listen, og Skjold S1 startet ikke etter oppdateringen."""
import glob
import os
import re

HER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _moduler():
    src = open(os.path.join(HER, "ki_amp_daemon.py"), encoding="utf-8").read()
    navn = set(re.findall(r"^\s*(?:import|from)\s+((?:skjold|ki)_\w+)", src, re.M))
    return {n for n in navn if os.path.exists(os.path.join(HER, n + ".py"))}


def test_alle_importerte_moduler_installeres():
    for skript in ("update.sh", "install.sh"):
        tekst = open(os.path.join(HER, skript), encoding="utf-8").read()
        alle = '"$SRC"/skjold_*.py /usr/local/bin/' in tekst
        mangler = [m for m in sorted(_moduler()) if not (alle and m.startswith("skjold_")) and f"{m}.py" not in tekst]
        assert not mangler, f"{skript} kopierer ikke: {mangler}"


def test_skjold_moduler_finnes():
    assert len(glob.glob(os.path.join(HER, "skjold_*.py"))) > 10 and "skjold_esphome" in _moduler()
