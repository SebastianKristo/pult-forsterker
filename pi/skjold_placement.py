"""Automatisk kalibrering av høyttalerplassering.

Måling: hver høyttaler (kanal på denne enheten, eller en annen Skjold via skjold_sync) spiller en kort logaritmisk
sweep etter tur i faste tidsluker. En mikrofon tar opp hele sekvensen – mobilen i lytteposisjon, eller mikrofonene på
enhetene selv. Opptaket dekonvolveres (Farina: invers sweep), og første tydelige topp i hver luke gir ankomsttid og nivå.

To moduser:
* Mobil i lytteposisjon (én mikrofon): bare relative ankomsttider er kjent → forsinkelse og nivå per høyttaler så alle
  treffer lytteren samtidig og likt. Nok til tidsjustering av multiroom/5.1. Posisjoner kun hvis høyttaler-
  posisjonene er kjent (fra enhetsmåling eller manuelt) – da finnes lytteren med TDOA-multilaterasjon.
* Enhetsmikrofoner (hver enhet tar opp alle andre): toveis målinger opphever klokkeforskjeller,
  d_ij = c·((T_ij + T_ji) − (T_ii + T_jj))/2, og klassisk MDS gir 2D-posisjoner (opp til speiling/rotasjon, som
  orienteres så midt-/fronthøyttaleren ligger rett frem).
Til slutt: vinkler sett fra lytteren, forslag til rolle (V/S/H/Vs/Hs) og avvik fra ITU-R BS.775 (0°, ±30°, ±110°).
"""
from __future__ import annotations

import math

import numpy as np

SR = 48000
C = 343.0
F1, F2, SWEEP_S, SLOT_S = 200.0, 16000.0, 1.0, 1.6
ITU = {"C": 0.0, "L": 30.0, "R": -30.0, "Ls": 110.0, "Rs": -110.0}


def sweep(sr: int = SR, dur: float = SWEEP_S, f1: float = F1, f2: float = F2) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    k = math.log(f2 / f1)
    x = np.sin(2 * math.pi * f1 * dur / k * (np.exp(t / dur * k) - 1))
    fade = int(0.01 * sr)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


def inverse(s: np.ndarray, sr: int = SR, dur: float = SWEEP_S, f1: float = F1, f2: float = F2) -> np.ndarray:
    """Farinas inverse filter: tidsreversert sweep med −6 dB/okt amplitudekorreksjon."""
    t = np.arange(len(s)) / sr
    k = math.log(f2 / f1)
    return s[::-1] * np.exp(-t * k / dur)


def sequence_signal(n: int, sr: int = SR, lead_s: float = 0.5) -> list[tuple[float, float]]:
    """Tidsluker (start_s, slutt_s) relativt opptaksstart for n høyttalere."""
    return [(lead_s + i * SLOT_S, lead_s + (i + 1) * SLOT_S) for i in range(n)]


def impulse(rec: np.ndarray, sr: int = SR) -> np.ndarray:
    s = sweep(sr)
    inv = inverse(s, sr)
    n = 1 << int(math.ceil(math.log2(len(rec) + len(inv))))
    ir = np.fft.irfft(np.fft.rfft(rec, n) * np.fft.rfft(inv, n), n)[:len(rec) + len(inv) - 1]
    return ir[len(s) - 1:]          # indeks 0 = sweepen startet i opptaket


def arrivals(rec: np.ndarray, n: int, sr: int = SR, lead_s: float = 0.5) -> list[dict]:
    """Per luke: {t_ms, level_db, snr_db}. t_ms er ankomst relativt luke-start (inkl. systemlatens)."""
    ir = np.abs(impulse(np.asarray(rec, float), sr))
    out = []
    for a, b in sequence_signal(n, sr, lead_s):
        i0, i1 = int(a * sr), min(len(ir), int((a + SLOT_S * 0.8) * sr))
        w = ir[i0:i1]
        if not len(w):
            out.append({"t_ms": None, "level_db": None, "snr_db": 0.0}); continue
        pk = w.max()
        noise = np.median(w) + 1e-12
        # første topp over 50 % av maks = direkte lyd (refleksjoner kommer senere og er ofte sterke i bass)
        first = int(np.argmax(w > 0.5 * pk))
        j = first + int(np.argmax(w[first:first + int(0.0015 * sr)]))
        # parabolsk interpolasjon for under-sample presisjon
        if 0 < j < len(w) - 1:
            y0, y1, y2 = w[j - 1], w[j], w[j + 1]
            den = y0 - 2 * y1 + y2
            frac = 0.5 * (y0 - y2) / den if den else 0.0
        else:
            frac = 0.0
        e = float(np.sum(w[max(0, j - 24):j + int(0.004 * sr)] ** 2))
        out.append({"t_ms": round(float((j + frac) / sr * 1000), 4), "level_db": round(10 * math.log10(e + 1e-20), 2),
                    "snr_db": round(float(20 * math.log10(pk / noise)), 1)})
    return out


def align(arr: list[dict], max_gain_db: float = 10.0) -> list[dict]:
    """Forsinkelse og nivå per høyttaler så alle treffer lytteren samtidig og likt (den svakeste/fjerneste = 0)."""
    ok = [a for a in arr if a.get("t_ms") is not None]
    if not ok:
        return [{"delay_ms": 0.0, "gain_db": 0.0, "rel_cm": None} for _ in arr]
    tmax = max(a["t_ms"] for a in ok)
    tmin = min(a["t_ms"] for a in ok)
    lmin = min(a["level_db"] for a in ok)
    out = []
    for a in arr:
        if a.get("t_ms") is None:
            out.append({"delay_ms": 0.0, "gain_db": 0.0, "rel_cm": None}); continue
        out.append({"delay_ms": round(float(tmax - a["t_ms"]), 3),
                    "gain_db": round(float(max(-max_gain_db, lmin - a["level_db"])), 2),
                    "rel_cm": round(float((a["t_ms"] - tmin) / 1000 * C * 100), 1)})
    return out


def pairwise(T: np.ndarray) -> np.ndarray:
    """T[i, j] = ankomst (s) av høyttaler i i mikrofon j (j sin klokke). → avstandsmatrise (m)."""
    T = np.asarray(T, float)
    d = np.diag(T)
    D = C * ((T + T.T) - (d[:, None] + d[None, :])) / 2
    np.fill_diagonal(D, 0.0)
    return np.maximum(D, 0.0)


def mds2d(D: np.ndarray) -> np.ndarray:
    """Klassisk MDS: avstandsmatrise → n×2 koordinater (sentrert)."""
    D = np.asarray(D, float)
    n = len(D)
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, v = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:2]
    return v[:, idx] * np.sqrt(np.maximum(w[idx], 0))


def locate_listener(pos: np.ndarray, t_ms: list[float]) -> np.ndarray:
    """TDOA-multilaterasjon: punkt der d_i − d_0 best passer c·(t_i − t_0). Grovsøk + Gauss–Newton."""
    pos = np.asarray(pos, float)
    t = np.asarray(t_ms, float) / 1000
    dd = C * (t - t[0])

    def res(p):
        d = np.linalg.norm(pos - p, axis=1)
        return (d - d[0]) - dd

    lo, hi = pos.min(0) - 3, pos.max(0) + 3
    gx, gy = np.meshgrid(np.linspace(lo[0], hi[0], 61), np.linspace(lo[1], hi[1], 61))
    best = min(((float(np.sum(res(np.array([x, y])) ** 2)), (x, y)) for x, y in zip(gx.ravel(), gy.ravel())))[1]
    p = np.array(best, float)
    for _ in range(30):
        r = res(p)
        J = np.zeros((len(pos), 2))
        eps = 1e-5
        for k in range(2):
            q = p.copy(); q[k] += eps
            J[:, k] = (res(q) - r) / eps
        step, *_ = np.linalg.lstsq(J, -r, rcond=None)
        p = p + step
        if np.linalg.norm(step) < 1e-6:
            break
    return p


def orient(pos: np.ndarray, listener: np.ndarray, front: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Flytt lytteren til origo og roter så «front» (indeks, eller snittet av alle) ligger rett frem (+y)."""
    p = np.asarray(pos, float) - listener
    ref = p[front] if front is not None else p.mean(0)
    ang = math.atan2(ref[0], ref[1])
    R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
    return p @ R.T, np.zeros(2)


def angles(pos_rel: np.ndarray) -> list[float]:
    """Asimut (grader, + = venstre) sett fra lytteren i origo med front = +y."""
    return [round(math.degrees(math.atan2(-x, y)), 1) for x, y in np.asarray(pos_rel, float)]


def assign_roles(az: list[float], layout: str = "5.1") -> dict:
    """Greedy: hver ITU-rolle får nærmeste ledige høyttaler. → {rolle: (indeks, avvik_grader)}."""
    roles = {"2.0": ["L", "R"], "3.0": ["L", "C", "R"], "5.1": ["L", "C", "R", "Ls", "Rs"]}.get(layout, ["L", "R"])
    free = set(range(len(az)))
    out = {}
    for r in roles:
        if not free:
            break
        i = min(free, key=lambda k: abs(((az[k] - ITU[r]) + 180) % 360 - 180))
        free.discard(i)
        out[r] = {"index": i, "dev_deg": round(((az[i] - ITU[r]) + 180) % 360 - 180, 1)}
    return out


def trims_from_positions(pos_rel: np.ndarray) -> list[dict]:
    d = np.linalg.norm(np.asarray(pos_rel, float), axis=1)
    far = d.max()
    return [{"dist_m": round(float(x), 3), "delay_ms": round(float((far - x) / C * 1000), 3),
             "gain_db": round(float(20 * math.log10(max(x, 0.1) / far)), 2)} for x in d]


def solve(T: np.ndarray | None = None, listener_t_ms: list[float] | None = None, front: int | None = None,
          layout: str = "5.1", left: int | None = None) -> dict:
    """Full løsning fra enhetsmålinger (T) og ev. mobilmåling (listener_t_ms).
    MDS kan ikke skille et rom fra speilbildet: «left» (indeks til en høyttaler som står til venstre) avgjør det."""
    D = pairwise(T)
    pos = mds2d(D)
    if listener_t_ms is not None and all(t is not None for t in listener_t_ms):
        L = locate_listener(pos, listener_t_ms)
    else:   # uten mobil: anta lytteren 2,5 m foran snittet av høyttalerne motsatt av «bak»-gruppen – her bare sentroiden
        L = pos.mean(0)
    rel, _ = orient(pos, L, front)
    az = angles(rel)
    if left is not None and az[left] < 0:
        rel = rel * np.array([-1.0, 1.0])
        az = angles(rel)
    return {"positions": [[round(float(x), 3), round(float(y), 3)] for x, y in rel], "listener": [0.0, 0.0],
            "angles": az, "distances": [[round(float(v), 3) for v in row] for row in D],
            "roles": assign_roles(az, layout), "trims": trims_from_positions(rel)}
