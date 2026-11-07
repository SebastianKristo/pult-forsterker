"""Hjelperne bak Skjold-kortet i Home Assistant (custom_components/skjold/cardhelpers.py – uten HA-avhengigheter)."""
import importlib.util
import os

import pytest

_p = os.path.join(os.path.dirname(__file__), "..", "..", "custom_components", "skjold", "cardhelpers.py")
_spec = importlib.util.spec_from_file_location("cardhelpers", _p)
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def test_eq_state_by_index_and_by_bands():
    st = {"input": "radio"}
    assert H.eq_state({"eq": {"radio": {"preset": 2, "eq": [-2, -1, 2, 3, 1]}}}, st)["preset"] == "Vokal"
    assert H.eq_state({"eq": {"radio": {"preset": -1, "eq": [2, 1, 0, -2, -3]}}}, st)["preset"] == "Kveld"
    assert H.eq_state({"eq": {"radio": {"eq": [9, 9, 9, 9, 9]}}}, st)["preset"] == "Egen"
    assert H.eq_state({}, {"input": "bt", "headphones": True})["source"] == "hp"
    assert len(H.eq_state(None, st)["profiles"]) == 14


def test_eq_patch():
    assert H.eq_patch("kveld", "air") == {"eq": {"air": {"preset": 3, "eq": [2, 1, 0, -2, -3]}}}
    with pytest.raises(ValueError):
        H.eq_patch("Ukjent", "air")


def test_logo_urls_go_via_home_assistant():
    assert H.logo_url("abc", "/api/logo?k=0123456789abcdef") == "/api/skjold_logo/abc?k=0123456789abcdef"
    assert H.logo_url("abc", "") == "" and H.logo_url("abc", "/api/logo?k=bad") == ""
    assert H.valid_key("0123456789abcdef") and not H.valid_key("../etc")
    out = H.card_presets("e1", [{"n": 1, "title": "NRK P1", "image": "x"}, {"title": "uten nr"}],
                         [{"n": 1, "title": "NRK P1", "logo": "/api/logo?k=00112233445566ff"}])
    assert out == [{"n": 1, "title": "NRK P1", "image": "x", "logo": "/api/skjold_logo/e1?k=00112233445566ff"}]
