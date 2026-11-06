import os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_xtc as x  # noqa: E402


def _ears(span=50, dist=60, strength=1.0):
    hd, hc = x.filters(span, dist, strength)
    d, g = x.geometry(span, dist)
    n = 8192
    f = np.fft.rfftfreq(n, 1 / 48000)
    Hd, Hc = np.fft.rfft(hd, n), np.fft.rfft(hc, n)
    C = g * np.exp(-2j * np.pi * f * d / 48000)  # akustisk krysstale (relativ til direkte vei)
    # venstre inngang -> venstre øre (ipsi) og høyre øre (kryss)
    eL = Hd + C * Hc
    eR = Hc + C * Hd
    return f, eL, eR, C


def test_xtc_separation_and_no_boost():
    f, eL, eR, C = _ears()
    b = (f >= 500) & (f <= 3000)
    sep = 20 * np.log10(np.abs(eL[b]) / np.abs(eR[b]))
    raw = 20 * np.log10(1 / np.abs(C[b]))
    assert (sep - raw).min() > 10, (sep - raw).min()
    assert 20 * np.log10(np.abs(eL[b])).max() < 3


def test_strength_zero_is_passthrough_and_files(tmp_path):
    hd, hc = x.filters(50, 60, 0.0)
    assert np.abs(hc).max() < 1e-6 and abs(hd.max() - 1) < 1e-3
    x.write(str(tmp_path), 50, 60, 0.7, 18)
    assert os.path.getsize(tmp_path / "xtc_direct.raw") == x.NTAPS * 4
    y = x.dsp_yaml(str(tmp_path / "xtc_direct.raw"), str(tmp_path / "xtc_cross.raw"))
    assert "xtc_d" in y[0] and "xtc_split" in y[1]
