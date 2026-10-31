"""Falsk daemon for --demo og --shots (ingen nettverk, ingen maskinvare)."""
import copy, time

BASE = {"power": True, "input": "radio", "volume": 42, "mute": False, "bt_pairing": False, "preset": 2,
        "presets": [{"n": i + 1, "title": t} for i, t in enumerate(["NRK P1", "NRK P3", "P4", "Radio Norge", "NRK Klassisk", "NRK Jazz"])],
        "playing": True, "paused": False, "station": "NRK P3", "title": "Dance The Way I Feel", "artist": "Ofenbach",
        "album": "", "duration": 0, "position": 0, "bt_device": "", "name": "Skjold Node", "lyrion": True,
        "inputs": ["radio", "airplay", "bt", "spotify"], "usb_pc": 1, "usb_pc_names": ["PC 1", "PC 2"], "cover": ""}
SETTINGS = {"clock": True, "clockStyle": 0, "dim": 1, "off": 1}

AIRPLAY = dict(input="airplay", station="", title="Midnight City", artist="M83", duration=243, position=64)
BT = dict(input="bt", station="", title="Teardrop", artist="Massive Attack", duration=331, position=120, bt_device="Sebastians iPhone")
SPOTIFY = dict(input="spotify", station="", title="Clair de lune", artist="Claude Debussy", duration=301, position=30)


def st(**kw):
    s = copy.deepcopy(BASE); s.update(kw); return s


class FakeClient:
    def __init__(self, status=None, settings=None, online=True):
        self.status = status or st(); self.settings = dict(SETTINGS, **(settings or {})); self.online = online
    def snapshot(self): return self.online, (copy.deepcopy(self.status) if self.online else None), dict(self.settings), None
    def start(self): return self


# --demo: (sekunder fra start, endring) – sykler gjennom tilstandene i en løkke
TIMELINE = [
    (4, {}), (6, {"volume": 55}), (6.6, {"volume": 61}), (9, {"preset": 3, "station": "P4", "title": "Flowers", "artist": "Miley Cyrus"}),
    (12, AIRPLAY), (16, {"paused": True}), (18, {"paused": False}), (20, BT), (24, {"bt_pairing": True}),
    (30, {"bt_pairing": False}), (32, SPOTIFY), (36, {"mute": True}), (38, {"mute": False}),
    (40, {"menu": {"open": True, "idx": 3}}), (43, {"menu": None}), (45, {"power": False}),
    (50, "__offline__"), (55, {"power": True, "input": "radio", "station": "NRK P1", "preset": 1, "title": "Nyheter", "artist": "NRK Dagsnytt"}),
    (60, {"rebooting": True}), (66, {"rebooting": False}),
]


class DemoClient(FakeClient):
    def __init__(self):
        super().__init__(); self.t0 = time.time(); self.applied = 0
    def snapshot(self):
        t = (time.time() - self.t0) % 70
        if t < 1 and self.applied: self.status, self.online, self.applied = st(), True, 0
        while self.applied < len(TIMELINE) and TIMELINE[self.applied][0] <= t:
            ch = TIMELINE[self.applied][1]
            if ch == "__offline__": self.online = False
            else: self.online = True; self.status.update(ch)
            self.applied += 1
        return super().snapshot()


def shots(layout, outdir, live_client=None):
    """Renderer nøkkelskjermene til PNG med en falsk klokke."""
    import os
    from .app import Ui
    from .display import PngSink, Backlight
    os.makedirs(outdir, exist_ok=True)
    class Clock:
        t = 1_793_450_000.0   # fast tidspunkt (lørdag 31.10.2026 ~ 13:33 lokal)
        def __call__(self): return self.t
    out = []

    def shot(name, client, setup=None, advance=0.0, pre=None):
        ck = Clock(); ui = Ui(client, layout, PngSink(outdir, keep_latest=False), Backlight({}, sim=True), boot=False, clock=ck)
        if pre: ui.viewmodel(); pre(client); ck.t += 0.05; ui.viewmodel()
        if setup: setup(ui, ck)
        ck.t += advance
        vm = ui.viewmodel(); img = layout.render(vm)
        p = os.path.join(outdir, name + ".png"); img.save(p)
        img.resize((img.width * 4, img.height * 4), 0).save(os.path.join(outdir, name + "@4x.png")); out.append(p)
        return vm

    fx_at = lambda k, ms, **kw: (lambda ui, ck: setattr(ui, "fx", dict({"k": k, "t0": ck.t - ms / 1000}, **kw)))
    shot("01_boot_splash_40", FakeClient(), fx_at("boot", 1100))
    shot("02_boot_splash_done", FakeClient(), fx_at("boot", 2500))
    shot("03_play_radio", FakeClient())
    shot("04_play_radio_volume", FakeClient(), pre=lambda c: c.status.update(volume=61))
    shot("05_play_airplay", FakeClient(st(**AIRPLAY)))
    shot("06_play_airplay_paused", FakeClient(st(**AIRPLAY, paused=True)))
    shot("07_play_bt", FakeClient(st(**BT)))
    shot("08_play_spotify_muted", FakeClient(st(**SPOTIFY)), pre=lambda c: c.status.update(mute=True))
    shot("09_switch_mid", FakeClient(st(**AIRPLAY)), pre=lambda c: c.status.update(BT), advance=0.1)
    shot("10_switch_end", FakeClient(st(**AIRPLAY)), pre=lambda c: c.status.update(BT), advance=0.5)
    shot("11_pairing", FakeClient(st(**BT)), pre=lambda c: c.status.update(bt_pairing=True), advance=2.3)
    shot("12_menu_radio", FakeClient(st(menu={"open": True, "idx": 3})))
    shot("12b_settings", FakeClient(st(version="2.0")), pre=lambda c: c.status.update(ui_event={"name": "settings", "t": 1}), advance=3.3)
    shot("13_reboot_steps", FakeClient(), fx_at("reboot", 1700))
    shot("14_reboot_collapse", FakeClient(), fx_at("reboot", 200))
    shot("15_welcome", FakeClient(), lambda ui, ck: (setattr(ui, "welcome", {"tittel": "Gratulerer med dagen", "navn": "Pappa"}),
                                                        setattr(ui, "fx", {"k": "welcome", "t0": ck.t - 3.6})))
    for sty in range(6):
        shot("16_clock_style%d" % sty, FakeClient(st(power=False), {"clockStyle": sty}))
    shot("17_standby_idle", FakeClient(st(**AIRPLAY, playing=False, paused=True)), lambda ui, ck: setattr(ui, "last_act", ck.t - 200))
    shot("18_offline", FakeClient(online=False), advance=7)
    shot("19_play_aux_idle", FakeClient(st(input="aux", inputs=["radio", "airplay", "bt", "aux", "usb"], title="", artist="", station="", playing=False)))
    saved = {"title": "Lagret", "sub": "Favoritt 2 · P4 Norge", "saved": 2, "p": 1}
    shot("21_lagret_pop", FakeClient(), pre=lambda c: c.status.update(hold=saved), advance=0.1)
    shot("22_lagret", FakeClient(), pre=lambda c: c.status.update(hold=saved), advance=0.8)
    shot("23_lagret_airplay", FakeClient(st(**AIRPLAY)), pre=lambda c: c.status.update(hold=saved), advance=0.8)
    if live_client is not None:
        live_client.poll_once(); shot("20_live_daemon", live_client)
    return out
