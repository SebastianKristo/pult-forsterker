"""Tilstandsmaskinen: daemon-status + lokale tidtakere -> ViewModel -> layout -> skjerm/bakgrunnslys."""
import datetime, io, json, os, signal, time
from PIL import Image
from . import fx, sources

WELCOME_FILE = os.environ.get("SKJOLD_WELCOME_FILE", "/var/lib/skjold/velkomst.json")
CLOCK_AFTER_S = 120          # design: «Etter 2 min på pause viser skjermen standby-klokke»
VOL_SHOW_S = 1.5             # design: volum vises nederst i 1,5 s
PAIR_S = 120                 # daemon: bt_pairing varer 2 min (_pairing_until)
OFFLINE_AFTER_S = 3.0
SETTINGS_S = 15.0         # innstillingsoversikten lukkes selv
DIM_AFTER = [None, 30, 60]   # settings.dim: Av / 30 s / 1 min
OFF_AFTER = [None, 120, 300] # settings.off: Av / 2 min / 5 min
BRIGHT = [1.0, 1.0, 0.6, 0.3]  # settings.bright (daemonen, /api/settings): Auto / Høy / Middels / Lav (Auto = Høy, ingen lyssensor)
DIM_LEVEL = 0.25


def read_welcome():
    try:
        with open(WELCOME_FILE, encoding="utf-8") as f:
            v = json.load(f)
        return v if v.get("aktiv") else None
    except (OSError, ValueError):
        return None


class Ui:
    def __init__(self, client, layout, sink, backlight, model="NODE", boot=True, clock=time.time):
        self.cl, self.lay, self.sink, self.bl, self.model = client, layout, sink, backlight, model
        self.clock = clock
        t = self.clock()
        self.t_start = t
        self.fx = {"k": "boot", "t0": t} if boot else None
        self.welcome = read_welcome()
        self.prev = None; self.prev_key = None
        self.last_act = t; self.vol_t = 0.0; self.pair_t0 = 0.0
        self.pos = (0.0, t); self.offline_since = None
        self._cover_key = None; self._cover_img = None
        self.last_frame = None; self.stopping = False
        self.settings_t0 = 0.0; self._ev_t = None

    # ---------- hendelser fra status ----------
    def _ingest(self, st, now):
        if st is None: return
        p = self.prev or {}
        key = (st.get("power"), st.get("input"), st.get("volume"), st.get("mute"), st.get("playing"), st.get("paused"),
               st.get("title"), st.get("station"), st.get("preset"), st.get("bt_pairing"), json.dumps(st.get("menu")),
               st.get("input_seq"), json.dumps(st.get("settings_menu")))
        if self.prev is not None and key != self.prev_key:
            self.last_act = now
            if self.welcome and (self.fx or {}).get("k") == "welcome":   # første trykk lukker hilsenen
                self.welcome = None; self.fx = None
                try: os.remove(WELCOME_FILE)
                except OSError: pass
        self.prev_key = key
        if self.prev is not None:
            if st.get("volume") != p.get("volume") or st.get("mute") != p.get("mute"): self.vol_t = now
            if st.get("input") != p.get("input") and st.get("input") and p.get("input") and not self.fx:
                ring = sources.ring(st.get("inputs"))
                fr = ring.index(p["input"]) if p["input"] in ring else 0
                to = ring.index(st["input"]) if st["input"] in ring else 0
                self.fx = {"k": "switch", "t0": now, "ring": ring, "from": fr, "to": to}
            if st.get("rebooting") and not p.get("rebooting"): self.fx = {"k": "reboot", "t0": now}
        if st.get("bt_pairing") and not p.get("bt_pairing"): self.pair_t0 = now
        ev = st.get("ui_event") or {}
        if ev.get("t") != self._ev_t:
            if self._ev_t is not None or self.prev is not None:
                if ev.get("name") == "settings": self.settings_t0 = now; self.last_act = now
            self._ev_t = ev.get("t")
        if "settings_menu" in st:   # daemonen styrer menyen selv – ikke bruk den skrivebeskyttede oversikten
            self.settings_t0 = 0.0
        elif self.settings_t0 and self.prev is not None and (st.get("input") != p.get("input") or st.get("bt_pairing")):
            self.settings_t0 = 0.0
        if st.get("position") != p.get("position") or st.get("title") != p.get("title"):
            self.pos = (float(st.get("position") or 0), now)
        self.prev = st

    def _cover(self, cover):
        if not cover or cover[1] is None: return None
        if cover[0] != self._cover_key:
            self._cover_key = cover[0]
            try: self._cover_img = Image.open(io.BytesIO(cover[1])).convert("RGB")
            except Exception: self._cover_img = None
        return self._cover_img

    # ---------- ViewModel ----------
    def viewmodel(self):
        now = self.clock(); online, st, se, cover = self.cl.snapshot()
        if online: self.offline_since = None; self._ingest(st, now)
        elif self.offline_since is None: self.offline_since = now
        d = datetime.datetime.fromtimestamp(now)
        vm = {"now": d, "now_ms": now * 1000, "clock": "%02d:%02d" % (d.hour, d.minute), "model": self.model,
              "name": (st or {}).get("name") or "Skjold " + self.model.capitalize(), "clock_style": int(se.get("clockStyle") or 0)}
        st = st or {}
        vm.update(input=st.get("input") or "radio", volume=int(st.get("volume") or 0), mute=bool(st.get("mute")))
        vm["vol_overlay"] = now - self.vol_t < VOL_SHOW_S
        # animasjoner har forrang
        if self.fx:
            t_ms = (now - self.fx["t0"]) * 1000; k = self.fx["k"]
            alive = {"boot": t_ms < fx.BOOT, "reboot": t_ms < fx.RB, "switch": t_ms < fx.SW, "welcome": True}[k]
            if not alive:
                self.fx = {"k": "boot", "t0": now} if k == "reboot" else \
                          {"k": "welcome", "t0": now} if k == "boot" and self.welcome else None
                return self.viewmodel()
            vm.update(screen=k, t_ms=t_ms, welcome=self.welcome)
            if k == "switch":
                vm.update(ring=self.fx["ring"], sw_from=self.fx["from"], sw_to=self.fx["to"], sw_sub=self._src_sub(st))
            vm["vol_overlay"] = vm["vol_overlay"] and k == "switch"
            return vm
        if not online and (self.prev is None or now - (self.offline_since or now) > OFFLINE_AFTER_S):
            if now - self.t_start > OFFLINE_AFTER_S or self.prev is not None:
                vm.update(screen="offline", offline_s=int(now - (self.offline_since or now)), vol_overlay=False); return vm
            vm.update(screen="boot", t_ms=fx.BOOT); return vm   # venter på daemonen rett etter oppstart
        hold = st.get("hold")   # {"key":"knob|src|radio|reboot","p":0-1,"title","sub"} eller bekreftelse {"title":"Lagret",…,"saved":n}
        if hold:
            vm.update(screen="hold", hold_p=hold.get("p", 1), hold_title=hold.get("title", ""), hold_sub=hold.get("sub", "Fortsett å holde"),
                      vol_overlay=False); return vm
        if st.get("bt_pairing"):
            pt = now - (self.pair_t0 or now)
            vm.update(screen="pair", pair_t=pt, pair_p=st.get("bt_pairing_left") and 1 - st["bt_pairing_left"] / PAIR_S or pt / PAIR_S)
            vm["vol_overlay"] = False; return vm
        sm = st.get("settings_menu")   # navigering med encoderen (daemonen): rader + valgt indeks
        if sm and sm.get("open"):
            rows = sm.get("rows") or [{"n": "–"}]
            vm.update(screen="menu", menu_head=sm.get("cat") or "INNSTILLINGER", menu_rows=rows,
                      menu_idx=max(0, min(len(rows) - 1, int(sm.get("idx") or 0))), vol_overlay=False); return vm
        if self.settings_t0 and now - self.settings_t0 < SETTINGS_S:
            rows = self._settings_rows(st, se); n = len(rows)
            vm.update(screen="menu", menu_head="INNSTILLINGER", menu_rows=rows,
                      menu_idx=min(n - 1, int((now - self.settings_t0) / 1.6) % n), vol_overlay=False); return vm
        menu = st.get("menu")
        if menu and menu.get("open"):
            pr = st.get("presets") or []
            rows = [{"n": (x.get("title") or "Tom plass"), "icon": str(x.get("n", i + 1)), "v": "●" if x.get("n") == st.get("preset") else ""}
                    for i, x in enumerate(pr)]
            vm.update(screen="menu", menu_head="RADIO", menu_rows=rows or [{"n": "Ingen favoritter"}],
                      menu_idx=max(0, min(len(rows) - 1, int(menu.get("idx", 1)) - 1)), vol_overlay=False); return vm
        playing = bool(st.get("playing")) and not st.get("paused")
        idle = now - self.last_act
        clock_on = bool(se.get("clock", True))
        if not st.get("power", True):
            vm.update(screen="clock" if clock_on else "off", vol_overlay=False); return vm
        if not playing and idle > CLOCK_AFTER_S and clock_on:
            vm.update(screen="clock", vol_overlay=False); return vm
        vm.update(screen="play", **self._nowplaying(st, now, cover)); return vm

    def _settings_rows(self, st, se):
        """Skrivebeskyttet innstillingsoversikt (encoder holdt 3 s). Navigering kommer når daemonen sender den."""
        opt = lambda k, o: o[se.get(k)] if isinstance(se.get(k), int) and 0 <= se.get(k) < len(o) else "–"
        return [{"n": "Maks volum", "icon": "♪", "v": opt("vmax", ["100 %", "90 %", "80 %"])},
                {"n": "Talebeskjed", "icon": "♪", "v": "På" if se.get("voice", st.get("voice")) else "Av"},
                {"n": "Standby-klokke", "icon": "▣", "v": fx.CLOCKS[int(se.get("clockStyle") or 0) % 6] if se.get("clock", True) else "Av"},
                {"n": "Dimme etter", "icon": "▣", "v": opt("dim", ["Av", "30 s", "1 min"])},
                {"n": "Slukk etter", "icon": "▣", "v": opt("off", ["Av", "2 min", "5 min"])},
                {"n": "Auto-kilde", "icon": "⇄", "v": "På" if st.get("auto_input") else "Av"},
                {"n": "Lyrion", "icon": "◠", "v": "Tilkoblet" if st.get("lyrion") else "Frakoblet"},
                {"n": "Navn", "icon": "i", "v": st.get("name") or "Skjold Node"},
                {"n": "Programvare", "icon": "i", "v": str(st.get("version") or "")}]

    def _src_sub(self, st):
        i = st.get("input")
        if i == "bt": return st.get("bt_device") or "Blåtann"
        if i == "usb":
            names = st.get("usb_pc_names") or ["PC 1", "PC 2"]; return names[max(0, min(len(names) - 1, int(st.get("usb_pc") or 1) - 1))]
        if i == "radio":
            n = sum(1 for p in st.get("presets") or [] if p.get("title")); return "Lyrion · %d favoritter" % n if n else "Lyrion"
        return sources.src(i)["sub"]

    def _nowplaying(self, st, now, cover):
        i = st.get("input") or "radio"; s = sources.src(i); title = st.get("title") or ""; artist = st.get("artist") or ""
        out = {"paused": bool(st.get("paused")), "cover": self._cover(cover), "duration": float(st.get("duration") or 0)}
        pos, t0 = self.pos
        out["position"] = min(out["duration"], pos + (now - t0 if st.get("playing") and not st.get("paused") else 0))
        if i == "radio":
            pr = int(st.get("preset") or 0); presets = st.get("presets") or []
            ptitle = next((p.get("title") for p in presets if p.get("n") == pr), "") or ""
            station = st.get("station") or ptitle
            out.update(kicker=(station or "RADIO").upper(), title=title or station or "Radio",
                       sub=artist or ("Lyrion" if st.get("lyrion") else "Lyrion ikke tilkoblet"),
                       art_txt=str(pr) if pr else "R", preset_idx=pr - 1 if pr else -1, duration=0)
            return out
        kick = {"bt": "BLÅTANN · " + (st.get("bt_device") or "").upper() if st.get("bt_device") else "BLÅTANN",
                "airplay": (st.get("airplay_device") or "AirPlay").upper(),
                "spotify": ("SPOTIFY · " + ((st.get("spotify") or {}).get("device") or "").upper()).rstrip(" ·")}.get(i, self._src_sub(st).upper())
        idle_title = {"airplay": "Klar for AirPlay", "bt": "Klar for Blåtann", "spotify": "Klar for Spotify",
                      "usb": "USB-lyd", "aux": "Linjeinngang", "aux2": "Linjeinngang"}.get(i, s["n"])
        out.update(kicker=kick, title=title or idle_title, sub=artist or (st.get("album") or ("" if title else "Velg %s på telefonen" % s["n"]
                   if i in ("airplay", "bt", "spotify") else "")), art_txt=(title or s["n"])[:1].upper(), preset_idx=-1)
        if not out["duration"] and not title: out["bottom"] = "Venter på lyd" if not st.get("playing") else ""
        return out

    # ---------- bakgrunnslys ----------
    def backlight_for(self, vm, se):
        if vm["screen"] == "off": return 0.0
        b = BRIGHT[int(se.get("bright") or 0)] if isinstance(se.get("bright"), int) and se.get("bright") < len(BRIGHT) else 1.0
        if vm["screen"] in ("boot", "reboot", "switch", "welcome", "pair", "menu", "hold", "offline"): return b
        idle = self.clock() - self.last_act
        off = OFF_AFTER[se.get("off")] if isinstance(se.get("off"), int) and 0 <= se.get("off") < 3 else None
        dim = DIM_AFTER[se.get("dim")] if isinstance(se.get("dim"), int) and 0 <= se.get("dim") < 3 else None
        if vm.get("vol_overlay"): return b
        playing = vm["screen"] == "play" and not vm.get("paused") and (self.prev or {}).get("playing")
        if off and idle > off and not playing: return 0.0
        if dim and idle > dim: return b * DIM_LEVEL
        return b

    # ---------- løkka ----------
    def step(self):
        vm = self.viewmodel()
        try:
            img = self.lay.render(vm)
        except Exception as e:   # én feil i en tegning skal ikke ta ned skjermen
            print("Tegnefeil (%s): %r" % (vm.get("screen"), e), flush=True); self.fx = None
            vm = {"screen": "off"}; img = Image.new("RGB", (self.lay.W, self.lay.H))
        _, _, se, _ = self.cl.snapshot(); lvl = self.backlight_for(vm, se) if "now" in vm else 0.0
        if lvl == 0.0: img = Image.new("RGB", img.size)
        b = img.tobytes()
        if b != self.last_frame:
            self.sink.show(img, vm["screen"]); self.last_frame = b
        self.bl.set(lvl)
        return vm

    def run(self, fps_anim=20, fps_idle=6, max_frames=0):
        def stop(*_): self.stopping = True
        signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
        n = 0
        while not self.stopping:
            t = time.time(); vm = self.step(); n += 1
            if max_frames and n >= max_frames: break
            fast = vm["screen"] in ("boot", "reboot", "switch", "welcome", "pair", "offline", "menu", "hold") or vm.get("vol_overlay") \
                or (vm["screen"] == "play" and vm.get("duration"))
            time.sleep(max(0.0, 1.0 / (fps_anim if fast else fps_idle) - (time.time() - t)))
        self.shutdown()

    def shutdown(self):
        """Ved stopp/omstart: CRT-kollaps fra reboot-animasjonen, så lyset av."""
        try:
            for ms in range(0, 400, 50):
                c = self.lay.canvas(); fx.reboot(c, ms, ms); self.sink.show(c.frame(), "stop"); time.sleep(0.05)
        except Exception:
            pass
        self.bl.set(0); self.bl.close(); self.sink.close()
