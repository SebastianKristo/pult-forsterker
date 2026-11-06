"""Skjold Sertifisert: måling, gating, PEQ-tilpasning, sertifisering og DSP-regler (syntetisk «høyttaler»)."""
import io
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_roomeq as rq  # noqa: E402
import skjold_speakerprofiles as sp  # noqa: E402


def speaker(x, peaks=(), reflect=None, sr=48000):
    """Lineær fase-fri «høyttaler»: magnitude fra peaking-filtre, valgfri refleksjon (delay ms, nivå)."""
    n = 1 << int(np.ceil(np.log2(len(x) + sr)))
    f = np.fft.rfftfreq(n, 1 / sr)
    g = np.zeros_like(f)
    for f0, q, db in peaks:
        g += rq.peq_db(f0, q, db, np.maximum(f, 1.0))
    X = np.fft.rfft(x, n) * 10 ** (g / 20)
    y = np.fft.irfft(X, n)[: len(x) + sr]
    if reflect:
        d = int(reflect[0] * sr / 1000)
        y[d:] += reflect[1] * y[:-d]
    return y


def wav(x, sr=48000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return b.getvalue()


def rec(peaks=(), reflect=None, noise=1e-4, seed=1):
    sw = rq.log_sweep()
    x = np.concatenate([np.zeros(48000), sw])
    y = speaker(x, peaks, reflect) * 0.3
    y += np.random.default_rng(seed).normal(0, noise, len(y))
    return wav(y)


def at(fr, db, f):
    return float(np.interp(np.log10(f), np.log10(fr), db))


def test_measure_finds_peak_and_gate_removes_room():
    m = sp.measure(rec(peaks=[(2000, 2, 6)], reflect=(8, 0.7)), gate_ms=5)
    db = sp.normalize(m["freqs"], m["db"])
    assert 4 < at(m["freqs"], db, 2000) < 8
    assert abs(at(m["freqs"], db, 5000)) < 2
    assert m["valid"][0] >= 199 and not m["clipped"] and m["snr"] > 30


def test_fit_peq_flattens_and_respects_limits():
    m = sp.measure(rec(peaks=[(2000, 2, 6), (6000, 3, -5)]))
    p = sp.build_profile([m], "Testmerke", "T1")
    fr = np.array([c["f"] for c in p["curve"]])
    after = np.array([c["db"] for c in p["after"]])
    band = (fr >= 300) & (fr <= 12000)
    assert np.max(np.abs(after[band])) < 2.5
    assert all(sp.MAX_CUT <= f["g"] <= sp.MAX_BOOST for f in p["filters"])
    assert any(abs(f["f"] - 2000) < 400 and f["g"] < -3 for f in p["filters"])


def test_quality_and_repeat_consistency():
    a = sp.measure(rec(peaks=[(1500, 1, 4)], seed=1))
    b = sp.measure(rec(peaks=[(1500, 1, 4)], seed=2))
    p = sp.build_profile([a, b], "X", "Y")
    assert p["points"] == 2 and p["score"] >= 70


def test_calibration_parse_and_apply():
    cal = sp.parse_calibration('"Sens Factor =-1.2dB"\n20 -3.0\n1000 0\n10000 2.0\n* kommentar\n')
    assert cal == [(20.0, -3.0), (1000.0, 0.0), (10000.0, 2.0)]
    fr = np.array([20.0, 1000.0, 10000.0])
    assert np.allclose(sp.calibration_curve(fr, cal), [-3, 0, 2])


def test_splice_levels_match():
    fr = sp.freqs()
    near = {"freqs": fr, "db": np.zeros_like(fr) - 10, "valid": [20, 400], "snr": 50, "clipped": False}
    far = {"freqs": fr, "db": np.zeros_like(fr), "valid": [200, 20000], "snr": 50, "clipped": False}
    s = sp.splice(near, far)
    assert np.max(np.abs(s["db"])) < 0.01 and s["valid"] == [20, 20000]


def test_certify_rule():
    fr = sp.freqs()
    base = [{"f": float(f), "db": 0.0} for f in fr]
    off = [{"f": float(f), "db": 6.0 if 1000 < f < 5000 else 0.0} for f in fr]
    subs = [{"curve": base, "score": 80, "source": s} for s in "abc"]
    assert sp.certify(subs)["certified"]
    assert not sp.certify(subs[:2])["certified"]
    assert not sp.certify([{**s, "source": "a"} for s in subs])["certified"]   # samme kilde teller én gang
    r = sp.certify(subs + [{"curve": off, "score": 90, "source": "d"}])
    assert r["certified"] and r["agree"] == 3


def test_dsp_filters_yield_bass_to_roomeq():
    p = {"filters": [{"f": 120, "q": 2, "g": -4}, {"f": 2500, "q": 2, "g": 9}, {"f": 9e9, "q": 1, "g": 1}]}
    assert sp.dsp_filters(p) == [(120.0, 2.0, -4.0), (2500.0, 2.0, 3.0)]
    assert sp.dsp_filters(p, roomeq_on=True) == [(2500.0, 2.0, 3.0)]


def test_power_hint():
    h = sp.power_hint(82, 3)
    assert h["watts"] == 50 and len(h["warnings"]) == 2


def test_store_offline_cache(tmp_path):
    def boom(*a, **k):
        raise OSError("offline")
    s = sp.Store("https://x", path=str(tmp_path / "c.json"), opener=boom)
    s.cache = {"p1": {"merke": "Dali", "modell": "Oberon 3", "antall": 4, "sertifisert": True}}
    r = s.search("oberon")
    assert r["offline"] and r["results"][0]["id"] == "p1"
    assert s.get("p1")["offline"]
