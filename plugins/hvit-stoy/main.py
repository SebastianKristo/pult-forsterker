"""Hvit støy-generator – skriver 20 s sømløs WAV (16-bit mono 44,1 kHz) og ber Skjold spille den."""
import os
import random
import struct
import wave

RATE = 44100


def samples(color, n, seed=1):
    rnd = random.Random(seed)
    b = [0.0] * 7
    last = 0.0
    out = []
    for _ in range(n):
        w = rnd.uniform(-1, 1)
        if color == "brun":
            last = (last + 0.02 * w) / 1.02
            v = last * 3.5
        elif color == "rosa":   # Paul Kellet sin filtrering
            b[0] = 0.99886 * b[0] + w * 0.0555179; b[1] = 0.99332 * b[1] + w * 0.0750759
            b[2] = 0.96900 * b[2] + w * 0.1538520; b[3] = 0.86650 * b[3] + w * 0.3104856
            b[4] = 0.55000 * b[4] + w * 0.5329522; b[5] = -0.7616 * b[5] - w * 0.0168980
            v = (sum(b[:6]) + b[6] + w * 0.5362) * 0.11
            b[6] = w * 0.115926
        else:
            v = w * 0.5
        out.append(max(-1.0, min(1.0, v)))
    return out


def write(path, color, seconds=20):
    data = samples(color, RATE * seconds)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(v * 30000)) for v in data))


def register(api):
    def play(_data):
        color = api.settings.get("farge") or "rosa"
        path = os.path.join(api.tmpdir(), f"stoy-{color}.wav")
        if not os.path.exists(path):
            write(path, color)
        api.volume(int(api.settings.get("volum") or 15))
        api.play("file://" + os.path.abspath(path), f"{color.capitalize()} støy")
        return path
    api.on("play", play)
    api.on("test", play)
