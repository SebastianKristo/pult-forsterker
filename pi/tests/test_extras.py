import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_extras as x  # noqa: E402


def _state():
    return {"settings": {"name": 1, "ndPass": "hemmelig", "eq": {"air": {"preset": 2}},
                         "plugins": {"mqtt": {"enabled": True, "host": "nas", "password": "mqttpw"},
                                     "record": {"enabled": True, "smb_password": "smbpw", "smb_share": "//nas/m"}}},
            "presets": [{"title": "NRK P1", "url": "http://p1"}, None], "volume": 30, "levels": {"radio": 90}}


def test_backup_restore_roundtrip_encrypted():
    st = _state()
    b = x.make_backup(st, {"name": "Stue"}, secrets_mode="encrypt", passphrase="hemmelig123")
    assert b["state"]["settings"]["ndPass"] == ""
    assert b["state"]["settings"]["plugins"]["mqtt"]["password"] == ""
    assert "hemmelig" not in str(b["state"])
    new = {"settings": {}, "presets": [], "volume": 10}
    prev = x.preview_restore(new, b, "all")
    assert any("plugin: mqtt" in c for c in prev["changes"]) and prev["has_secrets"]
    with pytest.raises(ValueError):
        x.apply_restore(new, b, "all", "feil-passfrase")
    x.apply_restore(new, b, "all", "hemmelig123")
    assert new["settings"]["ndPass"] == "hemmelig"
    assert new["settings"]["plugins"]["record"]["smb_password"] == "smbpw"
    assert new["presets"][0]["title"] == "NRK P1" and new["volume"] == 30


def test_backup_without_secrets_keeps_existing_and_settings_mode():
    st = _state()
    b = x.make_backup(st, {"name": "Stue"})
    assert "secrets_omitted" in b and b["secrets"] is None
    cur = {"settings": {"ndPass": "behold", "plugins": {"mqtt": {"password": "behold"}}}}
    x.apply_restore(cur, b, "settings")
    assert cur["settings"]["ndPass"] == "behold"           # tom hemmelighet sletter ikke
    assert cur["settings"]["plugins"] == {"mqtt": {"password": "behold"}}   # plugins røres ikke i «bare innstillinger»
    x.apply_restore(cur, b, "all")
    assert cur["settings"]["plugins"]["mqtt"]["password"] == "behold" and cur["settings"]["plugins"]["mqtt"]["host"] == "nas"


def test_restore_rejects_garbage():
    with pytest.raises(ValueError):
        x.preview_restore({}, {"hei": 1})


def test_rotate_backups(tmp_path):
    for i in range(20):
        (tmp_path / ("skjold-backup-Stue-202611%02d-0300.json" % (i + 1))).write_text("{}")
    gone = x.rotate_backups(str(tmp_path), keep=14)
    assert len(gone) == 6 and len(os.listdir(tmp_path)) == 14
    assert x.backup_filename("Stue Rom!", 0).startswith("skjold-backup-Stue-Rom-")


def test_autostandby_timing():
    a = x.AutoStandby()
    t = 1000.0
    assert not a.tick(t, 1, True, False)
    for i in range(1, 13):
        hit = a.tick(t + i * 5, 1, True, False)
    assert hit and a.idle_s >= 60
    a2 = x.AutoStandby()
    a2.tick(t, 1, True, False)
    for i in range(1, 30):
        assert not a2.tick(t + i * 5, 1, True, True)   # spiller → aldri standby
    a3 = x.AutoStandby()
    a3.tick(t, 1, True, False)
    for i in range(1, 30):
        assert not a3.tick(t + i * 5, 1, True, False, paused=True, pause_counts=False)   # pause teller ikke
    assert a3.left(1) == 60


def test_wrapped_aggregation(tmp_path):
    w = x.Wrapped(str(tmp_path / "wrapped.json"))
    t = time.mktime((2026, 3, 14, 20, 0, 0, 0, 0, -1))
    for i in range(120):   # 2 timer radio i strekk
        w.listen(t + i * 60, 60, "radio", "Stue")
    w.listen(t + 10_000, 600, "airplay", "Kjøkken")
    for _ in range(3):
        w.track(t, "a-ha", "Take On Me", "NRK P1")
    w.track(t, "Röyksopp", "Eple")
    w.save()
    s = x.Wrapped(str(tmp_path / "wrapped.json")).summary(2026)
    assert s["minutes"] == 130 and s["plays"] == 4
    assert s["artists"][0]["name"] == "a-ha" and s["tracks"][0]["count"] == 3
    assert s["stations"][0]["name"] == "NRK P1"
    assert s["by_input"][0]["name"] == "radio" and s["rooms"] == 2
    assert s["busiest_day"]["date"] == "2026-03-14" and s["busiest_hour"]["hour"] in (20, 21)
    assert s["longest_session"] >= 119
    assert x.Wrapped(str(tmp_path / "w2.json")).summary(2025)["empty"]


def test_roon_and_plex_commands():
    assert x.roon_installer_url("armv8").endswith("roonbridge-installer-linuxarmv8.sh")
    assert x.roon_installer_url("x64").endswith("roonbridge-installer-linuxx64.sh")
    with pytest.raises(ValueError):
        x.roon_installer_url("mips")
    cmd = x.roon_install_cmd("x64")
    assert cmd[0] == "bash" and "download.roonlabs.net" in cmd[-1] and "yes |" in cmd[-1]
    assert x.plex_install_cmd("/src/pi/install_plex.sh", "pi")[-2:] == ["bash", "/src/pi/install_plex.sh"]
    assert "KI_PLEX_SKIP_LOGIN=1" in x.plex_install_cmd("s")
    assert x.plex_claim_input("claim-AbC123xyz", "Stue") == "claim-AbC123xyz\nStue\n"
    with pytest.raises(ValueError):
        x.plex_claim_input("123", "Stue")


def test_pcm_open_by(tmp_path):
    p = tmp_path / "123"
    (p / "fd").mkdir(parents=True)
    (p / "comm").write_text("RAATServer\n")
    os.symlink("/dev/snd/pcmC1D0p", p / "fd" / "7")
    assert x.pcm_open_by({"RAATServer"}, proc=str(tmp_path))
    assert not x.pcm_open_by({"annen"}, proc=str(tmp_path))
