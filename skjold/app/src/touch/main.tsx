// Skjold Touch – skjermgrensesnittet på 7″ berøringsskjerm (800 × 480, kiosk).
// Bygget piksel-identisk etter design-handoff «Skjold Touch UI.dc.html»: mål, farger og tekster er hentet derfra.
// Data er ekte: status/hendelser fra daemonen, rom fra /api/rom (mDNS), innstillinger via /api/settings.
import { render } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { signal } from '@preact/signals';
import './touch.css';
import { api, coverUrl, getBase, INPUT_LABEL, PRODUCT_SHORT, productOf, setBase, type InputId, type Status } from '../lib/api';
import { loadSettings, playPause, reconnect, setSetting, setVolume, settings, startPolling, status, act, online } from '../lib/store';
import { art, TOUCH_IDLE, TOUCH_OUT, TOUCH_ROLES, TOUCH_STANDBY_S } from '../lib/settings';
import { favs, loadFavs, playFav } from '../lib/radio';
import { ndAlbum, ndAlbumList, ndConfigured, ndCover, type NdAlbum } from '../lib/navidrome';
import { playNd } from '../lib/library';
import { groupAll } from '../lib/groups';
import { DoorbellOverlay, TalkButton } from '../screens/features';

const MONO = "'IBM Plex Mono',monospace";
type Scr = 'now' | 'home' | 'lib' | 'rooms' | 'set';
interface Peer { id: string; navn: string; produkt: string; base: string }

// ---------- tilstand ----------
const scr = signal<Scr>('now');
const roomsOpen = signal(false);
const idle = signal(false), idleOp = signal(1);
const lib = signal(0);
const peers = signal<Peer[]>([]);
const peerSt = signal<Record<string, Status | null>>({});
const ctl = signal('');           // '' = denne enheten, ellers base til rommet som styres
const local = signal<Status | null>(null);
const boot = signal({ on: true, step: 0, op: 1 });
const now = signal(Date.now());
let lastAct = Date.now() + 4500;

// Kiosken kjører på enheten selv: start alltid på denne enheten (en lagret host fra fjernstyring nullstilles).
setBase(null);
startPolling(); void loadSettings(); void loadFavs();

const here = (): string => location.origin;
async function getAt<T>(base: string, path: string): Promise<T> { const r = await fetch((base || here()) + path, { cache: 'no-store' }); if (!r.ok) throw new Error(String(r.status)); return r.json() as Promise<T>; }
async function postAt(base: string, path: string, body: unknown): Promise<void> { await fetch((base || here()) + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }

async function pollRooms(): Promise<void> {
  try { local.value = await getAt<Status>('', '/api/status'); } catch { /* daemonen starter */ }
  try { peers.value = (await getAt<{ rom: Peer[] }>('', '/api/rom')).rom ?? []; } catch { /* eldre daemon */ }
  const res: Record<string, Status | null> = {};
  await Promise.all(peers.value.map(async (p) => { try { res[p.base] = await getAt<Status>(p.base, '/api/status'); } catch { res[p.base] = null; } }));
  peerSt.value = res;
}
void pollRooms(); setInterval(() => void pollRooms(), 5000);

function control(base: string): void {
  roomsOpen.value = false;
  if (base === ctl.value) return;
  ctl.value = base; setBase(base || null); reconnect();
}

// ---------- standby og oppstart ----------
function goIdle(): void { idle.value = true; idleOp.value = 0; setTimeout(() => { idleOp.value = 1; }, 30); }
function wake(): void { lastAct = Date.now(); idle.value = false; }
addEventListener('pointerdown', () => { lastAct = Date.now(); }, true);
addEventListener('contextmenu', (e) => e.preventDefault());
setInterval(() => {
  now.value = Date.now();
  const ms = (TOUCH_STANDBY_S[settings.value.tStandby] ?? 30) * 1000;
  if (!idle.value && !boot.value.on && ms > 0 && Date.now() - lastAct > ms) goIdle();
}, 1000);

let bootT: number[] = [];
function runBoot(): void {
  bootT.forEach(clearTimeout); idle.value = false;
  const set = (p: Partial<typeof boot.value>) => { boot.value = { ...boot.value, ...p }; };
  set({ on: true, step: 0, op: 1 });
  const seq: [number, Partial<typeof boot.value>][] = [[250, { step: 1 }], [500, { step: 2 }], [750, { step: 3 }], [1000, { step: 4 }], [1250, { step: 5 }], [1700, { step: 6 }], [2300, { step: 7 }], [2900, { step: 8 }]];
  bootT = seq.map(([ms, p]) => window.setTimeout(() => set(p), ms));
  // «Klar» først når daemonen svarer (minst 3,5 s), så tones flaten ut
  const t0 = Date.now();
  const ready = () => {
    if (!online.value && Date.now() - t0 < 20000) { bootT.push(window.setTimeout(ready, 250)); return; }
    set({ step: 9 });
    bootT.push(window.setTimeout(() => set({ op: 0 }), 400), window.setTimeout(() => { set({ on: false }); lastAct = Date.now(); }, 1000));
  };
  bootT.push(window.setTimeout(ready, 3500));
  lastAct = Date.now() + 4500;
}
runBoot();

// ---------- hjelpere ----------
// Reservefarger når det ikke finnes cover (samme 135°-gradienter som designfilen)
const PAL: [string, string][] = [['#e8893a', '#8a3b12'], ['#2563eb', '#0b1640'], ['#a3a3a3', '#2a2a2a'], ['#d9a441', '#4a2f08'], ['#16a34a', '#062a14'], ['#7c3aed', '#1c0b3a'], ['#db2777', '#3a0a24'], ['#0f5a6b', '#08202c'], ['#c2410c', '#3b0d0d']];
function grad(key: string, i?: number): string {
  let h = 0; for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const [a, b] = PAL[(i ?? h) % PAL.length]!; return 'linear-gradient(135deg,' + a + ',' + b + ')';
}
function artBg(key: string, image?: string, i?: number): string { return image && /^(https?:)?\/\//i.test(image) ? art(key, image).bg : grad(key, i); }
const fmt = (s: number) => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
const PLAY_D = 'M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z', PAUSE_D = 'M6 4.5h4v15H6zM14 4.5h4v15h-4z';
function artOf(s: Status | null, base = ''): string {
  if (!s) return '#1b1b1c';
  let u = coverUrl(s);
  if (u && base && u.startsWith(getBase())) u = base + u.slice(getBase().length);
  const fb = s.title || s.station ? grad(s.title || s.station) : '#1b1b1c';
  return u ? 'url("' + u.replace(/"/g, '') + '") center / cover no-repeat, ' + fb : fb;
}
function srcName(s: Status | null): string {
  if (!s) return '';
  if (s.radio_now?.genre === 'Navidrome') return 'NAVIDROME';
  return String(s.source_label || INPUT_LABEL[s.input as InputId] || s.input || '').toUpperCase();
}
function npLine(s: Status | null): string {
  if (!s || !s.power) return 'Av';
  if (!s.playing && !s.title) return 'Ingenting spilles';
  return [s.title || s.station, s.artist].filter(Boolean).join(' · ');
}
const role = () => settings.value.tRole ?? 0;   // 0 begge, 1 bare spiller, 2 bare fjernkontroll

// ---------- ikoner (fra designfilen) ----------
const IC: Record<Scr, string> = { now: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', home: 'M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10', lib: 'M4 4h4v16H4zM10 4h4v16h-4zM16 5l4 1-3 14-4-1z', rooms: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', set: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M16 4v4M10 10v4M18 16v4' };
type Src = [string, string, string, string, () => void];
const recv = (id: InputId) => () => { void act(() => api.input(id), { input: id }); scr.value = 'now'; };
const SRC: Src[] = [
  ['YouTube Music', 'Miks og spillelister', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM10 8.5v7l6-3.5z', '#c4302b', () => { lib.value = 0; scr.value = 'lib'; }],
  ['Navidrome', 'Ditt bibliotek', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z', '#1e5aa8', () => { lib.value = 1; scr.value = 'lib'; }],
  ['Radio', 'Norge og verden', 'M4 9h16v11H4zM8 9l9-5M8 14.5a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0M14 13h3M14 16h3', '#8a3b12', () => { lib.value = 2; scr.value = 'lib'; }],
  ['Spotify', 'Spotify Connect', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM7.5 9.5c3-1 6.5-.7 9 .8M8 12.5c2.5-.7 5.5-.4 7.5.8M8.5 15.3c2-.5 4-.3 5.6.6', '#1db954', recv('spotify')],
  ['AirPlay', 'Fra iPhone eller Mac', 'M5 17H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-1M12 15l5 6H7z', '#4a4a50', recv('airplay')],
  ['Blåtann', 'Synlig i 2 minutter', 'M7 7l10 10-5 4V3l5 4L7 17', '#1a4fd0', () => { void api.btPairing().catch(() => undefined); recv('bt')(); }],
  ['UPnP / DLNA', 'Mottaker', 'M4 12a8 8 0 0 1 16 0M7 12a5 5 0 0 1 10 0M10 12a2 2 0 0 1 4 0M12 14v6', '#4a4a50', () => { scr.value = 'now'; }],
  ['Chromecast', 'Cast fra apper', 'M3 7V6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-6M3 11a8 8 0 0 1 8 8M3 15a4 4 0 0 1 4 4M3 19h.01', '#4a4a50', () => { scr.value = 'now'; }]
];

// ---------- skjermer ----------
function NowPlaying() {
  const s = status.value, remote = !!ctl.value, out = settings.value.tOut ?? 2;
  const [pos, setPos] = useState(s?.position ?? 0);
  useEffect(() => { setPos(s?.position ?? 0); }, [s?.position, s?.title]);
  useEffect(() => { const t = setInterval(() => { if (status.value?.playing) setPos((p) => p + 1); }, 1000); return () => clearInterval(t); }, []);
  const dur = s?.duration ?? 0, p = dur > 0 ? Math.min(pos, dur) : 0, pct = dur > 0 ? (p / dur * 100).toFixed(1) + '%' : '0%';
  const room = remote ? peers.value.find((x) => x.base === ctl.value) : null;
  const kicker = remote ? 'SPILLER I ' + (room?.navn ?? s?.name ?? '').toUpperCase() : 'SPILLER NÅ · ' + ['RCA', '3,5 MM', 'RCA + 3,5 MM'][out];
  const title = s?.title || s?.station || (s?.power === false ? 'Av' : 'Ingenting spilles');
  return (
    <section style="flex:1;display:grid;grid-template-columns:300px minmax(0,1fr);grid-template-rows:300px auto;column-gap:26px;row-gap:14px;padding:18px 26px 14px;align-content:center;min-height:0">
      <div style={`position:relative;width:300px;height:300px;border-radius:14px;background:${artOf(s)};box-shadow:0 20px 50px rgba(0,0,0,.6)`}>
        <span style={`position:absolute;left:12px;bottom:10px;font-family:${MONO};font-size:10px;letter-spacing:.1em;color:rgba(255,255,255,.75)`}>{srcName(s)}</span>
      </div>
      <div style="display:flex;flex-direction:column;min-width:0">
        <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#f0c46a`}>{kicker}</span>
        <span style="margin-top:10px;font-size:30px;font-weight:600;line-height:1.1;letter-spacing:-.01em;text-wrap:pretty;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{title}</span>
        <span style="margin-top:6px;font-size:17px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.artist ?? ''}</span>
        <span style="margin-top:2px;font-size:13px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.album ?? ''}</span>
        <div style="flex:1" />
        <div style="display:flex;align-items:center;gap:8px;margin-top:10px">
          <button onClick={() => void act(() => api.transport('previous'))} aria-label="Forrige" style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M19 18.5v-13a.8.8 0 0 0-1.25-.66L9 10.9V6a1 1 0 0 0-2 0v12a1 1 0 0 0 2 0v-4.9l8.75 6.06A.8.8 0 0 0 19 18.5z" /></svg></button>
          <button onClick={playPause} aria-label="Spill/pause" style="width:72px;height:72px;flex-shrink:0;border-radius:36px;border:none;background:#f2f2ee;display:flex;align-items:center;justify-content:center;padding:0"><svg width="28" height="28" viewBox="0 0 24 24" fill="#0b0b0c"><path d={s?.playing ? PAUSE_D : PLAY_D} /></svg></button>
          <button onClick={() => void act(() => api.transport('next'))} aria-label="Neste" style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z" /></svg></button>
          <div style="flex:1" />
          <div style="display:flex;align-items:center;gap:6px;width:136px;flex-shrink:0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6" /></svg>
            <input type="range" min={0} max={100} value={s?.volume ?? 0} onInput={(e) => setVolume(+(e.currentTarget as HTMLInputElement).value)} onChange={(e) => setVolume(+(e.currentTarget as HTMLInputElement).value, true)} style="flex:1;min-width:0;accent-color:#f0c46a;height:28px" />
            <span style={`font-family:${MONO};font-size:12px;width:24px;text-align:right`}>{s?.volume ?? 0}</span>
          </div>
        </div>
      </div>
      <div style="grid-column:1 / -1;display:flex;flex-direction:column;gap:6px">
        <div style="height:22px;display:flex;align-items:center"><div style="position:relative;width:100%;height:4px;border-radius:2px;background:#2a2a2c"><div style={`width:${pct};height:100%;border-radius:2px;background:#f2f2ee`} /><div style={`position:absolute;top:-5px;left:${pct};width:14px;height:14px;margin-left:-7px;border-radius:50%;background:#f2f2ee`} /></div></div>
        <div style={`display:flex;justify-content:space-between;font-family:${MONO};font-size:11px;color:#8b8b86`}><span>{fmt(p)}</span><span>{dur > 0 ? fmt(dur) : 'DIREKTE'}</span></div>
      </div>
    </section>
  );
}

function Home() {
  return (
    <section style="flex:1;display:flex;flex-direction:column;gap:12px;padding:14px 18px 10px;min-height:0;overflow:hidden">
      <span style="font-size:20px;font-weight:600">Kilder</span>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(110px,1fr);gap:10px;flex:1;min-height:0">
        {SRC.map(([n, sub, d, tile, pick]) => (
          <button key={n} onClick={pick} style="min-height:110px;border-radius:14px;border:1px solid #242426;background:#141415;display:flex;flex-direction:column;align-items:flex-start;justify-content:space-between;gap:10px;padding:14px 14px 13px;box-sizing:border-box;text-align:left;min-width:0">
            <div style={`width:36px;height:36px;flex-shrink:0;border-radius:10px;background:${tile};display:flex;align-items:center;justify-content:center;color:#f2f2ee`}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg></div>
            <span style="display:flex;flex-direction:column;gap:3px;min-width:0;width:100%"><span style="font-size:14px;font-weight:600;color:#f2f2ee;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{n}</span><span style="font-size:11px;line-height:1.3;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</span></span>
          </button>
        ))}
      </div>
    </section>
  );
}

interface Card { t: string; s: string; art: string; live?: boolean; play: () => void }
function Library() {
  const [nd, setNd] = useState<NdAlbum[] | null>(null);
  useEffect(() => { if (lib.value === 1 && nd === null && ndConfigured()) ndAlbumList('newest', 12).then(setNd).catch(() => setNd([])); }, [lib.value]);
  const st = status.value;
  const TABS = ['YouTube Music', 'Navidrome', 'Radio'];
  let kicker = '', items: Card[] = [];
  if (lib.value === 0) { kicker = 'IKKE TILKOBLET · SETT OPP MUSIC ASSISTANT I APPEN'; }
  else if (lib.value === 1) {
    kicker = ndConfigured() ? 'NYLIG LAGT TIL' : 'IKKE TILKOBLET · LOGG INN PÅ NAVIDROME I APPEN';
    items = (nd ?? []).map((a) => ({ t: a.name, s: a.artist, art: artBg(a.name, ndCover(a.coverArt, 300)), play: () => { void ndAlbum(a.id).then((r) => { playNd(r.songs, 0); scr.value = 'now'; }); } }));
  } else {
    kicker = 'DINE FAVORITTER';
    items = favs.value.map((f, i) => ({ t: f.title, s: f.genre || 'Radio', art: artBg(f.title, f.image, i), live: st?.input === 'radio' && !!st.playing && (st.radio_now?.url === f.url || st.preset === f.n), play: () => { playFav(f); scr.value = 'now'; } }));
  }
  return (
    <section style="flex:1;display:flex;flex-direction:column;gap:14px;padding:18px 22px 0;min-height:0">
      <div style="display:flex;gap:8px;align-items:center">
        {TABS.map((n, i) => { const on = lib.value === i; return <button key={n} onClick={() => { lib.value = i; }} style={`height:38px;padding:0 16px;border-radius:19px;border:1px solid ${on ? '#f2f2ee' : '#2e2e30'};background:${on ? '#f2f2ee' : '#161617'};color:${on ? '#0b0b0c' : '#f2f2ee'};font-size:13px;font-weight:600;white-space:nowrap`}>{n}</button>; })}
        <div style="flex:1" />
        <div style="height:38px;width:200px;border-radius:19px;border:1px solid #2e2e30;background:#141415;display:flex;align-items:center;gap:8px;padding:0 14px;box-sizing:border-box;color:#8b8b86;font-size:13px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>Søk</div>
      </div>
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>{kicker}</span>
      <div style="display:flex;gap:16px;overflow-x:auto;scrollbar-width:none;padding-bottom:6px;touch-action:pan-x">
        {items.map((it, i) => (
          <button key={i} onClick={it.play} style="flex-shrink:0;width:148px;border:none;background:none;padding:0;text-align:left;display:flex;flex-direction:column;gap:8px">
            <div style={`position:relative;width:148px;height:148px;border-radius:12px;background:${it.art}`}>{it.live && <span style={`position:absolute;left:8px;top:8px;height:18px;padding:0 6px;border-radius:4px;background:#e05a4a;color:#fff;font-family:${MONO};font-size:9px;display:flex;align-items:center`}>DIREKTE</span>}</div>
            <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.t}</span><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.s}</span></span>
          </button>
        ))}
      </div>
    </section>
  );
}

interface RoomRow { base: string; name: string; model: string; st: Status | null; self: boolean }
function roomList(): RoomRow[] {
  const me = local.value;
  const self: RoomRow = { base: '', name: me?.name || 'Denne', model: 'Skjold ' + PRODUCT_SHORT[productOf(me)], st: me, self: true };
  const others = peers.value.map((p) => { const st = peerSt.value[p.base] ?? null; return { base: p.base, name: st?.name || p.navn, model: 'Skjold ' + PRODUCT_SHORT[productOf(st ?? { board: '', product: p.produkt })], st, self: false }; });
  return role() === 1 ? [self] : role() === 2 ? others : [self, ...others];
}

function Rooms() {
  const rows = roomList();
  return (
    <section style="flex:1;display:flex;flex-direction:column;gap:12px;padding:18px 22px;min-height:0">
      <div style="display:flex;align-items:center;gap:10px"><span style="font-size:22px;font-weight:600">Rom</span><div style="flex:1" />
        <button onClick={() => { groupAll(rows.map((r) => r.base || here())); scr.value = 'now'; }} style="height:36px;padding:0 14px;border-radius:18px;border:1px solid #2e2e30;background:#161617;font-size:12.5px">Spill i alle rom</button></div>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;overflow-y:auto;min-height:0">
        {rows.map((r) => {
          const on = r.base === ctl.value, pick = () => { control(r.base); scr.value = 'now'; };
          return (
            <div key={r.base} style={`display:grid;grid-template-columns:40px minmax(0,1fr) 120px;gap:12px;align-items:center;height:72px;padding:0 14px;border-radius:14px;border:1px solid ${on ? '#d9a441' : '#242426'};background:${on ? '#1c170d' : '#141415'};box-sizing:border-box`}>
              <button onClick={pick} style={`width:40px;height:40px;border-radius:10px;border:none;background:${r.st?.playing ? artOf(r.st, r.base) : '#1b1b1c'};padding:0`} />
              <button onClick={pick} style="border:none;background:none;padding:0;text-align:left;display:flex;flex-direction:column;gap:2px;min-width:0">
                <span style={`font-size:14px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap`}>{r.name}</span>
                <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.self ? 'Denne enheten' : npLine(r.st)}</span>
                <span style={`font-family:${MONO};font-size:9.5px;color:#6b6b67;white-space:nowrap`}>{r.model}</span>
              </button>
              <input type="range" min={0} max={100} value={(on ? status.value?.volume : r.st?.volume) ?? 0}
                onChange={(e) => { const v = +(e.currentTarget as HTMLInputElement).value; if (on) setVolume(v, true); else void postAt(r.base, '/api/volume', { volume: v }); }}
                onInput={(e) => { if (on) setVolume(+(e.currentTarget as HTMLInputElement).value); }}
                style="width:120px;accent-color:#f0c46a;height:28px" />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Setup() {
  const S = settings.value;
  const seg = (list: string[], cur: number, set: (i: number) => void, label?: (s: string) => string) => (
    <div style="display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426">
      {list.map((o, i) => <button key={o} onClick={() => set(i)} style={`height:34px;padding:0 12px;border-radius:9px;border:none;background:${i === cur ? '#2a2a2c' : 'transparent'};color:${i === cur ? '#f2f2ee' : '#8b8b86'};font-size:12px;font-weight:600;white-space:nowrap`}>{label ? label(o) : o}</button>)}
    </div>
  );
  const rows: [string, string, preact.ComponentChildren][] = [
    ['Rolle', 'Spiller med egen lydutgang, fjernkontroll for huset, eller begge', seg(TOUCH_ROLES, S.tRole ?? 0, (i) => { setSetting('tRole', i); if (i === 1) control(''); }, (o) => o.replace('Spiller og fjernkontroll', 'Begge').replace('Bare ', ''))],
    ['Lydutgang', 'PCM5122 HIFI HAT', seg(TOUCH_OUT, S.tOut ?? 2, (i) => setSetting('tOut', i))],
    ['Dimme skjermen', 'Etter siste trykk', seg(['30 s', '1 min', '5 min'], Math.max(0, (S.tStandby ?? 1) - 1), (i) => setSetting('tStandby', i + 1))],
    ['I standby', 'Når skjermen hviler', seg(TOUCH_IDLE, S.tIdle ?? 0, (i) => setSetting('tIdle', i))],
    ['Nattmodus', 'Svakt, rødlig lys 23–07', seg(['Av', 'På'], S.tNight ? 1 : 0, (i) => setSetting('tNight', i === 1))],
    ['Vis standby nå', 'Eller vent ' + (TOUCH_STANDBY_S[S.tStandby ?? 1] ?? 30) + ' s uten å trykke', (
      <div style="display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426">
        <button onClick={goIdle} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap">Standby</button>
        <button onClick={runBoot} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:12px;font-weight:600;white-space:nowrap">Start på nytt</button>
      </div>)]
  ];
  return (
    <section style="flex:1;display:flex;flex-direction:column;gap:12px;padding:18px 22px;min-height:0">
      <span style="font-size:22px;font-weight:600">Innstillinger</span>
      <div style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415;overflow-y:auto;min-height:0">
        {rows.map(([n, hint, ctrl], i) => (
          <div key={n} style={`display:flex;align-items:center;gap:14px;min-height:58px;padding:0 16px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'};flex-shrink:0`}>
            <span style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0"><span style="font-size:14px">{n}</span><span style="font-size:11.5px;color:#8b8b86">{hint}</span></span>
            {ctrl}
          </div>
        ))}
      </div>
    </section>
  );
}

function Standby({ clock, dateTxt }: { clock: string; dateTxt: string }) {
  const s = status.value, m = settings.value.tIdle ?? 0, h = new Date(now.value).getHours();
  const night = !!settings.value.tNight && (h >= 23 || h < 7);
  const bg = artOf(s), playing = !!s?.playing;
  return (
    <button onPointerDown={(e) => { e.preventDefault(); e.stopPropagation(); wake(); }} aria-label="Vekk skjermen" style={`position:absolute;inset:0;border:none;background:#000;padding:0;overflow:hidden;opacity:${idleOp.value};transition:opacity .8s ease;z-index:20`}>
      {m === 1 && !night && <>
        <div style={`position:absolute;inset:-60px;background:${bg};filter:blur(60px);opacity:.55`} />
        <div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.85),rgba(0,0,0,.35))" />
        <div style="position:absolute;left:56px;top:50%;transform:translateY(-50%);display:flex;align-items:center;gap:34px">
          <div style={`width:260px;height:260px;border-radius:16px;background:${bg};box-shadow:0 24px 60px rgba(0,0,0,.6);flex-shrink:0`} />
          <div style="display:flex;flex-direction:column;gap:8px;text-align:left;min-width:0;max-width:390px">
            <span style={`font-family:${MONO};font-size:11px;letter-spacing:.16em;color:#f0c46a`}>{ctl.value ? 'SPILLER I ' + (s?.name ?? '').toUpperCase() : 'SPILLER NÅ · ' + ['RCA', '3,5 MM', 'RCA + 3,5 MM'][settings.value.tOut ?? 2]}</span>
            <span style="font-size:34px;font-weight:600;color:#f2f2ee;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.title || s?.station || 'Ingenting spilles'}</span>
            <span style="font-size:18px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.artist ?? ''}</span>
            <span style="margin-top:18px;font-size:44px;font-weight:300;color:#f2f2ee">{clock}</span>
          </div>
        </div>
      </>}
      {(m === 0 || (m === 1 && night)) && (
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px">
          <span style={`font-size:132px;font-weight:300;letter-spacing:-.03em;color:${night ? '#7a2a20' : '#f2f2ee'};line-height:1`}>{clock}</span>
          <span style="font-size:17px;color:#8b8b86;white-space:nowrap">{dateTxt}</span>
          {playing && <span style="margin-top:26px;display:flex;align-items:center;gap:10px;font-size:13px;color:#8b8b86"><div style={`width:24px;height:24px;border-radius:5px;background:${bg}`} />{(s?.title || s?.station) + (s?.artist ? ' · ' + s.artist : '')}</span>}
        </div>
      )}
      {m !== 2 && <span style={`position:absolute;left:0;right:0;bottom:16px;text-align:center;font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#3a3a37`}>TRYKK FOR Å VEKKE</span>}
    </button>
  );
}

function Boot() {
  const b = boot.value, bs = b.step, BH = [26, 40, 56, 40, 26];
  const names = peers.value.map((p) => p.navn).slice(0, 3).join(', ');
  const msgs = ['', '', '', '', '', '', 'Starter lydmotoren …', 'Kobler til Skjold-nettverket …', names ? 'Finner rom: ' + names + ' …' : 'Finner rom …', 'Klar'];
  const txt = bs >= 6 ? 1 : 0;
  return (
    <div style={`position:absolute;inset:0;background:#000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;opacity:${b.op};transition:opacity .6s ease;z-index:30`}>
      <div style="display:flex;align-items:flex-end;gap:7px;height:64px">
        {BH.map((h, i) => <div key={i} style={`width:10px;height:${bs > i ? h : 4}px;border-radius:5px;background:#f0c46a;opacity:${bs > i ? 1 : 0.15};transition:height .5s cubic-bezier(.2,.8,.2,1),opacity .4s ease`} />)}
      </div>
      <div style={`display:flex;flex-direction:column;align-items:center;gap:6px;opacity:${txt};transform:translateY(${txt ? 0 : 10}px);transition:opacity .6s ease,transform .6s ease`}>
        <span style="font-size:34px;font-weight:600;letter-spacing:.06em;color:#f2f2ee">SKJOLD</span>
        <span style={`font-family:${MONO};font-size:12px;letter-spacing:.5em;color:#8b8b86;padding-left:.5em`}>TOUCH</span>
      </div>
      <div style={`width:180px;height:3px;border-radius:2px;background:#1c1c1e;overflow:hidden;opacity:${txt}`}><div style={`width:${Math.max(0, (bs - 5) / 4 * 100).toFixed(0)}%;height:100%;background:#f0c46a;transition:width .5s linear`} /></div>
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.1em;color:#6b6b67;opacity:${txt}`}>{msgs[bs] || ''}</span>
    </div>
  );
}

function App() {
  const s = status.value, d = new Date(now.value);
  const clock = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const dateTxt = d.toLocaleDateString('nb-NO', { weekday: 'long', day: 'numeric', month: 'long' }).replace(/^./, (c) => c.toUpperCase());
  const r = role(), cur = scr.value === 'rooms' && r === 1 ? 'now' : scr.value;
  // Bare fjernkontroll: styr første andre rom så snart det finnes
  useEffect(() => { if (r === 2 && !ctl.value && peers.value[0]) control(peers.value[0].base); if (r === 1 && ctl.value) control(''); }, [r, peers.value.length]);
  const NAV: [Scr, string][] = ([['now', 'Spiller'], ['home', 'Hjem'], ['lib', 'Bibliotek'], ['rooms', 'Rom'], ['set', 'Oppsett']] as [Scr, string][]).filter(([k]) => !(r === 1 && k === 'rooms'));
  const rows = roomList();
  const curRoom = rows.find((x) => x.base === ctl.value);
  const roomLabel = curRoom?.name ?? s?.name ?? 'Skjold Touch', roomSub = (curRoom?.model ?? 'Skjold Touch').replace('Skjold ', '');
  return (
    <div style="position:relative;width:800px;height:480px;background:#0b0b0c;overflow:hidden;display:grid;grid-template-columns:76px minmax(0,1fr)">
      <nav style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 0;background:#101011;border-right:1px solid #1f1f21">
        <div style="display:flex;gap:2.5px;align-items:flex-end;height:26px;margin-bottom:10px">{[14, 20, 26, 20, 14].map((h, i) => <div key={i} style={`width:4px;height:${h}px;border-radius:2px;background:#f0c46a`} />)}</div>
        {NAV.map(([k, label]) => { const on = cur === k; return (
          <button key={k} onClick={() => { scr.value = k; roomsOpen.value = false; }} aria-label={label} style={`width:60px;height:60px;border-radius:16px;border:none;background:${on ? 'rgba(240,196,106,.14)' : 'transparent'};color:${on ? '#f0c46a' : '#8b8b86'};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:0`}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={IC[k]} /></svg>
            <span style={`font-size:9.5px;font-weight:${on ? 600 : 400}`}>{label}</span>
          </button>); })}
        <div style="flex:1" />
        <button onClick={goIdle} aria-label="Standby" style="width:44px;height:44px;border-radius:22px;border:1px solid #2e2e30;background:transparent;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0" /></svg></button>
      </nav>
      <main style="position:relative;display:flex;flex-direction:column;min-width:0">
        <header style="height:52px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 18px;border-bottom:1px solid #1a1a1c">
          <button onClick={() => { roomsOpen.value = !roomsOpen.value; }} style="height:34px;display:flex;align-items:center;gap:8px;padding:0 12px 0 10px;border-radius:17px;border:1px solid #2e2e30;background:#161617;min-width:0">
            <div style={`width:8px;height:8px;border-radius:50%;background:${online.value ? '#6fcf7f' : '#3a3a37'};flex-shrink:0`} />
            <span style="font-size:13px;font-weight:600;white-space:nowrap">{roomLabel}</span>
            <span style={`font-family:${MONO};font-size:10px;color:#8b8b86;white-space:nowrap`}>{roomSub}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2.4" stroke-linecap="round"><path d="M6 9l6 6 6-6" /></svg>
          </button>
          {!!ctl.value && <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#f0c46a`}>FJERNKONTROLL</span>}
          <div style="flex:1" />
          <span style={`font-family:${MONO};font-size:14px;color:#c9c9c4`}>{clock}</span>
        </header>
        {cur === 'now' && <NowPlaying />}
        {cur === 'home' && <Home />}
        {cur === 'lib' && <Library />}
        {cur === 'rooms' && <Rooms />}
        {cur === 'set' && <Setup />}
        {cur !== 'now' && (
          <button onClick={() => { scr.value = 'now'; }} style="flex-shrink:0;height:58px;margin:0 14px 10px;border-radius:16px;border:1px solid #27272a;background:#151516;display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:12px;align-items:center;padding:0 10px;text-align:left">
            <div style={`width:42px;height:42px;border-radius:9px;background:${artOf(s)}`} />
            <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.title || s?.station || 'Ingenting spilles'}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{(s?.artist ? s.artist + ' · ' : '') + roomLabel}</span></span>
            <span onClick={(e) => { e.stopPropagation(); playPause(); }} style="width:42px;height:42px;border-radius:21px;background:#f2f2ee;display:flex;align-items:center;justify-content:center"><svg width="18" height="18" viewBox="0 0 24 24" fill="#0b0b0c"><path d={s?.playing ? PAUSE_D : PLAY_D} /></svg></span>
          </button>
        )}
        {roomsOpen.value && <>
          <div onClick={() => { roomsOpen.value = false; }} style="position:absolute;inset:52px 0 0 0;background:rgba(0,0,0,.55)" />
          <div style="position:absolute;top:58px;left:18px;width:300px;border-radius:16px;border:1px solid #2e2e30;background:#18181a;box-shadow:0 20px 50px rgba(0,0,0,.6);padding:8px;display:flex;flex-direction:column;gap:4px">
            <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86;padding:6px 8px`}>STYR ROM</span>
            {rows.map((x) => { const on = x.base === ctl.value; return (
              <button key={x.base} onClick={() => control(x.base)} style={`height:48px;border-radius:10px;border:none;background:${on ? '#2a2316' : 'transparent'};display:flex;align-items:center;gap:10px;padding:0 10px;text-align:left;flex-shrink:0`}>
                <div style={`width:8px;height:8px;border-radius:50%;background:${on ? '#6fcf7f' : '#3a3a37'}`} />
                <span style={`flex:1;font-size:14px;color:${on ? '#f0c46a' : '#f2f2ee'}`}>{x.name}</span><span style={`font-family:${MONO};font-size:10px;color:#8b8b86`}>{x.self ? 'DENNE' : x.model.replace('Skjold ', '').toUpperCase()}</span>
              </button>); })}
          </div>
        </>}
      </main>
      {idle.value && <Standby clock={clock} dateTxt={dateTxt} />}
      {boot.value.on && <Boot />}
    </div>
  );
}

// Til skjermbilder og test: window.__touch.screen('home') osv.
(window as unknown as { __touch: unknown }).__touch = {
  screen: (k: Scr) => { scr.value = k; }, lib: (i: number) => { lib.value = i; }, standby: goIdle, wake, boot: runBoot,
  skipBoot: () => { bootT.forEach(clearTimeout); boot.value = { on: false, step: 9, op: 0 }; }, rooms: (o: boolean) => { roomsOpen.value = o; }
};
render(<><App /><DoorbellOverlay /><div style="position:fixed;right:12px;bottom:12px;z-index:50"><TalkButton compact /></div></>, document.getElementById('touch')!);
