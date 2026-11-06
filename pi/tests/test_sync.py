import os, random, subprocess, sys, textwrap, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from skjold_sync.clock import ClockEstimator  # noqa: E402
from skjold_sync.proto import pack_audio, unpack_audio, JitterBuffer  # noqa: E402


def test_clock_converges_with_jitter_and_drift():
    rnd = random.Random(1)
    off, drift = 3.25, 80e-6  # leder = lokal*(1+drift)+off
    est = ClockEstimator()
    t = 100.0
    for _ in range(64):
        up, down = 0.002 + rnd.expovariate(1 / 0.004), 0.002 + rnd.expovariate(1 / 0.004)  # Wi-Fi-aktig jitter
        t1 = t; t2 = t1 * (1 + drift) + off + up; t3 = t2 + 0.0001; t4 = t1 + up + down + 0.0001 / (1 + drift)
        est.add(t1, t2, t3, t4)
        t += 0.5
    for tl in (t, t + 5):
        err = abs(est.to_leader(tl) - (tl * (1 + drift) + off))
        assert err < 0.001, err
    assert abs(est.to_local(est.to_leader(t)) - t) < 1e-6


def test_packets_reorder_and_loss():
    jb = JitterBuffer(48000, 2)
    blocks = [np.full((480, 2), i + 1, np.int16) for i in range(10)]
    pk = [unpack_audio(pack_audio(i, i * 480, 1.0 + i * 0.01, b)) for i, b in enumerate(blocks)]
    order = [0, 2, 1, 4, 3, 6, 5, 9, 8]  # pakke 7 tapt, resten stokket, 3 duplisert
    for i in order + [3]:
        jb.put(pk[i])
    out, miss = jb.frames(0, 4800)
    assert miss == 480 and jb.dups == 1
    for i in range(10):
        assert out[i * 480 + 10, 0] == (0 if i == 7 else i + 1)
    # fetch på ledertid gir samme som rammeindeks
    f = jb.fetch(1.0 + 0.05, 10)
    assert np.allclose(f[:, 0], 6)


LEADER = textwrap.dedent("""
    import sys, time, numpy as np
    sys.path.insert(0, sys.argv[1])
    from skjold_sync.engine import Leader
    OFF = 0.137
    clock = lambda: time.monotonic() + OFF
    L = Leader([("127.0.0.1", int(sys.argv[2]))], buffer_ms=150, clock_port=int(sys.argv[3]), clock=clock).start()
    rng = np.random.default_rng(7)
    sig = (rng.standard_normal((48000 * 2, 2)) * 6000).astype(np.int16)
    t = time.monotonic()
    for i in range(0, len(sig), 480):
        L.send(sig[i:i + 480])
        t += 0.01
        time.sleep(max(0, t - time.monotonic()))
    time.sleep(1.0)
    L.stop()
""")


def _free_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def test_two_process_loopback_offset_under_1ms(tmp_path):
    from skjold_sync.engine import Follower
    ap, cp = _free_port(), _free_port()
    script = tmp_path / "leader.py"; script.write_text(LEADER)
    proc = subprocess.Popen([sys.executable, str(script), os.path.join(os.path.dirname(__file__), ".."), str(ap), str(cp)])
    try:
        f = Follower("127.0.0.1", audio_port=ap, clock_port=cp)
        time.sleep(0.3)
        est = f.sync(32)
        f.start()
        time.sleep(1.2)
        assert est.ready
        assert abs(est.offset - 0.137) < 0.001, est.offset
        base_frame, t0 = f.jb.base
        local = time.monotonic() - 0.5   # et vindu som allerede er mottatt
        out = f.render(local, 4800)[:, 0]
        # fasit: kildesignalet på ekte ledertid (lokal + 0.137)
        rng = np.random.default_rng(7)
        sig = (rng.standard_normal((48000 * 2, 2)) * 6000).astype(np.int16)[:, 0].astype(np.float32)
        k = int(round((local + 0.137 - t0) * 48000)) + base_frame
        ref = sig[k - 200:k + 4800 + 200]
        cc = np.correlate(ref, out, "valid")
        lag = int(np.argmax(cc)) - 200
        ms = abs(lag) / 48.0
        print(f"loopback lag {lag} samples = {ms:.3f} ms, klokkefeil {abs(est.offset-0.137)*1e3:.3f} ms")
        assert ms < 1.0
        f.stop()
    finally:
        proc.wait(timeout=10)
