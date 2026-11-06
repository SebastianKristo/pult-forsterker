"""NTP/PTP-lignende klokkesynk: 4 tidsstempler -> offset + RTT; min-RTT-filtrering og lineær regresjon gir offset og drift."""
import socket, struct, threading, time

_FMT = "!4sddd"  # magic, t1 (følger send), t2 (leder mottak), t3 (leder send)
MAGIC = b"SKCK"


def now():
    return time.monotonic()


class ClockEstimator:
    """Estimerer leder_tid ≈ lokal_tid + offset + drift*(lokal_tid - ref)."""

    def __init__(self, window=64, keep=0.5):
        self.window, self.keep = window, keep
        self.samples = []  # (lokal midtpunkt, offset, rtt)
        self.offset, self.drift, self.ref = 0.0, 0.0, 0.0

    def add(self, t1, t2, t3, t4):
        rtt = (t4 - t1) - (t3 - t2)
        off = ((t2 - t1) + (t3 - t4)) / 2.0
        self.samples.append(((t1 + t4) / 2.0, off, rtt))
        self.samples = self.samples[-self.window:]
        self._fit()
        return off, rtt

    def _fit(self):
        s = sorted(self.samples, key=lambda x: x[2])
        s = s[:max(2, int(len(s) * self.keep))] if len(s) > 2 else s
        n = len(s)
        mx = sum(x[0] for x in s) / n
        my = sum(x[1] for x in s) / n
        sxx = sum((x[0] - mx) ** 2 for x in s)
        slope = sum((x[0] - mx) * (x[1] - my) for x in s) / sxx if n >= 4 and sxx > 1e-9 else 0.0
        self.ref, self.offset, self.drift = mx, my, max(-500e-6, min(500e-6, slope))

    def to_leader(self, t_local):
        return t_local + self.offset + self.drift * (t_local - self.ref)

    def to_local(self, t_leader):
        return (t_leader - self.offset + self.drift * self.ref) / (1.0 + self.drift)

    @property
    def ready(self):
        return len(self.samples) >= 4


class ClockServer(threading.Thread):
    """Leder: svarer på klokkeforespørsler."""

    def __init__(self, port=0, host="0.0.0.0", clock=now):
        super().__init__(daemon=True)
        self.clock = clock
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.port = self.sock.getsockname()[1]
        self.running = True

    def run(self):
        self.sock.settimeout(0.5)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(64)
            except socket.timeout:
                continue
            except OSError:
                break
            t2 = self.clock()
            if len(data) != struct.calcsize(_FMT) or data[:4] != MAGIC:
                continue
            _, t1, _, _ = struct.unpack(_FMT, data)
            self.sock.sendto(struct.pack(_FMT, MAGIC, t1, t2, self.clock()), addr)

    def stop(self):
        self.running = False
        self.sock.close()


class ClockClient:
    """Følger: spør lederen jevnlig og holder en ClockEstimator oppdatert."""

    def __init__(self, host, port, clock=now):
        self.addr, self.clock = (host, port), clock
        self.est = ClockEstimator()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.2)

    def poll(self, n=1):
        for _ in range(n):
            t1 = self.clock()
            self.sock.sendto(struct.pack(_FMT, MAGIC, t1, 0, 0), self.addr)
            try:
                data = self.sock.recv(64)
            except socket.timeout:
                continue
            t4 = self.clock()
            _, r1, t2, t3 = struct.unpack(_FMT, data)
            if r1 == t1:
                self.est.add(t1, t2, t3, t4)
        return self.est
