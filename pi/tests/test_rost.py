import skjold_rost as mini

PLAYERS = {"players_loop": [
    {"playerid": "AA:BB:CC:00:00:01", "name": "Stue", "model": "squeezelite", "modelname": "SqueezeLite", "connected": 1},
    {"playerid": "24:0a:c4:11:22:33", "name": "Skjold Røst bad", "model": "squeezelite", "modelname": "SqueezeESP32",
     "ip": "192.168.1.40:51234", "connected": 1, "power": 1, "isplaying": 0},
    {"playerid": "24:0a:c4:44:55:66", "name": "Kjøkken", "model": "squeezelite", "modelname": "SqueezeESP32", "connected": 0},
    {"playerid": "00:04:20:aa:bb:cc", "name": "Gammel Boom", "model": "boom", "modelname": "Squeezebox Boom"},
]}


def test_finds_only_minis_and_skips_own():
    out = mini.parse_players(PLAYERS, own_id="aa:bb:cc:00:00:01", sync_ids=["24:0A:C4:11:22:33"])
    assert [m["name"] for m in out] == ["Kjøkken", "Skjold Røst bad"]
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


def test_presets_to_buttons():
    presets = [{"title": "NRK P1", "url": "http://p1"}, None, {"title": "P3", "url": "http://p3"}, {"title": "Jazz", "url": ""}]
    cmds = mini.preset_commands(presets, [3, 1, 2, 4, 1])
    assert cmds == [
        ["jivefavorites", "set_preset", "key:1", "favorites_url:http://p3", "favorites_title:P3", "favorites_type:audio"],
        ["jivefavorites", "set_preset", "key:2", "favorites_url:http://p1", "favorites_title:NRK P1", "favorites_type:audio"],
    ]
    calls = []
    m = mini.Minis(lambda p, c: calls.append((p, c)) or {"players_loop": []}, lambda: "own", lambda: presets)
    m.act({"id": "24:0A:C4:11:22:33", "action": "presets", "value": [1, 3]})
    assert [c for c in calls if c[1][0] == "jivefavorites"][1][0] == "24:0a:c4:11:22:33"


def test_recognizes_new_ascii_and_old_names():
    for n in ("Skjold Røst bad", "Skjold Rost kjøkken", "Skjold Mini gammel"):
        assert mini.is_mini({"name": n, "model": "x"})
    assert not mini.is_mini({"name": "Stue", "model": "squeezelite", "modelname": "SqueezeLite"})
