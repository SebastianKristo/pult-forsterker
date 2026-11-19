// Skjold Røst: små ESP32-høyttalere (squeezelite-esp32) som spiller synkront med dette rommet via Lyrion.
import { useEffect, useState } from 'preact/hooks';
import { everyVisible } from '../lib/store';
import { apiPost, apiReq } from '../lib/api';

export interface RostSpeaker { id: string; name: string; ip: string; connected: boolean; power: boolean; playing: boolean; volume: number | null; synced: boolean; model: string }
interface RostList { lyrion: boolean; minis: RostSpeaker[]; error?: string }
interface Preset { n: number; title: string }

const A = '#d9a441';
const card = 'display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:14px;background:#141415;border:1px solid #242426';
const muted = 'font-size:12px;color:#8f8f8a;line-height:1.45';
const sbtn = (on: boolean) => `height:32px;padding:0 12px;border-radius:8px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;cursor:pointer;white-space:nowrap`;

export function RostCard() {
  const [d, setD] = useState<RostList | null>(null), [err, setErr] = useState('');
  const [presets, setPresets] = useState<Preset[]>([]), [picks, setPicks] = useState<number[]>([1, 2, 3, 4]), [open, setOpen] = useState(''), [msg, setMsg] = useState('');
  useEffect(() => { apiReq<{ items?: Preset[] }>('/api/presets').then((r) => setPresets(r.items ?? [])).catch(() => setPresets([])); }, []);
  const sendPresets = async (id: string) => {
    try { setD(await apiPost<RostList>('/api/rost', { id, action: 'presets', value: picks })); setMsg('Lagt på knappene'); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  const load = async () => { try { setD(await apiReq<RostList>('/api/rost')); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
  useEffect(() => { void load(); const t = everyVisible(() => void load(), 8000); return () => clearInterval(t); }, []);
  const act = async (id: string, action: string, value?: number | boolean) => {
    try { setD(await apiPost<RostList>('/api/rost', { id, action, value })); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  const list = d?.minis ?? [];
  return (
    <div style={card}>
      <span style="font-size:16px;font-weight:600">Skjold Røst</span>
      <span style={muted}>Små høyttalere med ESP32 og squeezelite-esp32. De vises som spillere i Lyrion og spiller i takt med dette rommet når du kobler dem til.</span>
      {d && !d.lyrion && <span style={muted}>Får ikke kontakt med Lyrion. Røst-høyttalere trenger Lyrion for å spille.</span>}
      {d?.lyrion && !list.length && <span style={muted}>Ingen Røst funnet. Gi høyttaleren et navn som begynner med «Skjold Røst» i oppsettet, så dukker den opp her.</span>}
      {list.map((m) => (
        <div key={m.id} style="display:flex;flex-direction:column;gap:8px;padding:10px 0;border-top:1px solid #242426">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
            <div style="display:flex;flex-direction:column;min-width:0">
              <span style="font-size:14px;font-weight:600">{m.name}</span>
              <span style={muted}>{m.connected ? `${m.ip || 'tilkoblet'}${m.playing ? ' · spiller' : ''}` : 'Frakoblet'}</span>
            </div>
            <div style="display:flex;gap:6px">
              <button disabled={!m.connected} onClick={() => void act(m.id, m.synced ? 'unsync' : 'sync')} style={sbtn(m.synced)}>{m.synced ? 'Spiller her' : 'Spill her'}</button>
              <button disabled={!m.connected} onClick={() => void act(m.id, 'power', !m.power)} style={sbtn(m.power)}>{m.power ? 'På' : 'Av'}</button>
              <button disabled={!m.connected} onClick={() => { setOpen(open === m.id ? '' : m.id); setMsg(''); }} style={sbtn(open === m.id)}>Knapper</button>
            </div>
          </div>
          {m.connected && m.volume !== null && <input type="range" min={0} max={100} value={m.volume} aria-label={`Volum ${m.name}`}
            onChange={(e) => void act(m.id, 'volume', +e.currentTarget.value)} style={`width:100%;accent-color:${A}`} />}
          {open === m.id && <div style="display:flex;flex-direction:column;gap:8px">
            <span style={muted}>Velg hvilke radiofavoritter knappene 1–4 på fronten skal spille.</span>
            {!presets.length && <span style={muted}>Du har ingen radiofavoritter ennå. Legg til noen under Radio først.</span>}
            {presets.length > 0 && [0, 1, 2, 3].map((i) => (
              <label key={i} style="display:flex;align-items:center;gap:10px;font-size:13px">
                <span style={`width:22px;height:22px;border-radius:6px;background:#1b1b1c;border:1px solid #2e2e30;display:grid;place-items:center;font-weight:600;color:${A}`}>{i + 1}</span>
                <select value={picks[i] ?? 0} onChange={(e) => { const p = [...picks]; p[i] = +e.currentTarget.value; setPicks(p); }}
                  style="flex:1;min-width:0;height:32px;border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;padding:0 8px">
                  <option value={0}>Ingen</option>
                  {presets.map((p) => <option key={p.n} value={p.n}>{p.n}. {p.title}</option>)}
                </select>
              </label>))}
            {presets.length > 0 && <div style="display:flex;gap:8px;align-items:center">
              <button onClick={() => void sendPresets(m.id)} style={sbtn(true)}>Legg på knappene</button>{msg && <span style={muted}>{msg}</span>}</div>}
          </div>}
        </div>
      ))}
      {list.length > 0 && <DusjPanel presets={presets} />}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}

interface Dusj { 'på': boolean; favoritt: number; minutter: number; aktive?: Record<string, number> }

/** Dusj-modus: hold ⏻ på Røst i 1,5 s → spiller valgt favoritt og slår av etter valgt tid. */
function DusjPanel({ presets }: { presets: Preset[] }) {
  const [d, setD] = useState<Dusj | null>(null), [err, setErr] = useState('');
  useEffect(() => { apiReq<Dusj>('/api/rost/dusj').then(setD).catch(() => setD(null)); }, []);
  const set = async (b: Partial<Dusj>) => { try { setD(await apiPost<Dusj>('/api/rost/dusj', b)); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
  if (!d) return null;
  const aktive = Object.values(d.aktive ?? {});
  return (
    <div style="display:flex;flex-direction:column;gap:8px;padding-top:10px;border-top:1px solid #242426">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <span style="font-size:14px;font-weight:600">Dusj-modus</span>
        <button onClick={() => void set({ 'på': !d['på'] })} style={sbtn(d['på'])}>{d['på'] ? 'På' : 'Av'}</button>
      </div>
      <span style={muted}>Hold ⏻ på Røst i 1,5 sekunder: den spiller favoritten under og slår seg av etter valgt tid, med myk nedtoning det siste halve minuttet.{aktive.length ? ` Pågår nå – ${Math.ceil(Math.max(...aktive) / 60)} min igjen.` : ''}</span>
      {d['på'] && <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <select value={d.favoritt} onChange={(e) => void set({ favoritt: +e.currentTarget.value })} aria-label="Favoritt i dusj-modus"
          style="flex:1;min-width:140px;height:32px;border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;padding:0 8px">
          {presets.map((p) => <option key={p.n} value={p.n}>{p.n}. {p.title}</option>)}
        </select>
        {[10, 15, 20, 30].map((m) => <button key={m} onClick={() => void set({ minutter: m })} style={sbtn(d.minutter === m)}>{m} min</button>)}
      </div>}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}

/** Skjold Røst-høyttalerne i «Spill på»-arket: huk av for å spille i takt med dette rommet (Lyrion-synk), og volum. */
export function RostRows() {
  const [list, setList] = useState<RostSpeaker[]>([]);
  const last = async () => { try { setList((await apiReq<{ minis?: RostSpeaker[] }>('/api/rost')).minis ?? []); } catch { setList([]); } };
  useEffect(() => { void last(); const t = setInterval(() => void last(), 6000); return () => clearInterval(t); }, []);
  const act = async (id: string, action: string, value?: number | boolean) => {
    try { setList((await apiPost<{ minis?: RostSpeaker[] }>('/api/rost', { id, action, value })).minis ?? []); } catch { /* prøver igjen ved neste oppdatering */ }
  };
  if (!list.length) return null;
  return (
    <div style="display:flex;flex-direction:column;gap:6px" data-testid="spk-rost">
      <span style="font-size:11px;color:#8b8b86;letter-spacing:.06em">SKJOLD RØST</span>
      {list.map((m) => (
        <div key={m.id} style="display:grid;grid-template-columns:30px minmax(0,1fr) 26px;gap:10px;align-items:center;padding:8px 10px;border-radius:12px;background:#141415;border:1px solid #242426">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM12 17.5a3 3 0 1 0 0-6a3 3 0 1 0 0 6M12 7.5h.01" /></svg>
          <div style="display:flex;flex-direction:column;gap:4px;min-width:0">
            <button disabled={!m.connected} onClick={() => void act(m.id, m.synced ? 'unsync' : 'sync')} style="border:none;background:none;padding:0;cursor:pointer;text-align:left;display:flex;justify-content:space-between;gap:8px;align-items:baseline;min-width:0"><span style={`flex:1 1 auto;min-width:0;font-size:14px;color:${m.synced ? '#f2f2ee' : '#c9c9c4'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{m.name}</span><span style="flex-shrink:0;font-size:11px;color:#8b8b86;white-space:nowrap">{!m.connected ? 'Ikke tilkoblet' : m.synced ? 'Spiller med' : m.playing ? 'Spiller' : 'Ledig'}</span></button>
            {m.volume != null && <input type="range" min={0} max={100} value={m.volume} disabled={!m.connected} onChange={(e) => void act(m.id, 'volume', +e.currentTarget.value)} style="width:100%;accent-color:#d9a441;height:20px" aria-label={'Volum ' + m.name} />}
          </div>
          <button disabled={!m.connected} onClick={() => void act(m.id, m.synced ? 'unsync' : 'sync')} aria-label={'Spill på ' + m.name} style={`width:26px;height:26px;border-radius:50%;border:1.5px solid ${m.synced ? A : '#3a3a3c'};background:${m.synced ? A : 'transparent'};color:#0b0b0c;cursor:pointer;padding:0;font-size:13px;font-weight:700`}>{m.synced ? '✓' : ''}</button>
        </div>
      ))}
      <span style="font-size:11px;color:#8b8b86;line-height:1.4">Røst spiller i takt med dette rommet når kilden går via Lyrion, som radio.</span>
    </div>
  );
}
