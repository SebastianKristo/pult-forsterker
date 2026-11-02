#!/usr/bin/python3
"""Skjold Node – tidlig oppstarts-/avslutningsskjerm (skjold-early.service / skjold-shutdown.service).

Kjører få sekunder etter kjernen, lenge før Python-venv, luma og daemonen er klare. Derfor bare standardbiblioteket:
rå SSD1306-kommandoer over /dev/i2c-N (ioctl I2C_SLAVE + write), innebygd 5×7-font, og lgpio (valgfri) for LED-jaget.

  skjold_early.py              oppstart: «SKJOLD · Strøm på» → «Starter … ca. N s» + fremdrift (N fra /var/lib/skjold/boot_time),
                               LED-jag. Slipper skjermen når Skjold OS tar den (/run/skjold/os-display) og LED-ene når
                               daemonen ber om det (SIGUSR1) eller Skjold OS er klar (/run/skjold/os-ready). Tidsavbrudd 180 s.
  skjold_early.py --final      avslutning (ExecStop i skjold-shutdown.service): «Slått av – trygt å trekke ut» (eller
                               «Starter på nytt») og LED-ene av. Skjermen beholder bildet så lenge den har strøm.
  skjold_early.py --sim DIR    ingen maskinvare: skriv rammene som PNG (krever Pillow) – oppstart over tid + avslutning.
"""
import os, sys, time, json, signal

RUN = os.environ.get("SKJOLD_RUN_DIR", "/run/skjold")
BOOT_TIME = os.environ.get("SKJOLD_BOOT_TIME", "/var/lib/skjold/boot_time")
STATE = os.environ.get("KI_AMP_STATE", "/var/lib/ki-amp/state.json")
PINS = [os.environ.get("KI_AMP_NODE_PINS", ""), "/etc/skjold/node_pins.json",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "node_pins.json")]
TIMEOUT = 180.0
W, H = 128, 32

# ---------- 5×7-font (store bokstaver, tall, æøå, litt tegnsetting) ----------
_F = {
 " ": "00000/00000/00000/00000/00000/00000/00000",
 "A": "01110/10001/10001/11111/10001/10001/10001", "B": "11110/10001/10001/11110/10001/10001/11110",
 "C": "01110/10001/10000/10000/10000/10001/01110", "D": "11110/10001/10001/10001/10001/10001/11110",
 "E": "11111/10000/10000/11110/10000/10000/11111", "F": "11111/10000/10000/11110/10000/10000/10000",
 "G": "01110/10001/10000/10111/10001/10001/01111", "H": "10001/10001/10001/11111/10001/10001/10001",
 "I": "01110/00100/00100/00100/00100/00100/01110", "J": "00111/00010/00010/00010/00010/10010/01100",
 "K": "10001/10010/10100/11000/10100/10010/10001", "L": "10000/10000/10000/10000/10000/10000/11111",
 "M": "10001/11011/10101/10101/10001/10001/10001", "N": "10001/10001/11001/10101/10011/10001/10001",
 "O": "01110/10001/10001/10001/10001/10001/01110", "P": "11110/10001/10001/11110/10000/10000/10000",
 "Q": "01110/10001/10001/10001/10101/10010/01101", "R": "11110/10001/10001/11110/10100/10010/10001",
 "S": "01111/10000/10000/01110/00001/00001/11110", "T": "11111/00100/00100/00100/00100/00100/00100",
 "U": "10001/10001/10001/10001/10001/10001/01110", "V": "10001/10001/10001/10001/10001/01010/00100",
 "W": "10001/10001/10001/10101/10101/10101/01010", "X": "10001/10001/01010/00100/01010/10001/10001",
 "Y": "10001/10001/01010/00100/00100/00100/00100", "Z": "11111/00001/00010/00100/01000/10000/11111",
 "Æ": "01111/10100/10100/11111/10100/10100/10111", "Ø": "01111/10011/10101/10101/10101/11001/11110",
 "Å": "00100/00000/01110/10001/11111/10001/10001",
 "0": "01110/10001/10011/10101/11001/10001/01110", "1": "00100/01100/00100/00100/00100/00100/01110",
 "2": "01110/10001/00001/00010/00100/01000/11111", "3": "11111/00010/00100/00010/00001/10001/01110",
 "4": "00010/00110/01010/10010/11111/00010/00010", "5": "11111/10000/11110/00001/00001/10001/01110",
 "6": "00110/01000/10000/11110/10001/10001/01110", "7": "11111/00001/00010/00100/01000/01000/01000",
 "8": "01110/10001/10001/01110/10001/10001/01110", "9": "01110/10001/10001/01111/00001/00010/01100",
 ".": "00000/00000/00000/00000/00000/01100/01100", ",": "00000/00000/00000/00000/01100/00100/01000",
 ":": "00000/01100/01100/00000/01100/01100/00000", "-": "00000/00000/00000/11111/00000/00000/00000",
 "–": "00000/00000/00000/11111/00000/00000/00000", "·": "00000/00000/00000/00100/00000/00000/00000",
 "%": "11000/11001/00010/00100/01000/10011/00011", "/": "00000/00001/00010/00100/01000/10000/00000",
 "!": "00100/00100/00100/00100/00100/00000/00100", "?": "01110/10001/00001/00010/00100/00000/00100",
 "(": "00010/00100/01000/01000/01000/00100/00010", ")": "01000/00100/00010/00010/00010/00100/01000",
 "…": "00000/00000/00000/00000/00000/00000/10101", "'": "00100/00100/01000/00000/00000/00000/00000",
}
FONT = {k: [int(r, 2) for r in v.split("/")] for k, v in _F.items()}


class Frame:
    """1-bit rammebuffer i SSD1306-format (4 sider à 8 rader × 128 kolonner)."""
    def __init__(self): self.b = bytearray(W * H // 8)
    def px(self, x, y, on=1):
        if 0 <= x < W and 0 <= y < H:
            i = (y >> 3) * W + x
            if on: self.b[i] |= 1 << (y & 7)
            else: self.b[i] &= ~(1 << (y & 7)) & 0xFF
    def rect(self, x, y, w, h, on=1):
        for yy in range(y, y + h):
            for xx in range(x, x + w): self.px(xx, yy, on)
    def frame(self, x, y, w, h):
        for xx in range(x, x + w): self.px(xx, y); self.px(xx, y + h - 1)
        for yy in range(y, y + h): self.px(x, yy); self.px(x + w - 1, yy)
    def text(self, x, y, s, scale=1, align="l"):
        s = s.upper(); w = text_w(s, scale)
        if align == "c": x -= w // 2
        elif align == "r": x -= w
        for ch in s:
            g = FONT.get(ch, FONT["?"])
            for r, bits in enumerate(g):
                for c in range(5):
                    if bits & (1 << (4 - c)): self.rect(x + c * scale, y + r * scale, scale, scale)
            x += 6 * scale
        return x


def text_w(s, scale=1): return max(0, len(s) * 6 * scale - scale)


# ---------- SSD1306 over /dev/i2c-N ----------
class Ssd1306:
    I2C_SLAVE = 0x0703

    def __init__(self, port=1, addr=0x3C, rotate=2, contrast=255):
        import fcntl
        dev = "/dev/i2c-%d" % port
        for _ in range(60):                      # i2c-dev kan komme et øyeblikk etter oss
            if os.path.exists(dev): break
            time.sleep(0.05)
        self.fd = os.open(dev, os.O_RDWR)
        fcntl.ioctl(self.fd, self.I2C_SLAVE, addr)
        seg, com = (0xA0, 0xC0) if rotate == 2 else (0xA1, 0xC8)
        self.cmd(0xAE, 0xD5, 0x80, 0xA8, H - 1, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x00, seg, com,
                 0xDA, 0x02, 0x81, max(1, min(255, contrast)), 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6)
        self.on = False

    def cmd(self, *c):
        for i in range(0, len(c), 16): os.write(self.fd, bytes([0x00]) + bytes(c[i:i + 16]))

    def show(self, fr):
        self.cmd(0x21, 0, W - 1, 0x22, 0, H // 8 - 1)
        for i in range(0, len(fr.b), 128): os.write(self.fd, b"\x40" + bytes(fr.b[i:i + 128]))
        if not self.on: self.cmd(0xAF); self.on = True

    def close(self):
        try: os.close(self.fd)
        except OSError: pass


class PngOut:
    def __init__(self, d): self.d = d; self.n = 0; os.makedirs(d, exist_ok=True)
    def show(self, fr, name=None):
        from PIL import Image
        im = Image.new("1", (W, H))
        for y in range(H):
            for x in range(W):
                if fr.b[(y >> 3) * W + x] & (1 << (y & 7)): im.putpixel((x, y), 1)
        name = name or "frame_%03d" % self.n; self.n += 1
        im.convert("L").resize((W * 4, H * 4), 0).save(os.path.join(self.d, name + ".png"))
        return name
    def close(self): pass


# ---------- LED-ringer (lgpio, valgfritt) ----------
class Leds:
    def __init__(self, pins, hz=1000, active_high=True):
        self.h = None; self.pins = list(pins); self.hz = hz; self.ah = active_high
        try:
            import lgpio
            self.lg = lgpio
            for chip in (0, 4):
                try:
                    h = lgpio.gpiochip_open(chip)
                    if "pinctrl" in (lgpio.gpiochip_get_chip_info(h)[2] or "") or chip == 4:
                        self.h = h; break
                    lgpio.gpiochip_close(h)
                except Exception:
                    pass
            if self.h is None: return
            for p in self.pins: lgpio.gpio_claim_output(self.h, p, 0 if active_high else 1)
        except Exception:
            self.h = None

    def set(self, vals):
        if self.h is None: return
        for p, v in zip(self.pins, vals):
            d = max(0.0, min(100.0, v * 100.0))
            if not self.ah: d = 100.0 - d
            try:
                if d <= 0.0 or d >= 100.0:
                    self.lg.tx_pwm(self.h, p, 0, 0); self.lg.gpio_write(self.h, p, 1 if d >= 100.0 else 0)
                else:
                    self.lg.tx_pwm(self.h, p, self.hz, d)
            except Exception:
                pass

    def close(self):
        if self.h is None: return
        self.set([0.0] * len(self.pins))
        try:
            for p in self.pins: self.lg.gpio_free(self.h, p)
            self.lg.gpiochip_close(self.h)
        except Exception:
            pass
        self.h = None


# ---------- oppsett fra filer ----------
def read_json(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return None


def node_cfg():
    for p in PINS:
        j = read_json(p) if p else None
        if j and int(j.get("schema", 1)) >= 2:
            sk = j.get("skjerm") or {}; le = j.get("leds") or {}
            order = {"radio": 0, "airbt": 1, "prev": 2, "next": 3}
            leds = [int(l["gpio"]) for l in sorted(le.get("liste") or [], key=lambda l: order.get(l.get("for"), 9))]
            return {"port": int(sk.get("i2c_port", 1)), "addr": int(str(sk.get("adresse", "0x3C")), 16), "rotate": int(sk.get("rotate", 2)),
                    "contrast": int(sk.get("kontrast", 255)), "leds": leds, "hz": max(100, int(le.get("pwm_hz", 1000))),
                    "ah": bool(le.get("aktiv_hoy", True))}
    return {"port": 1, "addr": 0x3C, "rotate": 2, "contrast": 255, "leds": [12, 16, 20, 21], "hz": 1000, "ah": True}


def led_prefs():
    """(nivå 0–1 opplevd, modus) fra daemonens state.json – samme regler som ki_amp_daemon.led_level/led_mode."""
    s = ((read_json(STATE) or {}).get("settings") or {})
    try:
        lvl = float(s["ledLevel"]) / 100 if s.get("ledLevel") is not None else [1.0, 0.6, 0.3, 0.0][int(s.get("led", 0))]
    except (TypeError, ValueError, IndexError, KeyError):
        lvl = 1.0
    m = s.get("ledMode", "press")
    if isinstance(m, int): m = ["press", "always", "off"][m] if 0 <= m < 3 else "press"
    return max(0.0, min(1.0, lvl)), m


def boot_estimate():
    v = read_json(BOOT_TIME)
    try:
        v = v.get("avg") if isinstance(v, dict) else v
        return max(5.0, min(600.0, float(v)))
    except (TypeError, ValueError, AttributeError):
        return 45.0


def uptime():
    try:
        with open("/proc/uptime") as f: return float(f.read().split()[0])
    except (OSError, ValueError): return 0.0


# ---------- skjermbilder ----------
def logo(fr, x, y):
    """Logoen (fem stolper, som i Skjold OS) i miniatyr."""
    for i, h in enumerate((6, 10, 13, 9, 5)):
        fr.rect(x + i * 3, y + 13 - h, 2, h)


def boot_frame(t_up, est, t_run):
    """Logo + SKJOLD (stor), statuslinje («STRØM PÅ» / «STARTER…» + «CA. N S»), fremdriftsstolpe nederst."""
    fr = Frame()
    logo(fr, 1, 0)
    fr.text(20, 0, "SKJOLD", 2)
    fr.text(127, 0, "NODE", 1, "r")
    left = max(0, int(round(est - t_up)))
    if t_run < 1.5:
        fr.text(0, 16, "STRØM PÅ")
    else:
        fr.text(0, 16, "STARTER" + "…" * (int(t_run * 2) % 2))
        fr.text(127, 16, "CA. %d S" % left if left > 0 else "SNART KLAR", 1, "r")
    # fremdrift (oppetid / estimat); kryper mot 100 % hvis oppstarten tar lenger tid enn sist
    p = min(0.97, t_up / est) if est else 0.0
    if t_up > est: p = 0.97 + 0.03 * (1 - 1 / (1 + (t_up - est) / 20))
    fr.frame(0, 25, 128, 7); n = int(round(124 * p))
    fr.rect(2, 27, n, 3)
    gx = 2 + int((t_run * 40) % max(1, n + 12)) - 6   # vandrende glimt i fyllet
    for xx in range(gx, gx + 3):
        if 2 <= xx < 2 + n: fr.rect(xx, 27, 1, 3, 0)
    return fr


def final_frame(reboot, est):
    fr = Frame()
    logo(fr, 1, 0)
    if reboot:
        fr.text(20, 0, "SKJOLD", 2); fr.text(0, 16, "STARTER PÅ NYTT"); fr.text(0, 25, "TILBAKE OM CA. %d S" % int(round(est)))
    else:
        fr.text(20, 0, "SLÅTT AV", 2); fr.text(0, 16, "TRYGT Å TREKKE UT"); fr.text(0, 25, "STRØMMEN")
    return fr


def chase(t, n=4, speed=1.6):
    """LED-jag: én ring om gangen med hale."""
    ph = (t * speed) % n
    return [max(0.0, 1.0 - ((ph - i) % n) / 1.6) for i in range(n)]


# ---------- moduser ----------
def run_boot(out, leds, sim_clock=None):
    os.makedirs(RUN, exist_ok=True)
    with open(os.path.join(RUN, "early.pid"), "w") as f: f.write(str(os.getpid()))
    for fn in ("early-leds-free", "os-display", "os-ready"):
        try: os.remove(os.path.join(RUN, fn))
        except OSError: pass
    st = {"leds": leds is not None and leds.h is not None, "screen": out is not None}

    def release(*_):
        if leds: leds.close()
        st["leds"] = False
        open(os.path.join(RUN, "early-leds-free"), "w").close()
    signal.signal(signal.SIGUSR1, release)
    signal.signal(signal.SIGTERM, lambda *_: st.update(leds=False, screen=False))
    est = boot_estimate(); lvl, mode = led_prefs(); g = lambda v: (v * lvl) ** 2.2
    t0 = time.monotonic()
    while st["leds"] or st["screen"]:
        t = time.monotonic() - t0
        if t > TIMEOUT: break
        if st["screen"] and os.path.exists(os.path.join(RUN, "os-display")):
            st["screen"] = False                           # Skjold OS har tatt skjermen
        if os.path.exists(os.path.join(RUN, "os-ready")) and st["leds"]:
            release()
        if st["screen"]: out.show(boot_frame(uptime(), est, t))
        if st["leds"]: leds.set([g(v) if mode != "off" else 0.0 for v in chase(t)])
        time.sleep(0.05 if st["leds"] else 0.12)
    if leds and st["leds"]: release()
    try: os.remove(os.path.join(RUN, "early.pid"))
    except OSError: pass


def is_reboot():
    try:
        import subprocess
        jobs = subprocess.run(["systemctl", "list-jobs", "--no-legend"], capture_output=True, text=True, timeout=3).stdout
        return "reboot.target" in jobs or "kexec.target" in jobs
    except Exception:
        return False


def run_final(out, leds):
    if leds: leds.set([0.0] * len(leds.pins)); leds.close()
    if out: out.show(final_frame(is_reboot(), boot_estimate()))


def sim(d):
    """Rammer for oppstarten på utvalgte tidspunkt (oppetid = 4 s + t) og avslutningsskjermene."""
    out = PngOut(d); est = boot_estimate() if os.path.exists(BOOT_TIME) else 38.0
    names = []
    for t in (0.2, 1.0, 2.0, 2.5, 8.0, 20.0, 33.0, 40.0, 60.0):
        names.append(out.show(boot_frame(4.0 + t, est, t), "boot_t%05.1f" % t))
    names.append(out.show(final_frame(False, est), "final_poweroff"))
    names.append(out.show(final_frame(True, est), "final_reboot"))
    with open(os.path.join(d, "leds.txt"), "w") as f:
        for i in range(12):
            t = i * 0.1; f.write("t=%.1f %s\n" % (t, " ".join("%.2f" % ((v * 0.6) ** 2.2) for v in chase(t))))
    print("\n".join(os.path.join(d, n + ".png") for n in names))


def main(argv):
    if "--sim" in argv:
        return sim(argv[argv.index("--sim") + 1])
    cfg = node_cfg()
    try: out = Ssd1306(cfg["port"], cfg["addr"], cfg["rotate"], cfg["contrast"])
    except Exception as e: print("skjold-early: ingen OLED (%s)" % e, file=sys.stderr); out = None
    lvl, mode = led_prefs()
    leds = Leds(cfg["leds"], cfg["hz"], cfg["ah"]) if cfg["leds"] and (lvl > 0 and mode != "off" or "--final" in argv) else None
    try:
        if "--final" in argv: run_final(out, leds)
        else: run_boot(out, leds)
    finally:
        if leds: leds.close()
        if out: out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
