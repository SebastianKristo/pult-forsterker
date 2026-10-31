"""python -m skjold_os [--sim DIR] [--demo] [--shots DIR] [--layout node] [--api URL]"""
import argparse, os, sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skjold_os", description="Skjold OS – skjerm-UI for Skjold Node")
    ap.add_argument("--sim", metavar="DIR", help="ingen maskinvare: skriv rammer som PNG til DIR (latest.png)")
    ap.add_argument("--every", type=int, default=0, help="--sim: lagre også hver N-te ramme som frame_NNNNN.png")
    ap.add_argument("--frames", type=int, default=0, help="stopp etter N rammer (test)")
    ap.add_argument("--demo", action="store_true", help="falsk daemon som sykler gjennom tilstandene")
    ap.add_argument("--shots", metavar="DIR", help="render nøkkelskjermene til DIR og avslutt")
    ap.add_argument("--layout", default=os.environ.get("SKJOLD_LAYOUT", "node"), choices=["node", "s1-oled", "s1-tft"])
    ap.add_argument("--api", default=os.environ.get("SKJOLD_API", "http://127.0.0.1:%s" % os.environ.get("KI_AMP_PORT", "8765")))
    ap.add_argument("--hz", type=float, default=8.0, help="poll-frekvens mot /api/status")
    ap.add_argument("--no-boot", action="store_true", help="hopp over oppstartsanimasjonen")
    a = ap.parse_args(argv)

    from . import layouts, config
    from .api import DaemonClient
    from .display import PngSink, Backlight, LumaST7735
    from .app import Ui
    lay = layouts.get(a.layout)

    if a.shots:
        from .demo import shots
        cl = DaemonClient(a.api)
        cl.poll_once()
        out = shots(lay, a.shots, cl if cl.online else None)
        print("\n".join(out)); return 0

    sk, src = config.screen_cfg()
    if a.demo:
        from .demo import DemoClient
        client = DemoClient()
    else:
        client = DaemonClient(a.api, a.hz).start()
    if a.sim:
        sink = PngSink(a.sim, a.every); bl = Backlight(sk.get("bakgrunnslys", {}), sim=True)
    elif a.layout.startswith("s1"):
        from .display_s1 import open_s1
        sink, bl = open_s1(a.layout)
    else:
        sink = LumaST7735(sk); bl = Backlight(sk.get("bakgrunnslys", {}))
    print("Skjold OS: layout=%s api=%s pins=%s %s" % (a.layout, a.api, src, "sim→" + a.sim if a.sim else "st7735"), flush=True)
    Ui(client, lay, sink, bl, model="S1" if a.layout.startswith("s1") else "NODE", boot=not a.no_boot).run(max_frames=a.frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())
