// «Romlig stereo» (Lyd) og «Synk-motor og trådløs sub» (Grupper og surround). Begge lagres som Skjold-plugins
// (xtc / sync) i daemonen, som bygger CamillaDSP-blokkene (pi/skjold_xtc.py, pi/skjold_sync/).
import { useEffect, useState } from 'preact/hooks';
import { api } from '../lib/api';

type Cfg = Record<string, any>;
const A = '#d9a441';
const box = 'display:flex;flex-direction:column;gap:10px;padding:14px;border-radius:14px;background:#141415;border:1px solid #242426';
const lbl = 'font-size:12px;color:#8b8b86';
const btn = (on = false) => `height:32px;padding:0 12px;border-radius:999px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12px;cursor:pointer`;

function usePlugin(id: string): [Cfg | null, (b: Cfg) => void, string] {
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.plugins().then((r) => { const p = r.plugins.find((x) => x.id === id); if (p) setCfg({ ...p.cfg, enabled: p.enabled }); }).catch(() => setErr('Ikke tilkoblet')); }, [id]);
  const set = (b: Cfg) => {
    setCfg((c) => ({ ...(c ?? {}), ...b }));
    api.setPlugin(id, b).then((r) => { const p = r.plugins.find((x) => x.id === id); if (p) setCfg({ ...p.cfg, enabled: p.enabled }); setErr(''); }).catch((e) => setErr(String(e?.message ?? e)));
  };
  return [cfg, set, err];
}

function Range({ label, v, min, max, step = 1, unit, on }: { label: string; v: number; min: number; max: number; step?: number; unit: string; on: (v: number) => void }) {
  const [x, setX] = useState(v);
  useEffect(() => setX(v), [v]);
  return (
    <label style="display:flex;flex-direction:column;gap:4px">
      <span style="display:flex;justify-content:space-between;font-size:13px"><span>{label}</span><span style="color:#c9c9c4">{String(x).replace('.', ',')} {unit}</span></span>
      <input type="range" min={min} max={max} step={step} value={x} onInput={(e) => setX(+e.currentTarget.value)} onChange={(e) => on(+e.currentTarget.value)} style="width:100%;accent-color:#d9a441" aria-label={label} />
    </label>
  );
}

function Switch({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) {
  return <button role="switch" aria-checked={on} aria-label={label} onClick={() => set(!on)} style={`width:44px;height:26px;border-radius:13px;border:none;background:${on ? A : '#3a3a3c'};position:relative;cursor:pointer;flex-shrink:0`}><i style={`position:absolute;top:3px;left:${on ? 21 : 3}px;width:20px;height:20px;border-radius:50%;background:#fff`} /></button>;
}

export function SpatialCard() {
  const [c, set, err] = usePlugin('xtc');
  if (!c) return null;
  return (
    <div style={box} data-testid="xtc-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Romlig stereo</span><span style={lbl}>Krysstalekansellering for skrivebordet – bredere lydbilde når du sitter midt foran høyttalerne.</span></div>
        <Switch on={!!c.enabled} set={(v) => set({ enabled: v })} label="Romlig stereo" />
      </div>
      {c.enabled && <>
        <Range label="Styrke" v={c.strength} min={0} max={100} unit="%" on={(v) => set({ strength: v })} />
        <Range label="Avstand mellom høyttalerne" v={c.span_cm} min={20} max={200} unit="cm" on={(v) => set({ span_cm: v })} />
        <Range label="Avstand til deg" v={c.dist_cm} min={30} max={200} unit="cm" on={(v) => set({ dist_cm: v })} />
        <button style={btn()} onClick={() => void api.xtcTest()}>Lyttetest</button>
      </>}
      {err && <span style="font-size:11px;color:#e0796b">{err}</span>}
    </div>
  );
}

export function SyncSubCard() {
  const [c, set, err] = usePlugin('sync');
  const [hosts, setHosts] = useState('');
  useEffect(() => { if (c) setHosts(c.role === 'leader' ? (c.followers ?? []).join(', ') : c.leader ?? ''); }, [c?.role]);
  if (!c) return null;
  const role = c.enabled ? c.role : 'off';
  return (
    <div style={box} data-testid="sync-card">
      <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Synk-motor (uten Lyrion)</span><span style={lbl}>Lederen sender lyden med tidsstempler, følgerne spiller den av på samme tidspunkt (mål: under 1 ms).</span></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">{([['off', 'Av'], ['leader', 'Leder'], ['follower', 'Følger']] as const).map(([k, n]) => <button key={k} style={btn(role === k)} onClick={() => set({ enabled: k !== 'off', role: k })}>{n}</button>)}</div>
      {role !== 'off' && <>
        <label style="display:flex;flex-direction:column;gap:4px"><span style="font-size:13px">{role === 'leader' ? 'Følgere (IP, kommaseparert)' : 'Leder (IP)'}</span>
          <input value={hosts} onInput={(e) => setHosts(e.currentTarget.value)} onBlur={() => set(role === 'leader' ? { followers: hosts.split(',').map((s) => s.trim()).filter(Boolean) } : { leader: hosts.trim() })} style="height:34px;border-radius:8px;border:1px solid #2e2e30;background:#0b0b0c;color:#f2f2ee;padding:0 10px" /></label>
        {role === 'leader' && <Range label="Buffer" v={c.buffer_ms} min={100} max={500} step={10} unit="ms" on={(v) => set({ buffer_ms: v })} />}
        <Range label="Forsinkelse for dette rommet" v={c.room_delay_ms} min={0} max={100} step={0.5} unit="ms" on={(v) => set({ room_delay_ms: v })} />
      </>}
      <div style="height:1px;background:#242426;margin:4px 0" />
      <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Sub</span><span style={lbl}>Bruk en Core eller Node som trådløs subwoofer for et rom. Hovedenheten får høypass (LR4, 24 dB/okt).</span></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">{([['off', 'Ingen sub'], ['main', 'Har sub'], ['sub', 'Er sub']] as const).map(([k, n]) => <button key={k} style={btn(c.sub_mode === k)} onClick={() => set({ enabled: true, sub_mode: k })}>{n}</button>)}</div>
      {c.sub_mode !== 'off' && <>
        {c.sub_mode === 'sub' && <label style="display:flex;flex-direction:column;gap:4px"><span style="font-size:13px">Sub for rom</span><input value={c.sub_for} onChange={(e) => set({ sub_for: e.currentTarget.value })} style="height:34px;border-radius:8px;border:1px solid #2e2e30;background:#0b0b0c;color:#f2f2ee;padding:0 10px" /></label>}
        <Range label="Delefrekvens" v={c.sub_xover} min={60} max={150} unit="Hz" on={(v) => set({ sub_xover: v })} />
        {c.sub_mode === 'sub' && <>
          <div style="display:flex;gap:6px;align-items:center"><span style="font-size:13px;flex:1">Fase</span>{[0, 180].map((p) => <button key={p} style={btn(c.sub_phase === p)} onClick={() => set({ sub_phase: p })}>{p}°</button>)}</div>
          <Range label="Finjustering (forsinkelse)" v={c.sub_fine_ms} min={0} max={20} step={0.1} unit="ms" on={(v) => set({ sub_fine_ms: v })} />
          <Range label="Nivå" v={c.sub_level} min={-15} max={6} step={0.5} unit="dB" on={(v) => set({ sub_level: v })} />
        </>}
        <button style={btn()} onClick={() => void api.xtcTest()}>Test</button>
      </>}
      {err && <span style="font-size:11px;color:#e0796b">{err}</span>}
    </div>
  );
}
