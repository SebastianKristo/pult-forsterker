// Skjold Touch – skjermgrensesnittet på 7″ berøringsskjerm (800 × 480, kiosk).
// Bygget piksel-identisk etter design-handoff «Skjold Touch UI.dc.html»: mål, farger og tekster er hentet derfra.
// Data er ekte: status/hendelser fra daemonen, rom fra /api/rom (mDNS), innstillinger via /api/settings.
import { render } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { effect, signal } from '@preact/signals';
import './touch.css';
import { api, coverUrl, getBase, INPUT_LABEL, PRODUCT_SHORT, productOf, setBase, type InputId, type Status } from '../lib/api';
import { loadSettings, playPause, reconnect, setSetting, setVolume, settings, startPolling, status, act, online } from '../lib/store';
import { art, TOUCH_BELL, TOUCH_IDLE, TOUCH_OUT, TOUCH_ROLES, TOUCH_STANDBY_S, TOUCH_START, TOUCH_WAKE, TOUCH_WAKE_ID } from '../lib/settings';
import { favs, loadFavs, playFav, playStation } from '../lib/radio';
import { ndAlbum, ndAlbumList, ndConfigured, ndCover, ndSearch, type NdAlbum } from '../lib/navidrome';
import { li, lq, lsvc, playNd } from '../lib/library';
import { ytmHomeCached, ytmSearch, ytmTracks, ytmWhy } from '../lib/ytm';
import { groupAll } from '../lib/groups';
import { canSeek, seekTo } from '../screens/player';
import { Keyboard, MONO, Sheet, Slider, useLongPress } from './ui';

type Scr = 'now' | 'home' | 'smart' | 'alarm' | 'lib' | 'rooms' | 'set';
const START: (Scr | 'standby')[] = ['now', 'home', 'smart', 'alarm', 'lib', 'rooms', 'set', 'standby'];
interface Peer { id: string; navn: string; produkt: string; base: string }
interface Alarm { time: string; days: number[]; on: boolean; name: string; smart: boolean; preset: number; url: string; volume: number; fade: number }
interface Tile { id: string; name: string; domain: string; on: boolean; kind: 'toggle' | 'info' | 'climate' | 'camera'; text: string; tag: string; target?: number | null; pct?: number }
interface Smart { ok: boolean; hub: string; tiles: Tile[]; scenes: { id: string; name: string }[]; error?: string; lock?: boolean }
// Det denne enheten selv melder (alarm, ringeklokke, stemme, kommandoer) – uavhengig av hvilket rom som fjernstyres
interface Dev {
  alarm?: { ringing: boolean; snoozed: boolean; name: string; time: string };
  doorbell?: { t: number; camera: boolean; seconds: number } | null;
  night?: { on: boolean };
  setup_net?: { active: boolean; ssid: string; password: string; url: string; joining: string; error: string } | null;
  touch?: { cmd: { cmd: string; arg: string; seq: number }; voice: { state: string; text: string; reply: string } };
}

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
const alarms = signal<Alarm[]>([]);
const smart = signal<Smart | null>(null);
const sceneOn = signal('');
const door = signal(0);        // tidsstempelet til ringingen som vises i fullskjerm (0 = lukket)
const doorToast = signal(0);
const unlocked = signal(false);
const morning = signal('');
const queueOpen = signal(false), talkOpen = signal(false), searchOpen = signal(false), dimId = signal('');
const dev = (): Dev => (local.value ?? {}) as Dev;

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
// Egen enhet direkte (hendelser), så alarm, ringeklokke og stemme kommer med en gang – også mens et annet rom fjernstyres
if (typeof EventSource !== 'undefined') {
  try { const ev = new EventSource(here() + '/api/events'); ev.onmessage = (e) => { try { local.value = JSON.parse(e.data as string) as Status; } catch { /* ignore */ } }; } catch { /* pollRooms holder den oppdatert */ }
}

// ---------- vekkeklokke, smarthus og nattmodus ----------
async function loadAlarms(): Promise<void> {
  try {
    const r = await getAt<{ plugins: { id: string; enabled: boolean; cfg: { alarms?: Partial<Alarm>[] } }[] }>('', '/api/plugins');
    const p = r.plugins.find((x) => x.id === 'alarm');
    alarms.value = (p?.cfg.alarms ?? []).map((a) => ({ time: a.time ?? '07:00', days: a.days ?? [], on: !!p?.enabled && a.on !== false, name: a.name ?? '', smart: a.smart ?? (a.fade ?? 0) > 0, preset: a.preset ?? 0, url: a.url ?? '', volume: a.volume ?? 30, fade: a.fade ?? 0 }));
  } catch { /* eldre daemon */ }
}
let saveAT = 0;
function saveAlarms(next: Alarm[]): void {
  alarms.value = next; clearTimeout(saveAT);
  saveAT = window.setTimeout(() => { void postAt('', '/api/plugins/alarm', { enabled: true, alarms: next }).catch(() => undefined); }, 400);
}
function nextAlarm(): { time: string; name: string } | null {
  const d = new Date(now.value), cur = d.getHours() * 60 + d.getMinutes(), wd = (d.getDay() + 6) % 7;
  let best: { time: string; name: string; inMin: number } | null = null;
  for (const a of alarms.value) {
    if (!a.on) continue;
    const [h, m] = a.time.split(':'), at = (+(h ?? 0)) * 60 + (+(m ?? 0)), days = a.days.length ? a.days : [0, 1, 2, 3, 4, 5, 6];
    for (let k = 0; k < 8; k++) if (days.includes((wd + k) % 7) && (k > 0 || at > cur)) { const inMin = k * 1440 + at - cur; if (!best || inMin < best.inMin) best = { time: a.time, name: a.name || 'Alarm', inMin }; break; }
  }
  return best;
}
async function loadSmart(): Promise<void> { try { smart.value = await getAt<Smart>('', '/api/touch/smart'); } catch { /* behold forrige */ } }
async function press(id: string, action: string, value?: number): Promise<void> {
  const sm = smart.value;
  if (sm && action === 'toggle') smart.value = { ...sm, tiles: sm.tiles.map((t) => (t.id === id ? { ...t, on: !t.on } : t)) };   // svar med en gang
  if (sm && action === 'brightness' && value != null) smart.value = { ...sm, tiles: sm.tiles.map((t) => (t.id === id ? { ...t, on: value > 0, pct: value, text: value > 0 ? 'På · ' + value + ' %' : 'Av' } : t)) };
  try { const r = await fetch(here() + '/api/touch/smart', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, action, value }) }); if (r.ok) smart.value = (await r.json()) as Smart; else void loadSmart(); } catch { void loadSmart(); }
}
void loadAlarms(); void loadSmart();
setInterval(() => { if (scr.value === 'smart' && !idle.value && !dimId.value) void loadSmart(); }, 4000);
setInterval(() => void loadAlarms(), 60000);

function nightNow(): boolean {
  const S = settings.value, h = new Date(now.value).getHours(), m = S.tNightMode || (S.tNight ? 1 : 0), a = S.tNStart ?? 22, b = S.tNEnd ?? 7;
  return m === 3 || (m === 1 && (a > b ? h >= a || h < b : h >= a && h < b)) || (m === 2 && !!dev().night?.on);
}
// Bakgrunnslys: fullt når skjermen er i bruk, dempet i standby og om natten (skjermer uten styrbart lys overser dette)
let blLast = -1;
function backlight(): void {
  const n = nightNow(), full = Math.max(20, Math.min(100, settings.value.tBright ?? 100));
  const lvl = idle.value ? ((settings.value.tIdle ?? 0) === 2 ? 0 : n ? 3 : Math.min(30, full)) : n ? Math.min(25, full) : full;
  if (lvl !== blLast) { blLast = lvl; void postAt('', '/api/touch/backlight', { level: lvl }).catch(() => undefined); }
}

// ---------- ringeklokke ----------
let doorT = 0;
function ringNow(t: number, force = false): void {
  const mode = settings.value.tBell ?? 0;
  if (mode === 2 && !force) return;
  wake(); clearTimeout(doorT);
  if (mode === 1 && !force) { doorToast.value = t; doorT = window.setTimeout(() => { doorToast.value = 0; }, 5000); return; }
  doorToast.value = 0; unlocked.value = false; door.value = t || Date.now() / 1000;
  doorT = window.setTimeout(() => { door.value = 0; }, 30000);
}

function control(base: string): void {
  roomsOpen.value = false;
  if (base === ctl.value) return;
  ctl.value = base; setBase(base || null); reconnect();
}

// ---------- standby og oppstart ----------
function goIdle(): void { idle.value = true; idleOp.value = 0; setTimeout(() => { idleOp.value = 1; }, 30); backlight(); }
function wake(): void { lastAct = Date.now(); if (idle.value) { idle.value = false; backlight(); } }
addEventListener('pointerdown', () => { lastAct = Date.now(); }, true);
addEventListener('contextmenu', (e) => e.preventDefault());
setInterval(() => {
  now.value = Date.now();
  const ms = (TOUCH_STANDBY_S[settings.value.tStandby] ?? 30) * 1000;
  if (!idle.value && !boot.value.on && !dev().alarm?.ringing && !door.value && !dev().setup_net?.active && ms > 0 && Date.now() - lastAct > ms) goIdle();
  if (!boot.value.on) backlight();
}, 1000);

// Det enheten melder: kommandoer fra HA/Homey/appen, alarm som ringer, ringeklokke og stemme
let seenCmd = -1, seenRing = -1, wasRinging = false, wasVoice = false;
effect(() => {
  const d = dev(), c = d.touch?.cmd;
  if (c) {
    if (seenCmd < 0) seenCmd = c.seq;
    else if (c.seq !== seenCmd) {
      seenCmd = c.seq;
      if (c.cmd === 'standby') goIdle(); else if (c.cmd === 'wake') wake(); else if (c.cmd === 'boot') runBoot();
      else if (c.cmd === 'page') { wake(); scr.value = c.arg as Scr; }
    }
  }
  const ringing = !!d.alarm?.ringing;
  if (ringing && !wasRinging) {
    wake(); clearTimeout(doorT); door.value = 0; morning.value = '';
    void getAt<{ text: string }>('', '/api/touch/morning').then((r) => { morning.value = r.text; }).catch(() => undefined);
  }
  wasRinging = ringing;
  if (local.value) {
    const t = d.doorbell?.t ?? 0;
    if (seenRing < 0) seenRing = t;          // en ringing fra før skjermen startet vises ikke på nytt
    else if (t && t !== seenRing) { seenRing = t; ringNow(t); }
  }
  const talking = !!d.touch?.voice && d.touch.voice.state !== 'idle';
  if (talking && !wasVoice) wake();
  wasVoice = talking;
});

let bootT: number[] = [], started = false;
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
    bootT.push(window.setTimeout(() => set({ op: 0 }), 400), window.setTimeout(() => {
      set({ on: false }); lastAct = Date.now();
      if (!started) { started = true; const st = START[settings.value.tStart ?? 0] ?? 'now'; if (st === 'standby') goIdle(); else scr.value = st; }   // startsiden fra Innstillinger
    }, 1000));
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
const IC: Record<Scr, string> = { smart: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z', alarm: 'M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 9v4l2.5 2.5M5 3 2 6M19 3l3 3', now: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', home: 'M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10', lib: 'M4 4h4v16H4zM10 4h4v16h-4zM16 5l4 1-3 14-4-1z', rooms: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', set: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M16 4v4M10 10v4M18 16v4' };
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
// ---------- spiller ----------
const BARS = [14, 20, 26, 20, 14];
const ROUND = 'width:48px;height:48px;flex-shrink:0;border-radius:24px;border:1px solid #2e2e30;background:rgba(22,22,23,.7);color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0';
function NowPlaying() {
  const s = status.value, remote = !!ctl.value, out = settings.value.tOut ?? 2;
  const [pos, setPos] = useState(s?.position ?? 0);
  const [vol, setVol] = useState<number | null>(null);     // mens fingeren drar i volumet
  useEffect(() => { setPos(s?.position ?? 0); }, [s?.position, s?.title]);
  useEffect(() => { const t = setInterval(() => { if (status.value?.playing) setPos((p) => p + 1); }, 1000); return () => clearInterval(t); }, []);
  const dur = s?.duration ?? 0, p = dur > 0 ? Math.min(pos, dur) : 0;
  const room = remote ? peers.value.find((x) => x.base === ctl.value) : null;
  const kicker = remote ? 'SPILLER I ' + (room?.navn ?? s?.name ?? '').toUpperCase() : 'SPILLER NÅ · ' + ['RCA', '3,5 MM', 'RCA + 3,5 MM'][out];
  const has = !!(s?.title || s?.station), off = s?.power === false;
  const title = s?.title || s?.station || (off ? 'Av' : 'Ingenting spilles');
  const v = Math.round(vol ?? s?.volume ?? 0), muted = !!s?.mute;
  const libQ = lq.value.length > 1 && dur > 0 && s?.input === 'radio';     // kø fra biblioteket (Navidrome / YouTube Music)
  const list = libQ || favs.value.length > 0;
  const bg = artOf(s);
  return (
    <section class="inn" style="position:relative;flex:1;min-height:0;overflow:hidden">
      {has && <>
        <div style={`position:absolute;inset:-50px;background:${bg};filter:blur(48px) saturate(1.25);opacity:.34`} />
        <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,12,.5),rgba(11,11,12,.94))" />
      </>}
      <div style="position:relative;height:100%;box-sizing:border-box;display:grid;grid-template-columns:244px minmax(0,1fr);grid-template-rows:244px auto auto;column-gap:24px;row-gap:4px;padding:14px 22px 8px;align-content:center">
        <div style={`position:relative;width:244px;height:244px;border-radius:14px;background:${has ? bg : '#141415'};box-shadow:0 18px 44px rgba(0,0,0,.55);overflow:hidden;display:flex;align-items:center;justify-content:center`}>
          {!has && <div style="display:flex;gap:6px;align-items:flex-end;height:60px;opacity:.5">{BARS.map((h, i) => <div key={i} style={`width:9px;height:${h * 2.2}px;border-radius:5px;background:#3a3a37`} />)}</div>}
          {has && <span style={`position:absolute;left:10px;bottom:10px;height:22px;padding:0 8px;border-radius:6px;background:rgba(0,0,0,.55);font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#f2f2ee;display:flex;align-items:center`}>{srcName(s)}</span>}
        </div>
        <div style="display:flex;flex-direction:column;min-width:0;padding-top:2px">
          <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#f0c46a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{kicker}</span>
          <span style="margin-top:10px;font-size:28px;font-weight:600;line-height:1.12;letter-spacing:-.01em;text-wrap:pretty;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">{title}</span>
          <span style="margin-top:6px;font-size:17px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{has ? s?.artist ?? '' : off ? 'Trykk på spill for å slå på' : 'Velg noe å høre på'}</span>
          <span style="margin-top:2px;font-size:13px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{has ? s?.album ?? '' : ''}</span>
          <div style="flex:1" />
          <div style="display:flex;align-items:center;gap:6px">
            <button onClick={() => void act(() => api.transport('previous'))} aria-label="Forrige" style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M19 18.5v-13a.8.8 0 0 0-1.25-.66L9 10.9V6a1 1 0 0 0-2 0v12a1 1 0 0 0 2 0v-4.9l8.75 6.06A.8.8 0 0 0 19 18.5z" /></svg></button>
            <button onClick={playPause} aria-label={s?.playing ? 'Pause' : 'Spill'} style="width:72px;height:72px;flex-shrink:0;border-radius:36px;border:none;background:#f2f2ee;display:flex;align-items:center;justify-content:center;padding:0;box-shadow:0 8px 24px rgba(0,0,0,.4)"><svg width="28" height="28" viewBox="0 0 24 24" fill="#0b0b0c"><path d={s?.playing ? PAUSE_D : PLAY_D} /></svg></button>
            <button onClick={() => void act(() => api.transport('next'))} aria-label="Neste" style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z" /></svg></button>
            <div style="flex:1" />
            {!has && <button onClick={() => { lib.value = 2; scr.value = 'lib'; }} style="height:48px;padding:0 18px;border-radius:24px;border:1px solid #2e2e30;background:rgba(22,22,23,.7);font-size:13px;font-weight:600">Radio</button>}
            {list && <button onClick={() => { queueOpen.value = true; }} aria-label={libQ ? 'Vis køen' : 'Vis kanalene'} style={ROUND}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 6h12M4 12h12M4 18h8M19 15v6M16 18h6" /></svg></button>}
            {role() !== 1 && peers.value.length > 0 && <button onClick={() => { scr.value = 'rooms'; }} aria-label="Velg rom" style={ROUND}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8h10v12H5zM9 8V4h10v12h-4M10 15.5a.1.1 0 1 0 0 .01" /></svg></button>}
          </div>
        </div>
        <div style={`grid-column:1 / -1;display:flex;align-items:center;gap:4px;font-family:${MONO};font-size:11px;color:#8b8b86;height:44px`}>
          {dur > 0 ? <>
            <span style="width:40px">{fmt(p)}</span>
            <Slider label="Spol" thin value={p} max={dur} color="#f2f2ee" disabled={!canSeek(s)} onInput={(n) => setPos(n)} onCommit={(n) => { setPos(n); void seekTo(Math.round(n)); }} />
            <span style="width:40px;text-align:right">{fmt(dur)}</span>
          </> : <>
            <span style="width:40px" />
            <div style="flex:1;height:4px;border-radius:2px;background:#2a2a2c;margin:0 11px" />
            <span style={`display:flex;align-items:center;gap:6px;color:${s?.playing ? '#f2f2ee' : '#8b8b86'};letter-spacing:.1em`}>{has && <span class={s?.playing ? 'puls' : ''} style={`width:7px;height:7px;border-radius:50%;background:${s?.playing ? '#e05a4a' : '#3a3a37'}`} />}{has ? 'DIREKTE' : ''}</span>
          </>}
        </div>
        <div style="grid-column:1 / -1;display:flex;align-items:center;gap:2px;height:44px">
          <button onClick={() => void act(() => api.mute(!muted), { mute: !muted })} aria-label={muted ? 'Slå på lyden' : 'Demp'} style={`width:44px;height:44px;border:none;background:none;color:${muted ? '#e05a4a' : '#c9c9c4'};display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;margin-left:-6px`}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={muted ? 'M4 9h3l5-4v14l-5-4H4zM16 9.5l5 5M21 9.5l-5 5' : v > 50 ? 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11' : 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6'} /></svg></button>
          <Slider label="Volum" value={v} color={muted ? '#6b6b67' : '#f0c46a'} onInput={(n) => { setVol(n); setVolume(Math.round(n)); }} onCommit={(n) => { setVol(null); setVolume(Math.round(n), true); }} />
          <span style={`font-family:${MONO};font-size:13px;width:32px;text-align:right;color:${muted ? '#6b6b67' : '#f2f2ee'}`}>{v}</span>
        </div>
      </div>
    </section>
  );
}

/** Kø (bibliotek) eller kanaler (radio) – glir opp over spilleren. */
function QueueSheet() {
  const s = status.value, dur = s?.duration ?? 0, libQ = lq.value.length > 1 && dur > 0 && s?.input === 'radio';
  const close = () => { queueOpen.value = false; };
  const row = 'height:52px;flex-shrink:0;border:none;border-radius:10px;display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;align-items:center;padding:0 10px;text-align:left';
  return (
    <Sheet title={libQ ? 'Spilles nå og etterpå' : 'Dine kanaler'} kicker={libQ ? 'KØ · ' + lq.value.length + ' LÅTER' : 'RADIO'} onClose={close} height={350}>
      <div class="rull" style="display:flex;flex-direction:column;gap:2px;overflow-y:auto;padding:0 8px 10px;touch-action:pan-y">
        {libQ ? lq.value.map((t, i) => { const on = i === li.value; return (
          <button key={t.id + i} onClick={() => { playNd(lq.value, i, lsvc.value ?? 'nd'); close(); }} style={row + `;background:${on ? '#2a2316' : 'transparent'}`}>
            <div style={`width:40px;height:40px;border-radius:8px;background:${artBg(t.title, ndCover(t.coverArt, 120))}`} />
            <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style={`font-size:14px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{t.title}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.artist}</span></span>
            <span style={`font-family:${MONO};font-size:11px;color:#8b8b86`}>{on ? 'NÅ' : t.duration ? fmt(t.duration) : ''}</span>
          </button>); })
          : favs.value.map((f, i) => { const on = s?.input === 'radio' && (s.radio_now?.url === f.url || s.preset === f.n); return (
            <button key={f.n} onClick={() => { playFav(f); close(); }} style={row + `;background:${on ? '#2a2316' : 'transparent'}`}>
              <div style={`width:40px;height:40px;border-radius:8px;background:${artBg(f.title, f.image || f.logo, i)}`} />
              <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style={`font-size:14px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{f.title}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{f.genre || 'Radio'}</span></span>
              <span style={`font-family:${MONO};font-size:11px;color:#f0c46a`}>{on && s?.playing ? 'SPILLER' : ''}</span>
            </button>); })}
      </div>
    </Sheet>
  );
}

function Home() {
  const st = status.value, h = new Date(now.value).getHours();
  const hils = h < 5 ? 'God natt' : h < 10 ? 'God morgen' : h < 18 ? 'God dag' : 'God kveld';
  const fv = favs.value.slice(0, 6);
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:10px;padding:14px 18px 10px;min-height:0;overflow:hidden">
      <span style="font-size:20px;font-weight:600">{hils}</span>
      {fv.length > 0 && <div style="display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;touch-action:pan-x;flex-shrink:0;margin:0 -18px;padding:0 18px">
        {fv.map((f, i) => { const on = st?.input === 'radio' && !!st.playing && (st.radio_now?.url === f.url || st.preset === f.n); return (
          <button key={f.n} onClick={() => { playFav(f); }} style={`flex-shrink:0;height:52px;max-width:190px;border-radius:26px;border:1px solid ${on ? '#d9a441' : '#242426'};background:${on ? '#1c170d' : '#141415'};display:flex;align-items:center;gap:10px;padding:0 16px 0 7px`}>
            <div style={`width:38px;height:38px;border-radius:19px;background:${artBg(f.title, f.image || f.logo, i)};flex-shrink:0`} />
            <span style={`font-size:13.5px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{f.title}</span>
          </button>); })}
      </div>}
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>KILDER</span>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:minmax(0,1fr);gap:10px;flex:1;min-height:0">
        {SRC.map(([n, sub, d, tile, pick]) => (
          <button key={n} onClick={pick} style="border-radius:14px;border:1px solid #242426;background:#141415;display:flex;flex-direction:column;align-items:flex-start;justify-content:space-between;gap:6px;padding:12px 13px 11px;box-sizing:border-box;text-align:left;min-width:0;min-height:0">
            <div style={`width:34px;height:34px;flex-shrink:0;border-radius:10px;background:${tile};display:flex;align-items:center;justify-content:center;color:#f2f2ee`}><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg></div>
            <span style="display:flex;flex-direction:column;gap:2px;min-width:0;width:100%"><span style="font-size:14px;font-weight:600;color:#f2f2ee;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{n}</span><span style="font-size:11px;line-height:1.3;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</span></span>
          </button>
        ))}
      </div>
    </section>
  );
}

interface Card { t: string; s: string; art: string; live?: boolean; play: () => void }
function Library() {
  const [nd, setNd] = useState<NdAlbum[] | null>(null);
  const [yt, setYt] = useState<NdAlbum[] | null>(null), [ytErr, setYtErr] = useState('');
  useEffect(() => { if (lib.value === 1 && nd === null && ndConfigured()) ndAlbumList('newest', 12).then(setNd).catch(() => setNd([])); }, [lib.value]);
  useEffect(() => {
    if (lib.value !== 0 || yt !== null) return;
    // YouTube Music fra Skjold (/api/ytm/home): spillelister, «Til deg» og album
    ytmHomeCached().then((h) => { const l = [...h.playlists, ...h.frequent, ...h.other, ...h.newest]; setYt(l.filter((x, i) => l.findIndex((y) => y.id === x.id) === i).slice(0, 24)); })
      .catch(async (e: unknown) => { setYtErr((await ytmWhy(e)).toUpperCase()); setYt([]); });
  }, [lib.value]);
  const st = status.value;
  const TABS = ['YouTube Music', 'Navidrome', 'Radio'];
  let kicker = '', items: Card[] = [];
  if (lib.value === 0) {
    kicker = ytErr || (yt === null ? 'HENTER …' : yt.length ? 'SPILLELISTER OG MIKSER' : 'FANT INGENTING · LEGG INN COOKIEN I APPEN');
    items = (yt ?? []).map((a) => ({ t: a.name, s: a.playlist ? 'Spilleliste' : a.artist, art: artBg(a.name, ndCover(a.coverArt, 300)), play: () => { void ytmTracks(a.id).then((r) => { if (r.length) { playNd(r, 0, 'ytm'); scr.value = 'now'; } }); } }));
  }
  else if (lib.value === 1) {
    kicker = ndConfigured() ? 'NYLIG LAGT TIL' : 'IKKE TILKOBLET · LOGG INN PÅ NAVIDROME I APPEN';
    items = (nd ?? []).map((a) => ({ t: a.name, s: a.artist, art: artBg(a.name, ndCover(a.coverArt, 300)), play: () => { void ndAlbum(a.id).then((r) => { playNd(r.songs, 0); scr.value = 'now'; }); } }));
  } else {
    kicker = 'DINE FAVORITTER';
    items = favs.value.map((f, i) => ({ t: f.title, s: f.genre || 'Radio', art: artBg(f.title, f.image, i), live: st?.input === 'radio' && !!st.playing && (st.radio_now?.url === f.url || st.preset === f.n), play: () => { playFav(f); scr.value = 'now'; } }));
  }
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:12px;padding:14px 22px 0;min-height:0">
      <div style="display:flex;gap:8px;align-items:center">
        {TABS.map((n, i) => { const on = lib.value === i; return <button key={n} onClick={() => { lib.value = i; }} style={`height:44px;padding:0 16px;border-radius:22px;border:1px solid ${on ? '#f2f2ee' : '#2e2e30'};background:${on ? '#f2f2ee' : '#161617'};color:${on ? '#0b0b0c' : '#f2f2ee'};font-size:13px;font-weight:600;white-space:nowrap`}>{n}</button>; })}
        <div style="flex:1" />
        <button onClick={() => { searchOpen.value = true; }} aria-label="Søk" style="height:44px;width:190px;border-radius:22px;border:1px solid #2e2e30;background:#141415;display:flex;align-items:center;gap:8px;padding:0 16px;box-sizing:border-box;color:#8b8b86;font-size:13px;text-align:left"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>Søk</button>
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
  const SEGBOX = 'display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426;align-items:center';
  const stepper = (txt: string, dn: () => void, up: () => void, w = 64) => (
    <div style={SEGBOX}>
      <button onClick={dn} aria-label="Forrige" style="width:44px;height:34px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:16px;font-weight:600">−</button>
      <span style={`min-width:${w}px;height:34px;padding:0 10px;border-radius:9px;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap;display:flex;align-items:center;justify-content:center;box-sizing:border-box`}>{txt}</span>
      <button onClick={up} aria-label="Neste" style="width:44px;height:34px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:16px;font-weight:600">+</button>
    </div>);
  const one = (txt: string, go: () => void) => <div style={SEGBOX}><button onClick={go} style="height:34px;padding:0 14px;border-radius:9px;border:none;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap">{txt}</button></div>;
  const nMode = S.tNightMode || (S.tNight ? 1 : 0);
  const rows: [string, string, preact.ComponentChildren][] = [
    ['Rolle', 'Spiller med egen lydutgang, fjernkontroll for huset, eller begge', seg(TOUCH_ROLES, S.tRole ?? 0, (i) => { setSetting('tRole', i); if (i === 1) control(''); }, (o) => o.replace('Spiller og fjernkontroll', 'Begge').replace('Bare ', ''))],
    ['Lydutgang', 'PCM5122 HIFI HAT', seg(TOUCH_OUT, S.tOut ?? 2, (i) => setSetting('tOut', i))],
    ['Lysstyrke', 'Skjermen når den er i bruk', stepper((S.tBright ?? 100) + ' %', () => setSetting('tBright', Math.max(20, (S.tBright ?? 100) - 20)), () => setSetting('tBright', Math.min(100, (S.tBright ?? 100) + 20)))],
    ['Dimme skjermen', 'Etter siste trykk', seg(['30 s', '1 min', '5 min'], Math.max(0, (S.tStandby ?? 1) - 1), (i) => setSetting('tStandby', i + 1))],
    ['I standby', 'Når skjermen hviler', seg(TOUCH_IDLE, S.tIdle ?? 0, (i) => setSetting('tIdle', i))],
    ['Startside', 'Siden som vises etter oppstart', stepper(TOUCH_START[S.tStart ?? 0] ?? '', () => setSetting('tStart', ((S.tStart ?? 0) + TOUCH_START.length - 1) % TOUCH_START.length), () => setSetting('tStart', ((S.tStart ?? 0) + 1) % TOUCH_START.length), 104)],
    ['Nattmodus', 'Svakt, rødlig lys og dempet skjerm', seg(['Av', 'Tidsplan', 'HA/Homey', 'På'], nMode, (i) => { setSetting('tNightMode', i); setSetting('tNight', i === 1); })],
    ['Natt fra', 'Brukes når nattmodus står på Tidsplan', stepper(String(S.tNStart ?? 22).padStart(2, '0') + ':00', () => setSetting('tNStart', ((S.tNStart ?? 22) + 23) % 24), () => setSetting('tNStart', ((S.tNStart ?? 22) + 1) % 24))],
    ['Natt til', 'Vanlig lys igjen fra dette klokkeslettet', stepper(String(S.tNEnd ?? 7).padStart(2, '0') + ':00', () => setSetting('tNEnd', ((S.tNEnd ?? 7) + 23) % 24), () => setSetting('tNEnd', ((S.tNEnd ?? 7) + 1) % 24))],
    ['Ringeklokke', 'Når noen ringer på', seg(TOUCH_BELL, S.tBell ?? 0, (i) => setSetting('tBell', i))],
    ['Test ringeklokke', 'Ringer på slik en ekte ringeklokke gjør', one('Ring på', () => void postAt('', '/api/doorbell', { test: true }))],
    ['Test alarm', 'Viser hvordan vekkingen ser ut', one('Start alarm', () => void postAt('', '/api/alarm', { action: 'test' }))],
    ['Stemmeassistent', 'Home Assistant Assist med mikrofon på enheten', seg(['Av', 'På'], S.tVoice ? 1 : 0, (i) => { setSetting('tVoice', i === 1); void postAt('', '/api/touch/voice', { mic: i === 1 && S.tMic !== false }); })],
    ...(S.tVoice ? [
      ['Vekkeord', 'Lyttes etter lokalt på enheten', seg(TOUCH_WAKE, S.tWake ?? 0, (i) => { setSetting('tWake', i); void postAt('', '/api/touch/voice', { wake: TOUCH_WAKE_ID[i] }); })],
      ['Mikrofon', 'Demp for å slå av lytting helt', seg(['På', 'Demp'], S.tMic === false ? 1 : 0, (i) => { setSetting('tMic', i === 0); void postAt('', '/api/touch/voice', { mic: i === 0 }); })]
    ] as [string, string, preact.ComponentChildren][] : []),
    ['Vis standby nå', 'Eller vent ' + (TOUCH_STANDBY_S[S.tStandby ?? 1] ?? 30) + ' s uten å trykke', (
      <div style="display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426">
        <button onClick={goIdle} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap">Standby</button>
        <button onClick={runBoot} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:12px;font-weight:600;white-space:nowrap">Start på nytt</button>
      </div>)],
    ['Om enheten', [local.value?.name, location.hostname, local.value?.version ? 'versjon ' + local.value.version : ''].filter(Boolean).join(' · '), <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#6b6b67;white-space:nowrap`}>SKJOLD TOUCH</span>]
  ];
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:12px;padding:14px 22px 12px;min-height:0">
      <span style="font-size:20px;font-weight:600">Innstillinger</span>
      <div class="rull" style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415;overflow-y:auto;min-height:0;touch-action:pan-y">
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

// ---------- smarthus ----------
const TILE_IC: Record<string, string> = {
  light: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z',
  climate: 'M14 14.8V4a2 2 0 0 0-4 0v10.8a4 4 0 1 0 4 0z', cover: 'M3 21V9l9-6 9 6v12M7 21v-8h10v8M7 16h10',
  switch: 'M13 2L4 14h7l-1 8 9-12h-7z', camera: 'M3 7h12v10H3zM15 10l6-3v10l-6-3', lock: 'M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4',
  sensor: 'M4 20V10M10 20V4M16 20v-7M22 20H2', weather: 'M7 18h10a4 4 0 0 0 .6-8A6 6 0 0 0 6 9.5 4.3 4.3 0 0 0 7 18z'
};
const tileIcon = (d: string) => TILE_IC[d] ?? (d === 'input_boolean' || d === 'fan' || d === 'media_player' ? TILE_IC.switch! : TILE_IC.sensor!);

function SmartHome() {
  const sm = smart.value;
  useEffect(() => { void loadSmart(); }, []);
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:10px;padding:14px 18px 10px;min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y">
      <div style="display:flex;align-items:center;gap:10px;min-height:36px"><span style="font-size:20px;font-weight:600">Smarthus</span><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>VIA {(sm?.hub ?? 'Home Assistant').toUpperCase()}</span><div style="flex:1" />
        {(sm?.scenes ?? []).map((sc) => { const on = sceneOn.value === sc.id; return <button key={sc.id} onClick={() => { sceneOn.value = sc.id; void press(sc.id, 'scene'); }} style={`height:44px;padding:0 14px;border-radius:22px;border:1px solid ${on ? '#f2f2ee' : '#2e2e30'};background:${on ? '#f2f2ee' : '#161617'};color:${on ? '#0b0b0c' : '#f2f2ee'};font-size:12px;font-weight:600;white-space:nowrap`}>{sc.name}</button>; })}</div>
      {!sm && <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>HENTER …</span>}
      {sm && !sm.ok && (
        <div style="border-radius:14px;border:1px solid #242426;background:#141415;padding:16px 18px;display:flex;flex-direction:column;gap:6px">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#f0c46a`}>IKKE KOBLET TIL</span>
          <span style="font-size:14px;line-height:1.45;color:#c9c9c4">{sm.error}</span>
          <span style="font-size:12px;line-height:1.45;color:#8b8b86">Flisene velges i appen under Innstillinger → Skjold Touch. Uten valg vises noen av lysene og bryterne dine.</span>
        </div>)}
      {sm?.ok && !sm.tiles.length && <span style="font-size:14px;color:#8b8b86">Fant ingen lys eller brytere i {sm.hub}.</span>}
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px">
        {(sm?.tiles ?? []).map((t) => <TileCard key={t.id} t={t} />)}
      </div>
    </section>
  );
}

// ---------- intercom ----------
const FRASER = ['Maten er klar', 'Kom hit litt', 'Vi drar om fem minutter', 'God natt'];
function Intercom() {
  const rooms = peers.value;
  const [to, setTo] = useState<string[]>([]);            // tom = alle rom
  const [rec, setRec] = useState(false), [secs, setSecs] = useState(0);
  const [msg, setMsg] = useState<{ t: string; ok: boolean } | null>(null);
  const [mic, setMic] = useState<boolean | null>(null);
  const mr = useRef<MediaRecorder | null>(null), chunks = useRef<Blob[]>([]), t0 = useRef(0);
  useEffect(() => { setMic(!!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'); }, []);
  useEffect(() => { if (!rec) return; const iv = setInterval(() => setSecs(Math.floor((Date.now() - t0.current) / 1000)), 250); return () => clearInterval(iv); }, [rec]);
  const ids = () => (to.length ? to : rooms.map((r) => r.id)).join(',');
  const names = () => { const l = to.length ? rooms.filter((r) => to.includes(r.id)).map((r) => r.navn) : []; return l.length ? l.join(' og ') : 'alle rom'; };
  const done = async (r: Response) => {
    const j = (await r.json().catch(() => ({}))) as { sent?: string[]; failed?: string[]; error?: string };
    if (!r.ok) setMsg({ t: j.error ? 'Ble ikke sendt: ' + j.error : 'Ble ikke sendt', ok: false });
    else if (j.failed?.length) setMsg({ t: 'Nådde ikke ' + j.failed.join(' og '), ok: false });
    else if (!j.sent?.length) setMsg({ t: 'Ingen rom tok imot. Sjekk at de andre enhetene er på.', ok: false });
    else setMsg({ t: 'Sendt til ' + j.sent.join(' og '), ok: true });
  };
  const sendText = (text: string) => { setMsg({ t: 'Sender …', ok: true }); void fetch(here() + '/api/intercom', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ to: ids(), text }) }).then(done).catch(() => setMsg({ t: 'Ble ikke sendt', ok: false })); };
  const start = async () => {
    if (rec || !rooms.length) return;
    setMsg(null);
    try {
      const st = await navigator.mediaDevices.getUserMedia({ audio: true });
      const m = new MediaRecorder(st); chunks.current = [];
      m.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      m.onstop = () => {
        st.getTracks().forEach((x) => x.stop());
        const b = new Blob(chunks.current, { type: m.mimeType || 'audio/webm' });
        if (Date.now() - t0.current < 700 || b.size < 2000) { setMsg({ t: 'For kort. Hold knappen inne mens du snakker.', ok: false }); return; }
        const fd = new FormData(); fd.append('to', ids()); fd.append('file', b, 'melding.' + (b.type.includes('mp4') ? 'm4a' : 'webm'));
        setMsg({ t: 'Sender …', ok: true });
        void fetch(here() + '/api/intercom', { method: 'POST', body: fd }).then(done).catch(() => setMsg({ t: 'Ble ikke sendt', ok: false }));
      };
      t0.current = Date.now(); setSecs(0); m.start(); mr.current = m; setRec(true);
    } catch { setMic(false); setMsg({ t: 'Fant ingen mikrofon på enheten. Hurtigmeldingene virker likevel.', ok: false }); }
  };
  const stop = () => { if (mr.current && mr.current.state !== 'inactive') mr.current.stop(); setRec(false); };
  const pill = (on: boolean) => `height:44px;padding:0 16px;border-radius:22px;border:1px solid ${on ? '#f0c46a' : '#2e2e30'};background:${on ? '#1c170d' : '#161617'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:13px;font-weight:600;white-space:nowrap;flex-shrink:0`;
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:7;background:#0b0b0c;display:flex;flex-direction:column;padding:12px 18px 14px;box-sizing:border-box;gap:10px">
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:20px;font-weight:600">Intercom</span>
        <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>SNAKK TIL {names().toUpperCase()}</span>
        <div style="flex:1" />
        <button onClick={() => { stop(); talkOpen.value = false; }} aria-label="Lukk intercom" style="width:44px;height:44px;margin-right:-10px;border:none;background:none;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
      </div>
      {!rooms.length ? <span style="font-size:14px;line-height:1.5;color:#8b8b86;max-width:520px">Fant ingen andre Skjold-enheter på nettet. Intercom sender en talemelding til de andre rommene, så du trenger minst én enhet til.</span> : <>
        <div style="display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;touch-action:pan-x;margin:0 -18px;padding:0 18px;flex-shrink:0">
          <button onClick={() => setTo([])} style={pill(!to.length)}>Alle rom</button>
          {rooms.map((r) => { const on = to.includes(r.id); return <button key={r.id} onClick={() => setTo(on ? to.filter((x) => x !== r.id) : [...to, r.id])} style={pill(on)}>{r.navn}</button>; })}
        </div>
        <div style="flex:1;min-height:0;display:flex;align-items:center;gap:26px">
          <div style="display:flex;flex-direction:column;align-items:center;gap:10px;width:230px;flex-shrink:0">
            <button class="flat" disabled={mic === false} onPointerDown={(e) => { e.preventDefault(); void start(); }} onPointerUp={stop} onPointerLeave={stop} onPointerCancel={stop} onContextMenu={(e) => e.preventDefault()} aria-label="Hold for å snakke"
              style={`position:relative;width:132px;height:132px;border-radius:66px;border:none;background:${rec ? '#e05a4a' : mic === false ? '#1f1f21' : '#f0c46a'};color:${mic === false ? '#6b6b67' : '#0b0b0c'};display:flex;align-items:center;justify-content:center;padding:0;touch-action:none;transition:background .15s ease,transform .15s ease;transform:scale(${rec ? 1.06 : 1})`}>
              {rec && <span class="ring" style="position:absolute;inset:-10px;border-radius:50%;border:2px solid #e05a4a" />}
              <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 11a7 7 0 0 1-14 0M12 18v3" /></svg>
            </button>
            <span style={`font-family:${MONO};font-size:11px;letter-spacing:.12em;color:${rec ? '#e05a4a' : '#8b8b86'};white-space:nowrap`}>{rec ? 'TAR OPP · 0:' + String(secs).padStart(2, '0') : mic === false ? 'INGEN MIKROFON' : 'HOLD FOR Å SNAKKE'}</span>
          </div>
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:8px">
            <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>ELLER SEND EN FERDIG MELDING</span>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">
              {FRASER.map((f) => <button key={f} onClick={() => sendText(f)} style="height:54px;border-radius:14px;border:1px solid #242426;background:#141415;font-size:13.5px;font-weight:600;padding:0 12px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{f}</button>)}
            </div>
            <span style={`min-height:20px;font-size:13px;color:${rec || !msg ? '#8b8b86' : msg.ok ? '#6fcf7f' : '#e05a4a'}`}>{rec ? 'Slipp knappen for å sende.' : msg?.t ?? 'Meldingen spilles i rommene du har valgt. Musikken dempes mens den varer.'}</span>
          </div>
        </div>
      </>}
    </div>
  );
}

// ---------- søk ----------
interface Hit { key: string; t: string; s: string; art: string; play: () => void }
function Search() {
  const [q, setQ] = useState(''), [kb, setKb] = useState(true), [busy, setBusy] = useState(false);
  const [hits, setHits] = useState<Hit[] | null>(null), [err, setErr] = useState('');
  const src = lib.value, seq = useRef(0);
  const go = (it: () => void) => () => { it(); searchOpen.value = false; scr.value = 'now'; };
  useEffect(() => {
    const t = q.trim(), n = ++seq.current;
    if (t.length < 2) { setHits(null); setBusy(false); setErr(''); return; }
    setBusy(true);
    const id = window.setTimeout(async () => {
      try {
        let l: Hit[];
        if (src === 2) { const r = await api.radioSearch(t); l = [...(r.norway ?? []), ...(r.world ?? [])].slice(0, 30).map((st, i) => ({ key: st.url + i, t: st.name, s: st.genre || st.country || 'Radio', art: artBg(st.name, st.image, i), play: () => playStation(st) })); }
        else { const r = src === 0 ? await ytmSearch(t) : await ndSearch(t); l = r.slice(0, 30).map((x, i) => ({ key: x.id + i, t: x.title, s: [x.artist, x.album].filter(Boolean).join(' · '), art: artBg(x.title, ndCover(x.coverArt, 120)), play: () => playNd(r, i, src === 0 ? 'ytm' : 'nd') })); }
        if (n === seq.current) { setHits(l); setErr(''); }
      } catch (e) { if (n === seq.current) { setHits([]); setErr(src === 0 ? await ytmWhy(e) : src === 1 && !ndConfigured() ? 'Navidrome er ikke koblet til. Logg inn i appen.' : 'Søket svarte ikke'); } }
      finally { if (n === seq.current) setBusy(false); }
    }, 500);
    return () => clearTimeout(id);
  }, [q, src]);
  const NAMES = ['YouTube Music', 'Navidrome', 'Radio'];
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;gap:8px;padding:8px 10px 8px 6px;flex-shrink:0">
        <button onClick={() => { searchOpen.value = false; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <button class="flat" onClick={() => setKb(true)} aria-label="Søkefelt" style="flex:1;min-width:0;height:44px;border-radius:22px;border:1px solid #2e2e30;background:#141415;display:flex;align-items:center;gap:8px;padding:0 16px;text-align:left;font-size:15px">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2" stroke-linecap="round" style="flex-shrink:0"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
          <span style={`white-space:pre;overflow:hidden;color:${q ? '#f2f2ee' : '#6b6b67'}`}>{q || 'Søk i ' + NAMES[src]}</span>{kb && <span class="caret" style="width:2px;height:20px;background:#f0c46a;margin-left:-6px;flex-shrink:0" />}
        </button>
        {NAMES.map((n, i) => <button key={n} onClick={() => { lib.value = i; }} style={`height:44px;padding:0 12px;border-radius:22px;border:1px solid ${src === i ? '#f2f2ee' : '#2e2e30'};background:${src === i ? '#f2f2ee' : '#161617'};color:${src === i ? '#0b0b0c' : '#c9c9c4'};font-size:12px;font-weight:600;white-space:nowrap;flex-shrink:0`}>{n.replace('YouTube Music', 'YouTube')}</button>)}
      </div>
      <div class="rull" onPointerDown={() => { if (hits?.length) setKb(false); }} style="flex:1;min-height:0;overflow-y:auto;display:flex;flex-direction:column;gap:2px;padding:0 10px 8px;touch-action:pan-y">
        {hits === null && !busy && <span style="padding:14px 10px;font-size:13.5px;color:#6b6b67">Skriv minst to bokstaver.</span>}
        {busy && hits === null && <span style={`padding:14px 10px;font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>SØKER …</span>}
        {hits !== null && !hits.length && !busy && <span style="padding:14px 10px;font-size:13.5px;color:#8b8b86">{err || 'Fant ingenting for «' + q.trim() + '».'}</span>}
        {(hits ?? []).map((h) => (
          <button key={h.key} onClick={go(h.play)} style={`height:52px;flex-shrink:0;border:none;border-radius:10px;background:transparent;display:grid;grid-template-columns:40px minmax(0,1fr);gap:12px;align-items:center;padding:0 10px;text-align:left;opacity:${busy ? 0.5 : 1}`}>
            <div style={`width:40px;height:40px;border-radius:8px;background:${h.art}`} />
            <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{h.t}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{h.s}</span></span>
          </button>))}
      </div>
      {kb && <Keyboard onKey={(c) => setQ((x) => (x + c).slice(0, 60))} onBack={() => setQ((x) => x.slice(0, -1))} onEnter={() => setKb(false)} />}
    </div>
  );
}

// ---------- dimmer ----------
function DimSheet() {
  const t = smart.value?.tiles.find((x) => x.id === dimId.value);
  const [v, setV] = useState<number | null>(null);
  if (!t) return null;
  const pct = Math.round(v ?? t.pct ?? 0);
  const set = (n: number) => { setV(n); void press(t.id, 'brightness', Math.round(n)).then(() => setV(null)); };
  return (
    <Sheet title={t.name} kicker={'LYSSTYRKE · ' + (pct ? pct + ' %' : 'AV')} onClose={() => { dimId.value = ''; }} height={210}>
      <div style="display:flex;flex-direction:column;gap:10px;padding:4px 14px 16px">
        <div style="display:flex;align-items:center;gap:4px"><Slider label="Lysstyrke" value={pct} onInput={(n) => setV(n)} onCommit={set} /><span style={`font-family:${MONO};font-size:15px;width:52px;text-align:right`}>{pct} %</span></div>
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px">
          {[0, 25, 50, 100].map((n) => <button key={n} onClick={() => set(n)} style={`height:46px;border-radius:12px;border:1px solid ${pct === n ? '#f0c46a' : '#2e2e30'};background:${pct === n ? '#1c170d' : '#161617'};color:${pct === n ? '#f0c46a' : '#f2f2ee'};font-size:13px;font-weight:600`}>{n ? n + ' %' : 'Av'}</button>)}
        </div>
      </div>
    </Sheet>
  );
}

function TileCard({ t }: { t: Tile }) {
  const dim = t.pct != null;
  const lp = useLongPress(() => { if (dim) dimId.value = t.id; });
  const act = t.kind === 'toggle' ? () => { if (!lp.fired()) void press(t.id, 'toggle'); } : t.kind === 'camera' ? () => ringNow(0, true) : undefined;
  return (
    <div style={`height:100px;border-radius:14px;border:1px solid ${t.on ? '#d9a441' : '#242426'};background:${t.on ? '#1c170d' : '#141415'};box-sizing:border-box;display:flex;flex-direction:column;justify-content:space-between;padding:12px;min-width:0;transition:background .2s ease,border-color .2s ease`}>
      <button onClick={act} {...(dim ? lp.on : {})} disabled={!act} style="border:none;background:none;padding:0;text-align:left;display:flex;align-items:center;gap:10px;min-width:0;min-height:44px;color:inherit;opacity:1;touch-action:manipulation">
        <div style={`width:34px;height:34px;flex-shrink:0;border-radius:10px;background:${t.on ? '#f0c46a' : t.kind === 'climate' ? '#8a3b12' : t.kind === 'camera' ? '#1e5aa8' : '#1f1f21'};color:${t.on ? '#0b0b0c' : t.kind === 'climate' || t.kind === 'camera' ? '#f2f2ee' : '#8b8b86'};display:flex;align-items:center;justify-content:center;transition:background .2s ease`}><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={tileIcon(t.domain)} /></svg></div>
        <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.name}</span><span style={`font-size:11px;color:${t.on && t.kind !== 'climate' ? '#f0c46a' : '#8b8b86'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{t.text}</span></span>
      </button>
      {t.kind === 'climate' && t.target != null
        ? <div style="display:flex;align-items:center;gap:6px"><button onClick={() => void press(t.id, 'down')} aria-label="Senk temperatur" style="width:44px;height:30px;border-radius:15px;border:1px solid #2e2e30;background:#161617;font-size:16px">−</button><span style={`flex:1;text-align:center;font-family:${MONO};font-size:15px`}>{t.target.toFixed(1).replace('.', ',')}°</span><button onClick={() => void press(t.id, 'up')} aria-label="Øk temperatur" style="width:44px;height:30px;border-radius:15px;border:1px solid #2e2e30;background:#161617;font-size:16px">+</button></div>
        : dim ? <button onClick={() => { dimId.value = t.id; }} aria-label={'Lysstyrke for ' + t.name} style={`height:30px;margin:-8px -6px -8px -6px;padding:0 6px;border:none;background:none;text-align:left;font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#6b6b67;display:flex;align-items:center;justify-content:space-between`}><span>{t.tag}</span><span style="color:#8b8b86">DIM ›</span></button>
        : <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#6b6b67;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{t.tag}</span>}
    </div>
  );
}

// ---------- vekkeklokke ----------
const DN = ['Ma', 'Ti', 'On', 'To', 'Fr', 'Lø', 'Sø'];
const DAYSETS: number[][] = [[0, 1, 2, 3, 4], [5, 6], [0, 1, 2, 3, 4, 5, 6]];
function daysTxt(d: number[]): string {
  if (!d.length || d.length === 7) return 'Hver dag';
  if (d.length === 5 && d.every((x) => x < 5)) return 'Hverdager';
  if (d.length === 2 && d.includes(5) && d.includes(6)) return 'Helg';
  return d.map((x) => DN[x]).join(' ');
}
const minOf = (t: string) => { const [h, m] = t.split(':'); return (+(h ?? 0)) * 60 + (+(m ?? 0)); };
const hhmm = (m: number) => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

function AlarmPage() {
  const AL = alarms.value, nx = nextAlarm();
  useEffect(() => { void loadAlarms(); }, []);
  const setA = (i: number, p: Partial<Alarm>) => saveAlarms(AL.map((a, j) => (j === i ? { ...a, ...p } : a)));
  const chip = 'height:44px;padding:0 4px;border:none;background:none;font-size:11.5px;color:#8b8b86;white-space:nowrap;text-decoration:underline;text-decoration-color:#3a3a37;text-underline-offset:3px';
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:10px;padding:14px 18px 10px;min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y">
      <div style="display:flex;align-items:center;gap:10px"><span style="font-size:20px;font-weight:600">Vekkeklokke</span><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>{nx ? 'NESTE ALARM ' + nx.time : 'INGEN ALARMER PÅ'}</span><div style="flex:1" />
        {AL.length < 10 && <button onClick={() => saveAlarms([...AL, { time: '08:00', days: [0, 1, 2, 3, 4], on: true, name: 'Alarm', smart: false, preset: 0, url: '', volume: 30, fade: 0 }])} style="height:44px;padding:0 16px;border-radius:22px;border:1px solid #2e2e30;background:#161617;font-size:12.5px;font-weight:600">+ Ny alarm</button>}</div>
      {!AL.length && <span style="font-size:14px;color:#8b8b86">Ingen alarmer ennå. Trykk «Ny alarm».</span>}
      {!!AL.length && <div style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415;flex-shrink:0">
        {AL.map((a, i) => { const m = minOf(a.time), fg = a.on ? '#f2f2ee' : '#6b6b67'; return (
          <div key={i} style={`display:flex;align-items:center;gap:8px;min-height:66px;padding:0 8px 0 10px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'}`}>
            <div style="display:flex;align-items:center">
              <button onClick={() => setA(i, { time: hhmm((m + 1435) % 1440) })} aria-label="Fem minutter tidligere" style="width:44px;height:48px;border:none;background:none;color:#8b8b86;font-size:20px">‹</button>
              <span style={`font-family:${MONO};font-size:30px;font-weight:500;color:${fg};width:92px;text-align:center`}>{a.time}</span>
              <button onClick={() => setA(i, { time: hhmm((m + 5) % 1440) })} aria-label="Fem minutter senere" style="width:44px;height:48px;border:none;background:none;color:#8b8b86;font-size:20px">›</button>
            </div>
            <span style="display:flex;flex-direction:column;flex:1;min-width:0">
              <span style={`font-size:14px;font-weight:600;color:${fg};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{a.name || 'Alarm'}</span>
              <span style="display:flex;gap:6px;margin-top:-10px;margin-bottom:-12px">
                <button onClick={() => { const k = DAYSETS.findIndex((d) => daysTxt(d) === daysTxt(a.days)); setA(i, { days: DAYSETS[(k + 1) % DAYSETS.length]! }); }} aria-label="Bytt dager" style={chip}>{daysTxt(a.days)}</button>
                <button onClick={() => setA(i, { smart: !a.smart, fade: a.smart ? 0 : 3 })} aria-label="Bytt mellom smart og vanlig vekking" style={chip}>{a.smart ? 'Smart vekking' : 'Vanlig'}</button>
              </span>
            </span>
            <button onClick={() => setA(i, { on: !a.on })} aria-label="Slå alarm av eller på" style="width:60px;height:48px;border:none;background:none;padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0"><span style={`position:relative;width:52px;height:30px;border-radius:15px;background:${a.on ? '#f0c46a' : '#2a2a2c'};transition:background .2s ease`}><span style={`position:absolute;top:3px;left:${a.on ? 25 : 3}px;width:24px;height:24px;border-radius:12px;background:#f2f2ee;transition:left .2s ease`} /></span></button>
            <button onClick={() => saveAlarms(AL.filter((_, j) => j !== i))} aria-label="Slett alarm" style="width:44px;height:48px;border:none;background:none;color:#6b6b67;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
          </div>); })}
      </div>}
      <div style="display:flex;gap:10px;flex-shrink:0">
        <div style="flex:1;border-radius:14px;border:1px solid #242426;background:#141415;padding:12px 14px;display:flex;flex-direction:column;gap:4px"><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#f0c46a`}>SMART VEKKING</span><span style="font-size:12px;line-height:1.4;color:#c9c9c4">Lyden starter svakt og øker over tre minutter. Har du satt opp vekkelys i appen, skrus lyset gradvis opp før alarmen.</span></div>
        <div style="flex:1;border-radius:14px;border:1px solid #242426;background:#141415;padding:12px 14px;display:flex;flex-direction:column;gap:4px"><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#6fcf7f`}>SAMME ALARMER OVERALT</span><span style="font-size:12px;line-height:1.4;color:#c9c9c4">Alarmene er de samme her, i appen og på web. De ligger på enheten og virker uten nett.</span></div>
      </div>
    </section>
  );
}

function AlarmRinging({ clock }: { clock: string }) {
  const a = dev().alarm;
  const post = (action: string) => { void postAt('', '/api/alarm', { action }).then(() => pollRooms()); };
  return (
    <div style="position:absolute;inset:0;z-index:26;background:radial-gradient(ellipse at 50% 110%,#5a3a12 0%,#1c130a 45%,#050506 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;animation:tinn .5s ease both">
      <span style={`font-family:${MONO};font-size:11px;letter-spacing:.18em;color:#f0c46a`}>{a?.snoozed ? 'SLUMRET · ' + (a.name || 'ALARM').toUpperCase() : 'GOD MORGEN · ' + (a?.name || 'ALARM').toUpperCase()}</span>
      <span style="font-size:120px;font-weight:300;letter-spacing:-.03em;line-height:1;color:#f2f2ee">{clock}</span>
      <span style="font-size:17px;color:#c9c9c4;min-height:24px;max-width:680px;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{morning.value}</span>
      <div style="display:flex;gap:12px;margin-top:26px">
        <button onClick={() => post('snooze')} style="height:64px;padding:0 34px;border-radius:32px;border:none;background:#f0c46a;color:#0b0b0c;font-size:16px;font-weight:600">Slumre 9 min</button>
        <button onClick={() => post('stop')} style="height:64px;padding:0 34px;border-radius:32px;border:1px solid #3a3a37;background:rgba(22,22,23,.85);color:#f2f2ee;font-size:16px;font-weight:600">Slå av</button>
      </div>
      <span style={`position:absolute;bottom:16px;font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#6b6b67`}>KAN OGSÅ SLÅS AV I APPEN, PÅ WEB OG I HOME ASSISTANT</span>
    </div>
  );
}

// ---------- ringeklokke ----------
function Door({ clock }: { clock: string }) {
  const [tick, setTick] = useState(0), [noCam, setNoCam] = useState(false);
  useEffect(() => { const iv = setInterval(() => setTick((x) => x + 1), 1000); return () => clearInterval(iv); }, []);
  const unlock = () => { void fetch(here() + '/api/touch/unlock', { method: 'POST' }).then((r) => { unlocked.value = r.ok; }).catch(() => undefined); };
  const close = () => { clearTimeout(doorT); door.value = 0; };
  return (
    <div style="position:absolute;inset:0;z-index:24;background:#050506;overflow:hidden;animation:tinn .3s ease both">
      <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 30%,#3d4247 0%,#1f2326 45%,#0b0d0e 100%)" />
      {!noCam && <img src={here() + '/api/doorbell/camera?t=' + door.value + '-' + tick} alt="Kamera ved inngangen" onError={() => setNoCam(true)} style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover" />}
      {noCam && <span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:15px;color:#8b8b86">Ingen kamera er satt opp</span>}
      <div style="position:absolute;left:0;right:0;top:0;height:68px;padding:0 20px;display:flex;align-items:center;gap:12px;background:linear-gradient(180deg,rgba(0,0,0,.75),rgba(0,0,0,0))">
        {!noCam && <span style={`height:22px;padding:0 8px;border-radius:5px;background:#e05a4a;color:#fff;font-family:${MONO};font-size:10px;letter-spacing:.1em;display:flex;align-items:center`}>DIREKTE</span>}
        <span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:17px;font-weight:600;color:#f2f2ee">{dev().doorbell?.t === door.value ? 'Det ringer på døren' : 'Inngang'}</span><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#c9c9c4`}>RINGEKLOKKE · INNGANG</span></span>
        <div style="flex:1" />
        <span style={`font-family:${MONO};font-size:14px;color:#f2f2ee`}>{clock}</span>
      </div>
      <div style="position:absolute;left:0;right:0;bottom:0;padding:18px 20px;display:flex;align-items:center;justify-content:center;gap:12px;background:linear-gradient(0deg,rgba(0,0,0,.85),rgba(0,0,0,0))">
        {!!smart.value?.lock && <button onClick={unlock} style={`height:56px;padding:0 22px;border-radius:28px;border:1px solid #f0c46a;background:${unlocked.value ? '#f0c46a' : 'rgba(22,22,23,.85)'};color:${unlocked.value ? '#0b0b0c' : '#f0c46a'};display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600`}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 11h12v10H6zM8 11V7a4 4 0 0 1 7.5-2" /></svg>{unlocked.value ? 'Låst opp' : 'Lås opp'}</button>}
        <button onClick={close} style="height:56px;padding:0 28px;border-radius:28px;border:1px solid #3a3a37;background:rgba(22,22,23,.85);color:#f2f2ee;font-size:14px;font-weight:600">Lukk</button>
      </div>
    </div>
  );
}

function DoorToast() {
  return (
    <button onClick={() => ringNow(doorToast.value, true)} style="position:absolute;top:60px;left:50%;transform:translateX(-50%);z-index:23;height:52px;padding:0 18px 0 12px;border-radius:26px;border:1px solid #d9a441;background:#1c170d;color:#f2f2ee;display:flex;align-items:center;gap:10px;box-shadow:0 12px 30px rgba(0,0,0,.5);animation:tinn .3s ease both">
      <span style="width:30px;height:30px;border-radius:15px;background:#f0c46a;color:#0b0b0c;display:flex;align-items:center;justify-content:center"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21h4" /></svg></span>
      <span style="font-size:14px;font-weight:600">Det ringer på døren</span><span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#f0c46a`}>VIS KAMERA</span>
    </button>
  );
}

// ---------- oppsett-nett (enheten har ikke nett) ----------
function SetupNet() {
  const n = dev().setup_net!;
  const steg = (i: number, a: string, b: preact.ComponentChildren) => (
    <div style="display:flex;gap:14px;align-items:flex-start">
      <span style={`width:30px;height:30px;flex-shrink:0;border-radius:15px;background:#1c170d;border:1px solid #d9a441;color:#f0c46a;font-family:${MONO};font-size:13px;display:flex;align-items:center;justify-content:center`}>{i}</span>
      <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px;font-weight:600">{a}</span><span style="font-size:13px;line-height:1.4;color:#a8a8a3">{b}</span></span>
    </div>);
  const kode = `font-family:${MONO};color:#f0c46a`;
  return (
    <div style="position:absolute;inset:0;z-index:22;background:#0b0b0c;display:grid;grid-template-columns:300px minmax(0,1fr);animation:tinn .4s ease both">
      <div style="display:flex;flex-direction:column;justify-content:center;gap:14px;padding:0 30px;background:#101011;border-right:1px solid #1f1f21">
        <div style="display:flex;gap:5px;align-items:flex-end;height:52px">{BARS.map((h, i) => <div key={i} style={`width:8px;height:${h * 2}px;border-radius:4px;background:#f0c46a`} />)}</div>
        <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#f0c46a`}>{n.joining ? 'KOBLER TIL' : 'IKKE PÅ NETT'}</span>
        <span style="font-size:28px;font-weight:600;line-height:1.12;letter-spacing:-.01em">{n.joining ? 'Kobler til «' + n.joining + '»' : 'Koble Touch til Wi-Fi'}</span>
        {!!n.error && !n.joining && <span style="font-size:13px;line-height:1.4;color:#e05a4a">{n.error}</span>}
      </div>
      <div style="display:flex;flex-direction:column;justify-content:center;gap:18px;padding:0 32px">
        {steg(1, 'Koble telefonen til dette nettet', <>Nett: <span style={kode}>{n.ssid}</span><br />Passord: <span style={kode}>{n.password}</span></>)}
        {steg(2, 'Velg hjemmenettet ditt', <>Oppsettsiden åpner seg selv. Skjer det ikke, gå til <span style={kode}>{n.url.replace('http://', '')}</span></>)}
        {steg(3, 'Ferdig', 'Touch slår av oppsett-nettet og kobler til. Denne siden forsvinner av seg selv.')}
      </div>
    </div>
  );
}

// ---------- stemme ----------
function Voice() {
  const v = dev().touch?.voice, st = v?.state ?? 'idle';
  const kicker = st === 'listen' ? 'LYTTER …' : st === 'think' ? 'TENKER …' : st === 'error' ? 'FIKK IKKE SVAR' : 'SVAR';
  return (
    <div style="position:absolute;inset:52px 0 0 0;z-index:5;background:rgba(6,6,7,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:0 48px;text-align:center;animation:tinn .2s ease both">
      <div style="display:flex;align-items:center;gap:6px;height:64px">
        {[0.55, 0.8, 1, 0.8, 0.55].map((k, i) => <div key={i} class={st === 'think' ? 'vb vb-t' : st === 'error' ? 'vb' : 'vb vb-l'} style={`width:10px;height:${Math.round(8 + 46 * k)}px;border-radius:5px;background:${st === 'think' || st === 'error' ? '#8b8b86' : '#f0c46a'};animation-delay:${i * 90}ms`} />)}
      </div>
      <span style={`font-family:${MONO};font-size:11px;letter-spacing:.16em;color:#f0c46a`}>{kicker}</span>
      <span style="font-size:26px;font-weight:600;line-height:1.2;color:#f2f2ee;text-wrap:balance;max-width:560px">{v?.text ? '«' + v.text + '»' : 'Si noe …'}</span>
      <span style="font-size:15px;line-height:1.45;color:#c9c9c4;text-wrap:pretty;max-width:520px;min-height:22px">{st === 'reply' ? v?.reply : ''}</span>
      <button onClick={() => void postAt('', '/api/touch/voice', { state: 'idle' })} style="height:44px;padding:0 20px;border-radius:22px;border:1px solid #2e2e30;background:#161617;font-size:13px;font-weight:600;margin-top:6px">Lukk</button>
      <span style={`position:absolute;bottom:14px;left:0;right:0;font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#6b6b67`}>HOME ASSISTANT ASSIST · {(TOUCH_WAKE[settings.value.tWake ?? 0] ?? '').toUpperCase()}</span>
    </div>
  );
}

function Standby({ clock, dateTxt }: { clock: string; dateTxt: string }) {
  const s = status.value, m = settings.value.tIdle ?? 0, night = nightNow(), nx = nextAlarm();
  const bg = artOf(s), playing = !!s?.playing;
  return (
    <button class="flat" onPointerDown={(e) => { e.preventDefault(); e.stopPropagation(); wake(); }} aria-label="Vekk skjermen" style={`position:absolute;inset:0;border:none;background:#000;padding:0;overflow:hidden;opacity:${idleOp.value};transition:opacity .8s ease;z-index:20`}>
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
          <span style={`font-size:17px;color:${night ? '#5a211a' : '#8b8b86'};white-space:nowrap`}>{dateTxt}</span>
          {nx && <span style={`margin-top:8px;font-family:${MONO};font-size:12px;letter-spacing:.12em;color:${night ? '#7a2a20' : '#f2f2ee'};opacity:.8`}>ALARM {nx.time}</span>}
          {playing && !night && <span style="margin-top:26px;display:flex;align-items:center;gap:10px;font-size:13px;color:#8b8b86"><div style={`width:24px;height:24px;border-radius:5px;background:${bg}`} />{(s?.title || s?.station) + (s?.artist ? ' · ' + s.artist : '')}</span>}
        </div>
      )}
      {m !== 2 && !night && <span style={`position:absolute;left:0;right:0;bottom:16px;text-align:center;font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#3a3a37`}>TRYKK FOR Å VEKKE</span>}
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
  const s = status.value, d = new Date(now.value), S = settings.value, D = dev();
  const talking = !!D.touch?.voice && D.touch.voice.state !== 'idle';
  const clock = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const dateTxt = d.toLocaleDateString('nb-NO', { weekday: 'long', day: 'numeric', month: 'long' }).replace(/^./, (c) => c.toUpperCase());
  const r = role(), cur = scr.value === 'rooms' && r === 1 ? 'now' : scr.value;
  // Bare fjernkontroll: styr første andre rom så snart det finnes
  useEffect(() => { if (r === 2 && !ctl.value && peers.value[0]) control(peers.value[0].base); if (r === 1 && ctl.value) control(''); }, [r, peers.value.length]);
  const NAV: [Scr, string][] = ([['now', 'Spiller'], ['home', 'Hjem'], ['smart', 'Smarthus'], ['alarm', 'Alarm'], ['lib', 'Bibliotek'], ['rooms', 'Rom'], ['set', 'Oppsett']] as [Scr, string][]).filter(([k]) => !(r === 1 && k === 'rooms'));
  const rows = roomList();
  const curRoom = rows.find((x) => x.base === ctl.value);
  const roomLabel = curRoom?.name ?? s?.name ?? 'Skjold Touch', roomSub = (curRoom?.model ?? 'Skjold Touch').replace('Skjold ', '');
  return (
    <div style="position:relative;width:800px;height:480px;background:#0b0b0c;overflow:hidden;display:grid;grid-template-columns:76px minmax(0,1fr);grid-template-rows:480px">
      <nav style="display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 0 8px;background:#101011;border-right:1px solid #1f1f21">
        <div style="display:flex;gap:2.5px;align-items:flex-end;height:26px;margin-bottom:4px">{[14, 20, 26, 20, 14].map((h, i) => <div key={i} style={`width:4px;height:${h}px;border-radius:2px;background:#f0c46a`} />)}</div>
        {NAV.map(([k, label]) => { const on = cur === k; return (
          <button key={k} onClick={() => { scr.value = k; roomsOpen.value = false; talkOpen.value = false; searchOpen.value = false; queueOpen.value = false; dimId.value = ''; }} aria-label={label} style={`width:64px;height:48px;border-radius:13px;border:none;background:${on ? 'rgba(240,196,106,.14)' : 'transparent'};color:${on ? '#f0c46a' : '#8b8b86'};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:0`}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={IC[k]} /></svg>
            <span style={`font-size:9px;font-weight:${on ? 600 : 400}`}>{label}</span>
          </button>); })}
        <div style="flex:1" />
        <button onClick={goIdle} aria-label="Standby" style="width:44px;height:44px;margin-bottom:-2px;border-radius:22px;border:1px solid #2e2e30;background:transparent;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0" /></svg></button>
      </nav>
      <main style="position:relative;display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden">
        <header style="height:52px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 18px;border-bottom:1px solid #1a1a1c">
          <button onClick={() => { roomsOpen.value = !roomsOpen.value; }} style="height:34px;display:flex;align-items:center;gap:8px;padding:0 12px 0 10px;border-radius:17px;border:1px solid #2e2e30;background:#161617;min-width:0">
            <div style={`width:8px;height:8px;border-radius:50%;background:${online.value ? '#6fcf7f' : '#3a3a37'};flex-shrink:0`} />
            <span style="font-size:13px;font-weight:600;white-space:nowrap">{roomLabel}</span>
            <span style={`font-family:${MONO};font-size:10px;color:#8b8b86;white-space:nowrap`}>{roomSub}</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2.4" stroke-linecap="round"><path d="M6 9l6 6 6-6" /></svg>
          </button>
          {!!ctl.value && <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#f0c46a`}>FJERNKONTROLL</span>}
          <div style="flex:1" />
          {role() !== 1 && <button onClick={() => { talkOpen.value = !talkOpen.value; }} aria-label="Intercom" style={`width:44px;height:44px;border:none;background:none;color:${talkOpen.value ? '#f0c46a' : '#c9c9c4'};padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0`}><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10v4l3 .6V9.4zM7 9.4 19 5v14L7 14.6M9.5 15.2V18a1.6 1.6 0 0 0 3.2 0v-2.2" /></svg></button>}
          {!!S.tVoice && (() => { const muted = S.tMic === false, vs = talking; return (
            <button onClick={() => { setSetting('tMic', muted); void postAt('', '/api/touch/voice', { mic: muted }); }} aria-label={muted ? 'Slå på mikrofonen' : 'Demp mikrofonen'} style={`height:44px;margin:0 -2px;display:flex;align-items:center;border:none;background:none;padding:0`}>
              <span style={`height:34px;display:flex;align-items:center;gap:7px;padding:0 12px 0 10px;border-radius:17px;border:1px solid ${vs ? '#d9a441' : muted ? '#7a2a20' : '#2e2e30'};background:${vs ? 'rgba(240,196,106,.14)' : muted ? 'rgba(224,90,74,.12)' : '#161617'};color:${vs ? '#f0c46a' : muted ? '#e05a4a' : '#c9c9c4'}`}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d={muted ? 'M3 3l18 18M9 9v2a3 3 0 0 0 5.1 2.1M15 10V5a3 3 0 0 0-5.7-1.3M19 11a7 7 0 0 1-1.2 3.9M5 11a7 7 0 0 0 11.4 5.4M12 18v3' : 'M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 11a7 7 0 0 1-14 0M12 18v3'} /></svg>
                <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;white-space:nowrap`}>{muted ? 'DEMPET' : vs ? 'LYTTER' : (TOUCH_WAKE[S.tWake ?? 0] ?? '').toUpperCase()}</span>
              </span>
            </button>); })()}
          <span style={`font-family:${MONO};font-size:14px;color:#c9c9c4`}>{clock}</span>
        </header>
        {cur === 'now' && <NowPlaying />}
        {cur === 'home' && <Home />}
        {cur === 'smart' && <SmartHome />}
        {cur === 'alarm' && <AlarmPage />}
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
        {searchOpen.value && cur === 'lib' && <Search />}
        {queueOpen.value && cur === 'now' && <QueueSheet />}
        {!!dimId.value && cur === 'smart' && <DimSheet />}
        {talkOpen.value && <Intercom />}
        {talking && <Voice />}
      </main>
      {idle.value && <Standby clock={clock} dateTxt={dateTxt} />}
      {(!!D.setup_net?.active || !!D.setup_net?.joining) && !boot.value.on && <SetupNet />}
      {!!doorToast.value && !door.value && <DoorToast />}
      {!!door.value && <Door clock={clock} />}
      {!!D.alarm?.ringing && <AlarmRinging clock={clock} />}
      {boot.value.on && <Boot />}
    </div>
  );
}

// Til skjermbilder og test: window.__touch.screen('home') osv.
(window as unknown as { __touch: unknown }).__touch = {
  screen: (k: Scr) => { scr.value = k; }, lib: (i: number) => { lib.value = i; }, standby: goIdle, wake, boot: runBoot,
  intercom: (o: boolean) => { talkOpen.value = o; }, search: (o: boolean) => { searchOpen.value = o; }, queue: (o: boolean) => { queueOpen.value = o; },
  skipBoot: () => { bootT.forEach(clearTimeout); started = true; boot.value = { on: false, step: 9, op: 0 }; }, rooms: (o: boolean) => { roomsOpen.value = o; },
  // de samme inngangene som i designet: alarm, ringeklokke, nattmodus og stemme
  alarm: () => void postAt('', '/api/alarm', { action: 'test' }), ring: () => ringNow(0, true),
  night: (on: boolean) => void postAt('', '/api/night', { on, src: 'Skjold Touch' }),
  voice: (state: string, text = '', reply = '') => void postAt('', '/api/touch/voice', { state, text, reply })
};
render(<App />, document.getElementById('touch')!);
