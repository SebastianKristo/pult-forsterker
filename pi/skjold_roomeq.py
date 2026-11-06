"""Romkorreksjon: analyse av et mikrofonopptak av Skjolds logaritmiske sweep (felles for web, iOS og Android).

Samme metode som web-UI-ets roomeq.ts: spektralforhold opptak/sweep (|R|²/|S|²) i 1/6-oktav (±1/12 oktav rundt hver
frekvens, 24 punkter per oktav fra 20 Hz til 1 kHz), referansenivå = snitt 300–1000 Hz, og inntil 8 peaking-kutt for
topper over 2 dB mellom 40 og 300 Hz (maks −10 dB, Q 1–10). Telefonmikrofoner er unøyaktige under ~40 Hz og over ~10 kHz,
derfor rettes bare bassen.
"""
import io
import math
import struct
import time
import wave

import numpy as np

SR = 48000
F_LO, F_HI = 40.0, 300.0
MAX_CUT, MAX_BOOST, MAX_FILTERS = -10.0, 3.0, 8


def log_sweep(f1=20.0, f2=20000.0, dur=6.0, sr=SR):
    """Identisk med daemonens avspilte sweep (før nivå)."""
    t = np.arange(int(dur * sr)) / sr
    k = math.log(f2 / f1)
    x = np.sin(2 * math.pi * f1 * dur / k * (np.exp(t / dur * k) - 1))
    fade = int(0.05 * sr)
    w = np.ones_like(x)
    w[:fade] = np.linspace(0, 1, fade)
    w[-fade:] = np.linspace(1, 0, fade)
    return (x * w * 0.5).astype("float64")


def log_freqs(f1=20.0, f2=1000.0, per_oct=24):
    out, f = [], f1
    while f <= f2 * 1.0001:
        out.append(f)
        f *= 2 ** (1 / per_oct)
    return np.array(out)


def decode(body: bytes, ctype: str = "", sr_hint: int = SR):
    """WAV (16/24/32-bit PCM eller 32-bit float, mono/stereo) eller rå s16le mono → (float64-array, sr)."""
    if body[:4] == b"RIFF" or "wav" in (ctype or ""):
        try:
            with wave.open(io.BytesIO(body)) as w:
                n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
                raw = w.readframes(n)
            if sw == 2:
                x = np.frombuffer(raw, "<i2").astype("float64") / 32768
            elif sw == 4:
                x = np.frombuffer(raw, "<i4").astype("float64") / 2147483648
            elif sw == 3:
                b = np.frombuffer(raw, "u1").reshape(-1, 3).astype("int32")
                v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
                x = np.where(v & 0x800000, v - 0x1000000, v).astype("float64") / 8388608
            else:
                raise ValueError(f"WAV med {sw * 8}-bit støttes ikke")
            if ch > 1:
                x = x.reshape(-1, ch).mean(axis=1)
            return x, sr
        except wave.Error:
            x = _float_wav(body)
            if x is not None:
                return x
            raise
    if len(body) % 2:
        body = body[:-1]
    return np.frombuffer(body, "<i2").astype("float64") / 32768, int(sr_hint or SR)


def _float_wav(body):
    """wave-modulen kan ikke lese IEEE float (format 3): les «fmt »/«data» selv."""
    try:
        i, ch, sr, bits, fmt, data = 12, 1, SR, 32, 1, None
        while i + 8 <= len(body):
            cid, size = body[i:i + 4], struct.unpack("<I", body[i + 4:i + 8])[0]
            if cid == b"fmt ":
                fmt, ch, sr = struct.unpack("<HHI", body[i + 8:i + 16])
                bits = struct.unpack("<H", body[i + 22:i + 24])[0]
            elif cid == b"data":
                data = body[i + 8:i + 8 + size]
            i += 8 + size + (size & 1)
        if data is None or fmt != 3 or bits != 32:
            return None
        x = np.frombuffer(data[:len(data) // 4 * 4], "<f4").astype("float64")
        if ch > 1:
            x = x[:len(x) // ch * ch].reshape(-1, ch).mean(axis=1)
        return x, sr
    except Exception:
        return None


def _resample(x, sr_from, sr_to):
    if sr_from == sr_to or len(x) == 0:
        return x
    n = int(round(len(x) * sr_to / sr_from))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def response(rec, sweep, sr=SR, freqs=None):
    """dB-respons (1/6-oktav) = 10·log10(Σ|R|² / Σ|S|²) per bånd."""
    freqs = log_freqs() if freqs is None else freqs
    n = 1
    while n < max(len(rec), len(sweep)):
        n <<= 1
    pr = np.abs(np.fft.rfft(rec, n)) ** 2
    ps = np.abs(np.fft.rfft(sweep, n)) ** 2
    hz = sr / n
    db = []
    for f in freqs:
        lo = max(1, int(math.floor(f * 2 ** (-1 / 12) / hz)))
        hi = min(n // 2 - 1, int(math.ceil(f * 2 ** (1 / 12) / hz)))
        db.append(10 * math.log10((pr[lo:hi + 1].sum() + 1e-20) / (ps[lo:hi + 1].sum() + 1e-20)))
    return np.array(db)


def peq_db(f0, q, g, f, sr=SR):
    """RBJ peaking-filter: forsterkning i dB ved frekvens f (array eller tall)."""
    A = 10 ** (g / 40)
    w0 = 2 * math.pi * f0 / sr
    al = math.sin(w0) / (2 * q)
    b0, b1, b2 = 1 + al * A, -2 * math.cos(w0), 1 - al * A
    a0, a1, a2 = 1 + al / A, b1, 1 - al / A
    w = 2 * np.pi * np.asarray(f, dtype="float64") / sr
    c1, c2, s1, s2 = np.cos(w), np.cos(2 * w), np.sin(w), np.sin(2 * w)
    nr, ni = b0 + b1 * c1 + b2 * c2, -(b1 * s1 + b2 * s2)
    dr, di = a0 + a1 * c1 + a2 * c2, -(a1 * s1 + a2 * s2)
    return 10 * np.log10((nr * nr + ni * ni) / (dr * dr + di * di))


def suggest(freqs, db, max_filters=MAX_FILTERS):
    """Inntil 8 kutt for topper > 2 dB over referansen (snitt 300–1000 Hz) mellom 40 og 300 Hz."""
    ref = db[(freqs >= 300) & (freqs <= 1000)]
    target = float(ref.mean()) if len(ref) else 0.0
    err = db - target
    filters = []
    band = (freqs >= F_LO) & (freqs <= F_HI)
    for _ in range(max_filters):
        cand = np.where(band & (err > 2))[0]
        if not len(cand):
            break
        bi = int(cand[np.argmax(err[cand])])
        bv = float(err[bi])
        half = bv / 2
        lo = hi = bi
        while lo > 0 and err[lo - 1] > half:
            lo -= 1
        while hi < len(freqs) - 1 and err[hi + 1] > half:
            hi += 1
        f0 = float(freqs[bi])
        bw = max(float(freqs[hi] - freqs[lo]), f0 / 15)
        p = {"f": round(f0, 1), "q": round(max(1.0, min(10.0, f0 / bw)), 2), "g": -round(min(-MAX_CUT, bv), 1)}
        filters.append(p)
        err = err + peq_db(p["f"], p["q"], p["g"], freqs)
    after = db + sum((peq_db(p["f"], p["q"], p["g"], freqs) for p in filters), np.zeros_like(db))
    return filters, target, after


def analyze_curves(curves):
    """Snitt av flere målepunkter (dB) → forslag."""
    freqs = log_freqs()
    db = np.mean(np.array(curves), axis=0)
    filters, target, after = suggest(freqs, db)
    for p in filters:   # samme grenser som daemonen håndhever ved lagring
        p["g"] = max(MAX_CUT, min(MAX_BOOST, p["g"]))
    return {
        "curve": [{"f": round(float(f), 2), "db": round(float(d - target), 2)} for f, d in zip(freqs, db)],
        "after": [{"f": round(float(f), 2), "db": round(float(d - target), 2)} for f, d in zip(freqs, after)],
        "filters": filters, "target": round(target, 2), "points": len(curves),
        "range": [F_LO, F_HI],
    }


class Sessions:
    """Målepunkter per økt (session-id fra klienten), glemmes etter 30 min."""

    def __init__(self, ttl=1800):
        self.ttl, self.d = ttl, {}

    def add(self, sid, curve):
        now = time.time()
        self.d = {k: v for k, v in self.d.items() if now - v["t"] < self.ttl}
        s = self.d.setdefault(sid or "default", {"t": now, "curves": []})
        s["t"] = now
        s["curves"] = (s["curves"] + [list(curve)])[-8:]
        return s["curves"]

    def reset(self, sid):
        self.d.pop(sid or "default", None)


SESSIONS = Sessions()


def analyze(body, ctype="", sr_hint=SR, session="", reset=False, sweep_kw=None):
    """Hovedinngang: opptak (WAV/PCM) → kurve for dette punktet, lagt til økten, og forslag for snittet."""
    x, sr = decode(body, ctype, sr_hint)
    if len(x) < sr * 2:
        raise ValueError("opptaket er for kort (minst 2 s, helst hele sweepen på 6 s + 1 s før)")
    x = _resample(x, sr, SR)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak < 1e-3:
        raise ValueError("opptaket er stille – ga appen mikrofontilgang, og spilte Skjold sweepen?")
    sweep = log_sweep(**(sweep_kw or {}))
    db = response(x, sweep)
    if reset:
        SESSIONS.reset(session)
    curves = SESSIONS.add(session, db)
    out = analyze_curves(curves)
    out["clipped"] = peak > 0.98
    out["point"] = [{"f": round(float(f), 2), "db": round(float(d), 2)} for f, d in zip(log_freqs(), db)]
    return out
