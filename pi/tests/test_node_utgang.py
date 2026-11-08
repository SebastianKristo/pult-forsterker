"""Node/Core: lydutgangen som velges i appen (settings.out), bl.a. UCA222 på USB."""
import os
import sys

os.environ["KI_AMP_BOARD"] = "node"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

CARDS = """ 0 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones
                      bcm2835 Headphones
 1 [CODEC          ]: USB-Audio - USB Audio CODEC
                      BurrBrown from Texas Instruments USB AUDIO  CODEC at usb-0000:01:00.0-1.3, full speed
"""


def _d():
    import ki_amp_daemon as d
    return d


def test_usb_kort_fra_proc(tmp_path):
    d = _d()
    f = tmp_path / "cards"; f.write_text(CARDS)
    assert d.usb_audio_cards(str(f)) == [("CODEC", "USB Audio CODEC")]
    assert d.usb_audio_cards(str(tmp_path / "mangler")) == []


def test_valgt_utgang(monkeypatch):
    d = _d()
    if d.BOARD != "node":
        return   # daemonen var allerede lastet med et annet kort i samme testkjøring
    st = d.state.setdefault("settings", {})
    old = st.get("out")
    try:
        st.pop("out", None)
        assert d.dsp_playback() == d.DSP_PLAYBACK and d.dsp_format() == d.DSP_FORMAT   # ikke valgt: som installert
        monkeypatch.setattr(d, "usb_audio_cards", lambda: [("CODEC", "USB Audio CODEC")])
        st["out"] = 2
        assert d.dsp_playback() == "plughw:CODEC" and d.dsp_format() == "S16LE"
        assert 'device: "plughw:CODEC", format: S16LE' in d.dsp_config()
        monkeypatch.setattr(d, "usb_audio_cards", lambda: [])
        assert d.dsp_playback() == d.DSP_PLAYBACK   # UCA222 ikke koblet til
        st["out"] = 3
        assert d.dsp_playback() == d.DSP_PLAYBACK
    finally:
        if old is None: st.pop("out", None)
        else: st["out"] = old
