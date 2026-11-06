// Plugins (S1 Web v3 «plug»): Skjold-egne plugins kjører i daemonen (GET/POST /api/plugins), Lyrion-plugins installeres i Lyrion.
import { GuidePicker, ProgramsPanel } from './programs';
import { signal } from '@preact/signals';
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, INPUT_LABEL, type HistItem, type InputId, type Lyrics, type Plugin, type RecPayload, type RecSong, type SnapClient } from '../lib/api';
import { status } from '../lib/store';
import { favs, loadFavs } from '../lib/radio';
import { Toggle } from '../components/ui';
import { AutoStandbyPanel, BackupPanel, PlexampPanel, RoonPanel, WrappedPage } from './extras';
import { PodsumPanel } from './ai';
import { DiscoverPanel, PresencePanel, RadioListPanel, StorePage, WakeLightPanel } from './extras2';
import { averageCurves, logSweep, recordMic, responseFromRecording, suggest, type Curve, type Peq } from '../lib/roomeq';

const A = '#d9a441';
const MONO = "'IBM Plex Mono',monospace";
const DAYS = ['Ma', 'Ti', 'On', 'To', 'Fr', 'Lø', 'Sø'];
const CATS = ['Alle', 'På', 'Musikk', 'Radio og podkast', 'Verktøy', 'Hjem', 'Butikk'];

/** Merkelogoer fra Simple Icons (CC0). */
const BRAND: Record<string, { bg: string; fg: string; fp: string }> = {
  spotty: { bg: '#000000', fg: '#1DB954', fp: 'M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z' },
  tidal: { bg: '#000000', fg: '#ffffff', fp: 'M12.012 3.992L8.008 7.996 4.004 3.992 0 7.996 4.004 12l4.004-4.004L12.012 12l-4.004 4.004 4.004 4.004 4.004-4.004L12.012 12l4.004-4.004-4.004-4.004zM16.042 7.996l3.979-3.979L24 7.996l-3.979 3.979z' },
  deezer: { bg: '#A238FF', fg: '#ffffff', fp: 'M.693 10.024c.381 0 .693-1.256.693-2.807 0-1.55-.312-2.807-.693-2.807C.312 4.41 0 5.666 0 7.217s.312 2.808.693 2.808ZM21.038 1.56c-.364 0-.684.805-.91 2.096C19.765 1.446 19.184 0 18.526 0c-.78 0-1.464 2.036-1.784 5-.312-2.158-.788-3.536-1.325-3.536-.745 0-1.386 2.704-1.62 6.472-.442-1.932-1.083-3.145-1.793-3.145s-1.35 1.213-1.793 3.145c-.242-3.76-.874-6.463-1.628-6.463-.537 0-1.013 1.378-1.325 3.535C6.938 2.036 6.262 0 5.474 0c-.658 0-1.247 1.447-1.602 3.665-.217-1.291-.546-2.105-.91-2.105-.675 0-1.221 2.807-1.221 6.272 0 3.466.546 6.273 1.221 6.273.277 0 .537-.476.736-1.273.32 2.928.996 4.938 1.776 4.938.606 0 1.143-1.204 1.507-3.11.251 3.622.875 6.195 1.602 6.195.46 0 .875-1.023 1.187-2.677C10.142 21.6 11 24 12.004 24c1.005 0 1.863-2.4 2.235-5.822.312 1.654.727 2.677 1.186 2.677.728 0 1.352-2.573 1.603-6.195.364 1.906.9 3.11 1.507 3.11.78 0 1.455-2.01 1.775-4.938.208.797.46 1.273.737 1.273.675 0 1.22-2.807 1.22-6.273-.008-3.457-.553-6.272-1.23-6.272ZM23.307 10.024c.381 0 .693-1.256.693-2.807 0-1.55-.312-2.807-.693-2.807-.381 0-.693 1.256-.693 2.807s.312 2.808.693 2.808Z' },
  lastfm: { bg: '#D51007', fg: '#ffffff', fp: 'M10.584 17.21l-.88-2.392s-1.43 1.594-3.573 1.594c-1.897 0-3.244-1.649-3.244-4.288 0-3.382 1.704-4.591 3.381-4.591 2.42 0 3.189 1.567 3.849 3.574l.88 2.749c.88 2.666 2.529 4.81 7.285 4.81 3.409 0 5.718-1.044 5.718-3.793 0-2.227-1.265-3.381-3.63-3.931l-1.758-.385c-1.21-.275-1.567-.77-1.567-1.595 0-.934.742-1.484 1.952-1.484 1.32 0 2.034.495 2.144 1.677l2.749-.33c-.22-2.474-1.924-3.492-4.729-3.492-2.474 0-4.893.935-4.893 3.932 0 1.87.907 3.051 3.189 3.601l1.87.44c1.402.33 1.869.907 1.869 1.704 0 1.017-.99 1.43-2.86 1.43-2.776 0-3.93-1.457-4.59-3.464l-.907-2.75c-1.155-3.573-2.997-4.893-6.653-4.893C2.144 5.333 0 7.89 0 12.233c0 4.18 2.144 6.434 5.993 6.434 3.106 0 4.591-1.457 4.591-1.457z' },
  podcast: { bg: '#9933CC', fg: '#ffffff', fp: 'M5.34 0A5.328 5.328 0 000 5.34v13.32A5.328 5.328 0 005.34 24h13.32A5.328 5.328 0 0024 18.66V5.34A5.328 5.328 0 0018.66 0zm6.525 2.568c2.336 0 4.448.902 6.056 2.587 1.224 1.272 1.912 2.619 2.264 4.392.12.59.12 2.2.007 2.864a8.506 8.506 0 01-3.24 5.296c-.608.46-2.096 1.261-2.336 1.261-.088 0-.096-.091-.056-.46.072-.592.144-.715.48-.856.536-.224 1.448-.874 2.008-1.435a7.644 7.644 0 002.008-3.536c.208-.824.184-2.656-.048-3.504-.728-2.696-2.928-4.792-5.624-5.352-.784-.16-2.208-.16-3 0-2.728.56-4.984 2.76-5.672 5.528-.184.752-.184 2.584 0 3.336.456 1.832 1.64 3.512 3.192 4.512.304.2.672.408.824.472.336.144.408.264.472.856.04.36.03.464-.056.464-.056 0-.464-.176-.896-.384l-.04-.03c-2.472-1.216-4.056-3.274-4.632-6.012-.144-.706-.168-2.392-.03-3.04.36-1.74 1.048-3.1 2.192-4.304 1.648-1.737 3.768-2.656 6.128-2.656zm.134 2.81c.409.004.803.04 1.106.106 2.784.62 4.76 3.408 4.376 6.174-.152 1.114-.536 2.03-1.216 2.88-.336.43-1.152 1.15-1.296 1.15-.023 0-.048-.272-.048-.603v-.605l.416-.496c1.568-1.878 1.456-4.502-.256-6.224-.664-.67-1.432-1.064-2.424-1.246-.64-.118-.776-.118-1.448-.008-1.02.167-1.81.562-2.512 1.256-1.72 1.704-1.832 4.342-.264 6.222l.413.496v.608c0 .336-.027.608-.06.608-.03 0-.264-.16-.512-.36l-.034-.011c-.832-.664-1.568-1.842-1.872-2.997-.184-.698-.184-2.024.008-2.72.504-1.878 1.888-3.335 3.808-4.019.41-.145 1.133-.22 1.814-.211zm-.13 2.99c.31 0 .62.06.844.178.488.253.888.745 1.04 1.259.464 1.578-1.208 2.96-2.72 2.254h-.015c-.712-.331-1.096-.956-1.104-1.77 0-.733.408-1.371 1.112-1.745.224-.117.534-.176.844-.176zm-.011 4.728c.988-.004 1.706.349 1.97.97.198.464.124 1.932-.218 4.302-.232 1.656-.36 2.074-.68 2.356-.44.39-1.064.498-1.656.288h-.003c-.716-.257-.87-.605-1.164-2.644-.341-2.37-.416-3.838-.218-4.302.262-.616.974-.966 1.97-.97z' },
  mqtt: { bg: '#660066', fg: '#ffffff', fp: 'M10.657 23.994h-9.45A1.212 1.212 0 0 1 0 22.788v-9.18h.071c5.784 0 10.504 4.65 10.586 10.386Zm7.606 0h-4.045C14.135 16.246 7.795 9.977 0 9.942V6.038h.071c9.983 0 18.121 8.044 18.192 17.956Zm4.53 0h-.97C21.754 12.071 11.995 2.407 0 2.372v-1.16C0 .55.544.006 1.207.006h7.64C15.733 2.49 21.257 7.789 24 14.508v8.291c0 .663-.544 1.195-1.207 1.195ZM16.713.006h6.092A1.19 1.19 0 0 1 24 1.2v5.914c-.91-1.242-2.046-2.65-3.158-3.762C19.588 2.11 18.122.987 16.714.005Z' }
};
/** Strek-ikoner for plugins uten eget merke. */
const ICON: Record<string, { bg: string; fg: string; st: string; fi?: string }> = {
  sleep: { bg: '#1c2433', fg: '#9fc0ff', st: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z' },
  alarm: { bg: '#2a2112', fg: '#f0c46a', st: 'M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 9v4l2.5 2.5M5 3 2 6M19 3l3 3' },
  news: { bg: '#2a1412', fg: '#ff8a7a', st: 'M4 5h13v14H6a2 2 0 0 1-2-2zM17 9h3v8a2 2 0 0 1-2 2M8 9h5M8 13h5M8 16h3' },
  lyrics: { bg: '#1f1f21', fg: '#f2f2ee', st: 'M4 6h16M4 10h16M4 14h10M4 18h7' },
  history: { bg: '#16201a', fg: '#9be0a8', st: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2' },
  nightcap: { bg: '#1c2433', fg: '#9fc0ff', st: 'M20 13A8 8 0 1 1 11 4a6 6 0 0 0 9 9zM15 4h6M18 1v6' },
  listenbrainz: { bg: '#353070', fg: '#eb743b', st: 'M4 15v-3a8 8 0 0 1 16 0v3M4 15a2 2 0 0 0 2 2h1v-6H6a2 2 0 0 0-2 2zM20 15a2 2 0 0 1-2 2h-1v-6h1a2 2 0 0 1 2 2z' },
  webhook: { bg: '#1f1f21', fg: '#c9b48a', st: 'M18 17h-6c-1 0-2 .9-2.5 1.9A4 4 0 1 1 2.6 15M6 17l3.1-5.8c.5-1-.1-2.2-.5-3.1a4 4 0 1 1 6.9-4M12 6l3.1 5.7c.5 1 1.8 1.3 2.9 1.3a4 4 0 0 1 0 8' },
  kids: { bg: '#2a2112', fg: '#f0c46a', st: 'M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8zM5 21v-1a7 7 0 0 1 14 0v1M10 7h.01M14 7h.01' },
  record: { bg: '#2a1412', fg: '#ff6a5a', st: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z', fi: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z' },
  snapcast: { bg: '#14233a', fg: '#7fb2ff', st: 'M4 4h7v16H4zM13 4h7v16h-7zM7.5 13.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM16.5 13.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM7.5 8h.01M16.5 8h.01' },
  roomeq: { bg: '#16201a', fg: '#9be0a8', st: 'M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3' },
  qobuz: { bg: '#000000', fg: '#ffffff', st: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM14 14l5 5' },
  rp: { bg: '#1d2b1f', fg: '#e8d9a8', st: 'M4 12a8 8 0 0 1 16 0M7 12a5 5 0 0 1 10 0M12 12v8M9 20h6' },
  roon: { bg: '#0b0b0c', fg: '#f2f2ee', st: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z' },
  plexamp: { bg: '#1f1a0a', fg: '#ebaf00', st: 'M8 4l9 8-9 8z' },
  autostandby: { bg: '#1c2433', fg: '#9fc0ff', st: 'M12 3v8M6.3 6.3a8 8 0 1 0 11.4 0' },
  backup: { bg: '#16201a', fg: '#9be0a8', st: 'M4 7h16v12H4zM8 7V4h8v3M12 11v5M9.5 13.5 12 16l2.5-2.5' },
  wrapped: { bg: '#2a1d08', fg: '#d9a441', st: 'M4 9h16v11H4zM2 6h20v3H2zM12 6v14M12 6c-2-4-6-3-5 0M12 6c2-4 6-3 5 0' },
  subwave: { bg: '#0b0b0c', fg: '#f0c46a', st: 'M2 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0 2 3 2 3' },
  dstm: { bg: '#1f1f21', fg: '#f0c46a', st: 'M18.2 8.5a3.5 3.5 0 1 1 0 7c-2.6 0-4-3.5-6.2-3.5s-3.6 3.5-6.2 3.5a3.5 3.5 0 1 1 0-7c2.6 0 4 3.5 6.2 3.5s3.6-3.5 6.2-3.5z' }
};

export function PlugLogo({ id, size = 44 }: { id: string; size?: number }) {
  const box = `width:${size}px;height:${size}px;border-radius:${Math.round(size / 4)}px;overflow:hidden;display:flex;align-items:center;justify-content:center;flex-shrink:0`;
  const b = BRAND[id];
  if (b) return <span style={`${box};background:${b.bg};color:${b.fg}`}><svg viewBox="0 0 24 24" style="width:58%;height:58%;display:block"><path d={b.fp} fill="currentColor" /></svg></span>;
  if (id === 'bbc') return <span style={`${box};background:#000;gap:2px`}>{['B', 'B', 'C'].map((c, i) => <b key={i} style="width:24%;aspect-ratio:1;background:#fff;color:#000;font:700 9px/1 Arial,Helvetica,sans-serif;display:grid;place-items:center">{c}</b>)}</span>;
  const ic = ICON[id] ?? { bg: '#1f1f21', fg: '#c9c9c4', st: 'M12 3v18M3 12h18' };
  return <span style={`${box};background:${ic.bg};color:${ic.fg}`}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="width:52%;height:52%;display:block"><path d={ic.st} />{ic.fi && <path d={ic.fi} fill="currentColor" stroke="none" />}</svg></span>;
}

// ---------- data ----------
export const plugList = signal<Plugin[] | null>(null);
export const plugErr = signal('');
export const sleepLeft = signal(0);
export async function loadPlugins(): Promise<void> {
  try { const r = await api.plugins(); plugList.value = r.plugins; sleepLeft.value = r.sleep; plugErr.value = ''; } catch (e) { plugErr.value = e instanceof Error ? e.message : String(e); }
}
export const plugCount = (): number => (plugList.value ?? []).filter((p) => p.enabled).length;
async function setPlugin(id: string, b: Record<string, unknown>): Promise<string> {
  try { const r = await api.setPlugin(id, b); plugList.value = r.plugins; sleepLeft.value = r.sleep; return ''; } catch (e) { return e instanceof Error ? e.message : String(e); }
}

// ---------- små byggeklosser ----------
const fld = `height:38px;padding:0 10px;border-radius:9px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;color:#f2f2ee;min-width:0`;
const pbtn = `height:38px;padding:0 16px;border-radius:999px;border:none;background:${A};color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`;
const sbtn = 'height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const Row = ({ label, hint, children }: { label: string; hint?: string; children: preact.ComponentChildren }) => (
  <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:12px 0;border-top:1px solid #1f1f21">
    <div style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">{label}</span>{hint && <span style="font-size:12px;color:#8b8b86;line-height:1.4">{hint}</span>}</div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end">{children}</div>
  </div>
);
const Days = ({ v, on }: { v: number[]; on: (d: number[]) => void }) => (
  <div style="display:flex;gap:4px">{DAYS.map((n, i) => { const sel = v.includes(i); return <button key={i} onClick={() => on(sel ? v.filter((x) => x !== i) : [...v, i].sort())} style={`width:32px;height:30px;border-radius:8px;border:1px solid ${sel ? '#5a4420' : '#2e2e30'};background:${sel ? '#1c170d' : 'transparent'};color:${sel ? '#f0c46a' : '#8b8b86'};font-size:11.5px;cursor:pointer`}>{n}</button>; })}</div>
);
const FavSel = ({ v, on, none }: { v: number; on: (n: number) => void; none?: string }) => (
  <select value={String(v)} onChange={(e) => on(+(e.currentTarget as HTMLSelectElement).value)} style={fld}>
    {none && <option value="0">{none}</option>}
    {favs.value.map((f) => <option key={f.n} value={String(f.n)}>{f.n}. {f.title}</option>)}
  </select>
);
const Num = ({ v, on, min = 0, max = 100, w = 72 }: { v: number; on: (n: number) => void; min?: number; max?: number; w?: number }) => <input type="number" min={min} max={max} value={v} onInput={(e) => on(+(e.currentTarget as HTMLInputElement).value)} style={fld + `;width:${w}px;font-family:${MONO}`} />;
const Txt = ({ v, on, ph, w = 240, pw }: { v: string; on: (s: string) => void; ph?: string; w?: number; pw?: boolean }) => <input type={pw ? 'password' : 'text'} value={v} placeholder={ph} onInput={(e) => on((e.currentTarget as HTMLInputElement).value)} style={fld + `;width:${w}px;max-width:100%`} autoCapitalize="off" spellcheck={false} />;
const Time = ({ v, on }: { v: string; on: (s: string) => void }) => <input type="time" value={v} onInput={(e) => on((e.currentTarget as HTMLInputElement).value)} style={fld + `;font-family:${MONO}`} />;

// ---------- side ----------
const sel = signal<string | null>(null);
export function PluginsPage() {
  const [cat, setCat] = useState('Alle'), [q, setQ] = useState('');
  useEffect(() => { void loadPlugins(); if (!favs.value.length) void loadFavs(); const t = setInterval(() => void loadPlugins(), 15000); return () => clearInterval(t); }, []);
  const all = plugList.value ?? [];
  const ql = q.trim().toLowerCase();
  const list = all.filter((p) => (cat === 'Alle' || (cat === 'På' ? p.enabled : p.cat === cat)) && (!ql || (p.name + ' ' + p.desc).toLowerCase().includes(ql)));
  const cur = all.find((p) => p.id === sel.value);
  return (
    <>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div style="display:flex;gap:4px;padding:4px;border-radius:10px;background:#141415;border:1px solid #242426;flex-wrap:wrap">
          {CATS.map((n) => <button key={n} onClick={() => setCat(n)} style={`height:34px;padding:0 14px;border-radius:7px;border:none;background:${cat === n ? '#2a2a2c' : 'transparent'};color:${cat === n ? '#f2f2ee' : '#8b8b86'};font-size:13px;cursor:pointer;white-space:nowrap`}>{n}</button>)}
        </div>
        <input value={q} onInput={(e) => setQ((e.currentTarget as HTMLInputElement).value)} placeholder="Søk i plugins" style="height:42px;width:280px;max-width:100%;padding:0 14px;border-radius:10px;border:1px solid #2e2e30;background:#141415;font-size:14px;outline:none;color:#f2f2ee" />
      </div>
      {cat === 'Butikk' ? <StorePage /> : <>
      {plugErr.value && !plugList.value && <span style="font-size:13px;color:#ff8a7a">Får ikke hentet plugins fra Skjold: {plugErr.value}. Oppdater Skjold under Innstillinger → Oppdatering.</span>}
      {cur && <Detail p={cur} />}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">
        {list.map((p) => {
          const fg = p.enabled ? '#6fcf7f' : p.status === 'Krever oppsett' || p.status.startsWith('Krever') ? '#f0c46a' : '#6a6a65';
          return (
            <div key={p.id} style={`display:flex;flex-direction:column;gap:12px;padding:18px;border-radius:14px;border:1px solid ${sel.value === p.id ? '#5a4420' : p.enabled ? '#3a3220' : '#242426'};background:#141415`}>
              <div style="display:flex;align-items:center;gap:12px">
                <PlugLogo id={p.id} />
                <div style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px;font-weight:600">{p.name}</span><span style={`font-family:${MONO};font-size:10px;color:#8b8b86`}>Fra {p.src === 'lyrion' ? 'Lyrion' : 'Skjold'} · {p.cat}</span></div>
              </div>
              <span style="font-size:12.5px;color:#a9a9a3;line-height:1.45;text-wrap:pretty;flex:1">{p.desc}</span>
              <div style="display:flex;align-items:center;justify-content:space-between;gap:10px">
                <span style={`display:flex;align-items:center;gap:6px;font-size:11px;color:${fg};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}><i style={`width:6px;height:6px;border-radius:50%;background:${fg};flex-shrink:0`} />{p.status}</span>
                {p.src === 'lyrion'
                  ? <a href={p.url} target="_blank" rel="noreferrer" style={sbtn + ';display:inline-flex;align-items:center;text-decoration:none'}>Installer i Lyrion ↗</a>
                  : <div style="display:flex;gap:8px;align-items:center"><button onClick={() => { sel.value = sel.value === p.id ? null : p.id; }} style={sbtn}>{sel.value === p.id ? 'Lukk' : 'Innstillinger'}</button>{p.id !== 'kids' && <Toggle on={p.enabled} label={p.name} onChange={(v) => void setPlugin(p.id, { enabled: v })} />}</div>}
              </div>
            </div>
          );
        })}
      </div>
      {plugList.value && list.length === 0 && <span style="font-size:13px;color:#8b8b86">Ingen plugins passer.</span>}
      <span style="font-size:12px;color:#6a6a65;line-height:1.5">Lyrion-plugins installeres i Lyrions egne innstillinger (Plugins). Skjold-plugins kjører på denne enheten og deles med appen. Flere finnes under Butikk.</span>
      </>}
    </>
  );
}

function Detail({ p }: { p: Plugin }) {
  const [d, setD] = useState<Record<string, any>>(() => JSON.parse(JSON.stringify(p.cfg)));
  const [msg, setMsg] = useState('');
  useEffect(() => { setD(JSON.parse(JSON.stringify(p.cfg))); setMsg(''); }, [p.id]);
  const up = (k: string, v: unknown) => setD({ ...d, [k]: v });
  const save = async (extra: Record<string, unknown> = {}) => { setMsg('Lagrer …'); const e = await setPlugin(p.id, { ...d, ...extra }); setMsg(e ? 'Feil: ' + e : 'Lagret'); };
  const saveBtn = <div style="display:flex;gap:10px;align-items:center;padding-top:12px;border-top:1px solid #1f1f21"><button onClick={() => void save()} style={pbtn}>Lagre</button><span style={`font-size:12px;color:${msg.startsWith('Feil') ? '#ff8a7a' : '#8b8b86'}`}>{msg}</span></div>;
  let body: preact.ComponentChildren = null;
  switch (p.id) {
    case 'sleep': body = <SleepPanel enabled={p.enabled} />; break;
    case 'alarm': body = <>{(d.alarms as any[]).map((a, i) => (
      <div key={i} style="display:flex;flex-direction:column;gap:8px;padding:12px 0;border-top:1px solid #1f1f21">
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><Time v={a.time} on={(v) => { const x = [...d.alarms]; x[i] = { ...a, time: v }; up('alarms', x); }} /><Days v={a.days} on={(v) => { const x = [...d.alarms]; x[i] = { ...a, days: v }; up('alarms', x); }} /><Toggle on={a.on} label="Alarm på" onChange={(v) => { const x = [...d.alarms]; x[i] = { ...a, on: v }; up('alarms', x); }} /></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><FavSel v={a.preset} none="Strøm-URL" on={(v) => { const x = [...d.alarms]; x[i] = { ...a, preset: v }; up('alarms', x); }} />{!a.preset && <Txt v={a.url} ph="https://…" on={(v) => { const x = [...d.alarms]; x[i] = { ...a, url: v }; up('alarms', x); }} />}<span style="font-size:12px;color:#8b8b86">Volum</span><Num v={a.volume} on={(v) => { const x = [...d.alarms]; x[i] = { ...a, volume: v }; up('alarms', x); }} /><span style="font-size:12px;color:#8b8b86">Myk start (min)</span><Num v={a.fade} max={30} w={60} on={(v) => { const x = [...d.alarms]; x[i] = { ...a, fade: v }; up('alarms', x); }} /><button onClick={() => up('alarms', d.alarms.filter((_: unknown, j: number) => j !== i))} style={sbtn}>Fjern</button></div>
      </div>))}
      <WakeLightPanel light={d.light} set={(v) => up('light', v)} />
      <div><button onClick={() => up('alarms', [...d.alarms, { time: '07:00', days: [0, 1, 2, 3, 4], preset: favs.value[0]?.n ?? 0, url: '', volume: 30, fade: 3, on: true }])} style={sbtn}>+ Legg til alarm</button></div>{saveBtn}</>; break;
    case 'news': body = <><Row label="Tid"><Time v={d.time} on={(v) => up('time', v)} /></Row><Row label="Dager"><Days v={d.days} on={(v) => up('days', v)} /></Row><Row label="Volum"><Num v={d.volume} on={(v) => up('volume', v)} /></Row><Row label="Slå av etter" hint="Minutter. 0 = spill videre."><Num v={d.minutes} max={180} on={(v) => up('minutes', v)} /></Row><Row label="Strøm" hint="NRK P1 som standard"><Txt v={d.url} on={(v) => up('url', v)} /></Row>{saveBtn}</>; break;
    case 'lyrics': body = <span style="font-size:13px;color:#a9a9a3">Når pluginen er på, får Spiller-siden en egen fane «Tekst». Teksten hentes fra lrclib.net for låter med artist og tittel. Synkroniserte tekster følger låten linje for linje.</span>; break;
    case 'history': body = <HistoryPanel />; break;
    case 'nightcap': body = <><Row label="Fra"><Time v={d.start} on={(v) => up('start', v)} /></Row><Row label="Til"><Time v={d.end} on={(v) => up('end', v)} /></Row><Row label="Maks volum"><Num v={d.max} on={(v) => up('max', v)} /></Row>{saveBtn}</>; break;
    case 'listenbrainz': body = <><Row label="Brukertoken" hint="Fra listenbrainz.org → Settings → User token"><Txt v={d.token} pw on={(v) => up('token', v)} /></Row>{saveBtn}</>; break;
    case 'lastfm': body = <><span style="font-size:12.5px;color:#a9a9a3;line-height:1.5">Last.fm krever en egen API-konto (last.fm/api/account/create) og en sesjonsnøkkel for brukeren din. Lim inn alle tre.</span><Row label="API-nøkkel"><Txt v={d.key} on={(v) => up('key', v)} /></Row><Row label="Hemmelighet"><Txt v={d.secret} pw on={(v) => up('secret', v)} /></Row><Row label="Sesjonsnøkkel"><Txt v={d.session} pw on={(v) => up('session', v)} /></Row>{saveBtn}</>; break;
    case 'webhook': body = <><Row label="Adresse" hint="Får POST med JSON: event (track, play, pause, source), tittel, artist og kilde."><Txt v={d.url} ph="https://…" w={300} on={(v) => up('url', v)} /></Row>{saveBtn}</>; break;
    case 'kids': body = <KidsPanel p={p} d={d} up={up} save={save} msg={msg} />; break;
    case 'record': body = <><RecordPanel d={d} up={up} saveBtn={saveBtn} /><RadioListPanel /></>; break;
    case 'mqtt': body = <><Row label="Broker"><Txt v={d.host} ph="192.168.1.10" w={180} on={(v) => up('host', v)} /><Num v={d.port} max={65535} w={90} on={(v) => up('port', v)} /></Row><Row label="Brukernavn"><Txt v={d.user} w={180} on={(v) => up('user', v)} /></Row><Row label="Passord"><Txt v={d.password} pw w={180} on={(v) => up('password', v)} /></Row><Row label="TLS"><Toggle on={!!d.tls} onChange={(v) => up('tls', v)} /></Row><Row label="Emne-prefiks" hint={`Status: ${d.prefix || 'skjold'}/<id>/state · kommandoer: …/set`}><Txt v={d.prefix} w={140} on={(v) => up('prefix', v)} /></Row><Row label="Home Assistant-oppdagelse"><Toggle on={!!d.discovery} onChange={(v) => up('discovery', v)} /></Row>{saveBtn}</>; break;
    case 'snapcast': body = <SnapPanel d={d} up={up} saveBtn={saveBtn} />; break;
    case 'subwave': body = <SubwavePanel d={d} up={up} saveBtn={saveBtn} />; break;
    case 'roon': body = <RoonPanel />; break;
    case 'plexamp': body = <><PlexampPanel name={d.name} /><Row label="Navn" hint="Navnet Plexamp viser"><Txt v={d.name} on={(v) => up('name', v)} /></Row>{saveBtn}</>; break;
    case 'autostandby': body = <AutoStandbyPanel d={d} up={up} save={(x) => void save(x)} msg={msg} />; break;
    case 'backup': body = <><Row label="Nattlig backup" hint="Kl. 03 til NAS (Skjold-backup/<navn>/) hvis opptak-pluginen har SMB, ellers lokalt."><Toggle on={!!d.nightly} onChange={(v) => up('nightly', v)} /></Row><Row label="Behold"><Num v={d.keep} max={60} on={(v) => up('keep', v)} /></Row><Row label="Passfrase" hint="Krypterer passord i nattlig backup. Tom = passord tas ikke med."><Txt v={d.passphrase} pw on={(v) => up('passphrase', v)} /></Row>{saveBtn}<BackupPanel /></>; break;
    case 'wrapped': body = <WrappedPage />; break;
    case 'presence': body = <PresencePanel d={d} up={up} saveBtn={saveBtn} />; break;
    case 'discover': body = <DiscoverPanel />; break;
    case 'podsum': body = <PodsumPanel />; break;
    case 'roomeq': body = <RoomEqPanel enabled={p.enabled} filters={(p.cfg.filters as Peq[]) || []} />; break;
  }
  return (
    <div style="display:flex;flex-direction:column;gap:10px;padding:18px;border-radius:16px;border:1px solid #3a3220;background:#121214">
      <div style="display:flex;align-items:center;gap:12px"><PlugLogo id={p.id} size={36} /><div style="display:flex;flex-direction:column;min-width:0"><span style="font-size:16px;font-weight:600">{p.name}</span><span style="font-size:12px;color:#8b8b86">{p.status}</span></div><button onClick={() => { sel.value = null; }} style={sbtn + ';margin-left:auto'}>Lukk</button></div>
      {body}
    </div>
  );
}

function SleepPanel({ enabled }: { enabled: boolean }) {
  const left = sleepLeft.value;
  useEffect(() => { if (!left) return; const t = setInterval(() => { sleepLeft.value = Math.max(0, sleepLeft.value - 1); }, 1000); return () => clearInterval(t); }, [left > 0]);
  return (
    <>
      {left > 0 && <span style={`font-family:${MONO};font-size:28px;color:#f0c46a`}>{Math.floor(left / 60)}:{String(left % 60).padStart(2, '0')}</span>}
      <div style="display:flex;gap:8px;flex-wrap:wrap">{[15, 30, 45, 60, 90].map((m) => <button key={m} onClick={() => void setPlugin('sleep', { enabled: true, minutes: m })} style={sbtn}>{m} min</button>)}{left > 0 && <button onClick={() => void setPlugin('sleep', { minutes: 0 })} style={sbtn}>Avbryt</button>}</div>
      {!enabled && <span style="font-size:12px;color:#8b8b86">Velg en tid for å starte. Lyden skrus ned det siste minuttet.</span>}
    </>
  );
}

function HistoryPanel() {
  const [items, setItems] = useState<HistItem[] | null>(null);
  useEffect(() => { api.history().then((r) => setItems(r.items)).catch(() => setItems([])); }, []);
  if (!items) return <span style="font-size:12px;color:#8b8b86">Henter …</span>;
  if (!items.length) return <span style="font-size:13px;color:#8b8b86">Ingenting ennå. Slå på pluginen, så lagres det som spilles.</span>;
  return <div style="display:flex;flex-direction:column;max-height:360px;overflow:auto">{items.slice(0, 100).map((x, i) => (
    <div key={i} style="display:grid;grid-template-columns:64px minmax(0,1fr) auto;gap:12px;align-items:center;padding:8px 0;border-top:1px solid #1f1f21">
      <span style={`font-family:${MONO};font-size:11px;color:#8b8b86`}>{new Date(x.t * 1000).toLocaleString('nb-NO', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })}</span>
      <span style="display:flex;flex-direction:column;min-width:0"><b style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.title}</b><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.artist}{x.station ? ' · ' + x.station : ''}</span></span>
      <span style="font-size:11px;color:#8b8b86">{x.source}</span>
    </div>))}</div>;
}

function KidsPanel({ p, d, up, save, msg }: { p: Plugin; d: Record<string, any>; up: (k: string, v: unknown) => void; save: (e?: Record<string, unknown>) => Promise<void>; msg: string }) {
  const [pin, setPin] = useState('');
  const inputs = (status.value?.inputs ?? ['radio']) as InputId[];
  if (p.enabled) return (
    <>
      <span style="font-size:13px;color:#a9a9a3;line-height:1.5">Barnerom-modus er på: maks volum {p.cfg.max}, {(p.cfg.inputs as string[]).length ? 'bare ' + (p.cfg.inputs as InputId[]).map((x) => INPUT_LABEL[x] ?? x).join(', ') : 'alle kilder'}{p.cfg.bedtime ? ', leggetid ' + p.cfg.bedtime : ''}. Innstillingene er skjult i web-UI-et.</span>
      <Row label="Slå av" hint={p.cfg.pin ? 'Skriv PIN-koden' : undefined}>{p.cfg.pin && <Txt v={pin} pw w={110} ph="PIN" on={setPin} />}<button onClick={() => void save({ enabled: false, pin_check: pin })} style={sbtn}>Slå av</button></Row>
      {msg && <span style="font-size:12px;color:#ff8a7a">{msg.startsWith('Feil') ? msg : ''}</span>}
    </>
  );
  return (
    <>
      <Row label="Maks volum"><Num v={d.max} on={(v) => up('max', v)} /></Row>
      <Row label="Tillatte kilder" hint="Ingen valgt = alle">{inputs.map((x) => { const on = (d.inputs as string[]).includes(x); return <button key={x} onClick={() => up('inputs', on ? d.inputs.filter((y: string) => y !== x) : [...d.inputs, x])} style={sbtn + (on ? ';border-color:#5a4420;color:#f0c46a;background:#1c170d' : '')}>{INPUT_LABEL[x] ?? x}</button>; })}</Row>
      <Row label="Tillatte radiokanaler" hint="Ingen valgt = alle">{favs.value.slice(0, 12).map((f) => { const on = (d.presets as number[]).includes(f.n); return <button key={f.n} onClick={() => up('presets', on ? d.presets.filter((y: number) => y !== f.n) : [...d.presets, f.n])} style={sbtn + (on ? ';border-color:#5a4420;color:#f0c46a;background:#1c170d' : '')}>{f.title}</button>; })}</Row>
      <Row label="Leggetid" hint="Lyden skrus ned og slås av"><Time v={d.bedtime} on={(v) => up('bedtime', v)} /></Row>
      <Row label="PIN for å slå av" hint="Valgfri, 4–8 siffer"><Txt v={d.pin} pw w={110} on={(v) => up('pin', v.replace(/\\D/g, '').slice(0, 8))} /></Row>
      <div style="display:flex;gap:10px;align-items:center;padding-top:12px;border-top:1px solid #1f1f21"><button onClick={() => void save({ enabled: true })} style={pbtn}>Slå på barnerom-modus</button><span style="font-size:12px;color:#8b8b86">{msg}</span></div>
    </>
  );
}

function RecordPanel({ d, up, saveBtn }: { d: Record<string, any>; up: (k: string, v: unknown) => void; saveBtn: preact.ComponentChildren }) {
  const [rp, setRp] = useState<RecPayload>({ items: [], dir: '' });
  const [now, setNow] = useState({ preset: favs.value[0]?.n ?? 0, url: '', minutes: 60 });
  const [err, setErr] = useState('');
  const [smbMsg, setSmbMsg] = useState('');
  const [shares, setShares] = useState<string[]>([]);
  const load = () => api.recordings().then(setRp).catch(() => {});
  useEffect(() => { void load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, []);
  const post = async (b: Record<string, unknown>) => { setErr(''); try { setRp(await api.recPost(b)); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
  const host = String(d.smb_share || '').replace(/\\/g, '/').replace(/^smb:/i, '').replace(/^\/+/, '').split('/')[0] ?? '';
  const test = async () => {
    setSmbMsg('Kobler til …');
    try { const r = await api.recPost({ smb_test: true }); setRp(r); setSmbMsg(r.smb?.msg || 'Tilkoblet'); } catch (e) { setSmbMsg(e instanceof Error ? e.message : String(e)); }
  };
  const listShares = async () => {
    setSmbMsg('Henter delte mapper …'); setShares([]);
    try { const r = await api.recShares({ server: host, user: d.smb_user, password: d.smb_password, domain: d.smb_domain }); setShares(r.shares); setSmbMsg(r.shares.length ? 'Velg en delt mappe' : 'Fant ingen delte mapper'); } catch (e) { setSmbMsg(e instanceof Error ? e.message : String(e)); }
  };
  const smb = rp.smb;
  const songs = rp.songs ?? [];
  const mmss = (s?: number) => s == null ? '' : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  const stCol = (x: RecSong) => x.status === 'ok' ? '#6fcf7f' : x.status === 'duplikat' ? '#8b8b86' : '#ff8a7a';
  const stTxt = (x: RecSong) => x.status === 'ok' ? (x.where === 'smb' ? 'Lagret på NAS' : 'Lagret lokalt') : x.status === 'duplikat' ? 'Finnes fra før' : 'Feil' + (x.error ? ': ' + x.error : '');
  return (
    <>
      <span style="font-size:12px;color:#8b8b86;line-height:1.5">Opptak er for privat bruk.</span>
      <Row label="Ta opp nå"><FavSel v={now.preset} none="Strøm-URL" on={(v) => setNow({ ...now, preset: v })} />{!now.preset && <Txt v={now.url} ph="https://…" on={(v) => setNow({ ...now, url: v })} />}<Num v={now.minutes} min={1} max={240} on={(v) => setNow({ ...now, minutes: v })} /><span style="font-size:12px;color:#8b8b86">min</span><button onClick={() => void post({ start: now })} style={pbtn}>Ta opp</button></Row>
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}

      <span style="font-size:13px;font-weight:600;padding-top:8px">Lagre på NAS (SMB)</span>
      <span style="font-size:12px;color:#8b8b86;line-height:1.5">Låtene lagres som «Artist/Artist - Tittel» i den delte mappen. Uten NAS lagres de på Skjold.</span>
      <Row label="Delt mappe" hint="F.eks. //nas.local/musikk"><Txt v={d.smb_share} ph="//nas.local/musikk" w={220} on={(v) => up('smb_share', v)} /><button onClick={() => void listShares()} disabled={!host} style={sbtn}>Finn mapper</button></Row>
      {shares.length > 0 && <Row label={'Delte mapper på ' + host}>{shares.map((x) => <button key={x} onClick={() => { up('smb_share', `//${host}/${x}`); setShares([]); }} style={sbtn}>{x}</button>)}</Row>}
      <Row label="Undermappe" hint="Tom = rett i den delte mappen"><Txt v={d.smb_sub} ph="Radioopptak" w={180} on={(v) => up('smb_sub', v)} /></Row>
      <Row label="Brukernavn" hint="Tom = gjest"><Txt v={d.smb_user} w={160} on={(v) => up('smb_user', v)} /></Row>
      <Row label="Passord"><Txt v={d.smb_password} pw w={160} ph={d.smb_password ? 'satt' : ''} on={(v) => up('smb_password', v)} /></Row>
      <Row label="Domene" hint="Valgfritt"><Txt v={d.smb_domain} w={140} on={(v) => up('smb_domain', v)} /></Row>
      <Row label="SMB-versjon"><select value={d.smb_vers} onChange={(e) => up('smb_vers', (e.currentTarget as HTMLSelectElement).value)} style={fld}>{['auto', '3.1.1', '3.0', '2.1', '2.0', '1.0'].map((v) => <option key={v} value={v}>{v === 'auto' ? 'Automatisk' : v}</option>)}</select></Row>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button onClick={() => void test()} disabled={!d.smb_share} style={sbtn}>Test tilkobling</button>
        <span style={`font-size:12px;color:${smb?.ok ? '#6fcf7f' : smbMsg || smb?.msg ? '#ff8a7a' : '#8b8b86'}`}>{smbMsg || (smb?.set ? (smb.ok ? '● Tilkoblet ' + smb.share : smb.msg || 'Ikke tilkoblet') : 'Ikke satt – lagres lokalt')}</span></div>
      <span style="font-size:11.5px;color:#8b8b86">Lagre innstillingene før du tester.</span>

      <span style="font-size:13px;font-weight:600;padding-top:8px">Låter</span>
      <Row label="Del opptaket i låter" hint="Finner låtbytter fra kanalens låtinfo og lydmønsteret"><Toggle on={!!d.split} label="" onChange={(v) => up('split', v)} /></Row>
      <Row label="Format"><select value={d.fmt} onChange={(e) => up('fmt', (e.currentTarget as HTMLSelectElement).value)} style={fld}><option value="mp3">MP3 320 kbps</option><option value="flac">FLAC</option><option value="m4a">M4A (AAC 256)</option></select></Row>
      <Row label="Korteste låt" hint="Kortere klipp (jingler, reklame) lagres ikke"><Num v={d.min_len} min={20} max={900} on={(v) => up('min_len', v)} /><span style="font-size:12px;color:#8b8b86">sek</span></Row>
      <Row label="Behold duplikater" hint="Av = hopp over låter som allerede finnes"><Toggle on={!!d.keep_dupes} label="" onChange={(v) => up('keep_dupes', v)} /></Row>
      <Row label="Behold hele opptaket" hint="I tillegg til låtene"><Toggle on={!!d.keep_raw} label="" onChange={(v) => up('keep_raw', v)} /></Row>

      <span style="font-size:13px;font-weight:600;padding-top:8px">Planlagte opptak</span>
      {(d.schedules as any[]).map((a, i) => (
        <div key={i} style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:8px 0;border-top:1px solid #1f1f21">
          <Time v={a.time} on={(v) => { const x = [...d.schedules]; x[i] = { ...a, time: v }; up('schedules', x); }} />
          <Days v={a.days} on={(v) => { const x = [...d.schedules]; x[i] = { ...a, days: v }; up('schedules', x); }} />
          <FavSel v={a.preset} none="Strøm-URL" on={(v) => { const x = [...d.schedules]; x[i] = { ...a, preset: v }; up('schedules', x); }} />
          {!a.preset && <Txt v={a.url} ph="https://…" on={(v) => { const x = [...d.schedules]; x[i] = { ...a, url: v }; up('schedules', x); }} />}
          <Num v={a.minutes} min={1} max={240} on={(v) => { const x = [...d.schedules]; x[i] = { ...a, minutes: v }; up('schedules', x); }} /><span style="font-size:12px;color:#8b8b86">min</span>
          <Txt v={a.program || ''} ph="Programnavn (valgfritt)" w={170} on={(v) => { const x = [...d.schedules]; x[i] = { ...a, program: v }; up('schedules', x); }} />
          {a.program && <><span style="font-size:12px;color:#8b8b86">behold</span><Num v={a.keep || 8} min={1} max={52} on={(v) => { const x = [...d.schedules]; x[i] = { ...a, keep: v }; up('schedules', x); }} /></>}
          {a.nrk && <span style="font-size:11.5px;color:#8b8b86">NRK {String(a.nrk).toUpperCase()}</span>}
          <button onClick={() => up('schedules', d.schedules.filter((_: unknown, j: number) => j !== i))} style={sbtn}>Fjern</button>
        </div>))}
      <span style="font-size:12px;color:#8b8b86;line-height:1.5">Med programnavn lagres opptaket som en episode (ikke delt i låter) og vises som podkast under «Programmer».</span>
      <GuidePicker onPick={(sc) => up('schedules', [...d.schedules, sc])} />
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button onClick={() => up('schedules', [...d.schedules, { time: '08:00', days: [5, 6], preset: favs.value[0]?.n ?? 0, url: '', minutes: 60, on: true }])} style={sbtn}>+ Planlegg opptak</button><span style="font-size:12px;color:#8b8b86">Maks lokal lagring</span><Num v={d.max_mb} min={100} max={100000} w={90} on={(v) => up('max_mb', v)} /><span style="font-size:12px;color:#8b8b86">MB</span></div>
      {saveBtn}

      <span style="font-size:13px;font-weight:600;padding-top:8px">Opptak</span>
      {!rp.items.length && <span style="font-size:12.5px;color:#8b8b86">Ingen opptak ennå.</span>}
      {rp.items.map((x) => (
        <div key={x.name} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid #1f1f21">
          <span style="display:flex;flex-direction:column;min-width:0"><b style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.name.replace(/\.mp3$/, '')}</b><span style={`font-family:${MONO};font-size:11px;color:${x.recording ? '#ff6a5a' : '#8b8b86'}`}>{x.recording ? `● Tar opp${x.songs ? ' · ' + x.songs + ' låtbytter' : ''} · ` : ''}{(x.size / 1048576).toFixed(1)} MB</span></span>
          <span style="display:flex;gap:8px">{!x.recording && <button onClick={() => void post({ play: x.name })} style={sbtn}>Spill</button>}<button onClick={() => void post({ delete: x.name })} style={sbtn}>{x.recording ? 'Stopp' : 'Slett'}</button></span>
        </div>))}
      <ProgramsPanel programs={rp.programs ?? []} feed={rp.feed ?? ''} onChange={(x) => setRp(x as RecPayload)} />
      {songs.length > 0 && <>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:8px"><span style="font-size:13px;font-weight:600">Lagrede låter</span><button onClick={() => void post({ clear_songs: true })} style={sbtn}>Tøm listen</button></div>
        {songs.map((x, i) => (
          <div key={i} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:7px 0;border-top:1px solid #1f1f21">
            <span style="display:flex;flex-direction:column;min-width:0"><b style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.artist ? `${x.artist} – ${x.title}` : x.title}</b><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.channel} · {new Date(x.t * 1000).toLocaleString('nb-NO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span></span>
            <span style="display:flex;flex-direction:column;align-items:flex-end"><span style={`font-family:${MONO};font-size:11px;color:#c9c9c4`}>{mmss(x.dur)}</span><span style={`font-size:11px;color:${stCol(x)}`}>{stTxt(x)}</span></span>
          </div>))}
      </>}
    </>
  );
}

function SnapPanel({ d, up, saveBtn }: { d: Record<string, any>; up: (k: string, v: unknown) => void; saveBtn: preact.ComponentChildren }) {
  const [cl, setCl] = useState<SnapClient[]>([]), [err, setErr] = useState('');
  const load = (b?: Record<string, unknown>) => api.snapcast(b).then((r) => { setCl(r.clients); setErr(r.ok ? '' : r.error || ''); }).catch((e) => setErr(String(e)));
  useEffect(() => { void load(); }, []);
  return (
    <>
      <span style="font-size:12.5px;color:#a9a9a3;line-height:1.5">Beta. Installer først fra terminalen: hovedenheten med <code style={`font-family:${MONO};color:#f0c46a`}>sudo bash pi/install_snapcast.sh server</code>, de andre rommene med <code style={`font-family:${MONO};color:#f0c46a`}>sudo bash pi/install_snapcast.sh client &lt;hovedenhet&gt;</code>.</span>
      <Row label="Rolle"><select value={d.role} onChange={(e) => up('role', (e.currentTarget as HTMLSelectElement).value)} style={fld}><option value="server">Hovedenhet (server)</option><option value="client">Klient</option></select></Row>
      <Row label="Snapserver" hint="Tom = denne enheten"><Txt v={d.server} ph="skjold.local" w={180} on={(v) => up('server', v)} /></Row>
      {saveBtn}
      <span style="font-size:13px;font-weight:600;padding-top:8px">Klienter</span>
      {err && <span style="font-size:12px;color:#8b8b86">{err}</span>}
      {cl.map((c) => (
        <Row key={c.id} label={c.name || c.id} hint={c.connected ? 'Tilkoblet' : 'Frakoblet'}>
          <span style="font-size:12px;color:#8b8b86">Forsinkelse</span><Num v={c.latency} min={-500} max={2000} w={80} on={(v) => void load({ id: c.id, latency: v })} /><span style="font-size:12px;color:#8b8b86">ms · Volum</span><Num v={c.volume} on={(v) => void load({ id: c.id, volume: v })} />
        </Row>))}
    </>
  );
}

// ---------- Romkorreksjon ----------
function Graph({ curves }: { curves: { c: Curve; col: string }[] }) {
  if (!curves.length) return null;
  const W = 560, H = 200, f1 = 20, f2 = 1000;
  const x = (f: number) => (Math.log(f / f1) / Math.log(f2 / f1)) * W;
  const all = curves.flatMap((k) => k.c.db), mid = all.reduce((a, b) => a + b, 0) / all.length;
  const y = (v: number) => H / 2 - (v - mid) * 5;
  return (
    <svg viewBox={`0 0 ${W} ${H + 18}`} style="width:100%;max-width:560px;height:auto;background:#0b0b0c;border-radius:10px">
      {[40, 100, 300].map((f) => <g key={f}><line x1={x(f)} x2={x(f)} y1={0} y2={H} stroke="#242426" /><text x={x(f) + 3} y={H + 13} fill="#8b8b86" font-size="10">{f} Hz</text></g>)}
      <rect x={x(40)} y={0} width={x(300) - x(40)} height={H} fill="#d9a441" opacity="0.05" />
      {curves.map((k, i) => <polyline key={i} fill="none" stroke={k.col} stroke-width="2" points={k.c.f.map((f, j) => `${x(f).toFixed(1)},${Math.max(0, Math.min(H, y(k.c.db[j]!))).toFixed(1)}`).join(' ')} />)}
    </svg>
  );
}

function RoomEqPanel({ enabled, filters }: { enabled: boolean; filters: Peq[] }) {
  const [meas, setMeas] = useState<Curve[]>([]);
  const [busy, setBusy] = useState(''), [err, setErr] = useState('');
  const [res, setRes] = useState<{ filters: Peq[]; after: number[] } | null>(null);
  const level = useRef(0.5);
  const measure = async () => {
    setErr(''); setBusy('Forbereder …');
    try {
      const info = await api.roomeqSweep({ level: level.current, delay: 1.5 });
      const rec = await recordMic(info.delay + info.dur + 1.5, () => setBusy('Måler – vær stille …'));
      const sw = logSweep(info.f1, info.f2, info.dur, rec.sr);
      const c = responseFromRecording(rec.data, sw, rec.sr);
      const next = [...meas, c]; setMeas(next); setRes(suggest(averageCurves(next)));
      setBusy('');
    } catch (e) { setBusy(''); setErr(e instanceof Error ? (e.name === 'NotAllowedError' ? 'Mikrofonen er ikke tillatt. Gi nettleseren tilgang og prøv igjen.' : e.message) : String(e)); }
  };
  const avg = meas.length ? averageCurves(meas) : null;
  return (
    <>
      <span style="font-size:12.5px;color:#a9a9a3;line-height:1.55">Hold telefonen der du sitter, med mikrofonen opp. Skjold spiller en sweep i 6 sekunder mens telefonen lytter. Mål 3–5 steder i rommet, så tas snittet. Forslaget demper bare basstopper mellom 40 og 300 Hz (maks −10 dB), fordi telefonmikrofoner er unøyaktige utenfor dette. Åpne siden over https eller på samme maskin, ellers tillater ikke nettleseren mikrofonen.</span>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button disabled={!!busy} onClick={() => void measure()} style={pbtn}>{busy || (meas.length ? `Mål punkt ${meas.length + 1}` : 'Start måling')}</button>{meas.length > 0 && <button onClick={() => { setMeas([]); setRes(null); }} style={sbtn}>Nullstill</button>}<span style="font-size:12px;color:#8b8b86">{meas.length} målepunkt{meas.length === 1 ? '' : 'er'}</span></div>
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
      {avg && res && <><Graph curves={[{ c: avg, col: '#8b8b86' }, { c: { f: avg.f, db: res.after }, col: '#f0c46a' }]} /><span style="font-size:11.5px;color:#8b8b86">Grå: målt · gull: med korreksjon</span></>}
      {res && <div style="display:flex;flex-direction:column;gap:4px">{res.filters.length ? res.filters.map((f, i) => <span key={i} style={`font-family:${MONO};font-size:12px;color:#c9c9c4`}>{f.f.toFixed(0)} Hz · Q {f.q} · {f.g} dB</span>) : <span style="font-size:12.5px;color:#9be0a8">Ingen tydelige basstopper. Rommet trenger ingen korreksjon.</span>}</div>}
      {res && res.filters.length > 0 && <div style="display:flex;gap:10px"><button onClick={() => void setPlugin('roomeq', { enabled: true, filters: res.filters, measured: new Date().toISOString() })} style={pbtn}>Bruk korreksjonen</button></div>}
      {filters.length > 0 && <Row label="Lagret korreksjon" hint={filters.map((f) => `${f.f.toFixed(0)} Hz ${f.g} dB`).join(' · ')}><Toggle on={enabled} label="Romkorreksjon" onChange={(v) => void setPlugin('roomeq', { enabled: v })} /></Row>}
    </>
  );
}

// ---------- Sangtekster i Spiller ----------
export function LyricsPane({ pos }: { pos: number }) {
  const [l, setL] = useState<Lyrics | null>(null);
  const s = status.value, key = (s?.artist ?? '') + '|' + (s?.title ?? '');
  useEffect(() => { setL(null); api.lyrics().then(setL).catch(() => setL({ enabled: true, found: false, error: 'Får ikke kontakt med Skjold' })); }, [key]);
  const ref = useRef<HTMLDivElement>(null);
  const syn = l?.synced ?? [];
  let cur = -1; for (let i = 0; i < syn.length; i++) if (syn[i]!.t <= pos + 0.3) cur = i;
  useEffect(() => { const el = ref.current?.querySelector('[data-cur="1"]') as HTMLElement | null; el?.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, [cur]);
  if (!l) return <div class="dkx-empty"><span>Henter tekst …</span></div>;
  if (!l.enabled) return <div class="dkx-empty"><span>Slå på pluginen Sangtekster for å se teksten her.</span></div>;
  if (!l.found) return <div class="dkx-empty"><span>{l.instrumental ? 'Instrumental låt.' : l.error ? 'Fant ikke teksten (' + l.error + ').' : 'Fant ingen tekst for denne låten.'}</span></div>;
  return (
    <div ref={ref} style="display:flex;flex-direction:column;gap:10px;max-height:420px;overflow:auto;padding:6px 2px">
      {syn.length ? syn.map((x, i) => <span key={i} data-cur={i === cur ? '1' : '0'} style={`font-size:${i === cur ? 20 : 16}px;font-weight:${i === cur ? 600 : 400};color:${i === cur ? '#f2f2ee' : i < cur ? '#6a6a65' : '#a9a9a3'};transition:all .2s`}>{x.l || '♪'}</span>)
        : <pre style="margin:0;white-space:pre-wrap;font-family:inherit;font-size:15px;line-height:1.6;color:#c9c9c4">{l.plain}</pre>}
      <span style="font-size:10.5px;color:#6a6a65">Tekst fra lrclib.net</span>
    </div>
  );
}

// ---------- SUB/WAVE ----------
function SubwavePanel({ d, up, saveBtn }: { d: Record<string, any>; up: (k: string, v: unknown) => void; saveBtn: preact.ComponentChildren }) {
  const [msg, setMsg] = useState('');
  const test = async () => { setMsg('Tester …'); try { const r = await api.subwave(true); setMsg(!r.configured ? 'Slå på pluginen og lagre adressen først.' : r.error ? 'Feil: ' + r.error : 'Tilkoblet: ' + (typeof r.health === 'string' ? r.health : JSON.stringify(r.health)).slice(0, 160)); } catch (e) { setMsg('Feil: ' + (e instanceof Error ? e.message : String(e))); } };
  const act = async (b: Record<string, unknown>, ok: string) => { setMsg('…'); try { const r = await api.subwavePost(b); setMsg(r.error ? 'Feil: ' + r.error : ok); } catch (e) { setMsg('Feil: ' + (e instanceof Error ? e.message : String(e))); } };
  return (
    <>
      <Row label="Stasjonsadresse" hint="For eksempel https://radio.dittdomene.no"><Txt v={d.url} ph="https://…" w={280} on={(v) => up('url', v)} /></Row>
      <Row label="Brukernavn" hint="Valgfritt. Brukes bare hvis stasjonen er bak passord."><Txt v={d.user} w={160} on={(v) => up('user', v)} /></Row>
      <Row label="Passord" hint="Lagres på Skjold. Gir også DJ-handlinger som «Hopp over»."><Txt v={d.password} pw w={160} on={(v) => up('password', v)} /></Row>
      {saveBtn}
      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:6px"><button onClick={() => void test()} style={sbtn}>Test</button><button onClick={() => void act({ favorite: true }, 'Lagt til som radiofavoritt')} style={sbtn}>Legg til som radiofavoritt</button><button onClick={() => void act({ play: true }, 'Spiller SUB/WAVE')} style={pbtn}>Spill nå</button></div>
      {msg && <span style={`font-size:12px;color:${msg.startsWith('Feil') ? '#ff8a7a' : '#a9a9a3'};word-break:break-word`}>{msg}</span>}
    </>
  );
}

const pick = (o: any, ...ks: string[]): any => { if (!o || typeof o !== 'object') return undefined; for (const k of ks) if (o[k] != null && o[k] !== '') return o[k]; return undefined; };
const arr = (o: any, ...ks: string[]): any[] => { const v = pick(o, ...ks); return Array.isArray(v) ? v : []; };
const line = (x: any): [string, string] => typeof x === 'string' ? [x, ''] : [String(pick(x, 'title', 'name', 'text', 'message', 'line', 'summary') ?? JSON.stringify(x)).slice(0, 200), String(pick(x, 'artist', 'by', 'who', 'speaker', 'time', 'at', 'ts') ?? '')];

/** Spiller-fanene «Booth» og «Kø» når SUB/WAVE spiller, med «Ønsk deg en låt». */
export function SubwavePane({ mode }: { mode: 'booth' | 'queue' }) {
  const [d, setD] = useState<Record<string, any> | null>(null), [txt, setTxt] = useState(''), [msg, setMsg] = useState('');
  const load = () => api.subwave().then(setD).catch(() => setD({ error: 'Får ikke kontakt med Skjold' }));
  useEffect(() => { void load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);
  const ask = async () => { if (!txt.trim()) return; setMsg('Sender ønsket …'); try { const r = await api.subwavePost({ text: txt.trim() }); setMsg(r.error ? 'Feil: ' + r.error : 'Ønsket er sendt til DJ-en.'); if (!r.error) setTxt(''); } catch (e) { setMsg('Feil: ' + (e instanceof Error ? e.message : String(e))); } };
  const st = d?.state ?? {};
  const items = mode === 'queue' ? arr(st, 'queue', 'upcoming', 'up_next') : [...arr(st, 'booth', 'booth_log', 'dj_log', 'log'), ...arr(d?.session, 'transcript', 'messages', 'log')];
  const hist = mode === 'queue' ? arr(st, 'history', 'played', 'recent') : [];
  return (
    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;gap:8px"><input value={txt} onInput={(e) => setTxt((e.currentTarget as HTMLInputElement).value)} onKeyDown={(e) => { if (e.key === 'Enter') void ask(); }} placeholder="Ønsk deg en låt, f.eks. «noe rolig med piano»" style={fld + ';flex:1'} /><button onClick={() => void ask()} style={pbtn}>Ønsk</button></div>
      {msg && <span style={`font-size:12px;color:${msg.startsWith('Feil') ? '#ff8a7a' : '#9be0a8'}`}>{msg}</span>}
      {!d ? <span style="font-size:12px;color:#8b8b86">Henter fra SUB/WAVE …</span> : d.error && !items.length ? <span style="font-size:12px;color:#ff8a7a">{d.error}</span> : null}
      <div style="display:flex;flex-direction:column;max-height:340px;overflow:auto">
        {items.map((x, i) => { const [a, b] = line(x); return <div key={i} style="display:flex;flex-direction:column;gap:2px;padding:8px 0;border-top:1px solid #1f1f21"><span style="font-size:13.5px;color:#f2f2ee;line-height:1.45">{a}</span>{b && <span style="font-size:11.5px;color:#8b8b86">{b}</span>}</div>; })}
        {d && !items.length && !d.error && <span style="font-size:12.5px;color:#8b8b86">{mode === 'queue' ? 'Køen er tom.' : 'Ingenting i DJ-loggen ennå.'}</span>}
        {hist.length > 0 && <span class="kicker" style="padding-top:10px">SPILT</span>}
        {hist.slice(0, 15).map((x, i) => { const [a, b] = line(x); return <div key={'h' + i} style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-top:1px solid #1f1f21"><span style="font-size:13px;color:#a9a9a3">{a}</span><span style="font-size:11.5px;color:#6a6a65">{b}</span></div>; })}
      </div>
      {d?.admin && <div style="display:flex;gap:8px"><button onClick={() => void api.subwavePost({ action: 'skip' }).then(() => setMsg('Hopper over låten')).catch(() => {})} style={sbtn}>Hopp over</button></div>}
    </div>
  );
}
