"""CamillaDSP-blokker for romlig stereo (XTC), synk-forsinkelse og trådløs sub. Holdes utenfor daemonen så
dsp_config() bare trenger én krok: extra(xtc_cfg, sync_cfg, dir) -> (filters, mixers, pipeline-steg)."""
import os

DEFAULTS_XTC = {"strength": 70, "span_cm": 50, "dist_cm": 60, "mode": "stereo", "surround": 60, "width": 50, "offset_cm": 0}
DEFAULTS_PLACEMENT = {"layout": "2.0", "speakers": [], "trims": {}, "result": {}, "measured": 0}
DEFAULTS_SYNC = {"role": "off", "leader": "", "followers": [], "buffer_ms": 200, "room_delay_ms": 0,
                 "sub_mode": "off", "sub_for": "", "sub_xover": 80, "sub_phase": 0, "sub_fine_ms": 0.0, "sub_level": 0.0}


def _clamp(v, lo, hi, t=float):
    return max(lo, min(hi, t(v)))


def sanitize(k, v):
    """Returnerer renset verdi for kjente nøkler, ellers v uendret."""
    if k == "strength": return _clamp(v, 0, 100, int)
    if k == "span_cm": return _clamp(v, 20, 300, int)
    if k == "mode":
        if v not in ("stereo", "surround"): raise ValueError("modus må være stereo eller surround")
        return v
    if k in ("surround", "width"): return _clamp(v, 0, 100, int)
    if k == "offset_cm": return _clamp(v, -100, 100, int)
    if k == "layout":
        if v not in ("2.0", "3.0", "5.1"): raise ValueError("oppsett må være 2.0, 3.0 eller 5.1")
        return v
    if k == "trims":
        out = {}
        for ch, t in dict(v or {}).items():
            if ch in ("L", "R"):
                out[ch] = {"delay_ms": _clamp((t or {}).get("delay_ms", 0), 0, 50), "gain_db": _clamp((t or {}).get("gain_db", 0), -15, 3)}
        return out
    if k == "speakers":
        return [{"name": str(x.get("name", ""))[:60], "host": str(x.get("host", ""))[:100], "channel": x.get("channel", "both") if x.get("channel") in ("L", "R", "both") else "both",
                 "role": str(x.get("role", ""))[:4]} for x in (v or [])][:8]
    if k == "dist_cm": return _clamp(v, 30, 400, int)
    if k == "buffer_ms": return _clamp(v, 100, 500, int)
    if k == "room_delay_ms": return _clamp(v, 0, 500, float)
    if k == "role":
        if v not in ("off", "leader", "follower"): raise ValueError("rolle må være off, leader eller follower")
        return v
    if k == "sub_mode":
        if v not in ("off", "main", "sub"): raise ValueError("sub-modus må være off, main eller sub")
        return v
    if k in ("leader", "sub_for"): return str(v or "")[:100]
    if k == "followers": return [str(x)[:100] for x in (v or [])][:16]
    if k == "sub_xover": return _clamp(v, 60, 150, int)
    if k == "sub_phase":
        if int(v) not in (0, 180): raise ValueError("fase må være 0 eller 180")
        return int(v)
    if k == "sub_fine_ms": return _clamp(v, 0, 20, float)
    if k == "sub_level": return _clamp(v, -15, 6, float)
    return v


def channel_trims(xtc=None, placement=None):
    """Kanalvis forsinkelse/nivå: lytter utenfor midten (xtc.offset_cm) + målt plassering (placement.trims)."""
    t = {"L": [0.0, 0.0], "R": [0.0, 0.0]}
    if xtc and xtc.get("enabled") and int(xtc.get("offset_cm", 0) or 0):
        import skjold_spatial
        o = skjold_spatial.trims(xtc.get("span_cm", 50), xtc.get("dist_cm", 60), int(xtc["offset_cm"]))
        for ch in t:
            t[ch][0] += o[ch]["delay_ms"]; t[ch][1] += o[ch]["gain_db"]
    if placement and placement.get("enabled"):
        for ch, v in (placement.get("trims") or {}).items():
            if ch in t:
                t[ch][0] += float(v.get("delay_ms", 0)); t[ch][1] += float(v.get("gain_db", 0))
    return t


def extra(xtc=None, sync=None, xtc_dir="/var/lib/skjold/xtc", placement=None):
    filt, mix, steps = "", "", []
    sync = sync or {}
    on = bool(sync.get("enabled"))
    mode = sync.get("sub_mode", "off") if on else "off"
    if mode == "sub":
        mix += """
  sub_mono:
    channels: {in: 2, out: 2}
    mapping:
      - dest: 0
        sources: [{channel: 0, gain: -6.0}, {channel: 1, gain: -6.0}]
      - dest: 1
        sources: [{channel: 0, gain: -6.0}, {channel: 1, gain: -6.0}]"""
        steps.append("  - type: Mixer\n    name: sub_mono")
        filt += f"""
  sub_lp:
    type: BiquadCombo
    parameters: {{type: LinkwitzRileyLowpass, freq: {int(sync.get('sub_xover', 80))}, order: 4}}
  sub_gain:
    type: Gain
    parameters: {{gain: {float(sync.get('sub_level', 0)):.1f}, inverted: {'true' if int(sync.get('sub_phase', 0)) == 180 else 'false'}}}"""
        names = ["sub_lp", "sub_gain"]
        if float(sync.get("sub_fine_ms", 0)) > 0:
            filt += f"""
  sub_fine:
    type: Delay
    parameters: {{delay: {float(sync['sub_fine_ms']):.2f}, unit: ms}}"""
            names.append("sub_fine")
        for c in (0, 1):
            steps.append(f"  - type: Filter\n    channel: {c}\n    names: [{', '.join(names)}]")
    elif xtc and xtc.get("enabled") and float(xtc.get("strength", 0)) > 0:
        try:
            import skjold_xtc
            os.makedirs(xtc_dir, exist_ok=True)
            if xtc.get("mode") == "surround":     # virtuell surround: HRTF + XTC i samme 2×2-matrise
                import skjold_spatial
                pd, pc = skjold_spatial.write(xtc_dir, xtc)
            else:
                pd, pc = skjold_xtc.write(xtc_dir, xtc.get("span_cm", 50), xtc.get("dist_cm", 60), float(xtc["strength"]) / 100.0)
            f, m, s = skjold_xtc.dsp_yaml(pd, pc)
            filt += f; mix += m; steps += s
        except Exception as e:  # pragma: no cover - mangler skrivetilgang e.l.
            print("XTC av:", e)
    if mode == "main":
        filt += f"""
  sub_hp:
    type: BiquadCombo
    parameters: {{type: LinkwitzRileyHighpass, freq: {int(sync.get('sub_xover', 80))}, order: 4}}"""
        for c in (0, 1):
            steps.append(f"  - type: Filter\n    channel: {c}\n    names: [sub_hp]")
    if mode != "sub":
        for i, (ch, (d, g)) in enumerate(channel_trims(xtc, placement).items()):
            names = []
            if d > 0.001:
                filt += f"""
  trim_d{ch}:
    type: Delay
    parameters: {{delay: {d:.3f}, unit: ms, subsample: true}}"""
                names.append(f"trim_d{ch}")
            if abs(g) > 0.01:
                filt += f"""
  trim_g{ch}:
    type: Gain
    parameters: {{gain: {g:.2f}}}"""
                names.append(f"trim_g{ch}")
            if names:
                steps.append(f"  - type: Filter\n    channel: {i}\n    names: [{', '.join(names)}]")
    delay = (float(sync.get("buffer_ms", 200)) if on and sync.get("role") == "leader" else 0.0) + (float(sync.get("room_delay_ms", 0)) if on else 0.0)
    if delay > 0:
        filt += f"""
  sync_delay:
    type: Delay
    parameters: {{delay: {delay:.1f}, unit: ms}}"""
        for c in (0, 1):
            steps.append(f"  - type: Filter\n    channel: {c}\n    names: [sync_delay]")
    return filt, mix, steps
