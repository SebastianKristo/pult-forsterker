"""Skjold S1 rev F: knappelogikk, kontrakten mot skjold-ui, nattmodus-MQTT og WebSocket-protokollen (uten GPIO)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skjold_s1f as s1  # noqa: E402


class Api:
    def __init__(self, **st):
        self.state = {"power": True, "input": "airplay", "volume": 30, "mute": False, "bt_pairing": False, "preset": 2,
                      "last_wireless": "airplay", "headphones": False, "hp_volume": 20, **st}
        self.calls = []; self.menu = False; self.sett = {"dblPower": 0, "hpOwn": True}; self.consume = False; self.ui = []

    def __getattr__(self, n):
        return lambda *a: self.calls.append((n,) + a)

    def settings(self): return self.sett
    def ui_event(self, ev, src, d=0):
        self.ui.append((ev, src, d)); return self.consume
    def smenu_is_open(self): return self.menu
    def smenu_idx(self): return 0 if self.menu else None


def mk(**st):
    a = Api(**st)
    return a, s1.S1FControls(a)


def click(c, name, t, dur=0.05):
    c.press(name, t); c.tick(t + dur); c.release(name, t + dur)


def test_pins_file_parses_without_pyyaml():
    p = os.path.join(os.path.dirname(__file__), "..", "config", "s1f_pins.yaml")
    with open(p) as fh:
        cfg = s1.parse_yaml(fh.read())
    used = list(cfg["buttons"].values()) + list(cfg["leds"].values()) + list(cfg["encoder"].values()) + \
        [cfg["relay"], cfg["dac_xsmt"], cfg["headphone_detect"], cfg["usb_switch"]["pulse"], cfg["usb_switch"]["sense"]]
    assert len(used) == len(set(used)), "samme pinne brukt to ganger"
    assert not set(used) & {0, 1, 2, 3, 18, 19, 21}, "I²S/I²C/EEPROM-pinner er reservert"
    assert cfg["timing"]["click_window"] == 0.38 and cfg["led_active_high"] is True and cfg["usb_switch"]["sense_pc1"] == "low"


def test_power_single_click_waits_for_window():
    a, c = mk()
    click(c, "power", 0.0)
    c.tick(0.2); assert ("set_power", False) not in a.calls
    c.tick(0.5); assert ("set_power", False) in a.calls and ("power_event", "single_press") in a.calls


def test_power_double_click_is_night_mode_not_power():
    a, c = mk()
    click(c, "power", 0.0); click(c, "power", 0.2)
    c.tick(1.0)
    assert ("night_toggle", "Skjold") in a.calls and ("power_event", "double_press") in a.calls
    assert not any(x[0] == "set_power" for x in a.calls)


def test_double_press_off_setting_only_sends_event():
    a, c = mk(); a.sett["dblPower"] = 1
    click(c, "power", 0.0); click(c, "power", 0.1)
    assert ("power_event", "double_press") in a.calls and not any(x[0] == "night_toggle" for x in a.calls)


def test_power_hold_reboots_and_shows_ring():
    a, c = mk()
    c.press("power", 0.0); c.tick(0.2); assert c.ui["hold"] is None
    c.tick(1.5); h = c.ui["hold"]
    assert (h["kind"], h["p"], h["stage"], h["left"]) == ("reboot", 0.5, 0, 1.5)
    c.tick(3.0); c.release("power", 3.1); c.tick(4.0)
    assert ("reboot",) in a.calls and not any(x[0] == "set_power" for x in a.calls)


def test_encoder_clicks_and_hold():
    a, c = mk()
    click(c, "enc", 0.0); c.tick(1.0); assert ("set_mute", True) in a.calls
    click(c, "enc", 2.0); click(c, "enc", 2.2); c.tick(3.0); assert ("transport", "next") in a.calls
    click(c, "enc", 4.0); click(c, "enc", 4.1); click(c, "enc", 4.2); assert ("transport", "previous") in a.calls
    c.press("enc", 6.0); c.tick(7.6); c.release("enc", 7.7); assert ("smenu_open",) in a.calls


def test_encoder_in_settings_navigates():
    a, c = mk(); a.menu = True
    c.rotate(1); c.rotate(-1); click(c, "enc", 0.0); c.tick(1)
    assert ("smenu_step", 1) in a.calls and ("smenu_step", -1) in a.calls and ("smenu_press",) in a.calls
    assert c.ui["screen"] == "settings" and c.ui["sel"] == 0


def test_rotate_sets_volume_and_overlay():
    a, c = mk()
    c.rotate(1); assert ("set_volume", 31) in a.calls and c.ui["overlay"] == {"type": "volume"}
    a.state["headphones"] = True; c.rotate(-1); assert ("set_volume", 19) in a.calls   # eget hodetelefonvolum


def test_bt_button_toggles_and_pairs():
    a, c = mk()
    click(c, "bt", 0.0); assert ("set_input", "bt") in a.calls
    a2, c2 = mk(input="radio", last_wireless="bt"); click(c2, "bt", 0.0); assert ("set_input", "bt") in a2.calls
    a3, c3 = mk(); c3.press("bt", 0.0); c3.tick(2.1); c3.release("bt", 2.2); assert ("bt_pairing", True) in a3.calls
    a4, c4 = mk(bt_pairing=True); click(c4, "bt", 0.0); assert ("bt_pairing", False) in a4.calls


def test_aux_radio_usb():
    a, c = mk(input="aux"); click(c, "aux", 0.0); assert ("set_input", "aux2") in a.calls
    a, c = mk(input="airplay"); click(c, "radio", 0.0); assert ("set_input", "radio") in a.calls
    a, c = mk(input="radio"); click(c, "radio", 0.0); assert ("step_preset", 1) in a.calls
    a, c = mk(input="radio"); c.press("radio", 0.0); c.tick(0.5); assert c.ui["hold"] is None   # radio viser ring først etter 0,9 s
    c.tick(1.5); assert c.ui["hold"]["kind"] == "save"; c.tick(3.0); assert ("save_preset", 2) in a.calls
    a, c = mk(input="usb"); click(c, "usb", 0.0); assert ("usb_toggle",) in a.calls


def test_events_go_to_skjold_ui_first():
    a, c = mk()
    click(c, "bt", 0.0); c.rotate(-1); c.press("enc", 1.0); c.tick(2.6); c.release("enc", 2.7)
    assert a.ui == [("press", "air", 1), ("turn", "knob", -1), ("hold", "knob", 1)]
    a2, c2 = mk(); a2.consume = True   # hilsen vises / menyen er åpen: skjermen bruker hendelsen
    click(c2, "radio", 0.0); c2.rotate(1); c2.press("power", 1.0); c2.tick(4.5)
    assert [x for x in a2.calls if x[0] != "input_event"] == []      # aktivitet telles, men ingen handling utføres


def test_hold_status_for_screen():
    a, c = mk()
    c.press("enc", 0.0); c.tick(0.75)
    assert c.hold == {"key": "knob", "p": 0.5}
    c.release("enc", 0.8); assert c.hold is None


def test_led_frame():
    a, c = mk(input="aux2")
    f = c.led_frame(10.0, a.state, 0.55)
    assert f["aux"] == 0.55 and f["bt"] == 0 and f["power"] == 0.55
    a.state["bt_pairing"] = True
    on, off = c.led_frame(0.1, a.state)["bt"], c.led_frame(0.4, a.state)["bt"]
    assert on == 1.0 and off == 0.0
    a.state["power"] = False; assert c.led_frame(10.0, a.state)["aux"] == 0


def test_mqtt_night_discovery():
    msgs = dict(s1.mqtt_night_discovery("skjold/stue", "stue", {"identifiers": ["stue"]}))
    trig = msgs["homeassistant/device_automation/stue/power_double/config"]
    assert trig["type"] == "button_double_press" and trig["subtype"] == "power" and trig["payload"] == "double_press"
    ev = msgs["homeassistant/event/stue/power/config"]
    assert ev["event_types"] == ["single_press", "double_press", "long_press"]
    sw = msgs["homeassistant/switch/stue/nattmodus/config"]
    assert sw["state_topic"] == "skjold/stue/night" and sw["command_topic"] == "skjold/stue/set/night"
    assert "homeassistant/button/stue/night/config" in msgs
    assert s1.parse_steps(json.dumps([{"name": "Lys av", "done": True}, {"name": "Lås dør"}])) == \
        [{"name": "Lys av", "done": True}, {"name": "Lås dør", "done": False}]
    assert s1.parse_steps("ikke json") is None


def test_ws_commands():
    a = Api(input="radio")
    for m in ({"type": "vol", "v": 44}, {"type": "src", "v": 3}, {"type": "input", "i": 1}, {"type": "wl", "v": "bt"},
              {"type": "nightState", "on": True, "src": "Home Assistant", "steps": []}, {"type": "nightState", "on": True, "src": "S1"},
              {"type": "set", "k": "led", "v": 2}, {"type": "pause"}, {"type": "presets", "list": [["NRK P3", "http://x"]]}):
        s1.ws_command(m, a)
    assert ("set_volume", 44) in a.calls and ("play_preset", 4) in a.calls and ("set_input", "aux") in a.calls
    assert ("set_input", "bt") in a.calls and ("night_set", True, "Home Assistant", []) in a.calls
    assert sum(1 for x in a.calls if x[0] == "night_set") == 1   # src S1 = eget ekko, ignoreres
    assert ("settings_patch", {"led": 2}) in a.calls and ("transport", "playpause") in a.calls
    assert ("presets_set", [{"title": "NRK P3", "url": "http://x"}]) in a.calls
    assert s1.ws_command({"type": "tull"}, a)["type"] == "error"


def test_design_state():
    st = {"power": True, "input": "aux2", "volume": 12, "mute": True, "usb_pc": 2, "preset": 3, "night": True,
          "presets": [{"title": "P1"}, None, {"title": "P3"}], "title": "T", "artist": "A", "name": "Stue"}
    st["night"] = {"on": True, "src": "Skjold", "steps": []}
    d = s1.design_state(st, {"led": 0})
    assert (d["input"], d["aux"], d["usb"], d["preset"], d["vol"], d["muted"], d["night"]) == (1, 1, 1, 2, 12, True, True)
    assert d["presets"] == ["P1", "P3"] and d["set"] == {"led": 0}


# --- rev F-prompten: power i tre trinn, tilbakestilling og USB i standby ---
def test_power_slipp_etter_3s_er_omstart_ikke_mens_den_holdes():
    a, c = mk()
    c.press("power", 0.0); c.tick(3.5)
    assert not any(x[0] in ("reboot", "factory_reset") for x in a.calls)      # ingenting skjer før knappen slippes
    assert c.ui["hold"]["kind"] == "reboot" and c.ui["hold"]["stage"] == 1
    c.release("power", 5.0)
    assert ("reboot",) in a.calls and ("factory_reset",) not in a.calls


def test_power_10s_er_tilbakestilling():
    a, c = mk()
    c.press("power", 0.0); c.tick(8.0)
    assert c.ui["hold"]["kind"] == "reset" and c.ui["hold"]["stage"] == 2 and c.ui["hold"]["left"] == 2.0
    c.tick(10.01)
    assert ("factory_reset",) in a.calls
    c.release("power", 11.0)                                                  # slippet etterpå gjør ikke noe mer
    assert sum(1 for x in a.calls if x[0] in ("reboot", "factory_reset")) == 1


def test_power_kort_trykk_er_fortsatt_standby():
    a, c = mk()
    click(c, "power", 0.0, 0.2); c.tick(0.7)
    assert ("set_power", False) in a.calls and ("reboot",) not in a.calls


def test_tilbakestilling_virker_i_standby():
    a, c = mk(power=False)
    c.press("power", 0.0); c.tick(10.5)
    assert ("factory_reset",) in a.calls


def test_usb_i_standby_bytter_pc_uten_aa_slaa_paa():
    import time
    a, c = mk(power=False, input="airplay", usb_pc=2)
    t0 = time.monotonic()
    click(c, "usb", t0)
    assert ("usb_toggle",) in a.calls
    assert not any(x[0] in ("set_power", "set_input") for x in a.calls)
    assert c.ui["overlay"] == {"type": "usb", "pc": 2}
    assert c.led_frame(t0 + 0.5, a.state)["usb"] > 0                             # LED-ringen lyser mens skjermen viser PC n
    assert c.led_frame(t0 + 2.5, a.state)["usb"] == 0
    c.tick(t0 + 2.5); assert c.ui["overlay"] is None


def test_usb_naar_paa_er_som_foer():
    a, c = mk(input="airplay")
    click(c, "usb", 0.0)
    assert ("set_input", "usb") in a.calls and ("usb_toggle",) not in a.calls

