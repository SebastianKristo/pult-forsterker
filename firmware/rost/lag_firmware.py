#!/usr/bin/env python3
"""Bygger én flashbar fastvarefil for Skjold Røst: skjold-rost-firmware.bin (skrives til adresse 0x0).

Innhold:
  * squeezelite-esp32 for ESP32-S3 (ferdig bygg fra sle118/squeezelite-esp32, låst versjon + sha256)
  * Skjold-oppsettet som en ferdig NVS-partisjon («settings», navnerom «config»), så lyd, skjerm, dreieknapp og
    knapper virker uten at noe må tastes inn i NVS-editoren.

Bruk:
  python3 firmware/rost/lag_firmware.py [--ut DIR] [--zip FIL]      # laster ned upstream-bygget selv
Krever: pip install esptool esp-idf-nvs-partition-gen

Nøklene under er kontrollert mot kildekoden til squeezelite-esp32 (master-v4.3): navnene leses med
config_alloc_get(NVS_TYPE_STR, "<nøkkel>") og verdiene tolkes med PARSE_PARAM (atoi → bare desimaltall).
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

# ---------- upstream (låst) ----------
UPSTREAM_TAG = "S3-i2s.16.1779.master-v4.3"
UPSTREAM_ZIP = "squeezelite-esp32-master-v4.3-S3-i2s-16-21779.zip"
UPSTREAM_URL = f"https://github.com/sle118/squeezelite-esp32/releases/download/{UPSTREAM_TAG}/{UPSTREAM_ZIP}"
UPSTREAM_SHA256 = "188a85c17601c9c191ae3b407d45e28118f32b327da9113d39216f7f2e284048"

# Partisjonstabellen i bygget (partition-table.bin): settings = NVS på 0x3F0000, 0x10000 byte.
SETTINGS_OFFSET = 0x3F0000
SETTINGS_SIZE = 0x10000
NAMESPACE = "config"

# ---------- maskinvare (samme som koblingstabellen i kabinett/rost/LES_MEG.md) ----------
PINS = {
    "i2s_bck": 4, "i2s_ws": 5, "i2s_do": 6,      # PCM5102A
    "amp": 7,                                     # TPA3118 SDZ (høy = forsterker på)
    "oled_sda": 11, "oled_scl": 12,               # 2,42″ SSD1309 på I²C
    "btn_power": 8, "btn_1": 9, "btn_2": 18, "btn_3": 39, "btn_4": 47,
    "enc_a": 15, "enc_b": 16, "enc_sw": 17,
}
NAME = "Skjold-Rost"          # ASCII: nettverksnavn, Wi-Fi-oppsett og spillernavn (Skjold viser «Skjold Røst»)


def buttons():
    def b(gpio, action):
        return {"gpio": gpio, "type": "BUTTON_LOW", "pull": True, "debounce": 30, "normal": {"pressed": action}}
    power = b(PINS["btn_power"], "ACTRLS_POWER")          # LMS «button power»: av/på (forsterkeren følger, se set_GPIO)
    # Langt trykk (1,5 s) på ⏻ = dusj-modus: sender preset 5 (BCTRLS_PS5 → LMS «preset_5.single»). Skjold legger
    # dusj-favoritten på preset 5 og slår høyttaleren av etter valgt tid (pi/skjold_rost.py, Dusj).
    power.update({"long_press": 1500, "longpress": {"pressed": "BCTRLS_PS5"}})
    return [power,
            b(PINS["btn_1"], "BCTRLS_PS1"), b(PINS["btn_2"], "BCTRLS_PS2"),   # LMS «button preset_N.single»
            b(PINS["btn_3"], "BCTRLS_PS3"), b(PINS["btn_4"], "BCTRLS_PS4")]


def config():
    p = PINS
    return {
        # lyd: generisk I²S-DAC (PCM5102A trenger ingen I²C-oppsett)
        "dac_config": f"model=I2S,bck={p['i2s_bck']},ws={p['i2s_ws']},do={p['i2s_do']}",
        # forsterker på når det spilles, av etter -C 30 s stillhet (og når spilleren slås av i Lyrion)
        "set_GPIO": f"{p['amp']}=amp",
        "autoexec1": f"squeezelite -o I2S -b 500:2000 -C 30 -W -n {NAME}",
        # skjerm: SSD1309 128×64 er registerkompatibel med SSD1306. Adressen utelates med vilje: PARSE_PARAM bruker
        # atoi(), så «address=0x3C» ville blitt 0 – standard er 0x3C.
        "i2c_config": f"sda={p['oled_sda']},scl={p['oled_scl']},port=0,speed=400000",
        "display_config": "I2C,width=128,height=64,driver=SSD1306",
        "metadata_config": "format=%artist% - %title%",
        # dreieknapp: alltid volum, trykk = spill/pause, langt trykk bytter til forrige/neste
        "rotary_config": f"A={p['enc_a']},B={p['enc_b']},SW={p['enc_sw']},volume,longpress",
        "actrls_config": "knapper",
        "knapper": json.dumps(buttons(), separators=(",", ":")),
        "lms_ctrls_raw": "n",
        # navn
        "host_name": NAME,
        "ap_ssid": NAME,
        "airplay_name": NAME,
        "cspot_config": json.dumps({"deviceName": NAME, "bitrate": 160}, separators=(",", ":")),
    }


def nvs_csv(cfg):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["key", "type", "encoding", "value"])
    w.writerow([NAMESPACE, "namespace", "", ""])
    for k, v in cfg.items():
        w.writerow([k, "data", "string", v])
    return out.getvalue()


def fetch_upstream(path=None):
    if not path:
        path = os.path.join(tempfile.mkdtemp(prefix="sqz-"), UPSTREAM_ZIP)
        with urllib.request.urlopen(UPSTREAM_URL, timeout=120) as r, open(path, "wb") as f:
            shutil.copyfileobj(r, f)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if h != UPSTREAM_SHA256:
        sys.exit(f"Feil sha256 for {UPSTREAM_ZIP}: {h} (forventet {UPSTREAM_SHA256})")
    return path


def build(ut, zip_path=None):
    os.makedirs(ut, exist_ok=True)
    work = tempfile.mkdtemp(prefix="rostfw-")
    zipfile.ZipFile(fetch_upstream(zip_path)).extractall(work)
    b = os.path.join(work, "build")
    args = open(os.path.join(b, "flash_project_args")).read().split()
    flash_opts, parts = args[:6], args[6:]           # --flash_mode dio --flash_freq 80m --flash_size 8MB, så adresse/fil
    csv_path = os.path.join(ut, "skjold-rost-nvs.csv")
    open(csv_path, "w").write(nvs_csv(config()))
    nvs_bin = os.path.join(work, "skjold-nvs.bin")
    subprocess.run([sys.executable, "-m", "esp_idf_nvs_partition_gen", "generate", csv_path, nvs_bin, hex(SETTINGS_SIZE)],
                   check=True, stdout=subprocess.DEVNULL)
    pairs = [x for i in range(0, len(parts), 2) for x in (parts[i], os.path.join(b, parts[i + 1]))]
    pairs += [hex(SETTINGS_OFFSET), nvs_bin]
    out = os.path.join(ut, "skjold-rost-firmware.bin")
    subprocess.run([sys.executable, "-m", "esptool", "--chip", "esp32s3", "merge_bin", "-o", out, *flash_opts, *pairs],
                   check=True, stdout=subprocess.DEVNULL)
    manifest = {"name": "Skjold Røst", "version": UPSTREAM_TAG, "new_install_prompt_erase": True,
                "builds": [{"chipFamily": "ESP32-S3", "parts": [{"path": "skjold-rost-firmware.bin", "offset": 0}]}]}
    json.dump(manifest, open(os.path.join(ut, "manifest.json"), "w"), ensure_ascii=False, indent=2)
    shutil.rmtree(work, ignore_errors=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ut", default="ut")
    ap.add_argument("--zip", help="lokal kopi av upstream-zip (sjekkes mot sha256)")
    a = ap.parse_args()
    f = build(a.ut, a.zip)
    print(f"{f}  {os.path.getsize(f)} byte  sha256 {hashlib.sha256(open(f, 'rb').read()).hexdigest()}")
