"""RTP-lignende lydpakker og jitterbuffer indeksert på ledertid (sekunder)."""
import struct
import numpy as np

HDR = "!4sHIdHH"  # magic, seq, rammenummer, avspillingstid (ledertid), kanaler, rate/100
MAGIC = b"SKAU"
HLEN = struct.calcsize(HDR)


def pack_audio(seq, frame, play_at, pcm, rate=48000):
    pcm = np.asarray(pcm, dtype=np.int16)
    ch = 1 if pcm.ndim == 1 else pcm.shape[1]
    return struct.pack(HDR, MAGIC, seq & 0xFFFF, frame & 0xFFFFFFFF, play_at, ch, rate // 100) + pcm.tobytes()


def unpack_audio(data):
    if len(data) < HLEN or data[:4] != MAGIC:
        return None
    _, seq, frame, play_at, ch, r = struct.unpack(HDR, data[:HLEN])
    pcm = np.frombuffer(data[HLEN:], dtype=np.int16).reshape(-1, ch)
    return {"seq": seq, "frame": frame, "play_at": play_at, "rate": r * 100, "pcm": pcm}


class JitterBuffer:
    """Holder pakker sortert på rammenummer; tapte rammer fylles med stillhet. fetch() resampler asynkront
    (lineær interpolasjon) slik at lokal avspilling følger ledertid selv med klokkedrift."""

    def __init__(self, rate=48000, channels=2, max_s=2.0):
        self.rate, self.ch, self.max = rate, channels, int(max_s * rate)
        self.pk = {}  # frame -> pcm
        self.base = None  # (frame, play_at) for første pakke
        self.lost = 0
        self.dups = 0

    def put(self, p):
        if self.base is None:
            self.base = (p["frame"], p["play_at"])
        if p["frame"] in self.pk:
            self.dups += 1
            return
        self.pk[p["frame"]] = p["pcm"]
        if len(self.pk) > 4096:
            for k in sorted(self.pk)[:-4096]:
                del self.pk[k]

    def frames(self, start, n):
        """Hent n rammer fra rammenummer start (stillhet der pakker mangler)."""
        out = np.zeros((n, self.ch), dtype=np.float32)
        keys = sorted(k for k in self.pk if k + len(self.pk[k]) > start and k < start + n)
        cov = 0
        for k in keys:
            a = self.pk[k].astype(np.float32)
            s0, s1 = max(start, k), min(start + n, k + len(a))
            out[s0 - start:s1 - start] = a[s0 - k:s1 - k, :self.ch]
            cov += s1 - s0
        return out, n - cov

    def fetch(self, leader_t0, n, ratio=1.0):
        """n utgangsrammer som starter ved ledertid leader_t0; ratio = leder-samples per lokal sample (1+drift)."""
        if self.base is None:
            return np.zeros((n, self.ch), dtype=np.float32)
        f0 = self.base[0] + (leader_t0 - self.base[1]) * self.rate
        pos = f0 + np.arange(n) * ratio
        i0 = int(np.floor(pos[0]))
        span = int(np.ceil(pos[-1])) - i0 + 2
        blk, _ = self.frames(i0, span)
        idx = pos - i0
        lo = np.floor(idx).astype(int)
        fr = (idx - lo)[:, None]
        return blk[lo] * (1 - fr) + blk[np.minimum(lo + 1, span - 1)] * fr

    def missing(self, start, n):
        return self.frames(start, n)[1]
