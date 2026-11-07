import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_health as H


def test_cpu_pct_and_proc_stat():
    a = H.parse_proc_stat("cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 1 1 1 1\n")
    b = H.parse_proc_stat("cpu  150 0 150 900 0 0 0 0 0 0\n")
    assert a == (1000, 800) and b == (1200, 900)
    assert H.cpu_pct(a, b) == 50.0 and H.cpu_pct(None, b) is None


def test_throttled_flags():
    t = H.parse_throttled("0x50005")
    assert t["under_voltage"] and t["throttled"] and t["under_voltage_occurred"] and t["power_problem"]
    assert not t["freq_capped"]
    assert H.parse_throttled("0x0")["power_problem"] is False
    assert H.parse_throttled(None) is None and H.parse_throttled("zz") is None


def test_meminfo():
    m = H.parse_meminfo("MemTotal:        1024000 kB\nMemAvailable:     512000 kB\n")
    assert m == {"total_mb": 1000, "used_mb": 500, "pct": 50.0}
    assert H.parse_meminfo("") is None


def test_collect_perf_shape():
    p = H.collect_perf()
    for k in ("cpu_pct", "cpus", "load", "temp_c", "throttle", "memory", "disk", "uptime_s", "services"):
        assert k in p
