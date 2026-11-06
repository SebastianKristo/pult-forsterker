"""Skjold Sertifisert: måling og EQ-profiler for passive tredjepartshøyttalere.

Flyt
  1. Skjold spiller samme logaritmiske sweep som romkorreksjonen (POST /api/roomeq/sweep).
  2. Mikrofonen tar opp: nærfelt (1–3 cm foran basselementet, gyldig < ~400 Hz) og/eller kvasi-anekoisk (≈ 1 m på
     aksen, gated: vinduet stenges før første refleksjon kommer, gyldig over ~1/gate).
  3. Impulsresponsen hentes ut ved dekonvolusjon (Farinas inversfilter), gates, og blir en kurve i 1/12-oktav.
     Nærfelt og gated skjøtes ved SPLICE_HZ med nivåtilpasning.
  4. Kalibreringsfil for mikrofonen (UMIK/miniDSP-format «frekvens dB», eller innebygde forhåndsvalg) trekkes fra.
  5. EQ-profilen er inntil 10 PEQ-filtre (RBJ peaking) mot en målkurve, maks +3 dB løft og −12 dB kutt.
  6. Kvalitetsscore 0–100 (signal/støy, klipping, dekning, samsvar mellom gjentatte målinger).

Profilene deles anonymt i Skjold Cloud (skjold/sky, /hoyttaler/*). Skyen tar medianen av innsendingene, og en modell
blir «Skjold Sertifisert» når minst 3 uavhengige målinger stemmer innen 2 dB (RMS, 100 Hz–10 kHz) og snittscoren ≥ 70.
Samme regel ligger i `certify()` her, så klient og sky er enige.

DSP: filtrene legges i CamillaDSP-kjeden etter brukerens EQ. Når romkorreksjonen er på, eier den bassen: høyttaler-
filtre under 300 Hz droppes da, så de to aldri retter det samme.
"""
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request

import numpy as np

import skjold_roomeq as rq

SR = rq.SR
SPLICE_HZ = 300.0
MAX_BOOST, MAX_CUT, MAX_FILTERS = 3.0, -12.0, 10
FIT_LO, FIT_HI = 60.0, 16000.0
ROOMEQ_OWNS_BELOW = 300.0
CACHE_FILE = os.environ.get("SKJOLD_SPEAKER_CACHE", "/var/lib/ki-amp/speakerprofiles.json")

# Mikrofonforhåndsvalg (grove, offentlig kjente tendenser; en ekte kalibreringsfil er alltid bedre)
MIC_PRESETS = {
    "flat": [],
    "iphone": [(20, -12), (50, -5), (100, -1.5), (200, 0), (5000, 0), (8000, 1.5), (12000, -2), (16000, -8), (20000, -15)],
    "android": [(20, -14), (50, -7), (100, -2.5), (200, 0), (4000, 0), (7000, 2), (11000, -3), (16000, -10), (20000, -18)],
    "s1": [(20, -6), (40, -2), (80, 0), (10000, 0), (16000, -2), (20000, -6)],
}

TARGETS = {
    "flat": lambda f: np.zeros_like(f),
    # svakt fallende (≈ −1 dB per dekade over 1 kHz) – mindre skarp på lyse høyttalere
    "varm": lambda f: -np.clip(np.log10(np.maximum(f, 1000) / 1000), 0, None) * 1.0,
    # litt løft i bassen (+2 dB hylle under 120 Hz)
    "bass": lambda f: 2.0 / (1 + (f / 120.0) ** 2),
}


def freqs(per_oct=12, f1=20.0, f2=20000.0):
    return rq.log_freqs(f1, f2, per_oct)


# ---------------- måling ----------------
def inverse_sweep(sweep, f1=20.0, f2=20000.0, sr=SR):
    """Farinas inversfilter: tidsreversert sweep med −6 dB/oktav amplitudekorreksjon."""
    t = np.arange(len(sweep)) / sr
    dur = len(sweep) / sr
    env = np.exp(-t / dur * math.log(f2 / f1))
    return sweep[::-1] * env


def impulse(rec, sweep, sr=SR):
    n = 1
    while n < len(rec) + len(sweep):
        n <<= 1
    inv = inverse_sweep(sweep, sr=sr)
    h = np.fft.irfft(np.fft.rfft(rec, n) * np.fft.rfft(inv, n), n)
    return h


def gated_response(h, sr=SR, gate_ms=5.0, pre_ms=1.0, per_oct=12):
    """Hent topp, vindu [topp−pre, topp+gate] med halv-Hann i bakkant → (freqs, dB, gyldig fra Hz)."""
    pk = int(np.argmax(np.abs(h)))
    a = max(0, pk - int(pre_ms * sr / 1000))
    b = min(len(h), pk + int(gate_ms * sr / 1000))
    seg = h[a:b].astype("float64").copy()
    fade = max(4, len(seg) // 4)
    seg[-fade:] *= np.hanning(2 * fade)[fade:]
    return _spectrum(seg, sr, per_oct), 1000.0 / gate_ms


def _spectrum(seg, sr, per_oct):
    fr = freqs(per_oct)
    n = 1 << 16
    mag = np.abs(np.fft.rfft(seg, n)) ** 2
    hz = sr / n
    out = []
    for f in fr:
        lo = max(1, int(f * 2 ** (-1 / (2 * per_oct)) / hz))
        hi = min(len(mag) - 1, max(lo, int(math.ceil(f * 2 ** (1 / (2 * per_oct)) / hz))))
        out.append(10 * math.log10(mag[lo:hi + 1].mean() + 1e-20))
    return fr, np.array(out)


def snr_db(x, sr=SR):
    """Støygulv (stilleste 200 ms) mot signal (høyeste 200 ms-blokk)."""
    blk = int(0.2 * sr)
    if len(x) < 2 * blk:
        return 0.0
    rms = [float(np.sqrt(np.mean(x[i:i + blk] ** 2)) + 1e-12) for i in range(0, len(x) - blk, blk)]
    return 20 * math.log10(max(rms) / min(rms))


def parse_calibration(text):
    """UMIK/miniDSP/REW-format: linjer «frekvens dB [fase]»; kommentarer med * eller " ignoreres."""
    pts = []
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line or line[0] in "*\"#;" or line.lower().startswith("sens"):
            continue
        p = line.replace(",", " ").replace("\t", " ").split()
        try:
            f, d = float(p[0]), float(p[1])
        except (ValueError, IndexError):
            continue
        if 1 <= f <= 40000:
            pts.append((f, d))
    return sorted(pts)


def calibration_curve(fr, cal):
    if not cal:
        return np.zeros_like(fr)
    cf = np.log10([c[0] for c in cal])
    cd = np.array([c[1] for c in cal], dtype="float64")
    return np.interp(np.log10(fr), cf, cd)


def measure(body, ctype="", sr_hint=SR, mode="gated", gate_ms=5.0, mic="flat", calibration=""):
    """Ett opptak → {freqs, db, valid:[lo,hi], snr, clipped, mode}."""
    x, sr = rq.decode(body, ctype, sr_hint)
    x = rq._resample(x, sr, SR)
    if len(x) < SR * 2:
        raise ValueError("opptaket er for kort (minst 2 s, helst hele sweepen + 1 s før)")
    peak = float(np.max(np.abs(x)))
    if peak < 1e-3:
        raise ValueError("opptaket er stille – har mikrofonen tilgang, og spilte Skjold sweepen?")
    h = impulse(x, rq.log_sweep())
    if mode == "near":
        (fr, db), _ = gated_response(h, gate_ms=40.0)
        valid = [20.0, 400.0]
    else:
        (fr, db), lo = gated_response(h, gate_ms=max(2.0, min(20.0, gate_ms)))
        valid = [max(lo, 100.0), 20000.0]
    cal = parse_calibration(calibration) if calibration else MIC_PRESETS.get(mic, [])
    db = db - calibration_curve(fr, cal)
    return {"freqs": fr, "db": db, "valid": valid, "snr": round(snr_db(x), 1), "clipped": peak > 0.98, "mode": mode}


def splice(near, far, at=SPLICE_HZ):
    """Skjøt nærfelt (under `at`) og gated (over) med nivåtilpasning i oktaven rundt skjøten."""
    fr = far["freqs"]
    band = (fr >= at / 1.41) & (fr <= at * 1.41)
    off = float(np.mean(far["db"][band]) - np.mean(near["db"][band])) if band.any() else 0.0
    w = np.clip((np.log2(fr / at) + 0.5), 0, 1)   # glidende over en oktav
    db = (1 - w) * (near["db"] + off) + w * far["db"]
    return {"freqs": fr, "db": db, "valid": [near["valid"][0], far["valid"][1]],
            "snr": min(near["snr"], far["snr"]), "clipped": near["clipped"] or far["clipped"], "mode": "splice"}


def normalize(fr, db, lo=300.0, hi=3000.0):
    m = (fr >= lo) & (fr <= hi)
    return db - (float(np.mean(db[m])) if m.any() else 0.0)


def smooth(fr, db, oct_frac=6):
    out = np.empty_like(db)
    lf = np.log2(fr)
    for i in range(len(fr)):
        m = np.abs(lf - lf[i]) <= 1 / (2 * oct_frac)
        out[i] = 10 * np.log10(np.mean(10 ** (db[m] / 10)))
    return out


# ---------------- profil ----------------
def fit_peq(fr, db, target="flat", lo=FIT_LO, hi=FIT_HI, max_filters=MAX_FILTERS, max_boost=MAX_BOOST, max_cut=MAX_CUT):
    """Grådig tilpasning: største avvik (bredest først gjennom glatting) → ett peaking-filter, gjenta."""
    tgt = TARGETS.get(target, TARGETS["flat"])(fr)
    err = smooth(fr, normalize(fr, db)) - tgt
    band = (fr >= lo) & (fr <= hi)
    filters = []
    for _ in range(max_filters):
        e = np.where(band, err, 0.0)
        i = int(np.argmax(np.abs(e)))
        v = float(e[i])
        if abs(v) < 1.0:
            break
        half = v / 2
        a = b = i
        while a > 0 and band[a - 1] and (e[a - 1] - half) * np.sign(v) > 0:
            a -= 1
        while b < len(fr) - 1 and band[b + 1] and (e[b + 1] - half) * np.sign(v) > 0:
            b += 1
        f0 = float(fr[i])
        bw = max(float(fr[b] - fr[a]), f0 / 12)
        g = max(max_cut, min(max_boost, -v))
        p = {"f": round(f0, 1), "q": round(max(0.5, min(8.0, f0 / bw)), 2), "g": round(g, 1)}
        if abs(p["g"]) < 0.5:
            band[i] = False
            continue
        filters.append(p)
        err = err + rq.peq_db(p["f"], p["q"], p["g"], fr)
    return filters, err


def quality(meas, repeat_rms=None):
    """0–100: SNR (40 p), ikke klippet (15 p), dekning (25 p), samsvar mellom gjentak (20 p)."""
    s = min(40.0, max(0.0, (meas.get("snr", 0) - 15) * 40 / 35))
    s += 0 if meas.get("clipped") else 15
    lo, hi = meas.get("valid", [20000, 20000])
    s += 25 * min(1.0, max(0.0, math.log2(max(hi, 1) / max(lo, 1)) / math.log2(20000 / 60)))
    s += 20 if repeat_rms is None else max(0.0, 20 - 10 * max(0.0, repeat_rms - 0.5))
    return int(round(s))


def rms_diff(fr, a, b, lo=100.0, hi=10000.0):
    m = (fr >= lo) & (fr <= hi)
    return float(np.sqrt(np.mean((normalize(fr, a) - normalize(fr, b))[m] ** 2)))


def power_hint(sensitivity=None, impedance=None):
    """Råd for S1 (2×50 W i 4 Ω / 2×30 W i 8 Ω): følsomhet og impedans → anbefalt maksvolum og advarsler."""
    out = {"warnings": []}
    if impedance:
        if impedance < 4:
            out["warnings"].append("Under 4 Ω: S1 kan bli varm – hold volumet under 70 % og sørg for luft rundt.")
        out["watts"] = 50 if impedance <= 5 else 30
    if sensitivity:
        w = out.get("watts", 30)
        out["max_spl"] = round(sensitivity + 10 * math.log10(w), 1)
        if sensitivity < 84:
            out["warnings"].append("Lav følsomhet: forvent lite reserve ved høyt volum; unngå store bassløft.")
    return out


def build_profile(measurements, brand, model, target="flat", sensitivity=None, impedance=None):
    """Flere målinger (dict fra measure/splice) → profil klar til DSP og innsending."""
    if not measurements:
        raise ValueError("ingen målinger")
    fr = measurements[0]["freqs"]
    curves = [normalize(fr, m["db"]) for m in measurements]
    db = np.median(np.array(curves), axis=0)
    rep = None
    if len(curves) > 1:
        rep = float(np.mean([rms_diff(fr, c, db) for c in curves]))
    filters, after = fit_peq(fr, db, target)
    valid = [max(m["valid"][0] for m in measurements), min(m["valid"][1] for m in measurements)]
    score = min(quality(m, rep) for m in measurements)
    return {
        "brand": str(brand or "").strip()[:60], "model": str(model or "").strip()[:80], "target": target,
        "curve": [{"f": round(float(f), 1), "db": round(float(d), 2)} for f, d in zip(fr, db)],
        "after": [{"f": round(float(f), 1), "db": round(float(d), 2)} for f, d in zip(fr, after)],
        "filters": filters, "valid": [round(valid[0]), round(valid[1])], "score": score,
        "points": len(measurements), "sensitivity": sensitivity, "impedance": impedance,
        "hint": power_hint(sensitivity, impedance), "measured": time.strftime("%Y-%m-%d"),
    }


def profile_from_curve(curve, target="flat"):
    """Kurve fra skyen ([{f,db}]) → filtre (skyen lagrer bare kurver; tilpasning skjer lokalt)."""
    fr = np.array([float(c["f"]) for c in curve])
    db = np.array([float(c["db"]) for c in curve])
    filters, after = fit_peq(fr, db, target)
    return filters, [{"f": round(float(f), 1), "db": round(float(d), 2)} for f, d in zip(fr, after)]


def certify(submissions, min_n=3, max_rms=2.0, min_score=70):
    """Samme regel som skyen: ≥3 uavhengige innsendinger som stemmer innen 2 dB av medianen, snittscore ≥ 70."""
    subs = [s for s in submissions if s.get("curve")]
    if len(subs) < min_n:
        return {"certified": False, "agree": 0, "n": len(subs)}
    fr = np.array([c["f"] for c in subs[0]["curve"]])
    cs = np.array([[c["db"] for c in s["curve"]] for s in subs])
    med = np.median(cs, axis=0)
    ok = [s for s, c in zip(subs, cs) if rms_diff(fr, c, med) <= max_rms]
    srcs = {s.get("source") or id(s) for s in ok}
    score = float(np.mean([s.get("score", 0) for s in ok])) if ok else 0.0
    return {"certified": len(srcs) >= min_n and score >= min_score, "agree": len(srcs), "n": len(subs), "score": round(score)}


# ---------------- DSP ----------------
def dsp_filters(profile, roomeq_on=False):
    """Profilens filtre → [(f, q, g)]; under 300 Hz eier romkorreksjonen bassen når den er på."""
    out = []
    for p in (profile or {}).get("filters") or []:
        try:
            f, q, g = float(p["f"]), float(p.get("q", 1)), float(p["g"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (20 <= f <= 20000 and 0.3 <= q <= 15):
            continue
        if roomeq_on and f < ROOMEQ_OWNS_BELOW:
            continue
        out.append((round(f, 1), round(q, 2), max(MAX_CUT, min(MAX_BOOST, g))))
    return out[:MAX_FILTERS]


# ---------------- sky + cache ----------------
class Store:
    """Lokal cache av profiler fra skyen (fungerer offline), og klient mot /hoyttaler/* i Skjold Cloud."""

    def __init__(self, base, path=CACHE_FILE, opener=None, timeout=8):
        self.base, self.path, self.timeout = base.rstrip("/"), path, timeout
        self._open = opener or urllib.request.urlopen
        try:
            with open(path) as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.cache, f)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", "User-Agent": "Skjold/2.0"})
        with self._open(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode() or "null")

    def search(self, q):
        try:
            res = self._req("GET", "/hoyttaler/sok?q=" + urllib.parse.quote(str(q or "")[:80]))
            return {"results": res.get("treff", []), "offline": False}
        except Exception:
            ql = str(q or "").lower()
            hits = [{"id": k, "merke": v.get("merke"), "modell": v.get("modell"), "antall": v.get("antall", 1),
                     "sertifisert": v.get("sertifisert", False), "score": v.get("score")}
                    for k, v in self.cache.items() if ql in f"{v.get('merke', '')} {v.get('modell', '')}".lower()]
            return {"results": hits, "offline": True}

    def get(self, pid):
        try:
            p = self._req("GET", "/hoyttaler/profil/" + urllib.parse.quote(pid))
            self.cache[pid] = p
            self._save()
            return p
        except Exception:
            if pid in self.cache:
                return {**self.cache[pid], "offline": True}
            raise

    def submit(self, profile, source):
        body = {"merke": profile["brand"], "modell": profile["model"], "kurve": profile["curve"],
                "score": profile["score"], "gyldig": profile["valid"], "kilde": hashlib.sha256(source.encode()).hexdigest()[:16],
                "folsomhet": profile.get("sensitivity"), "impedans": profile.get("impedance")}
        return self._req("POST", "/hoyttaler/send", body)

    def flag(self, pid, reason):
        return self._req("POST", "/hoyttaler/flagg", {"id": pid, "grunn": str(reason or "")[:200]})
