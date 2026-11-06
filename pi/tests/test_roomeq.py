"""Romkorreksjon: syntetisk rom (sweep gjennom en resonans) skal gi et kutt ved resonansfrekvensen."""
import io
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_roomeq as rq  # noqa: E402


def _biquad_peak(x, f0, q, g, sr=48000):
    A = 10 ** (g / 40); w0 = 2 * np.pi * f0 / sr; al = np.sin(w0) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A]); a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    b, a = b / a[0], a / a[0]
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b[0] * v + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def _room(f0=80.0, gain=9.0, noise=0.002, seed=0):
    sw = rq.log_sweep()
    y = _biquad_peak(sw, f0, 4.0, gain) * 0.6
    rec = np.concatenate([np.zeros(48000), y, np.zeros(24000)])
    rec += np.random.default_rng(seed).normal(0, noise, len(rec))
    return rec


def _wav(x, sr=48000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return b.getvalue()


def test_cut_hits_resonance():
    out = rq.analyze(_wav(_room()), "audio/wav", session="t1", reset=True)
    assert out["points"] == 1 and out["filters"]
    top = min(out["filters"], key=lambda p: p["g"])
    assert 70 <= top["f"] <= 92, top
    assert -10 <= top["g"] <= -5
    assert all(40 <= p["f"] <= 300 and p["g"] >= -10 for p in out["filters"])
    after = {round(c["f"]): c["db"] for c in out["after"]}
    near = [d for f, d in after.items() if 70 <= f <= 92]
    assert max(near) < 3.5


def test_flat_room_no_filters_and_raw_pcm_and_resample():
    sw = rq.log_sweep() * 0.6
    rec = np.concatenate([np.zeros(44100), np.interp(np.linspace(0, len(sw) - 1, int(len(sw) * 44100 / 48000)), np.arange(len(sw)), sw)])
    pcm = (rec * 32767).astype("<i2").tobytes()
    out = rq.analyze(pcm, "application/octet-stream", sr_hint=44100, session="t2", reset=True)
    assert out["filters"] == []


def test_points_are_averaged():
    rq.analyze(_wav(_room(seed=1)), session="t3", reset=True)
    out = rq.analyze(_wav(_room(gain=3.0, seed=2)), session="t3")
    assert out["points"] == 2
    top = min(out["filters"], key=lambda p: p["g"])
    assert -8 < top["g"] < -2   # snitt av +9 og +3 dB


def test_silent_recording_rejected():
    try:
        rq.analyze(_wav(np.zeros(48000 * 7)), session="t4", reset=True)
    except ValueError as e:
        assert "stille" in str(e)
    else:
        raise AssertionError("stille opptak skulle feile")
