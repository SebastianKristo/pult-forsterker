"""Leder/følger-motor. Lederen sender PCM i 10 ms-pakker med avspillingstid = nå + buffer (100–500 ms) og
forsinker egen utgang like mye (CamillaDSP Delay). Følgere synker klokken og spiller pakkene på riktig ledertid."""
import socket, threading, time
import numpy as np
from .clock import ClockServer, ClockClient, now
from .proto import pack_audio, unpack_audio, JitterBuffer

AUDIO_PORT, CLOCK_PORT = 5004, 5005


def clamp_buffer(ms):
    return max(100, min(500, int(ms or 200)))


class Leader:
    def __init__(self, followers, buffer_ms=200, rate=48000, clock_port=CLOCK_PORT, clock=now):
        self.followers, self.rate, self.clock = list(followers), rate, clock
        self.buffer = clamp_buffer(buffer_ms) / 1000.0
        self.clk = ClockServer(clock_port, clock=clock)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = self.frame = 0
        self.t0 = None

    def start(self):
        self.clk.start()
        return self

    def send(self, pcm):
        """Send en blokk (n x ch int16). Første blokk ankrer tidslinjen; deretter følger avspillingstid rammetallet."""
        if self.t0 is None:
            self.t0 = self.clock() + self.buffer
        play_at = self.t0 + self.frame / self.rate
        pkt = pack_audio(self.seq, self.frame, play_at, pcm, self.rate)
        for f in self.followers:
            self.sock.sendto(pkt, f)
        self.seq += 1
        self.frame += len(pcm)
        return play_at

    def stop(self):
        self.clk.stop()


class Follower(threading.Thread):
    def __init__(self, leader_host, audio_port=AUDIO_PORT, clock_port=CLOCK_PORT, rate=48000, channels=2,
                 extra_delay_ms=0.0, clock=now):
        super().__init__(daemon=True)
        self.clock = clock
        self.cc = ClockClient(leader_host, clock_port, clock=clock)
        self.jb = JitterBuffer(rate, channels)
        self.extra = extra_delay_ms / 1000.0  # per-rom forsinkelse
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", audio_port))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self.running = True

    def run(self):
        last = 0.0
        while self.running:
            if self.clock() - last > 0.25:
                self.cc.poll(1)
                last = self.clock()
            try:
                p = unpack_audio(self.sock.recv(65536))
            except (socket.timeout, OSError):
                continue
            if p:
                self.jb.put(p)

    def sync(self, n=16):
        self.cc.poll(n)
        return self.cc.est

    def render(self, local_t0, n):
        """n rammer som skal ut av DAC ved lokal tid local_t0."""
        est = self.cc.est
        return self.jb.fetch(est.to_leader(local_t0) - self.extra, n, ratio=1.0 + est.drift)

    def stop(self):
        self.running = False
        self.sock.close()


def status():
    return {"engine": "skjold_sync", "audio_port": AUDIO_PORT, "clock_port": CLOCK_PORT}


def run_leader(followers, buffer_ms=200, device="hw:Loopback,1,0", rate=48000):
    """Leser PCM fra ALSA (arecord) og sender til følgerne. Lokal utgang forsinkes i CamillaDSP (sync_delay)."""
    import subprocess
    L = Leader([(h, AUDIO_PORT) for h in followers], buffer_ms, rate).start()
    p = subprocess.Popen(["arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(rate), "-c", "2", "-t", "raw"],
                         stdout=subprocess.PIPE)
    n = rate // 100
    while True:
        b = p.stdout.read(n * 4)
        if not b:
            break
        L.send(np.frombuffer(b, np.int16).reshape(-1, 2))


def run_follower(leader, extra_delay_ms=0.0, device="default", rate=48000):
    """Spiller av på riktig ledertid via aplay. Latens i aplay måles ikke – juster med per-rom forsinkelse."""
    import subprocess
    f = Follower(leader, extra_delay_ms=extra_delay_ms, rate=rate)
    f.sync(16)
    f.start()
    p = subprocess.Popen(["aplay", "-q", "-D", device, "-f", "S16_LE", "-r", str(rate), "-c", "2", "-t", "raw",
                          "--buffer-time=40000"], stdin=subprocess.PIPE)
    n = rate // 100
    t = now() + 0.05
    while True:
        blk = f.render(t + 0.04, n)
        p.stdin.write(np.clip(blk, -32768, 32767).astype(np.int16).tobytes())
        t += n / rate
        time.sleep(max(0.0, t - now() - 0.02))


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "leader":
        run_leader(sys.argv[2].split(","), int(sys.argv[3]) if len(sys.argv) > 3 else 200)
    else:
        run_follower(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)
