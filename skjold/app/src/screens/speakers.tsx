// «Skjold Sertifisert»: EQ-profil for passive høyttalere. Mål selv (sweep fra Skjold + mikrofon i nettleseren, analysen
// gjøres i daemonen: pi/skjold_speakerprofiles.py), eller hent en delt profil fra Skjold Cloud (/hoyttaler/*).
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, apiPost, apiReq } from '../lib/api';
import { recordMic } from '../lib/roomeq';

type P = Record<string, any>;
const A = '#d9a441';
const box = 'display:flex;flex-direction:column;gap:10px;padding:14px;border-radius:14px;background:#141415;border:1px solid #242426';
const lbl = 'font-size:12px;color:#8b8b86;line-height:1.5';
const inp = 'height:34px;border-radius:8px;border:1px solid #2e2e30;background:#0b0b0c;color:#f2f2ee;padding:0 10px;min-width:0';
const btn = (on = false) => `height:32px;padding:0 12px;border-radius:999px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12px;cursor:pointer`;

export const speakersApi = {
  get: () => apiReq<P>('/api/speakers'),
  set: (b: P) => apiPost<P>('/api/speakers', b),
  search: (q: string) => apiReq<{ results: P[]; offline: boolean }>('/api/speakers/search?q=' + encodeURIComponent(q), undefined, undefined, 10000),
  save: (b: P) => apiPost<P>('/api/speakers/save', b),
  share: () => apiPost<P>('/api/speakers/share', {}),
  flag: (id: string, reason: string) => apiPost<P>('/api/speakers/flag', { id, reason }),
  measure: (q: string, wav: Blob) => apiReq<P>('/api/speakers/measure?' + q, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav }, undefined, 30000),
  calibration: (txt: string) => apiReq<P>('/api/speakers/calibration', { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: txt }),
};

/** Float32 mono → 16-bit WAV. */
export function toWav(x: Float32Array, sr: number): Blob {
  const b = new ArrayBuffer(44 + x.length * 2), v = new DataView(b);
  const s = (o: number, t: string) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  s(0, 'RIFF'); v.setUint32(4, 36 + x.length * 2, true); s(8, 'WAVEfmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); s(36, 'data'); v.setUint32(40, x.length * 2, true);
  for (let i = 0; i < x.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x[i]!)) * 32767, true);
  return new Blob([b], { type: 'audio/wav' });
}

function Plot({ curve, after }: { curve?: { f: number; db: number }[]; after?: { f: number; db: number }[] }) {
  if (!curve?.length) return null;
  const W = 320, H = 110, x = (f: number) => (Math.log10(f / 20) / 3) * W, y = (d: number) => H / 2 - Math.max(-15, Math.min(15, d)) * (H / 30);
  const path = (c: { f: number; db: number }[]) => c.filter((p) => p.f >= 20 && p.f <= 20000).map((p, i) => `${i ? 'L' : 'M'}${x(p.f).toFixed(1)},${y(p.db).toFixed(1)}`).join('');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style="width:100%;height:auto;background:#0b0b0c;border-radius:10px" role="img" aria-label="Frekvensrespons før og etter korreksjon">
      {[100, 1000, 10000].map((f) => <line key={f} x1={x(f)} x2={x(f)} y1={0} y2={H} stroke="#242426" />)}
      <line x1={0} x2={W} y1={H / 2} y2={H / 2} stroke="#2e2e30" />
      <path d={path(curve)} fill="none" stroke="#8b8b86" stroke-width="1.5" />
      {after && <path d={path(after)} fill="none" stroke={A} stroke-width="1.8" />}
    </svg>
  );
}

function Badge({ p }: { p: P }) {
  if (p.certified || p.sertifisert) return <span style="font-size:11px;padding:2px 8px;border-radius:999px;background:#2a2112;color:#f0c46a;border:1px solid #3a3220">✓ Skjold Sertifisert</span>;
  return <span style="font-size:11px;color:#8b8b86">{(p.points ?? p.antall ?? 1)} måling{(p.points ?? p.antall ?? 1) === 1 ? '' : 'er'}</span>;
}

export function SpeakerCard() {
  const [c, setC] = useState<P | null>(null);
  const [err, setErr] = useState(''), [busy, setBusy] = useState('');
  const [q, setQ] = useState(''), [hits, setHits] = useState<{ results: P[]; offline: boolean } | null>(null);
  const [mode, setMode] = useState<'' | 'measure'>('');
  const [sess] = useState(() => 'w' + Math.random().toString(36).slice(2, 10));
  const [prev, setPrev] = useState<P | null>(null);
  const [form, setForm] = useState({ brand: '', model: '', sensitivity: '', impedance: '', share: true });
  const reset = useRef(true);
  const load = () => speakersApi.get().then(setC).catch(() => setErr('Ikke tilkoblet'));
  useEffect(() => { void load(); }, []);
  if (!c) return err ? <div style={box}><span style={lbl}>{err}</span></div> : null;
  const run = async (f: () => Promise<unknown>) => { setErr(''); try { await f(); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setBusy(''); } };
  const prof: P = c.profile || {};

  const measure = (m: 'gated' | 'near') => run(async () => {
    setBusy('Forbereder …');
    const info = await api.roomeqSweep({ level: 0.4, delay: 1.5 });
    const rec = await recordMic(info.delay + info.dur + 1.5, () => setBusy('Måler – vær stille …'));
    const qs = new URLSearchParams({ session: sess, mode: m, sr: String(rec.sr), brand: form.brand, model: form.model, ...(reset.current ? { reset: '1' } : {}) });
    reset.current = false;
    setPrev(await speakersApi.measure(qs.toString(), toWav(rec.data, rec.sr)));
  });

  return (
    <div style={box} data-testid="speaker-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <div style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Høyttalerprofil</span><span style={lbl}>Retter høyttalernes egen frekvensgang. Romkorreksjonen tar seg av bassen i rommet{c.roomeq_on ? ' (på – profilen bruker bare filtre over 300 Hz)' : ''}.</span></div>
        <button role="switch" aria-checked={!!c.enabled} aria-label="Høyttalerprofil" disabled={!prof.filters?.length} onClick={() => void run(async () => setC(await speakersApi.set({ enabled: !c.enabled })))} style={`width:44px;height:26px;border-radius:13px;border:none;background:${c.enabled ? A : '#3a3a3c'};position:relative;cursor:pointer;flex-shrink:0`}><i style={`position:absolute;top:3px;left:${c.enabled ? 21 : 3}px;width:20px;height:20px;border-radius:50%;background:#fff`} /></button>
      </div>

      {prof.model && <div style="display:flex;flex-direction:column;gap:6px">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span style="font-size:14px;font-weight:600">{prof.brand} {prof.model}</span><Badge p={prof} />{prof.score != null && <span style="font-size:11px;color:#8b8b86">score {prof.score}</span>}</div>
        <Plot curve={prof.curve} after={prof.after} />
        <span style={lbl}>{(c.active_filters || []).length} filtre aktive · gyldig {prof.valid?.[0]}–{prof.valid?.[1]} Hz{prof.source === 'own' ? ' · egen måling' : ' · fra Skjold Cloud'}</span>
        {(prof.hint?.warnings || []).map((w: string) => <span key={w} style="font-size:12px;color:#f0c46a">{w}</span>)}
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {(['flat', 'varm', 'bass'] as const).map((t) => <button key={t} style={btn(c.target === t)} onClick={() => void run(async () => setC(c.profile_id && prof.source !== 'own' ? await speakersApi.set({ use: c.profile_id, target: t }) : await speakersApi.set({ target: t })))}>{t === 'flat' ? 'Nøytral' : t === 'varm' ? 'Varm' : 'Mer bass'}</button>)}
          {prof.source === 'own' && !c.profile_id && <button style={btn()} onClick={() => void run(async () => { await speakersApi.share(); await load(); })}>Del i Skjold Cloud</button>}
        </div>
      </div>}

      <div style="display:flex;gap:6px"><input style={inp + ';flex:1'} placeholder="Søk: merke eller modell (f.eks. Dali Oberon)" value={q} onInput={(e) => setQ(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void run(async () => setHits(await speakersApi.search(q))); }} /><button style={btn()} onClick={() => void run(async () => setHits(await speakersApi.search(q)))}>Søk</button></div>
      {hits && <div style="display:flex;flex-direction:column;gap:4px">
        {hits.offline && <span style={lbl}>Uten nett – viser bare profiler du har brukt før.</span>}
        {!hits.results.length && <span style={lbl}>Ingen treff. Mål høyttalerne selv og del profilen – da får neste person den.</span>}
        {hits.results.map((h) => <div key={h.id} style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #1f1f21">
          <span style="font-size:13px;flex:1;min-width:0">{h.merke} {h.modell}</span><Badge p={h} />
          <button style={btn(c.profile_id === h.id)} onClick={() => void run(async () => setC(await speakersApi.set({ use: h.id })))}>Bruk</button>
          <button style={btn()} title="Meld fra om en feil profil" onClick={() => { const r = prompt('Hva er galt med profilen?'); if (r !== null) void run(() => speakersApi.flag(h.id, r)); }}>⚑</button>
        </div>)}
      </div>}

      {mode !== 'measure' ? <button style={btn()} onClick={() => setMode('measure')}>Mål høyttalerne mine</button> : <div style="display:flex;flex-direction:column;gap:8px;border-top:1px solid #242426;padding-top:10px">
        <span style={lbl}>1) Spill én høyttaler (koble fra den andre eller sett balansen helt over). 2) Hold mikrofonen 1 m foran høyttaleren, i høyde med diskanten, minst 1 m fra vegger og gulv – «Gated» 3–5 ganger fra litt ulike vinkler. 3) Valgfritt: «Nærfelt» med mikrofonen 1–2 cm foran basselementet for en riktig bass. En kalibrert USB-mikrofon gir best resultat; last opp kalibreringsfilen under.</span>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
          <input style={inp} placeholder="Merke" value={form.brand} onInput={(e) => setForm({ ...form, brand: e.currentTarget.value })} />
          <input style={inp} placeholder="Modell" value={form.model} onInput={(e) => setForm({ ...form, model: e.currentTarget.value })} />
          <input style={inp} inputMode="decimal" placeholder="Følsomhet dB (valgfri)" value={form.sensitivity} onInput={(e) => setForm({ ...form, sensitivity: e.currentTarget.value })} />
          <input style={inp} inputMode="decimal" placeholder="Impedans Ω (valgfri)" value={form.impedance} onInput={(e) => setForm({ ...form, impedance: e.currentTarget.value })} />
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center"><span style={lbl}>Mikrofon:</span>
          {([['iphone', 'iPhone'], ['android', 'Android'], ['s1', 'S1/Touch'], ['flat', 'Kalibrert (flat)']] as const).map(([k, n]) => <button key={k} style={btn(c.mic === k)} onClick={() => void run(async () => setC(await speakersApi.set({ mic: k })))}>{n}</button>)}
          <label style={btn(c.mic === 'file') + ';display:inline-flex;align-items:center'}>Kalibreringsfil …<input type="file" accept=".txt,.cal,.frd" style="display:none" onChange={(e) => { const f = e.currentTarget.files?.[0]; if (f) void run(async () => { await speakersApi.calibration(await f.text()); await load(); }); }} /></label>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button disabled={!!busy} style={btn(true)} onClick={() => void measure('gated')}>{busy || `Gated måling${prev ? ` (${prev.gated})` : ''}`}</button>
          <button disabled={!!busy} style={btn()} onClick={() => void measure('near')}>Nærfelt{prev?.near ? ' ✓' : ''}</button>
          {prev && <button style={btn()} onClick={() => { reset.current = true; setPrev(null); }}>Nullstill</button>}
        </div>
        {prev && <>
          <span style={lbl}>Siste punkt: signal/støy {prev.point.snr} dB{prev.point.clipped ? ' · KLIPPET – senk volumet' : ''} · score {prev.profile.score}</span>
          <Plot curve={prev.profile.curve} after={prev.profile.after} />
          <label style="display:flex;gap:6px;align-items:center;font-size:12px"><input type="checkbox" checked={form.share} onChange={(e) => setForm({ ...form, share: e.currentTarget.checked })} />Del anonymt i Skjold Cloud (bare kurven, merke og modell)</label>
          <button disabled={!form.brand || !form.model || !prev.gated} style={btn(true)} onClick={() => void run(async () => {
            const r = await speakersApi.save({ session: sess, ...form, apply: true });
            if (r.shared?.error) setErr(r.shared.error);
            setMode(''); setPrev(null); reset.current = true; await load();
          })}>Lagre og bruk profilen</button>
        </>}
      </div>}
      {err && <span style="font-size:11px;color:#e0796b">{err}</span>}
    </div>
  );
}
