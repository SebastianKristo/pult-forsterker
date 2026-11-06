import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_cloud as sc  # noqa: E402


class FalskSky:
    """Etterligner /enhet/sync i workeren: versjonerte blobs, 409 ved utdatert base."""

    def __init__(self):
        self.lager, self.sett = {}, []

    async def __call__(self, metode, url, hdr, body):
        assert hdr["Authorization"].startswith("Bearer ")
        if metode == "GET":
            d = url.split("del=")[1]
            e = self.lager.get(d)
            return 200, {"del": d, "versjon": e["versjon"] if e else 0, "blob": e["blob"] if e else None}
        d, e = body["del"], self.lager.get(body["del"])
        cur = e["versjon"] if e else 0
        if body["base"] != cur:
            return 409, {"konflikt": True, "del": d, "versjon": cur, "blob": e["blob"]}
        self.lager[d] = {"versjon": cur + 1, "blob": body["blob"]}
        self.sett.append(body["blob"])
        return 200, {"versjon": cur + 1}


def hjem(tmp_path, navn, sky, data):
    bridge = {"hent": lambda d: data.get(d, {}), "sett": lambda d, v: data.__setitem__(d, dict(v)),
              "sky": lambda: {"url": "https://x", "id": "e1", "noekkel": "st_abc." + "0" * 64}}
    return sc.SkjoldCloud(bridge, str(tmp_path / f"{navn}.json"), http=sky)


def run(c):
    return asyncio.run(c)


def test_frase_og_krypto():
    f = sc.ny_frase()
    assert len(f.split()) == 12 and len(set(sc.ORD)) == 256
    k = sc.nokkel(f.upper())
    blob = sc.krypter(k, {"a": 1}, "eq")
    assert sc.dekrypter(k, blob, "eq") == {"a": 1}
    with pytest.raises(Exception):
        sc.dekrypter(k, blob, "rutiner")          # delnavnet er autentisert
    with pytest.raises(Exception):
        sc.dekrypter(sc.nokkel(sc.ny_frase()), blob, "eq")
    with pytest.raises(ValueError):
        sc.normaliser_frase("for få ord")


def test_rens_fjerner_hemmeligheter():
    assert sc.rens({"navn": "x", "password": "p", "wifi": {"ssid": "s", "passord": "q"}, "api_token": 1}) == \
        {"navn": "x", "wifi": {"ssid": "s"}}


def test_flett_sist_vinner_og_konflikt():
    lok = {"a": {"v": 1, "t": 10}, "b": {"v": 5, "t": 1}}
    fjern = {"a": {"v": 2, "t": 20}, "c": {"v": 3, "t": 5}}
    ut, konf = sc.flett(lok, fjern, {"a": sc._h(0)})
    assert ut["a"]["v"] == 2 and ut["b"]["v"] == 5 and ut["c"]["v"] == 3
    assert konf and konf[0]["nokkel"] == "a" and konf[0]["vant"] == "fjern"
    _, konf2 = sc.flett(lok, fjern, {"a": sc._h(1)})   # bare fjern endret ⇒ ingen konflikt
    assert konf2 == []


def test_to_hjem_synker(tmp_path):
    sky = FalskSky()
    da = {"favoritter": {"1": {"navn": "NRK P1"}}, "eq": {"bass": 2}}
    db = {"favoritter": {"2": {"navn": "P3"}}}
    a, b = hjem(tmp_path, "a", sky, da), hjem(tmp_path, "b", sky, db)
    frase = a.aktiver()["frase"]
    assert b.aktiver(frase) == {}
    assert run(a.synk())["ok"]
    assert run(b.synk())["ok"]
    assert db["favoritter"] == {"1": {"navn": "NRK P1"}, "2": {"navn": "P3"}} and db["eq"] == {"bass": 2}
    run(a.synk())
    assert da["favoritter"] == db["favoritter"]
    # sletting propagerer
    del db["favoritter"]["1"]
    run(b.synk()); run(a.synk())
    assert "1" not in da["favoritter"]
    # skyen ser aldri klartekst
    assert all("NRK" not in x for x in sky.sett)


def test_velg_deler_og_uten_sky(tmp_path):
    sky = FalskSky()
    data = {"favoritter": {"1": 1}, "wrapped": {"2025": 9}}
    a = hjem(tmp_path, "a", sky, data)
    a.aktiver()
    a.velg(["wrapped", "tull"])
    assert a.status()["deler"] == ["wrapped"]
    run(a.synk())
    assert set(sky.lager) == {"wrapped"}
    a.b["sky"] = lambda: {}
    r = run(a.synk())
    assert not r["ok"] and "koblet" in r["feil"]
    a.deaktiver()
    assert not a.status()["har_frase"]
