"""Daemonen er én stor modul: en funksjon definert to ganger på toppnivå overskriver den første stille
(slik «_safe» for knapper ble erstattet av plasseringens «_safe(fn)», og volumhjulet på Noden sluttet å virke)."""
import ast
import collections
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ki_amp_daemon.py")


def test_ingen_dobbeltdefinerte_toppnivafunksjoner():
    tree = ast.parse(open(P, encoding="utf-8").read())
    n = collections.Counter(x.name for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    dup = sorted(k for k, c in n.items() if c > 1)
    assert not dup, f"definert flere ganger: {dup}"
