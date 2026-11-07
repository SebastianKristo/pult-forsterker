"""Bass management: automatisk innmåling av trådløs sub mot hovedhøyttalerne.

Delefilteret finnes allerede i synk-motoren (pi/skjold_sync/dspblocks.py): hovedenheten («Har sub») får LR4 høypass,
sub-enheten («Er sub») mono-sum + LR4 lavpass på samme delefrekvens, med fase (0/180°), finjustering (forsinkelse)
og nivå. Denne modulen finner de tre siste automatisk:

1. Sub-enheten settes nøytral (fase 0°, 0 ms, 0 dB).
2. Hovedenheten spiller en sweep (begge kanaler), deretter spiller sub-enheten den samme sweepen i neste tidsluke
   (begge gjennom sine egne delefiltre, altså slik de faktisk låter).
3. Mobilen tar opp der du sitter; vi regner ut impulsresponsen for hver luke.
4. Vi prøver fase 0/180° og forsinkelse 0–20 ms i 0,1 ms-steg på sub-delen, og velger det som gir jevnest
   summert frekvensrespons rundt delefrekvensen (en oktav på hver side). Nivået settes så sub-båndet ligger likt
   med hovedhøyttalernes bånd like over delefrekvensen.

Sub-enheten kan bare forsinkes (ikke hovedenheten). Kommer sub-lyden fram for sent, rapporterer vi hvor mye
hovedenheten burde forsinkes (bruk «Forsinkelse for dette rommet» i synk-motoren på hovedenheten).
"""
import numpy as np

SR = 48000
DELAYS_MS = np.round(np.arange(-20.0, 20.0001, 0.1), 2)   # negativ = hovedenheten må forsinkes


def slot_irs(rec, n: int = 2, sr: int = SR, lead_s: float = 0.5, ir_len_s: float = 0.25):
    """Impulsrespons (med fortegn) per tidsluke fra et mobilopptak av sekvensen hoved → sub."""
    import skjold_placement as pl
    ir = pl.impulse(np.asarray(rec, float), sr)
    out = []
    for a, _b in pl.sequence_signal(n, sr, lead_s):
        i0 = int(a * sr)
        seg = ir[i0:i0 + int(ir_len_s * sr)]
        if len(seg) < int(ir_len_s * sr):
            seg = np.pad(seg, (0, int(ir_len_s * sr) - len(seg)))
        out.append(seg)
    return out


def _band(freqs, f1, f2):
    return (freqs >= f1) & (freqs <= f2)


def _db(x):
    return 20 * np.log10(np.abs(x) + 1e-12)


def analyze(ir_main, ir_sub, xover: float = 80.0, sr: int = SR, nfft: int = 1 << 15) -> dict:
    """Velg fase, forsinkelse og nivå for sub-en. Returnerer også kurver (før/etter) for visning."""
    ir_main, ir_sub = np.asarray(ir_main, float), np.asarray(ir_sub, float)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    M = np.fft.rfft(ir_main, nfft)
    S = np.fft.rfft(ir_sub, nfft)
    lo_band = _band(freqs, max(20.0, xover / 3), xover * 0.7)      # der sub-en dominerer
    hi_band = _band(freqs, xover * 1.5, xover * 3)                  # der hovedhøyttalerne dominerer
    lev_main = float(np.mean(_db(M[hi_band])))
    lev_sub = float(np.mean(_db(S[lo_band])))
    gain_db = float(np.clip(round((lev_main - lev_sub) * 2) / 2, -15, 6))
    g = 10 ** (gain_db / 20)
    eval_band = _band(freqs, xover / 2, xover * 2)
    f_eval = freqs[eval_band]
    Me, Se = M[eval_band], S[eval_band] * g

    def rot(f, phase, d_ms):
        """Relativ forsinkelse: d > 0 forsinker sub-en, d < 0 forsinker hovedhøyttalerne (uttrykt på sub-siden)."""
        return np.exp(-2j * np.pi * f * d_ms / 1000.0) * (-1 if phase == 180 else 1)

    def score(phase, d_ms):
        mag = _db(Me + Se * rot(f_eval, phase, d_ms))
        return float(np.std(mag)), float(np.mean(mag))

    best = None
    for phase in (0, 180):
        for d in DELAYS_MS:
            sd, mean = score(phase, float(d))
            if best is None or sd < best[0] - 1e-9:
                best = (sd, phase, float(d), mean)
    sd0, _ = score(0, 0.0)
    sd, phase, d_rel, _ = best
    d_ms = max(0.0, d_rel)
    main_delay_ms = round(max(0.0, -d_rel), 2)
    t_main = float(np.argmax(np.abs(ir_main)) / sr * 1000)
    t_sub = float(np.argmax(np.abs(ir_sub)) / sr * 1000)

    # kurver for visning, 1/12-oktav, 20–300 Hz
    pts = np.unique(np.round(np.geomspace(20, 300, 60), 1))

    def curve(phase_, d_, g_):
        tot = _db(M + S * g_ * rot(freqs, phase_, d_))
        return [round(float(np.interp(f, freqs, tot)), 2) for f in pts]
    return {"sub_phase": int(phase), "sub_fine_ms": round(d_ms, 2), "sub_level": gain_db,
            "flatness_db": round(sd, 2), "flatness_before_db": round(sd0, 2),
            "main_delay_ms": main_delay_ms, "t_main_ms": round(t_main, 2), "t_sub_ms": round(t_sub, 2),
            "freqs": [float(f) for f in pts], "before": curve(0, 0.0, 1.0), "after": curve(phase, d_rel, g)}


def lr4_sos(fc: float, sr: int = SR, kind: str = "low"):
    """LR4 = to kaskaderte 2.-ordens Butterworth (samme som CamillaDSP LinkwitzRiley order 4). Brukt i tester."""
    from scipy.signal import butter
    sos = butter(2, fc, btype="lowpass" if kind == "low" else "highpass", fs=sr, output="sos")
    return np.vstack([sos, sos])


def _sim(xover=80.0, sub_delay_ms=4.0, invert=False, sub_gain_db=-3.0, sr=SR, n=int(0.25 * SR)):
    """Syntetiske impulsresponser (for tester): hoved = LR4 høypass, sub = LR4 lavpass, forsinket/invertert/dempet."""
    from scipy.signal import sosfilt
    imp = np.zeros(n); imp[100] = 1.0
    main = sosfilt(lr4_sos(xover, sr, "high"), imp)
    sub = sosfilt(lr4_sos(xover, sr, "low"), imp)
    k = int(round(abs(sub_delay_ms) / 1000 * sr))
    if sub_delay_ms >= 0:
        sub = np.concatenate([np.zeros(k), sub])[:n]
    else:
        main = np.concatenate([np.zeros(k), main])[:n]
    return main, sub * (10 ** (sub_gain_db / 20)) * (-1 if invert else 1)


if __name__ == "__main__":   # pragma: no cover
    m, s = _sim()
    print({k: v for k, v in analyze(m, s).items() if not isinstance(v, list)})
