"""Lydmåling for maskinvaretestene: generer signaler, spill via Skjold-kjeden (ALSA «default» → dmix → CamillaDSP),
ta opp fra måle-inngangen (loopback-kabel fra DAC/forsterker-utgang til et USB-lydkort), og analyser."""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import wave

import numpy as np

RATE = 48000


def tone(freq: float, secs: float, amp: float = 0.25, ch: str = "LR") -> np.ndarray:
    t = np.arange(int(RATE * secs)) / RATE
    s = amp * np.sin(2 * np.pi * freq * t)
    fade = int(RATE * 0.02)
    s[:fade] *= np.linspace(0, 1, fade)
    s[-fade:] *= np.linspace(1, 0, fade)
    left = s if "L" in ch else np.zeros_like(s)
    right = s if "R" in ch else np.zeros_like(s)
    return np.stack([left, right], axis=1)


def sweep(f0: float = 20, f1: float = 20000, secs: float = 4.0, amp: float = 0.25) -> np.ndarray:
    t = np.arange(int(RATE * secs)) / RATE
    k = np.log(f1 / f0)
    s = amp * np.sin(2 * np.pi * f0 * secs / k * (np.exp(t / secs * k) - 1))
    return np.stack([s, s], axis=1)


def write_wav(path: str, data: np.ndarray) -> None:
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(pcm.shape[1]); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm.tobytes())


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2" if sw == 2 else "<i4").astype(np.float64)
    a /= 32768.0 if sw == 2 else 2147483648.0
    return a.reshape(-1, ch)


def play_and_record(data: np.ndarray, capture: str, play_dev: str = "default", pad: float = 0.6) -> np.ndarray:
    """Spill `data` på play_dev og ta opp fra capture samtidig. Returnerer opptaket (frames × 2)."""
    secs = len(data) / RATE + 2 * pad
    with tempfile.TemporaryDirectory() as td:
        src, rec = os.path.join(td, "src.wav"), os.path.join(td, "rec.wav")
        write_wav(src, data)
        r = subprocess.Popen(["arecord", "-q", "-D", capture, "-f", "S16_LE", "-c", "2", "-r", str(RATE),
                              "-d", str(int(np.ceil(secs))), rec], stderr=subprocess.PIPE)
        time.sleep(pad)
        subprocess.run(["aplay", "-q", "-D", play_dev, src], check=True, timeout=secs + 10)
        _, err = r.communicate(timeout=secs + 10)
        if r.returncode != 0:
            raise RuntimeError("arecord feilet: " + err.decode(errors="replace").strip())
        return read_wav(rec)


def rms_db(x: np.ndarray) -> float:
    return 20 * np.log10(max(np.sqrt(np.mean(np.square(x))), 1e-12))


def active(x: np.ndarray, thresh_db: float = -50) -> np.ndarray:
    """Del av opptaket der signalet faktisk er til stede (fjerner stillhet før/etter)."""
    win = RATE // 100
    n = len(x) // win
    if n == 0:
        return x
    e = np.array([rms_db(x[i * win:(i + 1) * win]) for i in range(n)])
    idx = np.where(e > thresh_db)[0]
    if len(idx) == 0:
        return x[:0]
    a, b = idx[0] * win + RATE // 20, (idx[-1] + 1) * win - RATE // 20
    return x[a:b] if b > a else x[idx[0] * win:(idx[-1] + 1) * win]


def peak_freq(x: np.ndarray) -> float:
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    spec[f < 20] = 0
    return float(f[int(np.argmax(spec))])


def thdn_db(x: np.ndarray, f0: float) -> float:
    """THD+N i dB: alt unntatt grunntonen (±1/6 oktav) relativt til total effekt."""
    w = np.blackman(len(x))
    p = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    band = (f > 20) & (f < 20000)
    fund = band & (f > f0 / 2 ** (1 / 6)) & (f < f0 * 2 ** (1 / 6))
    tot, fp = p[band].sum(), p[fund].sum()
    return 10 * np.log10(max(tot - fp, 1e-20) / max(tot, 1e-20))


def glitches(x: np.ndarray, f0: float, max_jump: float = 0.25) -> int:
    """Teller brå hopp i amplitude-omhylningen (dropouts/klikk) i en jevn tone."""
    win = max(int(RATE / f0 * 4), 64)
    n = len(x) // win
    env = np.array([np.sqrt(np.mean(np.square(x[i * win:(i + 1) * win]))) for i in range(n)])
    if len(env) < 3:
        return 0
    med = np.median(env)
    return int(np.sum(np.abs(np.diff(env)) > max_jump * max(med, 1e-9)))


def band_level_db(x: np.ndarray, lo: float, hi: float) -> float:
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    m = (f >= lo) & (f <= hi)
    return 10 * np.log10(max(p[m].mean(), 1e-30))


def spectrum_png(x: np.ndarray, path: str, title: str = "") -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    p = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    db = 20 * np.log10(np.maximum(p / max(p.max(), 1e-12), 1e-9))
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.semilogx(f[1:], db[1:], lw=0.8)
    ax.set_xlim(20, 20000); ax.set_ylim(-140, 5); ax.grid(True, which="both", alpha=0.3)
    ax.set_xlabel("Hz"); ax.set_ylabel("dBr"); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)
    return True
