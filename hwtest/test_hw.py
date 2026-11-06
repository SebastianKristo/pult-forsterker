"""Maskinvaretester for Skjold. Kjøres på en ekte enhet (self-hosted runner) mot den installerte daemonen.

Miljøvariabler:
  SKJOLD_URL          daemonens adresse (standard http://127.0.0.1:8765)
  HWTEST_CAPTURE      ALSA-enhet for måle-inngangen (loopback-kabel fra utgangen), f.eks. «plughw:CARD=CODEC,DEV=0».
                      Ikke satt → lydmålingene hoppes over.
  HWTEST_PLAY         ALSA-enhet testsignalene spilles på (standard «default» = dmix → CamillaDSP, samme vei som AirPlay)
  HWTEST_RADIO_URL    stabil radiostrøm (standard NRK P1 MP3)
  HWTEST_EXPECT       forventet release-tag (f.eks. skjold-v0.1.50) – sjekkes mot /api/update
  HWTEST_SERVICES     kommaseparert liste over systemd-tjenester som skal være aktive (standard: se SERVICES)
  HWTEST_OUT          mappe for opptak/plott (standard hwtest-out)
  HWTEST_RESTART=1    restart ki-amp og mål oppstartstid (krever sudo uten passord)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

import numpy as np
import pytest

import audio

BASE = os.environ.get("SKJOLD_URL", "http://127.0.0.1:8765").rstrip("/")
CAPTURE = os.environ.get("HWTEST_CAPTURE", "").strip()
PLAY = os.environ.get("HWTEST_PLAY", "default")
RADIO = os.environ.get("HWTEST_RADIO_URL", "http://lyd.nrk.no/nrk_radio_p1_ostlandssendingen_mp3_h")
OUT = os.environ.get("HWTEST_OUT", "hwtest-out")
SERVICES = [s for s in os.environ.get("HWTEST_SERVICES", "ki-amp,camilladsp,shairport-sync,ki-squeezelite,nqptp").split(",") if s]
os.makedirs(OUT, exist_ok=True)

needs_audio = pytest.mark.skipif(not CAPTURE or not shutil.which("arecord"), reason="ingen måle-inngang (HWTEST_CAPTURE) / arecord")
needs_systemd = pytest.mark.skipif(not shutil.which("systemctl") or not os.path.isdir("/run/systemd/system"), reason="ikke systemd")


# ---------- hjelpere ----------
def http(method: str, path: str, body=None, timeout: float = 8.0, raw: bool = False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
        return (r.status, r.headers.get("Content-Type", ""), b) if raw else json.loads(b or b"{}")


def get(path, **kw):
    return http("GET", path, **kw)


def post(path, body=None, **kw):
    return http("POST", path, body if body is not None else {}, **kw)


def wait_for(fn, timeout: float, every: float = 0.5, what: str = "betingelse"):
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        try:
            v = fn()
            if v:
                return v
        except Exception as e:  # noqa: BLE001 – vi vil vente gjennom forbigående feil
            last = e
        time.sleep(every)
    raise AssertionError(f"{what} ble ikke oppfylt innen {timeout:.0f} s" + (f" (siste feil: {last})" if last else ""))


def vol_db(v: int) -> float:   # samme formel som daemonen (pi/ki_amp_daemon.py vol_db)
    return -80.0 if v <= 0 else max(-60.0, 40.0 * np.log10(v / 100.0))


@pytest.fixture(scope="session")
def status():
    return wait_for(lambda: get("/api/status"), 30, what="/api/status svarer")


@pytest.fixture()
def restore_state(status):
    """Sett tilbake volum, demping og kilde etter testen."""
    before = get("/api/status")
    yield before
    for p, b in (("/api/mute", {"mute": before.get("mute", False)}), ("/api/volume", {"volume": before.get("volume", 30)})):
        try:
            post(p, b)
        except Exception:
            pass


# ---------- grunnleggende ----------
def test_status_svarer_raskt():
    t0 = time.time()
    s = get("/api/status", timeout=5)
    dt = time.time() - t0
    assert dt < 2.0, f"/api/status brukte {dt:.2f} s (maks 2 s)"
    for k in ("power", "input", "volume", "mute"):
        assert k in s, f"/api/status mangler «{k}»"


@needs_systemd
@pytest.mark.parametrize("svc", SERVICES)
def test_tjeneste_aktiv(svc):
    r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
    if r.stdout.strip() in ("inactive", "unknown") and subprocess.run(["systemctl", "cat", svc], capture_output=True).returncode != 0:
        pytest.skip(f"{svc} er ikke installert på denne enheten")
    assert r.stdout.strip() == "active", f"{svc} er «{r.stdout.strip()}». Sjekk: journalctl -u {svc} -n 50"


@needs_systemd
def test_skjold_ui_aktiv_paa_s1f():
    env = open("/etc/ki-amp.env").read() if os.path.exists("/etc/ki-amp.env") else ""
    if "KI_AMP_BOARD=s1f" not in env:
        pytest.skip("ikke S1 rev F")
    r = subprocess.run(["systemctl", "is-active", "skjold-ui"], capture_output=True, text=True)
    assert r.stdout.strip() == "active", "skjold-ui (skjermen) kjører ikke"


@needs_systemd
@pytest.mark.skipif(os.environ.get("HWTEST_RESTART") != "1", reason="sett HWTEST_RESTART=1 for å teste omstart")
def test_oppstart_etter_restart():
    subprocess.run(["sudo", "-n", "systemctl", "restart", "ki-amp"], check=True, timeout=30)
    t0 = time.time()
    wait_for(lambda: get("/api/status", timeout=2), 60, every=0.25, what="daemonen svarer etter restart")
    dt = time.time() - t0
    assert dt < 20, f"daemonen brukte {dt:.1f} s på å svare etter restart"


def test_helsesjekk_uten_feil():
    try:
        h = get("/api/health", timeout=15)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pytest.skip("helsesjekk finnes ikke i denne versjonen")
        raise
    bad = []
    def walk(o, path=""):
        if isinstance(o, dict):
            if o.get("level") in ("error", "feil") or o.get("status") in ("error", "feil"):
                bad.append(f"{path}: {o.get('message') or o.get('melding') or o}")
            for k, v in o.items():
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(h)
    assert not bad, "helsesjekken rapporterer feil:\n" + "\n".join(bad[:10])


def test_web_ui_lastes():
    code, ct, body = get("/", raw=True)
    assert code == 200 and "html" in ct, f"web-UI svarte {code} {ct}"
    html = body.decode(errors="replace")
    assert "<script" in html, "index.html mangler script"
    import re
    m = re.search(r'src="\.?/?(assets/[^"]+\.js)"', html)
    if m:
        c2, _, b2 = get("/" + m.group(1), raw=True)
        assert c2 == 200 and len(b2) > 1000, f"{m.group(1)} svarte {c2}"


def test_web_ui_rendres_i_nettleser():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("Playwright ikke installert på runneren")
    errs = []
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:
            exe = "/opt/pw-browsers/chromium"
            exe = next((os.path.join(r, f) for r, _, fs in os.walk(exe) for f in fs if f in ("chrome", "chromium")), None) if os.path.isdir(exe) else None
            if not exe:
                pytest.skip("Playwright finner ingen nettleser (kjør «playwright install chromium»)")
            b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(BASE + "/", wait_until="networkidle", timeout=30000)
        pg.wait_for_timeout(2000)
        pg.screenshot(path=os.path.join(OUT, "web-ui.png"))
        b.close()
    assert not errs, "JavaScript-feil i web-UI-et:\n" + "\n".join(errs[:5])


# ---------- oppdatering ----------
def test_versjon_etter_installasjon():
    u = get("/api/update?check=0", timeout=15)
    exp = os.environ.get("HWTEST_EXPECT", "").strip()
    if not exp:
        pytest.skip("HWTEST_EXPECT ikke satt")
    cur = u.get("current") or ""
    assert cur in (exp, "lokal"), f"installert versjon er «{cur}», forventet «{exp}»"


def test_trygg_oppdatering_tilbakerulling():
    path = os.path.join(os.path.dirname(__file__), "..", "pi", "skjold_safeupdate.py")
    if not os.path.exists(path):
        pytest.skip("trygg oppdatering finnes ikke i denne versjonen")
    r = subprocess.run(["python3", "-m", "pytest", "-q", "-k", "rollback or tilbake", os.path.join(os.path.dirname(path), "tests")],
                       capture_output=True, text=True, cwd=os.path.dirname(path), timeout=300)
    if "no tests ran" in r.stdout or r.returncode == 5:
        pytest.skip("ingen tilbakerullingstester funnet")
    assert r.returncode == 0, "tilbakerulling feilet:\n" + r.stdout[-2000:]


# ---------- nettverkstjenester ----------
def _browse(stype: str) -> str:
    if not shutil.which("avahi-browse"):
        pytest.skip("avahi-browse finnes ikke")
    r = subprocess.run(["avahi-browse", "-rtp", stype], capture_output=True, text=True, timeout=20)
    return r.stdout


def _name(status) -> str:
    return (status.get("name") or "").strip()


def test_airplay_annonseres(status):
    out = _browse("_raop._tcp")
    n = _name(status)
    assert out.strip(), "ingen AirPlay-mottakere funnet (_raop._tcp)"
    if n:
        assert n.lower() in out.lower(), f"AirPlay-mottakeren «{n}» annonseres ikke"


def test_spotify_connect_annonseres(status):
    if not any(subprocess.run(["systemctl", "is-active", s], capture_output=True, text=True).stdout.strip() == "active" for s in ("ki-spotify", "raspotify")):
        pytest.skip("Spotify Connect er ikke på")
    out = _browse("_spotify-connect._tcp")
    assert out.strip(), "Spotify Connect annonseres ikke (_spotify-connect._tcp)"


def test_lyrion_ser_spilleren(status):
    port = int(os.environ.get("HWTEST_LMS_PORT", "9000"))
    host = os.environ.get("HWTEST_LMS_HOST", "127.0.0.1")
    body = json.dumps({"id": 1, "method": "slim.request", "params": ["", ["players", 0, 50]]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://{host}:{port}/jsonrpc.js", data=body,
                                                           headers={"Content-Type": "application/json"}), timeout=8) as r:
            res = json.loads(r.read()).get("result", {})
    except Exception as e:
        pytest.skip(f"Lyrion svarer ikke på {host}:{port} ({e})")
    names = [p.get("name", "") for p in res.get("players_loop", [])]
    assert names, "Lyrion ser ingen spillere"
    n = _name(status)
    if n:
        assert any(n.lower() == x.lower() for x in names), f"Lyrion ser ikke «{n}» (ser: {names})"


# ---------- radio ----------
def test_radio_spiller_med_tittel_og_logo(restore_state):
    try:
        post("/api/radio/play", {"url": RADIO, "title": "NRK P1"}, timeout=20)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        if e.code == 409 and "Lyrion" in body:
            pytest.skip("Lyrion ikke tilgjengelig – radio kan ikke testes")
        pytest.fail(f"/api/radio/play svarte {e.code}: {body}")
    s = wait_for(lambda: (lambda x: x if x.get("input") == "radio" and (x.get("playing") or (x.get("radio_now") or {}).get("name")) else None)(get("/api/status")),
                 20, what="radio spiller")
    rn = s.get("radio_now") or {}
    assert rn.get("name") or s.get("title"), "status har verken radio_now.name eller title"
    logo = rn.get("logo") or next((p.get("logo") for p in s.get("presets") or [] if p and p.get("logo")), None)
    assert logo, "verken radio_now.logo eller presets[].logo er satt – kanalbildet vil mangle i appene"
    code, ct, body = get(logo if logo.startswith("/") else "/" + logo.split("/", 3)[-1], raw=True, timeout=20)
    assert code == 200 and ct.startswith("image/") and len(body) > 100, f"logoen {logo} ga {code} {ct} ({len(body)} B)"


@needs_audio
def test_radio_gir_lyd(restore_state):
    post("/api/radio/play", {"url": RADIO, "title": "NRK P1"}, timeout=20)
    post("/api/volume", {"volume": 40})
    t0 = time.time()
    while time.time() - t0 < 20:
        rec = audio.play_and_record(np.zeros((audio.RATE // 2, 2)), CAPTURE, PLAY, pad=0.5)
        if audio.rms_db(rec) > -50:
            return
    pytest.fail("ingen lyd på måle-inngangen 20 s etter at radio ble startet")


# ---------- lydmålinger ----------
@pytest.fixture()
def lyd(restore_state):
    post("/api/mute", {"mute": False})
    post("/api/volume", {"volume": 50})
    time.sleep(0.5)
    yield


@needs_audio
def test_tone_1khz_niva_frekvens_thdn(lyd):
    rec = audio.play_and_record(audio.tone(1000, 3.0), CAPTURE, PLAY)
    x = audio.active(rec.mean(axis=1))
    assert len(x) > audio.RATE, "fant ikke tonen i opptaket – sjekk loopback-kabelen og HWTEST_CAPTURE"
    audio.spectrum_png(x, os.path.join(OUT, "spektrum_1khz.png"), "1 kHz, volum 50")
    f = audio.peak_freq(x)
    assert abs(f - 1000) < 5, f"målt frekvens {f:.1f} Hz (forventet 1000)"
    lvl = audio.rms_db(x)
    assert lvl > -45, f"for lavt nivå: {lvl:.1f} dBFS"
    th = audio.thdn_db(x, 1000)
    limit = float(os.environ.get("HWTEST_THDN_MAX", "-40"))
    assert th < limit, f"THD+N {th:.1f} dB (maks {limit})"
    g = audio.glitches(x, 1000)
    assert g == 0, f"{g} dropouts/klikk i tonen"


@needs_audio
def test_venstre_hoyre_ikke_byttet(lyd):
    for ch, i in (("L", 0), ("R", 1)):
        rec = audio.play_and_record(audio.tone(1000, 1.5, ch=ch), CAPTURE, PLAY)
        a, b = audio.rms_db(audio.active(rec[:, i])), audio.rms_db(audio.active(rec[:, 1 - i]))
        assert a - b > 15, f"kanal {ch}: {a:.1f} dB på riktig side mot {b:.1f} dB på feil side (L/R byttet eller krysstale)"


@needs_audio
def test_volum_gir_forventet_db(lyd):
    levels = {}
    for v in (60, 40):
        post("/api/volume", {"volume": v}); time.sleep(0.6)
        rec = audio.play_and_record(audio.tone(1000, 1.5), CAPTURE, PLAY)
        levels[v] = audio.rms_db(audio.active(rec.mean(axis=1)))
    want = vol_db(60) - vol_db(40)
    got = levels[60] - levels[40]
    assert abs(got - want) <= 0.5, f"volum 60→40 ga {got:.2f} dB, forventet {want:.2f} dB (±0,5)"


@needs_audio
def test_mute_demper_mer_enn_60db(lyd):
    on = audio.rms_db(audio.active(audio.play_and_record(audio.tone(1000, 1.5), CAPTURE, PLAY).mean(axis=1)))
    post("/api/mute", {"mute": True}); time.sleep(0.6)
    off = audio.rms_db(audio.play_and_record(audio.tone(1000, 1.5), CAPTURE, PLAY).mean(axis=1))
    post("/api/mute", {"mute": False})
    assert on - off > 60, f"demping ga bare {on - off:.1f} dB"


@needs_audio
def test_eq_endrer_responsen(lyd):
    st = get("/api/status")
    src = {"airplay": "air", "bt": "bt", "radio": "radio", "aux": "aux", "aux2": "aux", "usb": "usb"}.get(st.get("input"), "air")
    before = (get("/api/settings").get("settings") or {}).get("eq", {}).get(src)
    def measure():
        rec = audio.play_and_record(audio.sweep(secs=4.0), CAPTURE, PLAY)
        x = rec.mean(axis=1)
        return audio.band_level_db(x, 9000, 14000) - audio.band_level_db(x, 800, 1200)
    try:
        post("/api/settings", {"eq": {src: {"preset": -1, "eq": [0, 0, 0, 0, 0]}}}); time.sleep(1.5)
        flat = measure()
        post("/api/settings", {"eq": {src: {"preset": -1, "eq": [0, 0, 0, 0, -10]}}}); time.sleep(1.5)
        cut = measure()
    finally:
        if before:
            post("/api/settings", {"eq": {src: before}})
    assert flat - cut > 5, f"12 kHz-kutt på −10 dB ga bare {flat - cut:.1f} dB endring (EQ virker ikke i lydkjeden?)"
