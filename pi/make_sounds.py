#!/usr/bin/env python3
"""Lager talemeldingene i pi/sounds/ på forhånd med Kokoro (engelsk AI-stemme af_heart).
Kjøres på en PC, ikke på Pi-en:  pip install kokoro-onnx soundfile  +  modellfilene fra
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0, så:  python3 make_sounds.py <modellmappe>
Pi-en spiller bare de ferdige WAV-filene (44,1 kHz stereo, 16 bit)."""
import os, subprocess, sys, tempfile
import soundfile as sf
from kokoro_onnx import Kokoro

VOICE, LANG, SPEED = "af_heart", "en-us", 0.95
NUM = ["one", "two", "three", "four", "five", "six"]
PHRASES = {
    "bt_pairing": "Bluetooth pairing. Connect from your phone or computer.",
    "bt_pairing_timeout": "No device connected. Pairing stopped.",
    "bt_connected": "Bluetooth connected.",
    "bt_disconnected": "Bluetooth disconnected.",
    "input_airplay": "AirPlay.",
    "input_bt": "Bluetooth.",
    "input_aux": "Aux input one.",
    "input_aux2": "Aux input two.",
    "input_usb": "USB audio.",
    "input_radio": "Radio.",
    "power_on": "Ready to play.",
    "mix_on": "Mixing on.",
    "mix_off": "Mixing off.",
    "usb_pc_1": "USB switched to computer one.",
    "usb_pc_2": "USB switched to computer two.",
    "headphones_on": "Headphones.",
    "headphones_off": "Speakers.",
}
for i, w in enumerate(NUM, 1):
    PHRASES[f"radio_preset_{i}"] = f"Preset {w}."
    PHRASES[f"radio_saved_{i}"] = f"Saved to preset {w}."
    PHRASES[f"radio_empty_{i}"] = f"Preset {w} is empty. Hold the button to save."

model = sys.argv[1] if len(sys.argv) > 1 else "."
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
os.makedirs(out, exist_ok=True)
k = Kokoro(os.path.join(model, "kokoro-v1.0.onnx"), os.path.join(model, "voices-v1.0.bin"))
only = os.environ.get("ONLY", "")
for key, text in PHRASES.items():
    if only and key not in only.split(","):
        continue
    s, sr = k.create(text, voice=VOICE, speed=SPEED, lang=LANG)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        sf.write(tmp.name, s, sr)
        # 44,1 kHz stereo 16 bit (samme som dmix), litt stille før, myk inn/ut, jevn lydstyrke
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp.name, "-af",
                        "adelay=120,afade=t=in:d=0.02,areverse,afade=t=in:d=0.08,areverse,loudnorm=I=-20:TP=-3:LRA=7,aresample=44100",
                        "-ac", "2", "-sample_fmt", "s16", os.path.join(out, key + ".wav")], check=True)
    print(key, "–", text)
