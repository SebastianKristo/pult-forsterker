import skjold_mini as mini

PLAYERS = {"players_loop": [
    {"playerid": "AA:BB:CC:00:00:01", "name": "Stue", "model": "squeezelite", "modelname": "SqueezeLite", "connected": 1},
    {"playerid": "24:0a:c4:11:22:33", "name": "Skjold Mini bad", "model": "squeezelite", "modelname": "SqueezeESP32",
     "ip": "192.168.1.40:51234", "connected": 1, "power": 1, "isplaying": 0},
    {"playerid": "24:0a:c4:44:55:66", "name": "Kjøkken", "model": "squeezelite", "modelname": "SqueezeESP32", "connected": 0},
    {"playerid": "00:04:20:aa:bb:cc", "name": "Gammel Boom", "model": "boom", "modelname": "Squeezebox Boom"},
]}


def test_finds_only_minis_and_skips_own():
    out = mini.parse_players(PLAYERS, own_id="aa:bb:cc:00:00:01", sync_ids=["24:0A:C4:11:22:33"])
    assert [m["name"] for m in out] == ["Kjøkken", "Skjold Mini bad"]
    bad = out[1]
    assert bad["ip"] == "192.168.1.40" and bad["connected"] and bad["power"] and bad["synced"]
    assert not out[0]["connected"] and not out[0]["synced"]


def test_parse_sync():
    assert mini.parse_sync({"_sync": "-"}) == []
    assert mini.parse_sync({"_sync": "a,b"}) == ["a", "b"]
    assert mini.parse_sync({}) == []


def test_actions_send_right_lyrion_commands():
    calls = []

    def rpc(player, cmd):
        calls.append((player, cmd))
        if cmd[0] == "players":
            return PLAYERS
        if cmd[:2] == ["sync", "?"]:
            return {"_sync": "-"}
        if cmd[:2] == ["mixer", "volume"] and cmd[2] == "?":
            return {"_volume": "35"}
        return {}
    m = mini.Minis(rpc, lambda: "aa:bb:cc:00:00:01")
    lst = m.list()
    assert lst["lyrion"] and lst["minis"][1]["volume"] == 35
    calls.clear()
    m.act({"id": "24:0a:c4:11:22:33", "action": "sync"})
    assert calls[0] == ("aa:bb:cc:00:00:01", ["sync", "24:0a:c4:11:22:33"])
    calls.clear()
    m.act({"id": "24:0a:c4:11:22:33", "action": "volume", "value": 140})
    assert calls[0] == ("24:0a:c4:11:22:33", ["mixer", "volume", "100"])
    calls.clear()
    m.act({"id": "24:0a:c4:11:22:33", "action": "unsync"})
    assert calls[0] == ("24:0a:c4:11:22:33", ["sync", "-"])


def test_no_lyrion():
    def rpc(player, cmd):
        raise RuntimeError("Lyrion ikke funnet")
    assert mini.Minis(rpc, lambda: "").list()["lyrion"] is False
