import math, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_spatial as vs  # noqa: E402
import skjold_placement as pl  # noqa: E402
import skjold_xtc as xtc  # noqa: E402

SR = 48000


def _ears(pd, pc, span=50, dist=60):
    """Venstre inngang → (venstre øre, høyre øre) med samme forenklede akustikk som XTC-testene."""
    n = 8192
    f = np.fft.rfftfreq(n, 1 / SR)
    d, g = xtc.geometry(span, dist)
    Cx = (g / xtc.SHADOW) * xtc.SHADOW * np.exp(-2j * np.pi * f * d / SR)
    Pd, Pc = np.fft.rfft(pd, n), np.fft.rfft(pc, n)
    return f, Pd + Cx * Pc, Pc + Cx * Pd


def test_off_is_identity():
    pd, pc = vs.filters(strength=0, surround=0, width=0)
    H = np.fft.rfft(pd, 8192)
    assert np.abs(pc).max() < 1e-6
    assert np.allclose(np.abs(H[50:3000]), 1.0, atol=0.02)


def test_virtual_surround_widens_and_never_clips():
    f, eL0, eR0 = _ears(*vs.filters(strength=0, surround=0, width=0))
    b = (f >= 500) & (f <= 3000)
    ild0 = np.mean(20 * np.log10(np.abs(eL0[b]) / np.abs(eR0[b])))
    ilds = []
    for w in (0.0, 0.5, 1.0):
        _f, eL, eR = _ears(*vs.filters(strength=1, surround=0, width=w))
        ilds.append(np.mean(20 * np.log10(np.abs(eL[b]) / np.abs(eR[b]))))
    assert abs(ilds[0] - ild0) < 0.5                       # XTC + «virtuell = fysisk» ≈ samme bilde
    assert ilds[0] < ilds[1] < ilds[2] and ilds[2] > ild0 + 3, (ild0, ilds)   # bredere virtuelle fronter
    # bak-ambiensen: energi rundt 12 ms i kryssfilteret når surround er på
    pc0, pc1 = vs.filters(surround=0)[1], vs.filters(surround=1)[1]
    i = int(0.012 * SR) + 32
    assert np.abs(pc1[i - 100:i + 200]).sum() > 3 * np.abs(pc0[i - 100:i + 200]).sum()
    pd, pc = vs.filters()
    Pd, Pc = np.fft.rfft(pd, 8192), np.fft.rfft(pc, 8192)
    assert max(np.abs(Pd + Pc).max(), np.abs(Pd - Pc).max()) <= 1.0001


def test_hrtf_itd_and_shadow():
    f = np.array([200.0, 4000.0])
    l, r = vs.hrtf(90, "L", f), vs.hrtf(90, "R", f)
    assert abs(l[1]) > abs(r[1]) * 2                        # hodeskygge i diskanten
    itd = vs._itd_s(180 - vs.EAR_DEG + 90) - vs._itd_s(abs(90 - vs.EAR_DEG))
    assert 0.0005 < itd < 0.0008


def test_listener_offset_roundtrip(tmp_path):
    t = vs.trims(60, 80, 15)
    assert t["L"]["delay_ms"] > 0 and t["R"]["delay_ms"] == 0 and t["L"]["gain_db"] < 0
    dl, dr = math.hypot(0.3 - 0.15, 0.8), math.hypot(0.3 + 0.15, 0.8)
    assert abs(vs.offset_from_tdoa(60, 80, (dr - dl) / 343 * 1000) - 15) < 0.5
    a, b = vs.write(str(tmp_path), {"strength": 70, "surround": 50})
    assert os.path.getsize(a) == vs.NTAPS * 4


def _rec(true_ms, gains, refl=True):
    s = pl.sweep()
    rng = np.random.default_rng(3)
    rec = np.zeros(int(SR * (0.5 + len(true_ms) * pl.SLOT_S + 1)))
    for i, (a, _b) in enumerate(pl.sequence_signal(len(true_ms))):
        d = int(round((a + true_ms[i] / 1000) * SR))
        rec[d:d + len(s)] += gains[i] * s
        if refl:
            d2 = d + int(0.007 * SR)
            rec[d2:d2 + len(s)] += 0.6 * gains[i] * s
    return rec + rng.standard_normal(len(rec)) * 0.02


def test_arrivals_and_align():
    A = pl.arrivals(_rec([2.0, 5.5, 3.25], [1.0, 0.5, 0.7]), 3)
    assert [round(a["t_ms"], 1) for a in A] == [2.0, 5.5, 3.2]
    al = pl.align(A)
    assert al[1]["delay_ms"] == 0 and abs(al[0]["delay_ms"] - 3.5) < 0.05
    assert abs(al[0]["gain_db"] + 6.0) < 0.3


def test_trilateration_5_1():
    pos = np.array([[-1.4, 2.4], [1.4, 2.4], [0.0, 2.7], [-1.9, -0.9], [1.9, -0.9]])   # x+ = høyre
    L = np.array([0.1, 0.0])
    d = np.linalg.norm(pos[:, None] - pos[None], axis=2)
    o = np.random.default_rng(1).uniform(0, 0.05, 5)
    T = o[None, :] - o[:, None] + d / 343 + 0.011
    tl = (np.linalg.norm(pos - L, axis=1) / 343 + 0.25) * 1000
    r = pl.solve(T, list(tl), front=2, left=0)
    assert r["roles"]["L"]["index"] == 0 and r["roles"]["R"]["index"] == 1 and r["roles"]["C"]["index"] == 2
    assert r["roles"]["Ls"]["index"] == 3 and r["roles"]["Rs"]["index"] == 4
    true_d = np.linalg.norm(pos - L, axis=1)
    assert np.allclose([t["dist_m"] for t in r["trims"]], true_d, atol=0.03)
