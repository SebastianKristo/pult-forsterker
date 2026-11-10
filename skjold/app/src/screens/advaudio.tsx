// «Romlig stereo» (Lyd) og «Synk-motor og trådløs sub» (Grupper og surround). Begge lagres som Skjold-plugins
// (xtc / sync) i daemonen, som bygger CamillaDSP-blokkene (pi/skjold_xtc.py, pi/skjold_sync/).
import { useEffect, useState } from 'preact/hooks';
import { api, type Placement, type PlacementResult, type PlacementSpeaker } from '../lib/api';
import { primeMic, recordMic } from '../lib/roomeq';

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

/** Mobilmåling: tar opp mens Skjold spiller en kort sweep på hver høyttaler etter tur, og sender opptaket til analyse. */
export async function measureWithPhone(onStage?: (s: string) => void): Promise<PlacementResult> {
  await primeMic();
  const pl = await api.placement();
  const n = pl.speakers_eff.length;
  const secs = 2 + 0.5 + n * 1.6 + 2;
  let tRec = 0;
  const recP = recordMic(secs, () => { tRec = Date.now() / 1000; });
  await new Promise((r) => setTimeout(r, 300));
  onStage?.('Hold mobilen der du sitter – måler ' + n + ' høyttalere …');
  const t1 = Date.now() / 1000;
  const st = await api.placementStart();
  const t2 = Date.now() / 1000;
  const off = st.now - (t1 + t2) / 2;              // serverklokke − mobilklokke
  const { data, sr } = await recP;
  onStage?.('Analyserer …');
  const pcm = new Int16Array(data.length);
  for (let i = 0; i < data.length; i++) pcm[i] = Math.max(-32768, Math.min(32767, Math.round(data[i]! * 32767)));
  return api.placementAnalyze(pcm, sr, n, Math.max(0, st.start_at - off - tRec));
}

export function SpatialCard() {
  const [c, set, err] = usePlugin('xtc');
  const [msg, setMsg] = useState('');
  if (!c) return null;
  const sur = c.mode === 'surround';
  const findSeat = async () => {
    try {
      const r = await measureWithPhone(setMsg);
      if (r.offset_cm == null) { setMsg('Fant ikke begge høyttalerne – prøv igjen litt høyere volum.'); return; }
      set({ offset_cm: Math.round(r.offset_cm) });
      setMsg(r.offset_cm === 0 ? 'Du sitter midt foran.' : `Du sitter ${Math.abs(Math.round(r.offset_cm))} cm til ${r.offset_cm > 0 ? 'venstre' : 'høyre'} – justert.`);
    } catch (e) { setMsg('Måling feilet: ' + String((e as Error)?.message ?? e) + ' (mikrofon krever HTTPS eller appen)'); }
  };
  return (
    <div style={box} data-testid="xtc-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Romlig lyd</span><span style={lbl}>{sur ? 'Virtuell surround: HRTF plasserer lyden rundt deg, krysstalekansellering gjør det hørbart fra to høyttalere.' : 'Krysstalekansellering for skrivebordet – bredere lydbilde når du sitter midt foran høyttalerne.'}</span></div>
        <Switch on={!!c.enabled} set={(v) => set({ enabled: v })} label="Romlig lyd" />
      </div>
      {c.enabled && <>
        <div style="display:flex;gap:6px">{([['stereo', 'Romlig stereo'], ['surround', 'Virtuell surround']] as const).map(([k, n]) => <button key={k} style={btn(c.mode === k)} onClick={() => set({ mode: k })}>{n}</button>)}</div>
        <Range label="Styrke" v={c.strength} min={0} max={100} unit="%" on={(v) => set({ strength: v })} />
        {sur && <>
          <Range label="Bredde foran" v={c.width} min={0} max={100} unit="%" on={(v) => set({ width: v })} />
          <Range label="Surround bak" v={c.surround} min={0} max={100} unit="%" on={(v) => set({ surround: v })} />
        </>}
        <Range label="Avstand mellom høyttalerne" v={c.span_cm} min={20} max={300} unit="cm" on={(v) => set({ span_cm: v })} />
        <Range label="Avstand til deg" v={c.dist_cm} min={30} max={400} unit="cm" on={(v) => set({ dist_cm: v })} />
        <Range label="Sitteplass (− høyre, + venstre)" v={c.offset_cm} min={-100} max={100} unit="cm" on={(v) => set({ offset_cm: v })} />
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button style={btn()} onClick={() => void findSeat()}>Finn plassen min med mobilen</button>
          <button style={btn()} onClick={() => void api.xtcTest()}>Lyttetest</button>
        </div>
        {msg && <span style="font-size:11.5px;color:#c9b48a">{msg}</span>}
      </>}
      {err && <span style="font-size:11px;color:#e0796b">{err}</span>}
    </div>
  );
}

const ROLE_NAMES: Record<string, string> = { L: 'Venstre', R: 'Høyre', C: 'Senter', Ls: 'V bak', Rs: 'H bak' };

/** Romkart: høyttalere (posisjoner fra enhetsmåling, ellers relative avstander fra mobilmåling) og lytteren i midten. */
function RoomMap({ r }: { r: PlacementResult }) {
  const W = 300, H = 220;
  let pts: { x: number; y: number; name: string }[] = [];
  const sp = r.speakers ?? [];
  if (r.positions?.length) {
    const m = Math.max(1, ...r.positions.flat().map((v) => Math.abs(v))) * 1.15;
    pts = r.positions.map(([x, y], i) => ({ x: W / 2 + (x / m) * (W / 2 - 20), y: H / 2 - (y / m) * (H / 2 - 20), name: sp[i]?.name || ROLE_NAMES[sp[i]?.role ?? ''] || '#' + (i + 1) }));
  } else if (r.align) {
    const n = r.align.length;
    pts = r.align.map((a, i) => { const ang = (n === 1 ? 0 : -60 + (120 * i) / (n - 1)) * Math.PI / 180; const rr = 70 + (a.rel_cm ?? 0) * 0.3; return { x: W / 2 + Math.sin(ang) * rr, y: H / 2 + 20 - Math.cos(ang) * rr, name: sp[i]?.name || '#' + (i + 1) }; });
  }
  const lx = W / 2, ly = r.positions?.length ? H / 2 : H / 2 + 20;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style="width:100%;max-width:360px;background:#0b0b0c;border-radius:10px;border:1px solid #242426" role="img" aria-label="Romkart">
      {pts.map((p, i) => <line key={'l' + i} x1={lx} y1={ly} x2={p.x} y2={p.y} stroke="#2e2e30" stroke-dasharray="3 3" />)}
      <circle cx={lx} cy={ly} r="7" fill={A} /><text x={lx} y={ly + 20} fill="#8b8b86" font-size="10" text-anchor="middle">Du</text>
      {pts.map((p, i) => <g key={i}><rect x={p.x - 8} y={p.y - 8} width="16" height="16" rx="3" fill="#1b1b1c" stroke="#f2f2ee" /><text x={p.x} y={p.y - 12} fill="#f2f2ee" font-size="10" text-anchor="middle">{p.name}</text></g>)}
    </svg>
  );
}

export function PlacementCard() {
  const [p, setP] = useState<Placement | null>(null);
  const [res, setRes] = useState<PlacementResult | null>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.placement().then((x) => { setP(x); if ((x.last as PlacementResult)?.mode) setRes(x.last as PlacementResult); }).catch(() => setMsg('Ikke tilkoblet')); }, []);
  if (!p) return msg ? <span style="font-size:11px;color:#e0796b">{msg}</span> : null;
  const sp: PlacementSpeaker[] = p.speakers.length ? p.speakers : p.speakers_eff;
  const save = (b: Record<string, unknown>) => api.setPlacement(b).then(setP).catch((e) => setMsg(String(e?.message ?? e)));
  const edit = (i: number, k: keyof PlacementSpeaker, v: string) => { const n = sp.map((s, j) => (j === i ? { ...s, [k]: v } : s)); setP({ ...p, speakers: n }); };
  const run = async (fn: () => Promise<PlacementResult>, stage: string) => {
    setBusy(true); setMsg(stage);
    try { const r = await fn(); setRes(r); setMsg(r.warning ?? 'Måling ferdig – se forslaget under.'); } catch (e) { setMsg('Måling feilet: ' + String((e as Error)?.message ?? e)); }
    setBusy(false);
  };
  const rows = res ? (res.align ?? res.trims ?? []) : [];
  return (
    <div style={box} data-testid="placement-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Høyttalerplassering</span><span style={lbl}>Hver høyttaler spiller en kort tone etter tur. Skjold måler når lyden når deg og stiller forsinkelse og nivå så alt treffer samtidig.</span></div>
        <Switch on={!!p.enabled} set={(v) => void save({ enabled: v })} label="Bruk plasseringskorreksjon" />
      </div>
      <div style="display:flex;gap:6px">{(['2.0', '3.0', '5.1'] as const).map((l) => <button key={l} style={btn(p.layout === l)} onClick={() => void save({ layout: l })}>{l}</button>)}</div>
      <div style="display:flex;flex-direction:column;gap:6px">
        {sp.map((s, i) => (
          <div key={i} style="display:grid;grid-template-columns:1fr 1fr 70px 64px;gap:6px">
            <input aria-label="Navn" value={s.name} onInput={(e) => edit(i, 'name', e.currentTarget.value)} placeholder="Navn" style="height:30px;border-radius:8px;border:1px solid #2e2e30;background:#0b0b0c;color:#f2f2ee;padding:0 8px;min-width:0" />
            <input aria-label="Enhet (IP)" value={s.host} onInput={(e) => edit(i, 'host', e.currentTarget.value)} placeholder="denne enheten" style="height:30px;border-radius:8px;border:1px solid #2e2e30;background:#0b0b0c;color:#f2f2ee;padding:0 8px;min-width:0" />
            <select aria-label="Kanal" value={s.channel} onChange={(e) => edit(i, 'channel', e.currentTarget.value)} style="height:30px;border-radius:8px;background:#0b0b0c;color:#f2f2ee;border:1px solid #2e2e30"><option value="L">V</option><option value="R">H</option><option value="both">Begge</option></select>
            <select aria-label="Rolle" value={s.role} onChange={(e) => edit(i, 'role', e.currentTarget.value)} style="height:30px;border-radius:8px;background:#0b0b0c;color:#f2f2ee;border:1px solid #2e2e30"><option value="">–</option>{Object.keys(ROLE_NAMES).map((r) => <option key={r} value={r}>{r}</option>)}</select>
          </div>
        ))}
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button style={btn()} onClick={() => setP({ ...p, speakers: [...sp, { name: '', host: '', channel: 'both', role: '' }] })} disabled={sp.length >= 8}>+ Høyttaler</button>
          {sp.length > 1 && <button style={btn()} onClick={() => setP({ ...p, speakers: sp.slice(0, -1) })}>− Fjern siste</button>}
          <button style={btn()} onClick={() => void save({ speakers: sp })}>Lagre liste</button>
        </div>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button style={btn(true)} disabled={busy} onClick={() => void run(() => measureWithPhone(setMsg), 'Starter …')}>Mål med mobilen</button>
        <button style={btn()} disabled={busy} onClick={() => void run(() => api.placementDevices(), 'Enhetene måler hverandre …')}>Mål med enhetenes mikrofoner</button>
      </div>
      {msg && <span style="font-size:11.5px;color:#c9b48a">{msg}</span>}
      {res && <>
        <RoomMap r={res} />
        <div style="display:flex;flex-direction:column;gap:2px;font-size:12px">
          {rows.map((t, i) => <div key={i} style="display:flex;justify-content:space-between"><span>{res.speakers?.[i]?.name || ROLE_NAMES[res.speakers?.[i]?.role ?? ''] || '#' + (i + 1)}{res.angles ? ` · ${res.angles[i]}°` : ''}</span><span style="color:#c9c9c4">+{t.delay_ms.toFixed(2).replace('.', ',')} ms · {t.gain_db.toFixed(1).replace('.', ',')} dB</span></div>)}
          {res.roles && <span style={lbl}>{Object.entries(res.roles).map(([r, v]) => `${ROLE_NAMES[r] ?? r}: ${v.dev_deg > 0 ? '+' : ''}${v.dev_deg}° fra ITU`).join(' · ')}</span>}
        </div>
        <button style={btn(true)} onClick={() => api.placementApply().then((a) => { setMsg('Brukt' + (a.remote.length ? ` (${a.remote.filter((x) => x.ok).length}/${a.remote.length} andre enheter oppdatert)` : '') + '.'); return api.placement().then(setP); }).catch((e) => setMsg(String(e?.message ?? e)))}>Bruk forslaget</button>
      </>}
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
