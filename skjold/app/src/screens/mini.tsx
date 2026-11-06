// Skjold Mini: små ESP32-høyttalere (squeezelite-esp32) som spiller synkront med dette rommet via Lyrion.
import { useEffect, useState } from 'preact/hooks';
import { apiPost, apiReq } from '../lib/api';

export interface Mini { id: string; name: string; ip: string; connected: boolean; power: boolean; playing: boolean; volume: number | null; synced: boolean; model: string }
interface MiniList { lyrion: boolean; minis: Mini[]; error?: string }

const A = '#d9a441';
const card = 'display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:14px;background:#141415;border:1px solid #242426';
const muted = 'font-size:12px;color:#8f8f8a;line-height:1.45';
const sbtn = (on: boolean) => `height:32px;padding:0 12px;border-radius:8px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;cursor:pointer;white-space:nowrap`;

export function MiniCard() {
  const [d, setD] = useState<MiniList | null>(null), [err, setErr] = useState('');
  const load = async () => { try { setD(await apiReq<MiniList>('/api/mini')); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
  useEffect(() => { void load(); const t = window.setInterval(() => void load(), 8000); return () => clearInterval(t); }, []);
  const act = async (id: string, action: string, value?: number | boolean) => {
    try { setD(await apiPost<MiniList>('/api/mini', { id, action, value })); setErr(''); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  const list = d?.minis ?? [];
  return (
    <div style={card}>
      <span style="font-size:16px;font-weight:600">Skjold Mini</span>
      <span style={muted}>Små høyttalere med ESP32 og squeezelite-esp32. De vises som spillere i Lyrion og spiller i takt med dette rommet når du kobler dem til.</span>
      {d && !d.lyrion && <span style={muted}>Får ikke kontakt med Lyrion. Mini-er trenger Lyrion for å spille.</span>}
      {d?.lyrion && !list.length && <span style={muted}>Ingen Mini funnet. Gi høyttaleren et navn som begynner med «Skjold Mini» i oppsettet, så dukker den opp her.</span>}
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
            </div>
          </div>
          {m.connected && m.volume !== null && <input type="range" min={0} max={100} value={m.volume} aria-label={`Volum ${m.name}`}
            onChange={(e) => void act(m.id, 'volume', +e.currentTarget.value)} style={`width:100%;accent-color:${A}`} />}
        </div>
      ))}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}
