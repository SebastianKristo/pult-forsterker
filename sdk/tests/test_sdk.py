"""Python-SDK mot simulatoren (ekte HTTP på en ledig port)."""
import asyncio
import os
import socket
import sys
import threading
import time

import pytest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HER, "..", "python"), os.path.join(HER, "..", "simulator")]
from skjold import Skjold, SkjoldFeil  # noqa: E402
from skjold_sim.__main__ import kjor  # noqa: E402


@pytest.fixture(scope="module")
def port():
    with socket.socket() as s_:
        s_.bind(("127.0.0.1", 0)); p = s_.getsockname()[1]
    threading.Thread(target=lambda: asyncio.run(kjor("127.0.0.1", p, 2, sek=1)), daemon=True).start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", p), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    return p


def test_kommandoer(port):
    s = Skjold("127.0.0.1", port=port)
    assert s.power(True)["power"] is True
    assert s.volume(40)["volume"] == 40
    assert s.volume(delta=-5)["volume"] == 35
    assert s.mute(True)["mute"] is True
    assert s.input("bt")["input"] == "bt"
    st = s.preset(2)
    assert st["preset"] == 2 and st["input"] == "radio"
    assert s.play("http://x/a.mp3", title="Test")["title"] == "Test"
    assert s.transport("pause")["playing"] is False


def test_feil(port):
    s = Skjold("127.0.0.1", port=port)
    with pytest.raises(SkjoldFeil) as e:
        s.input("tull")
    assert e.value.status == 400
    with pytest.raises(SkjoldFeil) as e:
        s.get("/api/finnes-ikke")
    assert e.value.status == 501


def test_events_og_rom(port):
    s = Skjold("127.0.0.1", port=port)
    it = s.events()
    forste = next(it)
    assert "volume" in forste
    s.volume(12)
    assert any(x["volume"] == 12 for _, x in zip(range(5), it))
    rom = s.get("/api/rooms")["rooms"]
    assert len(rom) == 2 and rom[0]["self"] and rom[1]["port"] == port + 1
