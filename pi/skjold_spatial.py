"""Virtuell surround fra to høyttalere: binaural gjengivelse (HRTF) + krysstalekansellering (XTC), tilpasset lytteposisjon.

Kjeden er lineær og symmetrisk, så hele behandlingen blir én 2×2 FIR-matrise med to unike filtre (direkte og kryss),
som kjøres i CamillaDSP med samme 2→4→2-oppsett som «Romlig stereo» (skjold_xtc.dsp_yaml).

1) Virtuelle høyttalere: stereo-inngangen plasseres som virtuelle fronter i ±front_deg (bredere enn de fysiske)
   og et ambiens-par bak i ±110°: bak_V = (V − 0,5·H)·forsinket 12 ms og lavpass 7 kHz (dekorrelert, som Pro Logic-
   lignende ambiens). Hver virtuell kilde gir ørersignaler via HRTF.
2) HRTF: innebygd modell av et kulehode (Brown & Duda 1998): ett-pol/ett-null hodeskygge per øre etter vinkelen
   mellom kilde og øre, og Woodworth-ITD. Ingen SOFA-fil trengs; modellen er glatt og lett nok for Pi 3.
   Den virtuelle HRTF-en normaliseres mot den fysiske høyttalerens ipsilaterale HRTF, så «virtuell = fysisk» gir
   vanlig stereo (identitet) etter XTC.
3) XTC fra skjold_xtc (Atal–Schroeder, båndbegrenset 200 Hz–6 kHz) etter lyttergeometrien.
4) Lytter utenfor midten (offset_cm): kanalvis forsinkelse og nivå så begge høyttalere treffer likt (trims()).

CPU: fire konvolusjoner à 1024 taps ved 48 kHz (CamillaDSP FFT-konvolusjon) – rundt 3–5 % av én kjerne på Pi 4,
8–12 % på Pi 3 (anslag fra CamillaDSP-benchmarks, ikke målt på Skjold-maskinvare).
"""
from __future__ import annotations

import math
import os

import numpy as np

import skjold_xtc as xtc

SR = xtc.SR
C = xtc.C
NTAPS = xtc.NTAPS
HEAD_R = 0.0875                # kulehodets radius (m)
EAR_DEG = 100.0                # ørene sitter litt bak midtlinjen
REAR_DEG = 110.0
REAR_DELAY_MS = 12.0


def _alpha(theta_deg: float) -> float:
    """Brown–Duda: skyggefaktor etter vinkel mellom kilde og øre (0° = rett mot øret)."""
    return 1.05 + 0.95 * math.cos(math.radians(theta_deg) / math.radians(150.0) * math.pi)


def _itd_s(theta_deg: float) -> float:
    """Woodworth-forsinkelse til ett øre relativt hodets sentrum (θ = vinkel kilde–øre)."""
    th = math.radians(min(180.0, abs(theta_deg)))
    a = HEAD_R / C
    return -a * math.cos(th) if th < math.pi / 2 else a * (th - math.pi / 2)


def hrtf(az_deg: float, ear: str, f: np.ndarray) -> np.ndarray:
    """Kompleks frekvensrespons fra kilde i asimut az (positiv = venstre) til øret «L»/«R»."""
    ear_az = EAR_DEG if ear == "L" else -EAR_DEG
    theta = abs(((az_deg - ear_az) + 180.0) % 360.0 - 180.0)
    w = 2 * np.pi * f
    w0 = C / HEAD_R
    a = _alpha(theta)
    shadow = (1 + 1j * a * w / (2 * w0)) / (1 + 1j * w / (2 * w0))
    return shadow * np.exp(-1j * w * _itd_s(theta))


def _lowpass_resp(f: np.ndarray, fc: float) -> np.ndarray:
    return 1.0 / (1 + 1j * f / fc)


def binaural_matrix(phys_deg: float, front_deg: float, rear_gain: float, nfft: int = 4096,
                    g_model: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(B_d, B_c) i frekvensdomenet (rfft, nfft): ønskede ørersignaler per inngang, normalisert mot fysisk ipsi-HRTF.
    g_model: krysstalenivået XTC-modellen antar for de fysiske høyttalerne. Kontra-leddene skaleres så kulehodets
    kryss/ipsi-forhold for den fysiske vinkelen blir lik modellens – da gir «virtuell = fysisk» nøyaktig identitet,
    og bredere virtuelle vinkler gir større nivåforskjell mellom ørene relativt til det XTC faktisk kansellerer."""
    f = np.fft.rfftfreq(nfft, 1 / SR)
    ref = hrtf(phys_deg, "L", f)
    ref = np.where(np.abs(ref) < 0.1, 0.1, ref)
    kappa = 1.0 if g_model is None else g_model / np.maximum(np.abs(hrtf(phys_deg, "R", f) / ref), 1e-3)
    Hi_f, Hc_f = hrtf(front_deg, "L", f), hrtf(front_deg, "R", f)   # venstre front → venstre/høyre øre
    Hi_r, Hc_r = hrtf(REAR_DEG, "L", f), hrtf(REAR_DEG, "R", f)
    D = np.exp(-2j * np.pi * f * REAR_DELAY_MS / 1000) * _lowpass_resp(f, 7000.0)
    Bd = Hi_f + rear_gain * D * (Hi_r - 0.5 * Hc_r)
    Bc = Hc_f + rear_gain * D * (Hc_r - 0.5 * Hi_r)
    # Under 150 Hz: ingen romlig info å hente (og kulemodellen er flat der) – la bassen gå rett gjennom.
    lo = 1.0 / (1 + (f / 150.0) ** 4)
    Bd = Bd / ref * (1 - lo) + lo
    Bc = Bc / ref * kappa * (1 - lo)
    return Bd, Bc


def _to_fir(H: np.ndarray, nfft: int, taps: int, pre: int) -> np.ndarray:
    """Kompleks respons → kausal FIR: flytt «pre» samples frem (for ITD < 0) og vindu-avkort."""
    h = np.fft.irfft(H, nfft)
    h = np.roll(h, pre)[:taps]
    w = np.ones(taps)
    k = taps // 8
    w[-k:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
    return h * w


def geometry_deg(span_cm: float, dist_cm: float) -> float:
    return math.degrees(math.atan2(span_cm / 2.0, max(10.0, dist_cm)))


def filters(span_cm: float = 50, dist_cm: float = 60, strength: float = 1.0, surround: float = 0.6,
            width: float = 0.5, head_cm: float = 18.0) -> tuple[np.ndarray, np.ndarray]:
    """(P_direkte, P_kryss) FIR, NTAPS lange. strength = XTC-styrke 0–1, surround = bak-ambiens 0–1,
    width = hvor mye bredere de virtuelle frontene er enn de fysiske (0 → samme vinkel, 1 → ±60°)."""
    nfft = 4096
    phys = geometry_deg(span_cm, dist_cm)
    front = phys + max(0.0, min(1.0, width)) * max(0.0, 60.0 - phys)
    Bd, Bc = binaural_matrix(phys, front, 0.7 * max(0.0, min(1.0, surround)), nfft, xtc.geometry(span_cm, dist_cm, head_cm)[1])
    k = max(0.0, min(1.0, strength))      # uten XTC gir binaural gjengivelse ingen mening → bland mot vanlig stereo
    Bd, Bc = k * Bd + (1 - k), k * Bc
    pre = 32                                                     # plass til negative ITD-er
    bd = _to_fir(Bd, nfft, NTAPS, pre)
    bc = _to_fir(Bc, nfft, NTAPS, pre)
    xd, xc = xtc.filters(span_cm, dist_cm, strength, head_cm)
    # P = X · B (symmetriske matriser): P_d = x_d*b_d + x_c*b_c,  P_c = x_d*b_c + x_c*b_d
    pd = np.convolve(xd, bd)[:NTAPS] + np.convolve(xc, bc)[:NTAPS]
    pc = np.convolve(xd, bc)[:NTAPS] + np.convolve(xc, bd)[:NTAPS]
    # Hodetrom: verste tilfelle (V = H eller V = −H) skal ikke over 0 dB
    Pd, Pc = np.fft.rfft(pd, 8192), np.fft.rfft(pc, 8192)
    peak = max(np.abs(Pd + Pc).max(), np.abs(Pd - Pc).max())
    g = 1.0 / max(1.0, peak)
    return (pd * g).astype(np.float32), (pc * g).astype(np.float32)


def write(dirpath: str, cfg: dict) -> tuple[str, str]:
    os.makedirs(dirpath, exist_ok=True)
    pd, pc = filters(cfg.get("span_cm", 50), cfg.get("dist_cm", 60), float(cfg.get("strength", 70)) / 100.0,
                     float(cfg.get("surround", 60)) / 100.0, float(cfg.get("width", 50)) / 100.0)
    a, b = os.path.join(dirpath, "vs_direct.raw"), os.path.join(dirpath, "vs_cross.raw")
    pd.astype("<f4").tofile(a)
    pc.astype("<f4").tofile(b)
    return a, b


def trims(span_cm: float, dist_cm: float, offset_cm: float) -> dict:
    """Lytter forskjøvet offset_cm mot venstre (+) / høyre (−): forsinkelse (ms) og nivå (dB) per kanal."""
    s, D, x = span_cm / 200.0, max(10.0, dist_cm) / 100.0, offset_cm / 100.0
    dl, dr = math.hypot(s - x, D), math.hypot(s + x, D)
    far = max(dl, dr)
    return {"L": {"delay_ms": round((far - dl) / C * 1000, 3), "gain_db": round(20 * math.log10(dl / far), 2)},
            "R": {"delay_ms": round((far - dr) / C * 1000, 3), "gain_db": round(20 * math.log10(dr / far), 2)}}


def offset_from_tdoa(span_cm: float, dist_cm: float, dt_ms: float) -> float:
    """Lytterens sideforskyvning (cm, + = venstre) fra ankomstforskjell t_H − t_V (ms) målt med mobilen."""
    lo, hi = -span_cm, span_cm
    want = dt_ms / 1000 * C
    s, D = span_cm / 200.0, max(10.0, dist_cm) / 100.0
    for _ in range(60):     # d_R − d_L øker monotont med x
        m = (lo + hi) / 2
        x = m / 100.0
        if math.hypot(s + x, D) - math.hypot(s - x, D) < want:
            lo = m
        else:
            hi = m
    return round((lo + hi) / 2, 1)
