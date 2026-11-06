"""Romlig stereo for skrivebordet: krysstalekansellering (XTC) som FIR-filtre for CamillaDSP.

Modell: hver høyttaler når øret på samme side direkte og øret på motsatt side litt senere og svakere
(«krysstale»): øre_V = V + g·z^-d·H, øre_H = H + g·z^-d·V, der d = (kontra − ipsi)/c og g = ipsi/kontra × hodeskygge.
Rekursiv kansellering (Atal–Schroeder) gir V' = V − g z^-d H' osv. Vi bruker de første leddene (2–3 iterasjoner):
  H_VV = 1 + g²z^-2d (+ g⁴z^-4d),   H_VH = −g z^-d − g³z^-3d
Korreksjonsleddene båndbegrenses til 200 Hz–6 kHz (under 200 Hz er hodet akustisk «lite», over 6 kHz varierer HRTF-en
for mye) og skaleres med styrken. Utgangen: V_ut = H_VV*V + H_VH*H, H_ut = H_VH*V + H_VV*H.
"""
from __future__ import annotations

import math
import os

import numpy as np

SR = 48000
C = 343.0          # lydhastighet m/s
NTAPS = 1024
SHADOW = 0.55      # hodeskygge i 0,5–3 kHz (ca. −5 dB), forenklet frekvensuavhengig i korreksjonsbåndet


def geometry(span_cm: float, dist_cm: float, head_cm: float = 18.0) -> tuple[float, float]:
    """(d i samples, g) for høyttalere ±span/2 og lytter i avstand dist, ører ±head/2."""
    s, D, h = span_cm / 200.0, max(10.0, dist_cm) / 100.0, head_cm / 200.0
    ipsi = math.hypot(s - h, D)
    contra = math.hypot(s + h, D)
    d = (contra - ipsi) / C * SR
    g = ipsi / contra * SHADOW
    return d, g


def _frac_delay(n: int, delay: float, taps: int = 48) -> np.ndarray:
    """Vindusvektet sinc med brøk-forsinkelse plassert i en buffer på n samples."""
    out = np.zeros(n)
    i0 = int(math.floor(delay))
    k = np.arange(i0 - taps // 2, i0 + taps // 2 + 1)
    k = k[(k >= 0) & (k < n)]
    x = k - delay
    w = 0.5 + 0.5 * np.cos(np.pi * x / (taps / 2 + 1))
    out[k] = np.sinc(x) * w
    return out


def _bandpass(lo: float, hi: float, taps: int = 255) -> np.ndarray:
    n = np.arange(taps) - (taps - 1) / 2
    h = (2 * hi / SR) * np.sinc(2 * hi / SR * n) - (2 * lo / SR) * np.sinc(2 * lo / SR * n)
    return h * np.blackman(taps)


def filters(span_cm: float = 50, dist_cm: float = 60, strength: float = 1.0, head_cm: float = 18.0,
            iterations: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """(H_direkte, H_kryss) som FIR med NTAPS taps. Direkte = δ + båndbegrensede like ledd, kryss = −odde ledd."""
    d, g = geometry(span_cm, dist_cm, head_cm)
    g *= max(0.0, min(1.0, strength))
    bp = _bandpass(200.0, 6000.0)
    lat = (len(bp) - 1) // 2                     # båndpassets forsinkelse – samme for direkte δ
    corr_d, corr_c = np.zeros(NTAPS), np.zeros(NTAPS)
    for k in range(1, iterations * 2):           # k=1,3,5 → kryss; k=2,4 → direkte
        term = (g ** k) * _frac_delay(NTAPS, k * d)
        if k % 2:
            corr_c -= term
        elif k <= 2 * (iterations - 1):
            corr_d += term
    h_d = np.convolve(corr_d, bp)[:NTAPS]
    h_c = np.convolve(corr_c, bp)[:NTAPS]
    h_d[lat] += 1.0
    return h_d.astype(np.float32), h_c.astype(np.float32)


def write(dirpath: str, span_cm: float, dist_cm: float, strength: float, head_cm: float = 18.0) -> tuple[str, str]:
    os.makedirs(dirpath, exist_ok=True)
    h_d, h_c = filters(span_cm, dist_cm, strength, head_cm)
    pd, pc = os.path.join(dirpath, "xtc_direct.raw"), os.path.join(dirpath, "xtc_cross.raw")
    h_d.astype("<f4").tofile(pd)
    h_c.astype("<f4").tofile(pc)
    return pd, pc


def dsp_yaml(path_direct: str, path_cross: str) -> tuple[str, str, list[str]]:
    """(filters-YAML, mixers-YAML, pipeline-steg). Splitter 2→4 kanaler, filtrerer og summerer 4→2."""
    filt = f"""
  xtc_d:
    type: Conv
    parameters: {{type: Raw, filename: "{path_direct}", format: FLOAT32LE}}
  xtc_c:
    type: Conv
    parameters: {{type: Raw, filename: "{path_cross}", format: FLOAT32LE}}"""
    mix = """
  xtc_split:
    channels: {in: 2, out: 4}
    mapping:
      - {dest: 0, sources: [{channel: 0, gain: 0, inverted: false}]}
      - {dest: 1, sources: [{channel: 1, gain: 0, inverted: false}]}
      - {dest: 2, sources: [{channel: 0, gain: 0, inverted: false}]}
      - {dest: 3, sources: [{channel: 1, gain: 0, inverted: false}]}
  xtc_sum:
    channels: {in: 4, out: 2}
    mapping:
      - {dest: 0, sources: [{channel: 0, gain: 0, inverted: false}, {channel: 1, gain: 0, inverted: false}]}
      - {dest: 1, sources: [{channel: 2, gain: 0, inverted: false}, {channel: 3, gain: 0, inverted: false}]}"""
    steps = ["  - type: Mixer\n    name: xtc_split",
             "  - type: Filter\n    channel: 0\n    names: [xtc_d]",
             "  - type: Filter\n    channel: 1\n    names: [xtc_c]",
             "  - type: Filter\n    channel: 2\n    names: [xtc_c]",
             "  - type: Filter\n    channel: 3\n    names: [xtc_d]",
             "  - type: Mixer\n    name: xtc_sum"]
    return filt, mix, steps


def test_signal(sr: int = SR, dur: float = 6.0) -> np.ndarray:
    """Lyttetest: rosa-aktig støy som panoreres hardt V → midt → H → utenfor (motfase-lekk), stereo int16."""
    rng = np.random.default_rng(1)
    n = int(sr * dur)
    x = np.cumsum(rng.standard_normal(n)) * 0.0
    w = rng.standard_normal(n)
    b = np.array([0.049922, -0.095993, 0.050613, -0.004408]); a = np.array([1, -2.494956, 2.017265, -0.522190])
    y = np.zeros(n)
    for i in range(n):   # enkel rosa-støy (Kellet-filter)
        y[i] = b[0] * w[i] + (b[1] * w[i - 1] if i else 0) + (b[2] * w[i - 2] if i > 1 else 0) + (b[3] * w[i - 3] if i > 2 else 0) \
            - (a[1] * y[i - 1] if i else 0) - (a[2] * y[i - 2] if i > 1 else 0) - (a[3] * y[i - 3] if i > 2 else 0)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.4
    t = np.linspace(0, 1, n)
    pan = np.interp(t, [0, 0.25, 0.5, 0.75, 1], [-1, -1, 0, 1, 1])
    left = y * np.cos((pan + 1) * np.pi / 4)
    right = y * np.sin((pan + 1) * np.pi / 4)
    return (np.stack([left, right], 1) * 32767).astype("<i2")
