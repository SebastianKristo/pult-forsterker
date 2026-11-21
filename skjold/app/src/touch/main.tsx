// Skjold Touch – skjermgrensesnittet på 7″ berøringsskjerm (800 × 480, kiosk).
// Bygget piksel-identisk etter design-handoff «Skjold Touch UI.dc.html»: mål, farger og tekster er hentet derfra.
// Data er ekte: status/hendelser fra daemonen, rom fra /api/rom (mDNS), innstillinger via /api/settings.
import { render } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { effect, signal } from '@preact/signals';
import './touch.css';
import { api, coverUrl, getBase, INPUT_LABEL, PRODUCT_SHORT, productOf, setBase, type InputId, type Lyrics, type PodEpisode, type PodShow, type Status } from '../lib/api';
import { loadSettings, playPause, reconnect, setSetting, setVolume, settings, startPolling, status, act, online, toast } from '../lib/store';
import { art, TOUCH_BELL, TOUCH_IDLE, TOUCH_OUT, TOUCH_ROLES, TOUCH_STANDBY_S, TOUCH_START, TOUCH_WAKE, TOUCH_WAKE_ID } from '../lib/settings';
import { favs, loadFavs, playFav, playStation } from '../lib/radio';
import { ndAlbum, ndAlbumList, ndArtist, ndConfigured, ndCover, ndSearch, ndSearchAll, type NdAlbum, type NdArtist, type NdSong } from '../lib/navidrome';
import { li, lq, lsvc, playNd } from '../lib/library';
import { ytmHomeCached, ytmSearch, ytmTracks, ytmWhy } from '../lib/ytm';
import '../lib/services';   // innloggingene (Navidrome, YouTube Music) hentes fra enheten – kiosken har ingen egne
import { groupAll, groupBusy, groupNone, groups, inGroup, loadGroup, removePreset, savePreset, setMembers, toggleMember } from '../lib/groups';
import { qrMatrix } from '../lib/qr';
import { canSeek, seekTo } from '../screens/player';
import { lydProsent, spillKlokke, spillLyd, startTrykkelyder } from './lyd';
import { AlleInnstillinger } from './innstillinger';
import { hjulMål, Keyboard, MONO, Sheet, Slider, TekstFelt, useLongPress, useTekst, Wheel } from './ui';

type Scr = 'now' | 'home' | 'smart' | 'alarm' | 'lib' | 'rooms' | 'set';
const START: (Scr | 'standby')[] = ['now', 'home', 'smart', 'alarm', 'lib', 'rooms', 'set', 'standby'];
interface Peer { id: string; navn: string; produkt: string; base: string }
interface Alarm { time: string; days: number[]; on: boolean; name: string; smart: boolean; preset: number; url: string; volume: number; fade: number }
interface Tile { id: string; name: string; domain: string; on: boolean; kind: 'toggle' | 'info' | 'climate' | 'camera'; text: string; tag: string; target?: number | null; pct?: number }
interface Smart { ok: boolean; hub: string; tiles: Tile[]; scenes: { id: string; name: string }[]; error?: string; lock?: boolean }
interface WakeNum { value: number; min: number; max: number; step: number }
interface WakeAlarm {
  id: string; name: string; on: boolean; days: { key: string; time: string; on: boolean; ok: boolean }[]; fade: WakeNum | null; off_after: WakeNum | null;
  night_light: boolean | null; wake_person: boolean | null; only_if_asleep: boolean | null; next: string; next_day: string; skip: string;
  running: boolean; phase: string; lights: number; can_test: boolean; person: { name: string; sleeping: boolean; pct: number | null; reason: string; can_set: boolean } | null;
}
interface WakeData { ok: boolean; alarms: WakeAlarm[]; error?: string }
// Det denne enheten selv melder (alarm, ringeklokke, stemme, kommandoer) – uavhengig av hvilket rom som fjernstyres
interface Dev {
  alarm?: { ringing: boolean; snoozed: boolean; name: string; time: string };
  doorbell?: { t: number; camera: boolean; seconds: number; v0?: number | null } | null;
  night?: { on: boolean; src?: string; steps?: { name: string; done?: boolean }[]; t?: number };
  setup_net?: { active: boolean; manual?: boolean; ssid: string; password: string; url: string; qr?: string; joining: string; error: string;
    kabel?: boolean; ethernet?: { device: string; state: string } | null } | null;
  ble_setup?: { state: string; error: string; ssid: string; url: string } | null;   // Wi-Fi over Bluetooth (Improv)
  touch?: { cmd: { cmd: string; arg: string; seq: number }; voice: { state: string; text: string; reply: string }; hjul?: { n: number; s: number; v?: number; r?: number }; timere?: Timer[] };
  home?: { cal?: { day: string; items: string[] }; weather?: { temp?: number | string; text?: string } };
  hold?: { key: string; p: number; title: string; sub: string } | null;   // fysisk knapp som holdes (POWER = omstart)
  rebooting?: boolean; poweroff?: boolean;
}

// ---------- nettbrett (Skjold Touch-appen for Android) ----------
// Appen laster touch.html?fluid=1 fra en Skjold-enhet og gir et lite grensesnitt (window.SkjoldTablet).
// Da fyller grensesnittet hele skjermen (ikke fast 800 × 480), lysstyrken styres av nettbrettet selv,
// og av/på-knappen starter ikke Skjold-enheten på nytt.
interface SkjoldTabletApi { setBrightness(level: number): void; velgEnhet(): void; navn?(): string; appVersjon?(): string; oppdaterApp?(): void }
const TABLET = (window as unknown as { SkjoldTablet?: SkjoldTabletApi }).SkjoldTablet;
const FLUID = !!TABLET || /[?&]fluid=1\b/.test(location.search);
/** Omslaget på Spiller-siden: 244 px på Touch, større på et nettbrett. */
const COVER = FLUID ? 'min(52vh, 40vw)' : '244px';
if (FLUID) {
  const m = document.querySelector('meta[name="viewport"]');
  if (m) m.setAttribute('content', 'width=device-width, initial-scale=1, user-scalable=no, viewport-fit=cover');
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
// Ny versjon installert (Innstillinger → Oppdatering): last skjermen på nytt, ellers kjører kiosken den gamle koden
// til nettleseren startes på nytt. Litt pause først, så daemonen er helt oppe igjen etter omstarten.
let forsteVersjon = '';
effect(() => {
  const v = local.value?.version;
  if (!v) return;
  if (!forsteVersjon) { forsteVersjon = v; return; }
  if (v !== forsteVersjon) window.setTimeout(() => location.reload(), 4000);
});
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
const queueOpen = signal(false), talkOpen = signal(false), searchOpen = signal(false), dimId = signal(''), lyricsOpen = signal(false);
const wakeData = signal<WakeData | null>(null), wakeOpen = signal(false), wakeSel = signal('');
const editAlarm = signal(-1);      // indeksen til alarmen som redigeres (-1 = ingen)
const dev = (): Dev => (local.value ?? {}) as Dev;
startTrykkelyder(() => lydProsent(settings.value.tLydP, settings.value.tLyd));   // myke klikk i høyttalerne (Oppsett → Trykkelyder)
// Volumglideren på skjermen: et lite hakk for hvert 2. %, lysere opp og mørkere ned (som en knott med hakk)
let volHakkSist = -1;
function volHakk(n: number): void {
  const steg = Math.round(n / 2);
  if (volHakkSist >= 0 && steg !== volHakkSist) spillLyd('hakk', lydProsent(settings.value.tLydP, settings.value.tLyd), steg > volHakkSist ? 1.12 : 0.9);
  volHakkSist = steg;
  window.clearTimeout(volHakkT); volHakkT = window.setTimeout(() => { volHakkSist = -1; }, 600);
}
let volHakkT = 0;
// Volumhjulet mens skjermtastaturet er oppe: daemonen teller steg (n) og trykk (s); vi flytter markøren / sletter ett tegn.
let hjulSist: { n: number; s: number; v?: number; r?: number } | null = null;
effect(() => {
  const h = dev().touch?.hjul;
  if (!h) return;
  const m = hjulMål.cur;
  if (hjulSist && (h.v ?? 0) > (hjulSist.v ?? 0)) {   // volumhjulet: ett lite hakk per steg (høyst 4 om gangen)
    const n = Math.min(4, (h.v ?? 0) - (hjulSist.v ?? 0)), p = lydProsent(settings.value.tLydP, settings.value.tLyd), tone = (h.r ?? 1) > 0 ? 1.12 : 0.9;
    for (let i = 0; i < n; i++) window.setTimeout(() => spillLyd('hakk', p, tone), i * 35);
  }
  if (hjulSist && m) {
    if (h.n !== hjulSist.n) m.flytt(h.n - hjulSist.n);
    for (let i = 0; i < Math.min(10, h.s - hjulSist.s); i++) m.slett();
  }
  hjulSist = h;
});

// Kiosken kjører på enheten selv: start alltid på denne enheten (en lagret host fra fjernstyring nullstilles).
setBase(null);
startPolling(); void loadSettings(); void loadFavs(); loadSwT();

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
// Smart vekking: vekkealarmene fra KI Søvn i Home Assistant (lys som tones opp, og om du sover)
let wakeW = 0;
async function loadWake(): Promise<void> {
  const t0 = Date.now();
  try { const r = await getAt<WakeData>('', '/api/touch/wake'); if (wakeW < t0) wakeData.value = r; } catch { /* eldre daemon */ }
}
function wakePatch(a: WakeAlarm, ch: Record<string, unknown>): WakeAlarm {
  const n: WakeAlarm = { ...a, days: a.days.map((d) => ({ ...d })) };
  for (const [k, v] of Object.entries(ch)) {
    const d = n.days.find((x) => x.key === k || x.key + '_aktiv' === k);
    if (d) { if (k.endsWith('_aktiv')) d.on = !!v; else d.time = String(v); }
    else if (k === 'aktiv') n.on = !!v;
    else if (k === 'nattlampe') n.night_light = !!v;
    else if (k === 'vekk_person') n.wake_person = !!v;
    else if (k === 'bare_hvis_sover') n.only_if_asleep = !!v;
    else if (k === 'fade_opp' && n.fade) n.fade = { ...n.fade, value: Number(v) };
    else if (k === 'av_etter' && n.off_after) n.off_after = { ...n.off_after, value: Number(v) };
  }
  return n;
}
const wakeErr = signal('');
async function setWake(id: string, ch: Record<string, unknown>): Promise<void> {
  const cur = wakeData.value; wakeW = Date.now() + 1500; wakeErr.value = '';
  if (cur) wakeData.value = { ...cur, alarms: cur.alarms.map((a) => (a.id === id ? wakePatch(a, ch) : a)) };
  try {
    const r = await fetch(here() + '/api/touch/wake', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, set: ch }) });
    const j = await r.json() as WakeData;
    wakeW = Date.now();
    if (r.ok && j.ok) wakeData.value = j; else { wakeErr.value = j.error || 'Home Assistant svarte ikke'; wakeW = 0; void loadWake(); }
  } catch { wakeErr.value = 'Får ikke kontakt med enheten'; wakeW = 0; }
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
  const S = settings.value, h = new Date(now.value).getHours(), m = S.tNightMode ?? (S.tNight ? 1 : 2), a = S.tNStart ?? 22, b = S.tNEnd ?? 7;
  return m === 3 || (m === 1 && (a > b ? h >= a || h < b : h >= a && h < b)) || (m === 2 && !!dev().night?.on);
}
// Bakgrunnslys: fullt når skjermen er i bruk, dempet i standby og om natten (skjermer uten styrbart lys overser dette)
let blLast = -1;
function backlight(): void {
  const n = nightNow(), full = Math.max(20, Math.min(100, settings.value.tBright ?? 100));
  // nattmodus: skjermen av i standby (et trykk vekker den, dempet); ellers som valgt under «I standby»
  const ti = settings.value.tIdle ?? 0;
  const lvl = idle.value ? (ti === 2 || n ? 0 : Math.min(ti >= 3 ? 60 : 30, full)) : n ? Math.min(25, full) : full;   // fjord-videoen trenger litt mer lys
  if (lvl !== blLast) {
    blLast = lvl;
    if (TABLET) { try { TABLET.setBrightness(lvl); } catch { /* eldre app */ } }
    else void postAt('', '/api/touch/backlight', { level: lvl }).catch(() => undefined);
  }
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
const saverOpen = signal(false);

// Fotoskjermsparer (pi/skjold_foto.py): Unsplash og dagens bilde (Wikimedia Commons + NASA), hentet av enheten.
interface FotoBilde { url: string; title: string; credit: string; sted?: string; source: string }
interface FotoCfg { foto_kilder: 'dagens' | 'unsplash' | 'begge'; unsplash_key: string; unsplash_tema: string }
const fotoCfg = signal<FotoCfg | null>(null);
function hentFotoCfg(): void { getAt<FotoCfg>('', '/api/touch').then((r) => { fotoCfg.value = r; }).catch(() => {}); }
function lagreFoto(b: Partial<FotoCfg>): void {
  if (fotoCfg.value) fotoCfg.value = { ...fotoCfg.value, ...b };
  void postAt('', '/api/touch', b).then(hentFotoCfg);
}
const FOTO_TEMA: [string, string][] = [['nature', 'Natur'], ['landscape', 'Landskap'], ['mountains', 'Fjell'], ['ocean', 'Hav'], ['norway', 'Norge'], ['architecture', 'Arkitektur'], ['night sky', 'Nattehimmel'], ['', 'Alt']];
const fotoTekst = signal(false);   // skjermtastaturet for Unsplash-nøkkelen

function FotoSaver({ clock, dateTxt }: { clock: string; dateTxt: string }) {
  const [liste, setListe] = useState<FotoBilde[]>([]), [feil, setFeil] = useState('');
  const [i, setI] = useState(0), [vis, setVis] = useState<[FotoBilde | null, FotoBilde | null]>([null, null]), [lag, setLag] = useState(0);
  const s = status.value, nx = nextAlarm();
  useEffect(() => {
    const hent = () => getAt<{ items: FotoBilde[]; feil: string }>('', '/api/touch/foto').then((r) => {
      const l = [...r.items]; for (let k = l.length - 1; k > 0; k--) { const j = Math.floor(Math.random() * (k + 1)); [l[k], l[j]] = [l[j]!, l[k]!]; }
      setListe(l); setFeil(r.feil);
    }).catch(() => setFeil('Fikk ikke hentet bilder'));
    hent();
    const t = window.setInterval(hent, 2 * 3600 * 1000);
    return () => window.clearInterval(t);
  }, []);
  // nytt bilde hvert 40. sekund: last det ferdig før det tones inn over det forrige (2,5 s)
  useEffect(() => {
    if (!liste.length) return;
    let av = false;
    const vis1 = (n: number) => {
      const b = liste[n % liste.length]!, img = new Image();
      img.onload = () => { if (av) return; setVis((v) => (lag === 0 ? [v[0], b] : [b, v[1]])); setLag((x) => 1 - x); };
      img.onerror = () => { if (!av) setI((x) => x + 1); };
      img.src = b.url;
    };
    vis1(i);
    const t = window.setTimeout(() => setI((x) => x + 1), 40000);
    return () => { av = true; window.clearTimeout(t); };
  }, [liste, i]);
  const nå = vis[lag === 1 ? 1 : 0];
  const bilde = (b: FotoBilde | null, på: boolean, k: number) => b && (
    <div key={b.url + k} style={`position:absolute;inset:0;opacity:${på ? 1 : 0};transition:opacity 2.5s ease`}>
      <img src={b.url} alt="" style={`position:absolute;inset:0;width:100%;height:100%;object-fit:cover;animation:${på ? 'fotozoom 42s linear both' : 'none'}`} />
    </div>);
  return <>
    <div style="position:absolute;inset:0;background:#000">{bilde(vis[0], lag === 0, 0)}{bilde(vis[1], lag === 1, 1)}</div>
    <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25) 0%,rgba(0,0,0,0) 25%,rgba(0,0,0,0) 55%,rgba(0,0,0,.7) 100%)" />
    <div style="position:absolute;left:36px;right:36px;bottom:30px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px">
      <span style="display:flex;flex-direction:column;gap:4px;text-align:left;flex-shrink:0">
        <span style="font-size:64px;font-weight:300;letter-spacing:-.02em;color:#f2f2ee;line-height:1;text-shadow:0 2px 18px rgba(0,0,0,.5)">{clock}</span>
        <span style="font-size:15px;color:#e4e4df;text-shadow:0 1px 8px rgba(0,0,0,.6)">{dateTxt}</span>
        {!!s?.playing && <span style="margin-top:4px;font-size:13px;color:#f2f2ee;max-width:380px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 8px rgba(0,0,0,.6)">{[s?.artist, s?.title || s?.station].filter(Boolean).join(' – ')}</span>}
        {nx && <span style={`font-family:${MONO};font-size:11px;letter-spacing:.12em;color:#f0c46a`}>ALARM {nx.time}</span>}
      </span>
      <span style="display:flex;flex-direction:column;align-items:flex-end;gap:3px;min-width:0;max-width:380px;text-align:right;text-shadow:0 1px 8px rgba(0,0,0,.7)">
        {!!nå?.title && <span style="font-size:13px;color:#f2f2ee;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">{nå.title}{nå.sted ? ' · ' + nå.sted : ''}</span>}
        {!!nå && <span style="font-size:11.5px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">Foto: {nå.credit}</span>}
        {!nå && <span style="font-size:13px;color:#8b8b86">{feil || 'Henter bilder …'}</span>}
      </span>
    </div>
  </>;
}

/** Valgene for Foto-skjermspareren: kilde, Unsplash-nøkkel og tema. */
function FotoValg() {
  useEffect(() => { hentFotoCfg(); }, []);
  const c = fotoCfg.value, nøkkel = useTekst(80);
  if (!c) return null;
  const pill = (på: boolean) => `height:34px;padding:0 12px;border-radius:9px;border:none;background:${på ? '#2a2a2c' : 'transparent'};color:${på ? '#f2f2ee' : '#8b8b86'};font-size:12px;font-weight:600;white-space:nowrap`;
  const box = 'display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426;align-items:center';
  const unsplash = c.foto_kilder !== 'dagens', ti = Math.max(0, FOTO_TEMA.findIndex(([k]) => k === c.unsplash_tema));
  if (fotoTekst.value) return (
    <div style="position:absolute;inset:0;z-index:9;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 20px">
        <span style="font-size:15px;font-weight:600">Unsplash-nøkkel («Access Key»)</span>
        <span style="font-size:12px;color:#8b8b86;line-height:1.4">Lag en gratis app på unsplash.com/developers og skriv inn Access Key her. Den lagres bare på denne enheten.</span>
        <div style="display:flex;align-items:center;height:48px;border-radius:12px;border:1px solid #2e2e30;background:#141415;padding:0 14px"><TekstFelt t={nøkkel} tom="Access Key" size={15} /></div>
      </div>
      <Keyboard enter="Lagre" onKey={nøkkel.inn} onBack={nøkkel.slett} onFlytt={nøkkel.flytt} onEnter={() => { if (nøkkel.v.trim()) lagreFoto({ unsplash_key: nøkkel.v.trim() }); fotoTekst.value = false; }} />
    </div>);
  return (
    <div style="display:flex;flex-direction:column;gap:8px;padding:0 16px 12px">
      <div style="display:flex;align-items:center;gap:10px">
        <span style="flex:1;font-size:13px;font-weight:600">Bilder fra</span>
        <div style={box}>{([['dagens', 'Dagens bilde'], ['unsplash', 'Unsplash'], ['begge', 'Begge']] as const).map(([k, n]) => <button key={k} onClick={() => lagreFoto({ foto_kilder: k })} style={pill(c.foto_kilder === k)}>{n}</button>)}</div>
      </div>
      {unsplash && <div style="display:flex;align-items:center;gap:10px">
        <span style="flex:1;font-size:12px;color:#8b8b86">{c.unsplash_key ? 'Unsplash-nøkkel lagret' : 'Unsplash trenger en gratis nøkkel'}</span>
        <div style={box}>
          <button onClick={() => { fotoTekst.value = true; }} style={pill(!c.unsplash_key)}>{c.unsplash_key ? 'Bytt nøkkel' : 'Skriv inn nøkkel'}</button>
          <button onClick={() => lagreFoto({ unsplash_tema: FOTO_TEMA[(ti + 1) % FOTO_TEMA.length]![0] })} style={pill(false)}>Tema: {FOTO_TEMA[ti]![1]}</button>
        </div>
      </div>}
    </div>);
}

/** Velg skjermsparer med forhåndsvisning, og start den med en gang. */
function SaverSheet() {
  const cur = settings.value.tIdle ?? 0;
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 15000); return () => clearInterval(t); }, []);
  const d = new Date(), hhmm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const vid = (cover: boolean) => <video autoplay muted loop playsInline style={`position:absolute;${cover ? 'inset:0;width:100%;height:100%;object-fit:cover' : 'left:0;right:0;top:50%;transform:translateY(-50%);width:100%;height:auto'}`}><source src="./media/fjord.mp4" type="video/mp4" /><source src="./media/fjord.webm" type="video/webm" /></video>;
  const preview = (i: number) => i === 0 ? <span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:300;color:#f2f2ee;letter-spacing:.02em">{hhmm}</span>
    : i === 1 ? <span style={`position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:58%;aspect-ratio:1;border-radius:8px;background:${local.value?.playing ? artOf(local.value) : 'linear-gradient(135deg,#7a5c26,#2a2a2c)'}`} />
    : i === 2 ? <span style={`position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#4a4a47`}>AV</span>
    : i === 5 ? <span style="position:absolute;inset:0;background:linear-gradient(160deg,#2c4a5e 0%,#7a8f6a 55%,#c9a46a 100%)"><span style="position:absolute;left:8px;bottom:6px;font-size:13px;font-weight:300;color:#fff">{hhmm}</span></span>
    : vid(i === 4);
  const pick = (i: number) => setSetting('tIdle', i);
  return (
    <Sheet title="Skjermsparer" kicker="VISES NÅR SKJERMEN HVILER" onClose={() => { saverOpen.value = false; fotoTekst.value = false; }} height={cur === 5 ? 420 : 330}>
      <div style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;padding:6px 16px 12px">
        {TOUCH_IDLE.map((n, i) => { const on = i === cur; return (
          <button key={n} onClick={() => pick(i)} aria-pressed={on} style="border:none;background:none;padding:0;display:flex;flex-direction:column;gap:7px;min-width:0;text-align:left">
            <div style={`position:relative;width:100%;aspect-ratio:5/3;border-radius:10px;overflow:hidden;background:#050505;box-shadow:0 0 0 ${on ? '2px #f0c46a' : '1px #2e2e30'}`}>{preview(i)}</div>
            <span style={`font-size:12.5px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{n}</span>
          </button>); })}
      </div>
      {cur === 5 && <FotoValg />}
      <div style="display:flex;gap:10px;align-items:center;padding:0 16px 14px">
        <button onClick={() => setSetting('tTips', settings.value.tTips === false)} aria-pressed={settings.value.tTips !== false} style="flex:1;min-width:0;border:none;background:none;padding:0;display:flex;align-items:center;gap:10px;text-align:left">
          <span style={`width:40px;height:24px;border-radius:12px;background:${settings.value.tTips !== false ? '#f0c46a' : '#3a3a3c'};position:relative;flex-shrink:0;transition:background .2s`}><i style={`position:absolute;top:3px;left:${settings.value.tTips !== false ? 19 : 3}px;width:18px;height:18px;border-radius:9px;background:#fff;transition:left .2s`} /></span>
          <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:13px;font-weight:600;color:#f2f2ee">Forslag på skjermspareren</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Radiokanalen du pleier å høre på nå, og nye podkastepisoder</span></span>
        </button>
        <button onClick={() => { saverOpen.value = false; goIdle(); }} style="height:44px;padding:0 20px;border-radius:22px;border:none;background:#f2f2ee;color:#0b0b0c;font-size:13.5px;font-weight:600;white-space:nowrap">Start nå</button>
      </div>
    </Sheet>
  );
}

function goIdle(): void { idle.value = true; idleOp.value = 0; setTimeout(() => { idleOp.value = 1; }, 30); backlight(); }
function wake(): void { lastAct = Date.now(); if (idle.value) { idle.value = false; backlight(); sluk = Date.now() + 700; } }
// Trykket som vekker skjermen skal bare vekke: standby-laget forsvinner allerede ved pointerdown, så uten dette landet
// pointerup/click på knappen som lå bak (f.eks. en radiostasjon som byttet kanal).
let sluk = 0;
const iTips = (e: Event) => !!(e.target as Element | null)?.closest?.('[data-ss-tip]');   // forslagene på skjermspareren kan trykkes
const slukk = (e: Event) => { if ((idle.value || Date.now() < sluk) && !iTips(e)) { e.stopPropagation(); e.preventDefault(); } };
for (const t of ['pointerup', 'click', 'mouseup', 'touchend']) addEventListener(t, slukk, { capture: true, passive: false });

// Bevegelser på skjermspareren (skjermen blir stående i standby): to fingre sveip ← neste / → forrige, dobbelttrykk =
// spill/pause, ett trykk = vekk. Alt i skjermspareren svelges, så ingenting bak den trykkes.
const gestTxt = signal('');
const gest = { ptr: new Map<number, { x0: number; y0: number; x: number; y: number }>(), maks: 0, t0: 0, sisteTrykk: 0, vekkT: 0, gT: 0 };
function gestVis(t: string): void { gestTxt.value = t; clearTimeout(gest.gT); gest.gT = window.setTimeout(() => { gestTxt.value = ''; }, 1100); }
addEventListener('pointerdown', (e) => {
  if (idle.value && !iTips(e)) {
    e.stopPropagation(); e.preventDefault();
    if (!gest.ptr.size) { gest.maks = 0; gest.t0 = Date.now(); }
    gest.ptr.set(e.pointerId, { x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY });
    gest.maks = Math.max(gest.maks, gest.ptr.size);
  }
  lastAct = Date.now();
}, { capture: true, passive: false });
addEventListener('pointermove', (e) => { const p = gest.ptr.get(e.pointerId); if (p) { p.x = e.clientX; p.y = e.clientY; } }, { capture: true });
const gestSlutt = (e: PointerEvent) => {
  const p = gest.ptr.get(e.pointerId); if (!p) return;
  p.x = e.clientX; p.y = e.clientY;
  if (gest.ptr.size > 1) { (p as { ferdig?: boolean }).ferdig = true; if ([...gest.ptr.values()].some((q) => !(q as { ferdig?: boolean }).ferdig)) return; }
  const alle = [...gest.ptr.values()]; gest.ptr.clear();
  const dx = alle.reduce((a, q) => a + q.x - q.x0, 0) / alle.length, dy = alle.reduce((a, q) => a + q.y - q.y0, 0) / alle.length;
  if (!idle.value) return;
  if (gest.maks >= 2 && Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.3) {
    clearTimeout(gest.vekkT); gest.sisteTrykk = 0;
    if (dx < 0) { void api.transport('next').catch(() => {}); gestVis(status.value?.subwave_admin ? 'Hopper over låten ›' : 'Neste låt ›'); } else { void api.transport('previous').catch(() => {}); gestVis('‹ Forrige låt'); }
    return;
  }
  if (gest.maks >= 2 || Math.hypot(dx, dy) > 24) return;   // annen bevegelse: ingenting
  const nå = Date.now();
  if (nå - gest.sisteTrykk < 330) {   // dobbelttrykk
    clearTimeout(gest.vekkT); gest.sisteTrykk = 0;
    const spiller = !!status.value?.playing; playPause(); gestVis(spiller ? 'Pause' : 'Spiller');
    return;
  }
  gest.sisteTrykk = nå;
  clearTimeout(gest.vekkT); gest.vekkT = window.setTimeout(() => { gest.sisteTrykk = 0; wake(); }, 340);
};
addEventListener('pointerup', gestSlutt, { capture: true });
addEventListener('pointercancel', (e) => { gest.ptr.delete(e.pointerId); }, { capture: true });

// Volum i skjermspareren: én finger i den øverste centimeteren, dra mot høyre (opp) eller venstre (ned). Volumet følger
// fingeren (hele bredden ≈ 70 trinn) og vises som en linje øverst. Drar du nedover i stedet, kommer hurtigpanelet.
const gestVol = signal<number | null>(null);
const vDrag = { id: -1, x0: 0, y0: 0, v0: 0, aktiv: false, t: 0 };
addEventListener('pointerdown', (e) => {
  if (!idle.value || e.clientY > Q_KANT || vDrag.id >= 0) return;
  Object.assign(vDrag, { id: e.pointerId, x0: e.clientX, y0: e.clientY, v0: status.value?.volume ?? 0, aktiv: false });
}, { capture: true });
addEventListener('pointermove', (e) => {
  if (e.pointerId !== vDrag.id) return;
  const dx = e.clientX - vDrag.x0, dy = e.clientY - vDrag.y0;
  if (!vDrag.aktiv) {
    if (qDrag.aktiv || gest.ptr.size > 1) { vDrag.id = -1; return; }   // hurtigpanel eller tofingersveip
    if (Math.abs(dx) > 12 && Math.abs(dx) > Math.abs(dy) * 1.2) { vDrag.aktiv = true; qDrag.y0 = -1; qDrag.id = -1; }   // ikke hurtigpanelet
    else return;
  }
  const v = Math.max(0, Math.min(100, Math.round(vDrag.v0 + dx / Math.max(320, innerWidth) * 70)));
  if (v !== gestVol.value) { gestVol.value = v; if (Date.now() - vDrag.t > 60) { vDrag.t = Date.now(); setVolume(v); } }
  e.preventDefault();
}, { capture: true, passive: false });
const vSlipp = (e: PointerEvent) => {
  if (e.pointerId !== vDrag.id) return;
  if (vDrag.aktiv && gestVol.value !== null) {
    setVolume(gestVol.value, true); clearTimeout(gest.vekkT); gest.sisteTrykk = 0;
    const v = gestVol.value; window.setTimeout(() => { if (gestVol.value === v) gestVol.value = null; }, 900);
  }
  vDrag.id = -1; vDrag.aktiv = false;
};
addEventListener('pointerup', vSlipp, { capture: true });
addEventListener('pointercancel', vSlipp, { capture: true });
addEventListener('contextmenu', (e) => e.preventDefault());
setInterval(() => {
  now.value = Date.now();
  const ms = (TOUCH_STANDBY_S[settings.value.tStandby] ?? 30) * 1000;
  if (!idle.value && !boot.value.on && !dev().alarm?.ringing && !door.value && !camOpen.value && !wifiOpen.value && !quick.value && !dev().setup_net?.active && !dev().setup_net?.kabel && ms > 0 && Date.now() - lastAct > ms) goIdle();
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
// også lokale adresser (/api/logo?k=… for radiologoene fra enheten), ikke bare http(s)
function artBg(key: string, image?: string, i?: number): string { return image && /^((https?:)?\/\/|\/|data:image\/)/i.test(image) ? art(key, image).bg : grad(key, i); }
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
const BARS = [14, 21, 26, 21, 14];   // Skjold-logoen: 22/33/42/33/22, stolpene henger fra toppen
const ROUND = 'width:48px;height:48px;flex-shrink:0;border-radius:24px;border:1px solid #2e2e30;background:rgba(22,22,23,.7);color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0';
// ---------- Timere: fra Home Assistant Assist («sett en timer på ti minutter») og fra skjermen ----------
interface Timer { id: string; navn: string; total: number; igjen: number; ferdig: boolean; aktiv: boolean; kilde: string }
const timerOpen = signal(false);
const timerKvittert = signal<string[]>([]);   // ferdige timere du har trykket Stopp på (de ryddes på enheten etter 10 min)
const mmss = (s: number) => (s >= 3600 ? Math.floor(s / 3600) + ':' + String(Math.floor((s % 3600) / 60)).padStart(2, '0') : Math.floor(s / 60)) + ':' + String(s % 60).padStart(2, '0');
function useTimere(): Timer[] {
  const [, tikk] = useState(0);
  useEffect(() => { const t = setInterval(() => tikk((n) => n + 1), 1000); return () => clearInterval(t); }, []);
  const l = dev().touch?.timere ?? [], fikk = useRef({ t: Date.now(), l });
  if (fikk.current.l !== l) fikk.current = { t: Date.now(), l };
  const gått = Math.floor((Date.now() - fikk.current.t) / 1000);
  return l.filter((x) => !timerKvittert.value.includes(x.id)).map((x) => { const ig = x.aktiv ? Math.max(0, x.igjen - gått) : x.igjen; return { ...x, igjen: ig, ferdig: x.ferdig || ig === 0 }; });
}
function stoppTimer(id: string): void { timerKvittert.value = [...timerKvittert.value, id]; void postAt('', '/api/touch/timer', { stopp: id }); }
/** Små nedtellinger øverst på skjermen. Trykk for å stoppe. */
function TimerStripe() {
  const l = useTimere().filter((x) => !x.ferdig);
  if (!l.length) return null;
  return <div style="position:absolute;top:8px;left:50%;transform:translateX(-50%);z-index:19;display:flex;gap:8px;pointer-events:auto">
    {l.slice(0, 3).map((x) => <button key={x.id} onClick={() => stoppTimer(x.id)} aria-label={'Stopp timeren ' + (x.navn || '')} style="height:36px;padding:0 14px;border-radius:18px;border:1px solid #3a2e17;background:rgba(28,23,13,.92);color:#f0c46a;display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2.5 2.5M9 2h6" /></svg>
      <span style={`font-family:${MONO}`}>{mmss(x.igjen)}</span>{x.navn && <span style="color:#c9b48a;font-weight:400;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{x.navn}</span>}{!x.aktiv && <span style="color:#8b8b86;font-weight:400">pause</span>}</button>)}
  </div>;
}
/** Tiden er ute: stor beskjed og klokketoner til du trykker Stopp (høyst 2 minutter). */
function TimerFerdig() {
  const l = useTimere().filter((x) => x.ferdig);
  const x = l[0];
  useEffect(() => {
    if (!x) return;
    wake();
    const start = Date.now(), spill = () => { if (Date.now() - start < 120000) spillKlokke(lydProsent(settings.value.tLydP, settings.value.tLyd)); };
    spill(); const t = setInterval(spill, 2600);
    return () => clearInterval(t);
  }, [x?.id]);
  if (!x) return null;
  return (
    <div style="position:absolute;inset:0;z-index:23;background:rgba(6,6,7,.94);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;animation:tinn .3s ease both">
      <svg width="86" height="86" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.4" stroke-linecap="round" class="puls"><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2.5 2.5M9 2h6" /></svg>
      <span style={`font-family:${MONO};font-size:12px;letter-spacing:.16em;color:#f0c46a`}>TIMEREN ER FERDIG · {mmss(x.total)}</span>
      <span style="font-size:40px;font-weight:600;color:#f2f2ee">{x.navn || 'Tiden er ute'}</span>
      <button onClick={() => l.forEach((y) => stoppTimer(y.id))} style="margin-top:10px;height:64px;padding:0 48px;border-radius:32px;border:none;background:#f2f2ee;color:#0b0b0c;font-size:18px;font-weight:600">Stopp</button>
    </div>);
}
/** Ny timer fra skjermen: hurtigvalg og pluss/minus, valgfritt navn. */
function TimerSheet() {
  const [min, setMin] = useState(5);
  const start = (m: number) => { void postAt('', '/api/touch/timer', { start: m * 60 }); timerOpen.value = false; };
  const knapp = (på: boolean) => `height:46px;border-radius:12px;border:1px solid ${på ? '#d9a441' : '#242426'};background:${på ? '#1c170d' : '#141415'};color:${på ? '#f0c46a' : '#f2f2ee'};font-size:15px;font-weight:600`;
  return (
    <Sheet title="Ny timer" kicker="NEDTELLING · ELLER SI «SETT EN TIMER PÅ …»" onClose={() => { timerOpen.value = false; }} height={330}>
      <div style="display:flex;flex-direction:column;gap:12px;padding:6px 16px 14px">
        <div style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px">{[1, 3, 5, 10, 15, 20, 25, 30, 45, 60, 90, 120].map((m) => <button key={m} onClick={() => setMin(m)} style={knapp(m === min)}>{m < 60 ? m + ' min' : m / 60 + ' t'}</button>)}</div>
        <div style="display:flex;align-items:center;gap:12px">
          <button onClick={() => setMin((m) => Math.max(1, m - 1))} style="width:52px;height:52px;border-radius:26px;border:none;background:#242426;color:#f2f2ee;font-size:22px">−</button>
          <span style={`font-family:${MONO};font-size:30px;min-width:120px;text-align:center`}>{mmss(min * 60)}</span>
          <button onClick={() => setMin((m) => Math.min(240, m + 1))} style="width:52px;height:52px;border-radius:26px;border:none;background:#242426;color:#f2f2ee;font-size:22px">+</button>
          <div style="flex:1" />
          <button onClick={() => start(min)} style="height:52px;padding:0 28px;border-radius:26px;border:none;background:#f0c46a;color:#0b0b0c;font-size:15px;font-weight:600">Start</button>
        </div>
      </div>
    </Sheet>);
}
/** Kalender fra Home Assistant på skjermspareren: neste dag med avtaler (høyst to). */
function KalKort({ nede = false }: { nede?: boolean }) {
  const k = dev().home?.cal;
  if (!k?.items?.length || settings.value.tKal === false) return null;
  return <div style={`position:absolute;${nede ? 'right:36px;bottom:110px' : 'right:30px;top:26px'};max-width:300px;padding:12px 16px;border-radius:14px;background:rgba(14,14,15,.62);border:1px solid rgba(255,255,255,.08);display:flex;flex-direction:column;gap:4px;text-align:left;backdrop-filter:blur(8px)`}>
    <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#f0c46a`}>{k.day}</span>
    {k.items.map((t, i) => <span key={i} style={`font-size:${i ? 13 : 15}px;font-weight:${i ? 400 : 600};color:${i ? '#c9c9c4' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{t}</span>)}
  </div>;
}

// ---------- Oppdatering av Skjold-enhetene (denne og de andre på nettet), som i web-UI ----------
interface UpdInfo { current: string | null; latest: string | null; available: boolean; running: boolean; result: string | null; log: string[]; can_update: boolean; error: string | null; channel?: string }
/** Oppdatering: stor versjon øverst (som i web-UI), «Oppdater nå», og de andre Skjold-enhetene under. */
function OppdateringSide() {
  const enheter = [{ base: '', navn: local.value?.name || 'Denne Touch', produkt: 'touch' }, ...peers.value.map((p) => ({ base: p.base, navn: p.navn, produkt: p.produkt }))];
  const [info, setInfo] = useState<Record<string, UpdInfo | 'feil' | undefined>>({});
  const [vis, setVis] = useState(''), [sjekker, setSjekker] = useState(false);
  const hent = (base: string, sjekk = true) => getAt<UpdInfo>(base, '/api/update' + (sjekk ? '' : '?check=0')).then((r) => setInfo((o) => ({ ...o, [base]: r }))).catch(() => setInfo((o) => ({ ...o, [base]: 'feil' })));
  useEffect(() => { enheter.forEach((e) => void hent(e.base)); }, []);
  useEffect(() => {   // følg med mens noen oppdaterer (enheten starter tjenesten på nytt underveis)
    const t = window.setInterval(() => { enheter.forEach((e) => { const i = info[e.base]; if (i && i !== 'feil' && i.running) void hent(e.base, false); }); }, 3000);
    return () => window.clearInterval(t);
  }, [info]);
  const oppdater = (base: string) => { void postAt(base, '/api/update', {}).then(() => window.setTimeout(() => void hent(base, false), 800)); setInfo((o) => { const i = o[base]; return i && i !== 'feil' ? { ...o, [base]: { ...i, running: true } } : o; }); };
  const sjekk = () => { setSjekker(true); void Promise.all(enheter.map((e) => hent(e.base))).finally(() => setSjekker(false)); };
  const meg = info[''], m = meg && meg !== 'feil' ? meg : null;
  const versjon = m ? (m.available ? m.latest : m.current) ?? m.latest ?? '–' : '…';
  const andre = enheter.slice(1);
  const klar = andre.filter((e) => { const i = info[e.base]; return i && i !== 'feil' && i.available && !i.running && i.can_update; });
  const pill = (på: boolean) => `height:36px;padding:0 14px;border-radius:18px;border:none;background:${på ? '#f0c46a' : '#242426'};color:${på ? '#0b0b0c' : '#f2f2ee'};font-size:12.5px;font-weight:600;white-space:nowrap`;
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <span style="font-size:20px;font-weight:600">Oppdatering</span>
      <div class="oppd-helt">
        <button class="rip oppd-sjekk" onClick={sjekk} disabled={sjekker}>{sjekker ? 'Sjekker …' : 'Se etter oppdatering'}</button>
        <b class="oppd-ver">{versjon}</b>
        <span style="font-size:15px;color:#e8e4da">{!m ? (meg === 'feil' ? 'Får ikke kontakt' : 'Sjekker …') : m.running ? 'Oppdaterer …' : m.available ? 'Oppdatering tilgjengelig' : m.error ? m.error : 'Du har nyeste versjon'}</span>
        <span style="font-size:34px;line-height:1;letter-spacing:-.02em"><b style="font-weight:700">Skjold</b><span style="font-weight:300;color:#c9c4b8">OS</span></span>
        <span style="font-size:12.5px;color:#f0c46a">Touch · {m?.channel === 'beta' ? 'betakanal' : 'stabil kanal'}</span>
      </div>
      {m && m.running && <div style="display:flex;flex-direction:column;gap:6px;padding:12px 14px;border-radius:14px;background:#141415;border:1px solid #242426">
        <span style="display:flex;align-items:center;gap:8px;font-size:13px"><i class="caret" style="width:9px;height:9px;border-radius:5px;background:#f0c46a" />Oppdaterer – skjermen starter på nytt når den er ferdig</span>
        <pre style={`margin:0;max-height:90px;overflow:auto;font-family:${MONO};font-size:10px;line-height:1.4;color:#a8a8a3;white-space:pre-wrap`}>{m.log.slice(-6).join('\n')}</pre></div>}
      {m && !m.running && m.available && m.can_update && <div style="display:flex;align-items:center;gap:16px">
        <button class="rip oppd-na" onClick={() => oppdater('')}>Oppdater nå</button>
        <span style="font-size:12.5px;color:#a9a9a3;line-height:1.4">Ca. 2 minutter · Skjold starter på nytt og musikken stopper et øyeblikk</span></div>}
      <div style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415">
        {([['Programvareversjon', m ? 'Du har ' + (m.current ?? '–') : '–'], ['Nyeste versjon', m?.latest ?? '–']] as [string, string][]).map(([n, v], i) => (
          <div key={n} style={`display:flex;align-items:center;min-height:50px;padding:0 16px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'}`}><span style="flex:1;font-size:14px">{n}</span><span style={`font-family:${MONO};font-size:12.5px;color:#c9c9c4`}>{v}</span></div>))}
      </div>
      {andre.length > 0 && <div style="display:flex;align-items:center;justify-content:space-between;margin-top:6px"><span style="font-size:15px;font-weight:600">Andre Skjold-enheter</span>
        {klar.length > 1 && <button onClick={() => klar.forEach((e) => oppdater(e.base))} style={pill(true)}>Oppdater alle ({klar.length})</button>}</div>}
      {andre.map((e) => {
        const i = info[e.base];
        const tekst = i === undefined ? 'Sjekker …' : i === 'feil' ? 'Svarer ikke' : i.running ? 'Oppdaterer … ' + (i.log[i.log.length - 1] ?? '').slice(0, 60)
          : i.available ? 'Ny versjon: ' + (i.latest ?? '') + ' (har ' + (i.current ?? '?') + ')' : i.error ? i.error : 'Oppdatert · ' + (i.current ?? i.latest ?? '');
        return (
          <div key={e.base} style="display:flex;flex-direction:column;gap:6px;padding:10px 12px;border-radius:12px;background:#141415;border:1px solid #242426">
            <div style="display:flex;align-items:center;gap:12px">
              <span style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0">
                <span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e.navn}</span>
                <span style={`font-size:11.5px;color:${i && i !== 'feil' && i.available ? '#f0c46a' : '#8b8b86'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{tekst}</span>
              </span>
              {i && i !== 'feil' && i.running && <span class="caret" style="width:10px;height:10px;border-radius:5px;background:#f0c46a" />}
              {i && i !== 'feil' && !i.running && i.available && i.can_update && <button onClick={() => oppdater(e.base)} style={pill(true)}>Oppdater</button>}
              {i && i !== 'feil' && !!i.log.length && <button onClick={() => setVis(vis === e.base ? '-' : e.base)} style={pill(false)}>{vis === e.base ? 'Skjul logg' : 'Logg'}</button>}
            </div>
            {vis === e.base && i && i !== 'feil' && <pre style={`margin:0;max-height:120px;overflow:auto;font-family:${MONO};font-size:10px;line-height:1.4;color:#a8a8a3;white-space:pre-wrap`}>{i.log.slice(-12).join('\n')}</pre>}
          </div>);
      })}
    </div>
  );
}

// ---------- LP-spiller: trykk på coveret / radiologoen på Spiller ----------
const lpOpen = signal(false);
effect(() => { if (scr.value !== 'now' || idle.value) lpOpen.value = false; });
/** Stort cover som et platecover med en vinylplate som glir ut og snurrer mens det spilles, og en tonearm som legger
 *  seg på plata. Trykk hvor som helst (utenom knappene) for å lukke. */
function LpSpiller() {
  const s = status.value, bg = artOf(s), spiller = !!s?.playing;
  const [pos, setPos] = useState(s?.position ?? 0);
  useEffect(() => { setPos(s?.position ?? 0); }, [s?.position, s?.title]);
  useEffect(() => { const t = setInterval(() => { if (status.value?.playing) setPos((p) => p + 1); }, 1000); return () => clearInterval(t); }, []);
  const dur = s?.duration ?? 0, andel = dur > 0 ? Math.min(1, pos / dur) : 0;
  const tid = (x: number) => Math.floor(x / 60) + ':' + String(Math.floor(x % 60)).padStart(2, '0');
  const C = 'min(74vh, 44vw)';                      // coverets side
  const knapp = 'width:46px;height:46px;border-radius:23px;border:none;background:rgba(255,255,255,.08);display:flex;align-items:center;justify-content:center;padding:0';
  const stopp = (e: Event) => e.stopPropagation();
  return (
    <div class="lp-inn" onClick={() => { lpOpen.value = false; }} style="position:absolute;inset:0;z-index:21;background:#060607;overflow:hidden">
      <div style={`position:absolute;inset:-80px;background:${bg};filter:blur(70px) saturate(1.3);opacity:.42`} />
      <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(0,0,0,0) 0%,rgba(0,0,0,.55) 70%,rgba(0,0,0,.85) 100%)" />
      {/* plata: bak coveret, glir ut mot høyre */}
      <div class={'lp-plate' + (spiller ? ' lp-ut' : '')} style={`position:absolute;top:50%;left:4vw;width:${C};height:${C};transform:translate(${spiller ? '40%' : '16%'},-50%);transition:transform 1.1s cubic-bezier(.2,.8,.2,1)`}>
        <div style={`position:absolute;inset:2%;border-radius:50%;animation:lpspinn 1.8s linear infinite;animation-play-state:${spiller ? 'running' : 'paused'};
          background:radial-gradient(circle,#0b0b0c 0 17%,transparent 17.2%),repeating-radial-gradient(circle,#141416 0 1px,#0c0c0d 1px 2.2px);box-shadow:0 20px 60px rgba(0,0,0,.7)`}>
          <div style={`position:absolute;inset:34%;border-radius:50%;background:${bg};background-size:cover;box-shadow:inset 0 0 0 2px rgba(0,0,0,.4)`} />
          <div style="position:absolute;left:50%;top:50%;width:3.2%;height:3.2%;margin:-1.6% 0 0 -1.6%;border-radius:50%;background:#060607" />
        </div>
        {/* lysrefleks som står stille mens plata går rundt */}
        <div style="position:absolute;inset:2%;border-radius:50%;background:conic-gradient(from 30deg,rgba(255,255,255,0) 0deg,rgba(255,255,255,.07) 30deg,rgba(255,255,255,0) 60deg,rgba(255,255,255,0) 180deg,rgba(255,255,255,.05) 210deg,rgba(255,255,255,0) 240deg);pointer-events:none" />
      </div>
      {/* tonearmen */}
      <svg viewBox="0 0 100 160" style={`position:absolute;top:5vh;left:calc(4vw + min(74vh, 44vw) * 1.12);height:min(52vh, 30vw);transform-origin:70% 12%;transform:rotate(${spiller ? 24 : 0}deg);transition:transform 1.4s cubic-bezier(.3,.7,.2,1) ${spiller ? '.6s' : '0s'};filter:drop-shadow(0 8px 10px rgba(0,0,0,.6))`}>
        <circle cx="70" cy="18" r="13" fill="#2a2a2c" stroke="#4a4a4e" stroke-width="2" /><circle cx="70" cy="18" r="5" fill="#8b8b86" />
        <path d="M70 18 L62 120 L48 140" fill="none" stroke="#c9c9c4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
        <rect x="38" y="134" width="16" height="22" rx="3" transform="rotate(35 46 145)" fill="#2a2a2c" stroke="#c9c9c4" stroke-width="2" />
      </svg>
      {/* coveret */}
      <div style={`position:absolute;top:50%;left:4vw;width:${C};height:${C};transform:translateY(-50%);border-radius:6px;background:${bg};box-shadow:0 30px 80px rgba(0,0,0,.75),0 0 0 1px rgba(255,255,255,.06)`}>
        <div style="position:absolute;inset:0;border-radius:6px;background:linear-gradient(115deg,rgba(255,255,255,.10) 0%,rgba(255,255,255,0) 35%)" />
      </div>
      {/* tekst og knapper */}
      <div onClick={stopp} style="position:absolute;right:3vw;bottom:7vh;width:min(23vw,260px);display:flex;flex-direction:column;gap:5px;text-align:left">
        <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.16em;color:#f0c46a`}>{srcName(s).toUpperCase()}</span>
        <span style="font-size:22px;font-weight:600;line-height:1.12;color:#f2f2ee;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">{s?.title || s?.station || ''}</span>
        <span style="font-size:16px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s?.artist ?? ''}</span>
        {!!s?.album && <span style="font-size:12.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.album}</span>}
        {dur > 0 && <div style="margin-top:10px;display:flex;flex-direction:column;gap:4px">
          <div style="height:3px;border-radius:2px;background:rgba(255,255,255,.14)"><div style={`width:${(andel * 100).toFixed(2)}%;height:100%;border-radius:2px;background:#f2f2ee`} /></div>
          <div style={`display:flex;justify-content:space-between;font-family:${MONO};font-size:10.5px;color:#8b8b86`}><span>{tid(Math.min(pos, dur))}</span><span>{tid(dur)}</span></div>
        </div>}
        <div style="margin-top:8px;display:flex;align-items:center;gap:8px">
          <button onClick={() => void act(() => api.transport('previous'))} aria-label="Forrige" style={knapp}><svg width="22" height="22" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M19 18.5v-13a.8.8 0 0 0-1.25-.66L9 10.9V6a1 1 0 0 0-2 0v12a1 1 0 0 0 2 0v-4.9l8.75 6.06A.8.8 0 0 0 19 18.5z" /></svg></button>
          <button onClick={playPause} aria-label={spiller ? 'Pause' : 'Spill'} style="width:58px;height:58px;border-radius:29px;border:none;background:#f2f2ee;display:flex;align-items:center;justify-content:center;padding:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#0b0b0c"><path d={spiller ? PAUSE_D : PLAY_D} /></svg></button>
          <button onClick={() => void act(() => api.transport('next'))} aria-label="Neste" style={knapp}><svg width="22" height="22" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M5 18.5v-13a.8.8 0 0 1 1.25-.66L15 10.9V6a1 1 0 0 1 2 0v12a1 1 0 0 1-2 0v-4.9l-8.75 6.06A.8.8 0 0 1 5 18.5z" /></svg></button>
        </div>
      </div>
      <span style={`position:absolute;right:4vw;top:4vh;font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#4a4a47`}>TRYKK FOR Å LUKKE</span>
    </div>
  );
}

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
        {/* toner helt ut mot topplinja (ingen kant), og mørkner nedover så teksten står tydelig */}
        <div style="position:absolute;inset:0;background:linear-gradient(180deg,#0b0b0c 0%,rgba(11,11,12,.72) 14%,rgba(11,11,12,.5) 34%,rgba(11,11,12,.94) 100%)" />
      </>}
      <div style={`position:relative;height:100%;box-sizing:border-box;display:grid;grid-template-columns:${COVER} minmax(0,1fr);grid-template-rows:${COVER} auto auto;column-gap:24px;row-gap:4px;padding:14px 22px 8px;align-content:center`}>
        <div onClick={() => { if (has) lpOpen.value = true; }} role={has ? 'button' : undefined} aria-label={has ? 'Vis som plate' : undefined} style={`position:relative;width:${COVER};height:${COVER};border-radius:14px;background:${has ? bg : '#141415'};box-shadow:0 18px 44px rgba(0,0,0,.55);overflow:hidden;display:flex;align-items:center;justify-content:center;cursor:${has ? 'pointer' : 'default'}`}>
          {!has && <div style="display:flex;gap:6px;align-items:flex-start;height:60px;opacity:.5">{BARS.map((h, i) => <div key={i} style={`width:9px;height:${h * 2.2}px;border-radius:5px;background:${i === 2 ? '#7a5c26' : '#3a3a37'}`} />)}</div>}
          {has && <span style={`position:absolute;left:10px;bottom:10px;height:22px;padding:0 8px;border-radius:6px;background:rgba(0,0,0,.55);font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#f2f2ee;display:flex;align-items:center`}>{srcName(s)}</span>}
        </div>
        <div style="display:flex;flex-direction:column;min-width:0;padding-top:2px">
          <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#f0c46a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{kicker}</span>
          <span style="margin-top:10px;font-size:28px;font-weight:600;line-height:1.12;letter-spacing:-.01em;text-wrap:pretty;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">{title}</span>
          {has && !!s?.artist && ndConfigured()
            ? <button class="flat" onClick={() => { artistSide.value = s.artist ?? ''; }} aria-label={'Vis artisten ' + s.artist} style="margin-top:6px;align-self:flex-start;max-width:100%;height:auto;border:none;background:none;padding:0;font-size:17px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left;display:flex;align-items:center;gap:6px">
                <span style="overflow:hidden;text-overflow:ellipsis;text-decoration:underline;text-decoration-color:#4a4a4e;text-underline-offset:4px">{s.artist}</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M9 6l6 6-6 6" /></svg></button>
            : <span style="margin-top:6px;font-size:17px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{has ? s?.artist ?? '' : off ? 'Trykk på spill for å slå på' : 'Velg noe å høre på'}</span>}
          <span style="margin-top:2px;font-size:13px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{has ? s?.album ?? '' : ''}</span>
          <div style="flex:1" />
          <div style="display:flex;align-items:center;gap:6px">
            <button onClick={() => void act(() => api.transport('previous'))} aria-label="Forrige" style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M19 18.5v-13a.8.8 0 0 0-1.25-.66L9 10.9V6a1 1 0 0 0-2 0v12a1 1 0 0 0 2 0v-4.9l8.75 6.06A.8.8 0 0 0 19 18.5z" /></svg></button>
            <button onClick={playPause} aria-label={s?.playing ? 'Pause' : 'Spill'} style="width:72px;height:72px;flex-shrink:0;border-radius:36px;border:none;background:#f2f2ee;display:flex;align-items:center;justify-content:center;padding:0;box-shadow:0 8px 24px rgba(0,0,0,.4)"><svg width="28" height="28" viewBox="0 0 24 24" fill="#0b0b0c"><path d={s?.playing ? PAUSE_D : PLAY_D} /></svg></button>
            <button onClick={() => void act(() => api.transport('next'))} aria-label={s?.subwave_admin ? 'Hopp over låten' : 'Neste'} style="width:56px;height:56px;border-radius:28px;border:none;background:transparent;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="26" height="26" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z" /></svg></button>
            <div style="flex:1" />
            {!has && <button onClick={() => { lib.value = 2; scr.value = 'lib'; }} style="height:48px;padding:0 18px;border-radius:24px;border:1px solid #2e2e30;background:rgba(22,22,23,.7);font-size:13px;font-weight:600">Radio</button>}
            {has && !!s?.artist && !!s?.title && <button onClick={() => { lyricsOpen.value = true; }} aria-label="Sangtekst" style={ROUND}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 6h16M4 10h16M4 14h10M4 18h7" /></svg></button>}
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
          <Slider label="Volum" value={v} color={muted ? '#6b6b67' : '#f0c46a'} onInput={(n) => { volHakk(n); setVol(n); setVolume(Math.round(n)); }} onCommit={(n) => { setVol(null); setVolume(Math.round(n), true); }} />
          <span style={`font-family:${MONO};font-size:13px;width:32px;text-align:right;color:${muted ? '#6b6b67' : '#f2f2ee'}`}>{v}</span>
        </div>
      </div>
    </section>
  );
}

/** Sangtekst (lrclib.net via /api/lyrics) – synkronisert linje for linje når teksten har tidskoder, som i SUB/WAVE. */
function LyricsSheet() {
  const s = status.value, key = (s?.artist ?? '') + '|' + (s?.title ?? '');
  const [l, setL] = useState<Lyrics | null>(null), [pos, setPos] = useState(s?.position ?? 0);
  useEffect(() => { setL(null); api.lyrics().then(setL).catch(() => setL({ enabled: true, found: false, error: 'Får ikke kontakt med Skjold' })); }, [key]);
  useEffect(() => { setPos(status.value?.position ?? 0); }, [s?.position, s?.title]);
  useEffect(() => { const t = setInterval(() => { if (status.value?.playing) setPos((p) => p + 0.5); }, 500); return () => clearInterval(t); }, []);
  const ref = useRef<HTMLDivElement>(null), syn = l?.synced ?? [];
  let cur = -1; for (let i = 0; i < syn.length; i++) if (syn[i]!.t <= pos + 0.3) cur = i;
  useEffect(() => { (ref.current?.querySelector('[data-cur="1"]') as HTMLElement | null)?.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, [cur, l]);
  const msg = !l ? 'Henter tekst …' : !l.enabled ? 'Slå på pluginen Sangtekster i appen for å se teksten her.' : !l.found ? (l.instrumental ? 'Instrumental låt.' : l.error ? 'Fant ikke teksten (' + l.error + ').' : 'Fant ingen tekst for denne låten.') : '';
  return (
    <Sheet title={s?.title ?? ''} kicker={(s?.artist ?? '').toUpperCase()} onClose={() => { lyricsOpen.value = false; }} height={430}>
      <div ref={ref} style="flex:1;min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y;display:flex;flex-direction:column;gap:12px;padding:6px 22px 20px">
        {msg ? <span style="font-size:15px;color:#a9a9a3;padding:20px 0">{msg}</span>
          : syn.length ? syn.map((x, i) => <span key={i} data-cur={i === cur ? '1' : '0'} style={`font-size:${i === cur ? 26 : 20}px;font-weight:${i === cur ? 700 : 500};line-height:1.25;color:${i === cur ? '#f2f2ee' : i < cur ? '#5a5a56' : '#9a9a94'};transition:all .25s`}>{x.l || '♪'}</span>)
          : <pre style="margin:0;white-space:pre-wrap;font-family:inherit;font-size:18px;line-height:1.55;color:#c9c9c4">{l?.plain}</pre>}
        {!msg && <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#5a5a56`}>TEKST FRA LRCLIB.NET</span>}
      </div>
    </Sheet>
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
          <button key={f.n} onClick={() => { playFav(f); }} style={`flex-shrink:0;height:52px;max-width:220px;border-radius:26px;border:1px solid ${on ? '#d9a441' : '#242426'};background:${on ? '#1d1814' : '#141415'};display:flex;align-items:center;gap:10px;padding:0 16px 0 7px`}>
            {/* NRK-logoene er brede ordmerker på mørk, firkantet bakgrunn: vis dem brede og uten skive (bakgrunnen blandes bort) */}
            {/nrk/i.test(f.image || f.logo || '')
              ? <div style={`width:62px;height:38px;margin-left:8px;flex-shrink:0;mix-blend-mode:lighten;background:url("${(f.image || f.logo || '').replace(/"/g, '')}") center / ${/static\.nrk\.no/.test(f.image || f.logo || '') ? 'contain' : '74px auto'} no-repeat`} />
              : <div style={`width:38px;height:38px;border-radius:19px;background:${artBg(f.title, f.image || f.logo, i)};flex-shrink:0`} />}
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

/** SUB/WAVE-stasjonene huskes fra forrige gang og hentes ved oppstart, så fanen står klar sammen med de andre i Bibliotek. */
type SwT = { i: number; name: string; image?: string };
const swT = signal<SwT[]>((() => { try { return JSON.parse(localStorage.getItem('skjold-touch-sw') || '[]') as SwT[]; } catch { return []; } })());
const swNowT = signal<number | null>(null);
function loadSwT(): void {
  api.subwave(true).then((r) => {
    const l = ((r.configured ? r.stations ?? [] : []) as SwT[]).map((x) => ({ i: x.i, name: x.name, image: x.image }));
    swNowT.value = r.playing_station ?? null;
    if (JSON.stringify(l) === JSON.stringify(swT.value)) return;
    swT.value = l;
    try { localStorage.setItem('skjold-touch-sw', JSON.stringify(l)); } catch { /* full lagring: hentes på nytt neste gang */ }
  }).catch(() => {});
}

/** Podkaster på Touch: favorittene (lagt til i appen eller web-UI) og episodene deres. */
const podTouch = signal<PodShow | null>(null);
let podFraSok = false;   // podkasten ble åpnet fra søket: «Tilbake» går tilbake dit
const pmin = (s: number) => (s >= 3600 ? Math.floor(s / 3600) + ' t ' : '') + Math.round((s % 3600) / 60) + ' min';
async function playPodTouch(e: PodEpisode, show?: PodShow): Promise<void> {
  try {
    if (e.nrk) await api.nrkPlay({ id: e.id, title: e.title, series: e.show, image: e.image, duration: e.duration, podcast: e.podcast });
    else await api.podPlay({ id: e.id, url: e.url ?? '', title: e.title, show: show?.title ?? e.show, image: e.image || show?.image, duration: e.duration, pid: show?.id ?? e.pid });
    scr.value = 'now';
  } catch { /* vises ikke: Touch har ingen feilmelding her */ }
}
function PodEpisodes({ s }: { s: PodShow }) {
  const [d, setD] = useState<PodEpisode[] | null>(null), [err, setErr] = useState('');
  useEffect(() => { setD(null); setErr(''); api.podShow(s.id).then((r) => setD(r.episodes)).catch((e) => { setErr(e instanceof Error ? e.message : String(e)); setD([]); }); }, [s.id]);
  return (
    <div style="flex:1;min-height:0;display:grid;grid-template-columns:150px minmax(0,1fr);gap:20px">
      <div style="display:flex;flex-direction:column;gap:8px;min-width:0;min-height:0;overflow:hidden">
        <button onClick={() => { podTouch.value = null; if (podFraSok) { podFraSok = false; sokHusk.fraSok = true; searchOpen.value = true; } }} style="height:40px;border-radius:20px;border:1px solid #2e2e30;background:#161617;font-size:13px;font-weight:600;flex-shrink:0">‹ Tilbake</button>
        <div style={`width:150px;height:150px;flex-shrink:0;border-radius:12px;background:${artBg(s.title, s.image)}`} />
        <span style="font-size:15px;font-weight:600;line-height:1.2;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{s.title}</span>
        <span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.author}</span>
      </div>
      <div style="min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y;display:flex;flex-direction:column;gap:8px;padding-bottom:14px">
        {d === null && <span style="color:#8b8b86;font-size:14px">Henter episoder …</span>}
        {err && <span style="color:#ff8a7a;font-size:14px">{err}</span>}
        {(d ?? []).slice(0, 60).map((e) => (
          <button key={e.id} onClick={() => void playPodTouch(e, s)} style="min-height:64px;border-radius:12px;border:1px solid #242426;background:#141415;padding:10px 14px;text-align:left;display:flex;flex-direction:column;gap:4px;justify-content:center;flex-shrink:0">
            <span style={`font-size:15px;font-weight:600;color:${e.heard ? '#8b8b86' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{e.title}</span>
            <span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[e.date, e.duration ? pmin(e.duration) : '', e.heard ? 'Hørt' : e.pos ? 'Fortsett der du slapp' : ''].filter(Boolean).join(' · ')}</span>
            {!!e.pos && !!e.duration && !e.heard && <div style="height:3px;border-radius:2px;background:#2e2e30;overflow:hidden"><i style={`display:block;height:100%;width:${Math.min(100, (e.pos / e.duration) * 100)}%;background:#d9a441`} /></div>}
          </button>
        ))}
      </div>
    </div>
  );
}

function Library() {
  const [nd, setNd] = useState<NdAlbum[] | null>(null);
  const [yt, setYt] = useState<NdAlbum[] | null>(null), [ytErr, setYtErr] = useState('');
  const ndOk = ndConfigured();   // innloggingen kommer fra enheten etter oppstart
  useEffect(() => { if (lib.value === 1 && (nd === null || !nd.length) && ndOk) ndAlbumList('newest', 12).then(setNd).catch(() => setNd([])); }, [lib.value, ndOk]);
  useEffect(() => {
    if (lib.value !== 0 || (yt !== null && yt.length)) return;   // tom/feil: prøv igjen når fanen åpnes
    // YouTube Music fra Skjold (/api/ytm/home): spillelister, «Til deg» og album
    ytmHomeCached().then((h) => { const l = [...h.playlists, ...h.frequent, ...h.other, ...h.newest]; setYt(l.filter((x, i) => l.findIndex((y) => y.id === x.id) === i).slice(0, 24)); })
      .catch(async (e: unknown) => { setYtErr((await ytmWhy(e)).toUpperCase()); setYt([]); });
  }, [lib.value]);
  const sw = swT.value, swNow = swNowT.value;
  useEffect(() => { loadSwT(); }, [lib.value]);   // i bakgrunnen: fanen vises med en gang fra det som er husket
  const [pf, setPf] = useState<PodShow[] | null>(null), [pn, setPn] = useState<PodEpisode[]>([]);
  const st = status.value;
  const TABS = ['YouTube Music', 'Navidrome', 'Radio', ...(sw.length ? ['SUB/WAVE'] : []), 'Podkaster'];
  const tab = TABS[lib.value] ?? 'Radio';
  useEffect(() => { if (tab !== 'Podkaster') return; api.podFavs().then((r) => setPf(r.items.slice().reverse())).catch(() => setPf([])); api.podNew().then((r) => setPn(r.items)).catch(() => setPn([])); }, [tab]);
  let kicker = '', items: Card[] = [];
  if (lib.value === 0) {
    kicker = ytErr || (yt === null ? 'HENTER …' : yt.length ? 'SPILLELISTER OG MIKSER' : 'FANT INGENTING · LEGG INN COOKIEN I APPEN');
    items = (yt ?? []).map((a) => ({ t: a.name, s: a.playlist ? 'Spilleliste' : a.artist, art: artBg(a.name, ndCover(a.coverArt, 300)), play: () => { void ytmTracks(a.id).then((r) => { if (r.length) { playNd(r, 0, 'ytm'); scr.value = 'now'; } }); } }));
  }
  else if (lib.value === 1) {
    kicker = ndOk ? 'NYLIG LAGT TIL' : 'IKKE TILKOBLET · LOGG INN PÅ NAVIDROME I APPEN';
    items = (nd ?? []).map((a) => ({ t: a.name, s: a.artist, art: artBg(a.name, ndCover(a.coverArt, 300)), play: () => { void ndAlbum(a.id).then((r) => { playNd(r.songs, 0); scr.value = 'now'; }); } }));
  } else if (tab === 'Podkaster') {
    kicker = pf === null ? 'HENTER …' : pf.length ? 'FAVORITTPODKASTER' + (pn.length ? ' · NYESTE EPISODER FØRST' : '') : 'INGEN FAVORITTER · LEGG TIL I APPEN UNDER RADIO → PODKASTER';
    const nyest = pn.slice(0, 6).map((e) => ({ t: e.title, s: 'NY · ' + e.show, art: artBg(e.show, e.image), play: () => void playPodTouch(e) }));
    items = [...nyest, ...(pf ?? []).map((f) => ({ t: f.title, s: f.author || 'Podkast', art: artBg(f.title, f.image), play: () => { podFraSok = false; podTouch.value = f; } }))];
  } else if (tab === 'SUB/WAVE') {
    kicker = 'SUB/WAVE · AI-DJ-STASJONER';
    items = sw.map((x) => ({ t: x.name, s: 'SUB/WAVE', art: artBg(x.name, x.image, x.i), live: swNow === x.i && !!st?.playing,
      play: () => { void api.subwavePost({ station: x.i, play: true }).catch(() => {}); swNowT.value = x.i; scr.value = 'now'; } }));
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
      {tab === 'Podkaster' && podTouch.value ? <PodEpisodes s={podTouch.value} /> : <>
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>{kicker}</span>
      <div style="flex:1;min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y;display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:16px 14px;align-content:start;padding-bottom:14px">
        {items.map((it, i) => (
          <button key={i} onClick={it.play} style="min-width:0;border:none;background:none;padding:0;text-align:left;display:flex;flex-direction:column;gap:8px">
            <div style={`position:relative;width:100%;aspect-ratio:1;border-radius:12px;background:${it.art}`}>{it.live && <span style={`position:absolute;left:8px;top:8px;height:18px;padding:0 6px;border-radius:4px;background:#e05a4a;color:#fff;font-family:${MONO};font-size:9px;display:flex;align-items:center`}>DIREKTE</span>}</div>
            <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.t}</span><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.s}</span></span>
          </button>
        ))}
      </div></>}
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

// ---------- Lag spillegruppe: velg hvor musikken kommer fra, huk av rommene, start – og lagre som fast gruppe ----------
const gruppeOpen = signal(false);
function GruppeSheet() {
  const rows = roomList(), keyOf = (r: RoomRow) => r.base || here();
  const [leder, setLeder] = useState(ctl.value || here());
  const [med, setMed] = useState<string[]>(() => { const m = groups.value.members; return m.length ? m.filter((k) => k !== (ctl.value || here())) : []; });
  const [navn, setNavn] = useState(false);
  const nt = useTekst(24);
  const radRom = (k: string) => rows.find((r) => keyOf(r) === k);
  const start = (l = leder, m = med) => {
    const lr = radRom(l);
    if (lr && lr.base !== ctl.value) control(lr.base);
    window.setTimeout(() => setMembers([l, ...m.filter((k) => k !== l)]), 300);
    gruppeOpen.value = false;
  };
  const brikke = (på: boolean) => `height:40px;padding:0 14px;border-radius:20px;border:1px solid ${på ? '#d9a441' : '#2e2e30'};background:${på ? '#1c170d' : '#161617'};color:${på ? '#f0c46a' : '#f2f2ee'};font-size:13px;font-weight:600;white-space:nowrap;display:flex;align-items:center;gap:8px`;
  if (navn) return (
    <div style="position:absolute;inset:0;z-index:9;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 20px">
        <span style="font-size:15px;font-weight:600">Navn på gruppen</span>
        <div style="display:flex;align-items:center;height:48px;border-radius:12px;border:1px solid #2e2e30;background:#141415;padding:0 14px"><TekstFelt t={nt} tom="F.eks. Hele huset" size={16} /></div>
      </div>
      <Keyboard enter="Lagre" onKey={nt.inn} onBack={nt.slett} onFlytt={nt.flytt} onEnter={() => { if (nt.v.trim()) savePreset(nt.v.trim(), [leder, ...med]); setNavn(false); }} />
    </div>);
  const ps = groups.value.presets;
  return (
    <Sheet title="Spillegruppe" kicker="SPILL DET SAMME I FLERE ROM, I TAKT" onClose={() => { gruppeOpen.value = false; }} height={420}>
      <div class="rull" style="overflow-y:auto;touch-action:pan-y;display:flex;flex-direction:column;gap:12px;padding:4px 16px 14px">
        {ps.length > 0 && <div style="display:flex;flex-direction:column;gap:6px">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#8b8b86`}>LAGREDE GRUPPER</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap">{ps.map((g, i) => (
            <span key={g.n + i} style="display:flex;gap:2px">
              <button onClick={() => start(g.ids[0] ?? leder, g.ids.slice(1))} style={brikke(false)}>{g.n} <span style="font-size:11px;color:#8b8b86">{g.ids.length} rom</span></button>
              <button onClick={() => removePreset(i)} aria-label={'Slett ' + g.n} style="width:32px;height:40px;border:none;background:none;color:#6b6b67;font-size:16px">×</button>
            </span>))}</div>
        </div>}
        <div style="display:flex;flex-direction:column;gap:6px">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#8b8b86`}>1 · MUSIKKEN KOMMER FRA</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap">{rows.map((r) => { const k = keyOf(r); return (
            <button key={k} onClick={() => { setLeder(k); setMed((m) => m.filter((x) => x !== k)); }} style={brikke(k === leder)}>
              <span style={`width:22px;height:22px;border-radius:6px;background:${r.st?.playing ? artOf(r.st, r.base) : '#2a2a2c'}`} />{r.name}</button>); })}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#8b8b86`}>2 · SPILL OGSÅ I</span>
          <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">{rows.filter((r) => keyOf(r) !== leder).map((r) => { const k = keyOf(r), på = med.includes(k); return (
            <button key={k} onClick={() => setMed((m) => (på ? m.filter((x) => x !== k) : [...m, k]))} aria-pressed={på} style={`height:52px;border-radius:12px;border:1px solid ${på ? '#d9a441' : '#242426'};background:${på ? '#1c170d' : '#141415'};display:flex;align-items:center;gap:12px;padding:0 14px;text-align:left`}>
              <span style={`width:26px;height:26px;border-radius:13px;border:1.5px solid ${på ? '#f0c46a' : '#3a3a3c'};background:${på ? '#f0c46a' : 'transparent'};color:#0b0b0c;font-size:14px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0`}>{på ? '✓' : ''}</span>
              <span style="display:flex;flex-direction:column;min-width:0"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.name}</span><span style="font-size:11px;color:#8b8b86">{r.model}</span></span>
            </button>); })}</div>
          {rows.length < 2 && <span style="font-size:12.5px;color:#8b8b86">Fant ingen andre Skjold-rom på nettet.</span>}
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button onClick={() => start()} disabled={!med.length} style={`height:46px;padding:0 22px;border-radius:23px;border:none;background:${med.length ? '#f0c46a' : '#242426'};color:${med.length ? '#0b0b0c' : '#6b6b67'};font-size:14px;font-weight:600`}>{med.length ? 'Spill i ' + (med.length + 1) + ' rom' : 'Velg minst ett rom til'}</button>
          {!!med.length && <button onClick={() => setNavn(true)} style="height:46px;padding:0 18px;border-radius:23px;border:1px solid #2e2e30;background:#161617;color:#f2f2ee;font-size:13px;font-weight:600">Lagre som fast gruppe</button>}
          <button onClick={() => { setMed(rows.map(keyOf).filter((k) => k !== leder)); }} style="height:46px;padding:0 16px;border-radius:23px;border:none;background:none;color:#d9a441;font-size:13px">Alle</button>
        </div>
      </div>
    </Sheet>
  );
}

function Rooms() {
  const rows = roomList();
  // Grupper: rommet du styrer leder, trykk på sirkelen for å ta et rom med i gruppen (spiller det samme, synkront)
  const lederKey = ctl.value || here(), keyOf = (r: RoomRow) => r.base || here();
  void groups.value;   // tegn på nytt når gruppen endres
  const med = (r: RoomRow) => inGroup(keyOf(r), lederKey);
  const antall = rows.filter(med).length;
  useEffect(() => { void loadGroup(); }, [ctl.value]);   // vis gruppen slik Lyrion har den
  return (
    <section style="flex:1;display:flex;flex-direction:column;gap:12px;padding:18px 22px;min-height:0">
      <div style="display:flex;align-items:center;gap:10px"><span style="font-size:22px;font-weight:600">Rom</span><div style="flex:1" />
        {antall > 1 && <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.1em;color:#f0c46a`}>{antall} ROM SPILLER SAMMEN{groupBusy.value ? ' …' : ''}</span>}
        {antall > 1 && <button onClick={() => groupNone()} style="height:36px;padding:0 14px;border-radius:18px;border:1px solid #2e2e30;background:#161617;font-size:12.5px">Løs opp</button>}
        <button onClick={() => { groupAll(rows.map(keyOf)); }} style="height:36px;padding:0 14px;border-radius:18px;border:1px solid #2e2e30;background:#161617;font-size:12.5px">Spill i alle rom</button>
        <button onClick={() => { gruppeOpen.value = true; }} style="height:36px;padding:0 16px;border-radius:18px;border:none;background:#f0c46a;color:#0b0b0c;font-size:12.5px;font-weight:600">+ Ny gruppe</button></div>
      {groups.value.presets.length > 0 && <div style="display:flex;gap:8px;overflow-x:auto;touch-action:pan-x;flex-shrink:0">
        {groups.value.presets.map((g, i) => <button key={g.n + i} onClick={() => { const l = rows.find((r) => keyOf(r) === g.ids[0]); if (l && l.base !== ctl.value) control(l.base); window.setTimeout(() => setMembers(g.ids), 300); }}
          style="height:36px;padding:0 14px;border-radius:18px;border:1px solid #3a2e17;background:#1c170d;color:#f0c46a;font-size:12.5px;font-weight:600;white-space:nowrap">▶ {g.n}</button>)}
      </div>}
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;overflow-y:auto;min-height:0">
        {rows.map((r) => {
          const on = r.base === ctl.value, pick = () => { control(r.base); scr.value = 'now'; };
          return (
            <div key={r.base} style={`display:grid;grid-template-columns:40px minmax(0,1fr) 110px 44px;gap:12px;align-items:center;height:72px;padding:0 14px;border-radius:14px;border:1px solid ${on ? '#d9a441' : '#242426'};background:${on ? '#1c170d' : '#141415'};box-sizing:border-box`}>
              <button onClick={pick} style={`width:40px;height:40px;border-radius:10px;border:none;background:${r.st?.playing ? artOf(r.st, r.base) : '#1b1b1c'};padding:0`} />
              <button onClick={pick} style="border:none;background:none;padding:0;text-align:left;display:flex;flex-direction:column;gap:2px;min-width:0">
                <span style={`font-size:14px;font-weight:600;color:${on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap`}>{r.name}</span>
                <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.self ? 'Denne enheten' : npLine(r.st)}</span>
                <span style={`font-family:${MONO};font-size:9.5px;color:#6b6b67;white-space:nowrap`}>{r.model}</span>
              </button>
              <input type="range" min={0} max={100} value={(on ? status.value?.volume : r.st?.volume) ?? 0}
                onChange={(e) => { const v = +(e.currentTarget as HTMLInputElement).value; if (on) setVolume(v, true); else void postAt(r.base, '/api/volume', { volume: v }); }}
                onInput={(e) => { if (on) setVolume(+(e.currentTarget as HTMLInputElement).value); }}
                style="width:110px;accent-color:#f0c46a;height:28px" />
              {(() => { const m = med(r), leder = keyOf(r) === lederKey; return (
                <button onClick={() => { if (!leder) toggleMember(lederKey, keyOf(r)); }} aria-pressed={m} aria-label={leder ? 'Rommet du styrer' : m ? 'Ta ut av gruppen' : 'Spill her også'}
                  style={`width:40px;height:40px;border-radius:20px;border:1.5px solid ${m ? '#f0c46a' : '#3a3a3c'};background:${m ? '#f0c46a' : 'transparent'};color:#0b0b0c;font-size:17px;font-weight:700;padding:0;opacity:${leder && !m ? 0.35 : 1}`}>{m ? '✓' : ''}</button>); })()}
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
    ...(lasVal.value ? [['Dørlås', lasVal.value.valgt === '-' ? 'Av – «Lås opp» vises ikke når det ringer på' : lasVal.value.bruker ? 'Vises når det ringer på' + (lasVal.value.valgt ? '' : ' (valgt automatisk)') : lasVal.value.error || ((lasVal.value.locks ?? []).length ? 'Velg låsen som skal låses opp fra Touch' : 'Fant ingen lås i Home Assistant'), stepper(lasNavn(), () => byttLas(-1), () => byttLas(1), 130)] as [string, string, preact.ComponentChildren]] : []),
    ['Wi-Fi', wifiNow.value ? 'Koblet til «' + wifiNow.value + '»' : 'Velg nett her, med mobilen (QR) eller over Bluetooth', one('Koble til nytt', () => { wifiOpen.value = true; })],
    ['Skjermsparer', 'Vises når skjermen hviler: ' + (TOUCH_IDLE[S.tIdle ?? 0] ?? '').toLowerCase(), <div style={SEGBOX}>
      <button onClick={() => { saverOpen.value = true; }} style="height:34px;padding:0 14px;border-radius:9px;border:none;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap">Velg</button>
      <button onClick={goIdle} style="height:34px;padding:0 14px;border-radius:9px;border:none;background:transparent;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap">Start nå</button></div>],
    ['Startside', 'Siden som vises etter oppstart', stepper(TOUCH_START[S.tStart ?? 0] ?? '', () => setSetting('tStart', ((S.tStart ?? 0) + TOUCH_START.length - 1) % TOUCH_START.length), () => setSetting('tStart', ((S.tStart ?? 0) + 1) % TOUCH_START.length), 104)],
    ['Nattmodus', 'Svakt, rødlig lys og dempet skjerm', seg(['Av', 'Tidsplan', 'HA/Homey', 'På'], nMode, (i) => { setSetting('tNightMode', i); setSetting('tNight', i === 1); })],
    ['Natt fra', 'Brukes når nattmodus står på Tidsplan', stepper(String(S.tNStart ?? 22).padStart(2, '0') + ':00', () => setSetting('tNStart', ((S.tNStart ?? 22) + 23) % 24), () => setSetting('tNStart', ((S.tNStart ?? 22) + 1) % 24))],
    ['Natt til', 'Vanlig lys igjen fra dette klokkeslettet', stepper(String(S.tNEnd ?? 7).padStart(2, '0') + ':00', () => setSetting('tNEnd', ((S.tNEnd ?? 7) + 23) % 24), () => setSetting('tNEnd', ((S.tNEnd ?? 7) + 1) % 24))],
    ['Ringeklokke', 'Når noen ringer på', seg(TOUCH_BELL, S.tBell ?? 0, (i) => setSetting('tBell', i))],
    ['Sidemeny', 'Utseendet på menyen: klassisk, smal, flytende eller faner nederst', seg(['Klassisk', 'Smal', 'Flytende', 'Bunnlinje'], S.tNav ?? 0, (i) => setSetting('tNav', i))],
    ['Kalender på skjermspareren', 'Neste avtaler fra Home Assistant (første kalender, eller den som er valgt)', seg(['Av', 'På'], S.tKal === false ? 0 : 1, (i) => setSetting('tKal', i === 1))],
    ['Trykkelyder', 'Myke klikk i høyttalerne når du trykker. Følger hovedvolumet; du hører styrken når du endrer den', (() => {
      const p = lydProsent(S.tLydP, S.tLyd), sett = (n: number) => { const v = Math.max(0, Math.min(100, n)); setSetting('tLydP', Math.round(v / 10)); window.setTimeout(() => spillLyd('trykk', v), 60); };
      return <div style={SEGBOX}>
        <button data-lyd="" onClick={() => sett(p - 10)} aria-label="Svakere" style="width:44px;height:34px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:16px;font-weight:600">−</button>
        <span style="min-width:64px;height:34px;padding:0 10px;border-radius:9px;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;display:flex;align-items:center;justify-content:center;box-sizing:border-box">{p ? p + ' %' : 'Av'}</span>
        <button data-lyd="" onClick={() => sett(p + 10)} aria-label="Sterkere" style="width:44px;height:34px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:16px;font-weight:600">+</button>
        <button data-lyd="" onClick={() => sett(p ? 0 : 40)} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:12px;font-weight:600">{p ? 'Av' : 'På'}</button>
      </div>;
    })()],
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
    ...(TABLET?.oppdaterApp ? [['Skjold-appen', 'Versjon ' + (TABLET.appVersjon?.() ?? '?') + ' på nettbrettet', one('Oppdater', () => { try { TABLET.oppdaterApp?.(); } catch { /* */ } })] as [string, string, preact.ComponentChildren]] : []),
    ...(TABLET ? [['Skjold-enhet', 'Nettbrettet styrer ' + (local.value?.name || location.hostname) + ' (' + location.host + ')', one('Bytt', () => { try { TABLET.velgEnhet(); } catch { /* */ } })] as [string, string, preact.ComponentChildren]] : []),
    ['Om enheten', [local.value?.name, location.hostname, local.value?.version ? 'versjon ' + local.value.version : ''].filter(Boolean).join(' · '), <span style={`font-family:${MONO};font-size:10px;letter-spacing:.1em;color:#6b6b67;white-space:nowrap`}>SKJOLD TOUCH</span>]
  ];
  return (
      <div style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415">
        {rows.map(([n, hint, ctrl], i) => (
          <div key={n} style={`display:flex;align-items:center;gap:14px;min-height:58px;padding:0 16px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'};flex-shrink:0`}>
            <span style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0"><span style="font-size:14px">{n}</span><span style="font-size:11.5px;color:#8b8b86">{hint}</span></span>
            {ctrl}
          </div>
        ))}
      </div>
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
        {sm?.hub !== 'Homey' && <button onClick={() => { camOpen.value = true; }} aria-label="Kameraer" style="height:44px;padding:0 14px;border-radius:22px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px;white-space:nowrap"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h12v10H3zM15 10l6-3v10l-6-3" /></svg>Kameraer</button>}
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

// ---------- kameraer (Home Assistant / UniFi Protect) ----------
const camOpen = signal(false);
interface Cam { id: string; name: string; on: boolean }
function CamView() {
  const [cams, setCams] = useState<Cam[] | null>(null), [err, setErr] = useState(''), [en, setEn] = useState(''), [tick, setTick] = useState(0);
  useEffect(() => { getAt<{ ok: boolean; cameras: Cam[]; error?: string }>('', '/api/touch/cameras').then((r) => { setCams(r.cameras || []); setErr(r.ok ? '' : r.error || 'Fikk ikke hentet kameraene'); }).catch(() => { setCams([]); setErr('Krever nyere Skjold-programvare'); }); }, []);
  useEffect(() => { const t = setInterval(() => setTick((x) => x + 1), en ? 1000 : 2500); return () => clearInterval(t); }, [en]);
  const img = (id: string) => here() + '/api/touch/camera/' + encodeURIComponent(id) + '?t=' + tick;
  const lukk = () => { if (en) setEn(''); else camOpen.value = false; };
  const liste = (cams ?? []).filter((c) => c.on), n = liste.length, kol = n <= 1 ? 1 : n <= 4 ? 2 : 3;
  const valgt = en ? liste.find((c) => c.id === en) : undefined;
  return (
    <div style="position:absolute;inset:0;z-index:25;background:#050506;display:flex;flex-direction:column;animation:tinn .25s ease both">
      <div style="height:52px;flex-shrink:0;display:flex;align-items:center;gap:12px;padding:0 14px">
        <button onClick={lukk} aria-label="Tilbake" style="height:40px;padding:0 14px;border-radius:20px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:13px;font-weight:600">‹ {valgt ? 'Alle kameraer' : 'Smarthus'}</button>
        <span style="font-size:17px;font-weight:600">{valgt ? valgt.name : 'Kameraer'}</span>
        <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>{valgt ? 'OPPDATERES HVERT SEKUND' : n ? n + ' KAMERA' + (n === 1 ? '' : 'ER') : ''}</span>
      </div>
      {cams === null ? <span style={`margin:auto;font-family:${MONO};font-size:11px;letter-spacing:.14em;color:#8b8b86`}>HENTER …</span>
        : !n ? <span style="margin:auto;max-width:520px;text-align:center;font-size:15px;line-height:1.5;color:#a9a9a3">{err || 'Fant ingen kameraer i Home Assistant. Legg til UniFi Protect (eller et annet kamera) i Home Assistant, eller velg kameraer som fliser i appen.'}</span>
          : valgt ? <button onClick={() => setEn('')} style="flex:1;min-height:0;margin:0 10px 10px;border:none;padding:0;border-radius:12px;overflow:hidden;background:#000"><img src={img(valgt.id)} alt={valgt.name} style="width:100%;height:100%;object-fit:contain;display:block" /></button>
            : <div style={`flex:1;min-height:0;display:grid;grid-template-columns:repeat(${kol},minmax(0,1fr));grid-auto-rows:minmax(0,1fr);gap:6px;padding:0 10px 10px`}>
              {liste.map((c) => (
                <button key={c.id} onClick={() => setEn(c.id)} style="position:relative;border:none;padding:0;border-radius:10px;overflow:hidden;background:#111;min-height:0">
                  <img src={img(c.id)} alt={c.name} style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover" />
                  <span style="position:absolute;left:8px;bottom:8px;padding:3px 8px;border-radius:6px;background:rgba(0,0,0,.6);font-size:12px;color:#f2f2ee">{c.name}</span>
                </button>))}
            </div>}
    </div>
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

// ---------- artistsiden (Navidrome): trykk på artistnavnet på Spiller ----------
const artistSide = signal('');   // navnet som ble trykket; '' = lukket
effect(() => { if (scr.value !== 'now') artistSide.value = ''; });
/** Finn artisten i Navidrome: likt navn først, ellers første del av «A feat. B» / «A & B» / «A, B». */
async function finnArtist(navn: string): Promise<NdArtist | null> {
  const prøv = [navn, navn.split(/\s+(?:feat\.?|ft\.?|featuring|&|og|x)\s+|,\s*/i)[0] ?? ''].map((x) => x.trim()).filter(Boolean);
  for (const n of [...new Set(prøv)]) {
    const r = await ndSearchAll(n);
    const lik = r.artists.find((a) => a.name.toLowerCase() === n.toLowerCase());
    if (lik) return lik;
    if (r.artists[0]) return r.artists[0];
  }
  return null;
}
function ArtistSide() {
  const navn = artistSide.value;
  const [a, setA] = useState<{ artist: NdArtist; albums: NdAlbum[] } | null | undefined>(undefined);
  const [sanger, setSanger] = useState<NdSong[]>([]), [alb, setAlb] = useState<{ album: NdAlbum; songs: NdSong[] } | null>(null);
  useEffect(() => {
    let av = false;
    setA(undefined); setAlb(null); setSanger([]);
    void (async () => {
      try {
        const ar = await finnArtist(navn);
        if (!ar) { if (!av) setA(null); return; }
        const [r, sok] = await Promise.all([ndArtist(ar.id), ndSearchAll(ar.name).catch(() => ({ songs: [] as NdSong[] }))]);
        if (av) return;
        setA(r);
        setSanger(sok.songs.filter((x) => x.artist.toLowerCase().includes(ar.name.toLowerCase())).slice(0, 30));
      } catch { if (!av) setA(null); }
    })();
    return () => { av = true; };
  }, [navn]);
  const spill = (l: NdSong[], i: number) => { playNd(l, i, 'nd'); artistSide.value = ''; scr.value = 'now'; };
  const rad = (x: NdSong, i: number, l: NdSong[], nr?: number) => (
    <button key={x.id + i} onClick={() => spill(l, i)} style="height:50px;flex-shrink:0;border:none;border-radius:10px;background:transparent;display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;align-items:center;padding:0 10px;text-align:left">
      {nr ? <span style={`font-family:${MONO};font-size:12px;color:#8b8b86;text-align:center`}>{nr}</span> : <div style={`width:40px;height:40px;border-radius:8px;background:${artBg(x.title, ndCover(x.coverArt, 120))}`} />}
      <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.title}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nr ? x.artist : x.album}</span></span>
      <span style={`font-family:${MONO};font-size:11px;color:#6b6b67`}>{x.duration ? Math.floor(x.duration / 60) + ':' + String(x.duration % 60).padStart(2, '0') : ''}</span>
    </button>);
  const tittel = alb ? alb.album.name : a?.artist.name ?? navn;
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;gap:10px;padding:8px 14px 8px 6px;flex-shrink:0">
        <button onClick={() => { if (alb) setAlb(null); else artistSide.value = ''; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#f0c46a`}>{alb ? (alb.album.artist + (alb.album.year ? ' · ' + alb.album.year : '')).toUpperCase() : 'ARTIST · NAVIDROME'}</span>
          <span style="font-size:20px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{tittel}</span>
        </span>
        {alb && !!alb.songs.length && <button onClick={() => spill(alb.songs, 0)} style="height:40px;padding:0 18px;border-radius:20px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13px;font-weight:600;flex-shrink:0">Spill albumet</button>}
        {!alb && !!sanger.length && <button onClick={() => spill(sanger, 0)} style="height:40px;padding:0 18px;border-radius:20px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13px;font-weight:600;flex-shrink:0">Spill sangene</button>}
      </div>
      <div class="rull" style="flex:1;min-height:0;overflow-y:auto;touch-action:pan-y;display:flex;flex-direction:column;gap:2px;padding:0 10px 10px">
        {a === undefined && <span style={`padding:14px 10px;font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>HENTER …</span>}
        {a === null && <span style="padding:14px 10px;font-size:13.5px;color:#8b8b86">Fant ikke «{navn}» i Navidrome.</span>}
        {alb ? alb.songs.map((x, i) => rad(x, i, alb.songs, i + 1)) : a && <>
          <span style={`padding:6px 10px 4px;font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>ALBUM · {a.albums.length}</span>
          <div style="display:flex;gap:12px;overflow-x:auto;touch-action:pan-x;padding:0 10px 8px;flex-shrink:0">
            {a.albums.map((al) => (
              <button key={al.id} onClick={() => { void ndAlbum(al.id).then(setAlb); }} style="width:132px;flex-shrink:0;border:none;background:none;padding:0;display:flex;flex-direction:column;gap:6px;text-align:left">
                <div style={`width:132px;height:132px;border-radius:10px;background:${artBg(al.name, ndCover(al.coverArt, 300))}`} />
                <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{al.name}</span>
                <span style="font-size:11px;color:#8b8b86">{[al.year, al.songCount ? al.songCount + ' sanger' : ''].filter(Boolean).join(' · ')}</span>
              </button>))}
          </div>
          {!!sanger.length && <span style={`padding:8px 10px 4px;font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>SANGER</span>}
          {sanger.map((x, i) => rad(x, i, sanger))}
        </>}
      </div>
    </div>
  );
}

// ---------- søk ----------
interface Hit { key: string; t: string; s: string; art: string; play: () => void }
// Husket søk: åpner du en podkast fra søket, tar «Tilbake» deg til søket med det du skrev og samme kilde.
const sokHusk = { q: '', src: -1, fraSok: false };
function Search() {
  const qt = useTekst(60, sokHusk.fraSok ? sokHusk.q : ''), q = qt.v;
  const [kb, setKb] = useState(!sokHusk.fraSok), [busy, setBusy] = useState(false);
  const [hits, setHits] = useState<Hit[] | null>(null), [err, setErr] = useState('');
  // Søkekilde: fanen du kom fra (SUB/WAVE har ikke søk, så da søkes det i YouTube Music). 3 = podkaster.
  const podIdx = 3 + (swT.value.length ? 1 : 0);
  const [src, setSrc] = useState(sokHusk.fraSok && sokHusk.src >= 0 ? sokHusk.src : lib.value <= 2 ? lib.value : lib.value === podIdx ? 3 : 0);
  useEffect(() => { sokHusk.fraSok = false; }, []);
  const seq = useRef(0);
  const go = (it: () => void) => () => { it(); searchOpen.value = false; scr.value = 'now'; };
  useEffect(() => {
    const t = q.trim(), n = ++seq.current;
    if (t.length < 2) { setHits(null); setBusy(false); setErr(''); return; }
    setBusy(true);
    const id = window.setTimeout(async () => {
      try {
        let l: Hit[];
        if (src === 3) { const r = await api.podSearch(t); l = r.shows.slice(0, 30).map((x, i) => ({ key: x.id, t: x.title, s: x.author || 'Podkast', art: artBg(x.title, x.image, i), play: () => { sokHusk.q = t; sokHusk.src = 3; podFraSok = true; podTouch.value = x; lib.value = podIdx; window.setTimeout(() => { scr.value = 'lib'; }, 0); } })); }
        else if (src === 2) { const r = await api.radioSearch(t); l = [...(r.norway ?? []), ...(r.world ?? [])].slice(0, 30).map((st, i) => ({ key: st.url + i, t: st.name, s: st.genre || st.country || 'Radio', art: artBg(st.name, st.image, i), play: () => playStation(st) })); }
        else { const r = src === 0 ? await ytmSearch(t) : await ndSearch(t); l = r.slice(0, 30).map((x, i) => ({ key: x.id + i, t: x.title, s: [x.artist, x.album].filter(Boolean).join(' · '), art: artBg(x.title, ndCover(x.coverArt, 120)), play: () => playNd(r, i, src === 0 ? 'ytm' : 'nd') })); }
        if (n === seq.current) { setHits(l); setErr(''); }
      } catch (e) { if (n === seq.current) { setHits([]); setErr(src === 0 ? await ytmWhy(e) : src === 1 && !ndConfigured() ? 'Navidrome er ikke koblet til. Logg inn i appen.' : 'Søket svarte ikke'); } }
      finally { if (n === seq.current) setBusy(false); }
    }, 500);
    return () => clearTimeout(id);
  }, [q, src]);
  const NAMES = ['YouTube Music', 'Navidrome', 'Radio', 'Podkaster'];
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="display:flex;align-items:center;gap:8px;padding:8px 10px 8px 6px;flex-shrink:0">
        <button onClick={() => { searchOpen.value = false; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <button class="flat" onClick={() => setKb(true)} aria-label="Søkefelt" style="flex:1;min-width:0;height:44px;border-radius:22px;border:1px solid #2e2e30;background:#141415;display:flex;align-items:center;gap:8px;padding:0 16px;text-align:left;font-size:15px">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2" stroke-linecap="round" style="flex-shrink:0"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
          {kb ? <TekstFelt t={qt} size={15} tom={['Søk i YouTube Music', 'Søk i Navidrome', 'Søk etter radiokanaler', 'Søk etter podkaster'][src] ?? 'Søk'} />
            : <span style={`white-space:pre;overflow:hidden;text-overflow:ellipsis;color:${q ? '#f2f2ee' : '#6b6b67'}`}>{q || (['Søk i YouTube Music', 'Søk i Navidrome', 'Søk etter radiokanaler', 'Søk etter podkaster'][src] ?? 'Søk')}</span>}
        </button>
        {NAMES.map((n, i) => <button key={n} onClick={() => setSrc(i)} style={`height:44px;padding:0 12px;border-radius:22px;border:1px solid ${src === i ? '#f2f2ee' : '#2e2e30'};background:${src === i ? '#f2f2ee' : '#161617'};color:${src === i ? '#0b0b0c' : '#c9c9c4'};font-size:12px;font-weight:600;white-space:nowrap;flex-shrink:0`}>{n.replace('YouTube Music', 'YouTube')}</button>)}
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
      {kb && <Keyboard onKey={qt.inn} onBack={qt.slett} onFlytt={qt.flytt} onEnter={() => setKb(false)} />}
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
function daysTxt(d: number[]): string {
  if (!d.length || d.length === 7) return 'Hver dag';
  if (d.length === 5 && d.every((x) => x < 5)) return 'Hverdager';
  if (d.length === 2 && d.includes(5) && d.includes(6)) return 'Helg';
  return d.map((x) => DN[x]).join(' ');
}
const hhmm = (m: number) => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

function AlarmPage() {
  const AL = alarms.value, nx = nextAlarm();
  useEffect(() => { void loadAlarms(); void loadWake(); const t = setInterval(() => void loadWake(), 5000); return () => clearInterval(t); }, []);
  const setA = (i: number, p: Partial<Alarm>) => saveAlarms(AL.map((a, j) => (j === i ? { ...a, ...p } : a)));
  return (
    <section class="inn" style="flex:1;display:flex;flex-direction:column;gap:10px;padding:14px 18px 10px;min-height:0;overflow-y:auto;scrollbar-width:none;touch-action:pan-y">
      <div style="display:flex;align-items:center;gap:10px"><span style="font-size:20px;font-weight:600">Vekkeklokke</span><span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>{nx ? 'NESTE ALARM ' + nx.time : 'INGEN ALARMER PÅ'}</span><div style="flex:1" />
        <button onClick={() => { timerOpen.value = true; }} style="height:44px;padding:0 16px;border-radius:22px;border:1px solid #3a2e17;background:#1c170d;color:#f0c46a;font-size:12.5px;font-weight:600">+ Timer</button>
        {AL.length < 10 && <button onClick={() => { saveAlarms([...AL, { time: '07:00', days: [0, 1, 2, 3, 4], on: true, name: 'Alarm', smart: false, preset: 0, url: '', volume: 30, fade: 0 }]); editAlarm.value = AL.length; }} style="height:44px;padding:0 16px;border-radius:22px;border:1px solid #2e2e30;background:#161617;font-size:12.5px;font-weight:600">+ Ny alarm</button>}</div>
      {!AL.length && <span style="font-size:14px;color:#8b8b86">Ingen alarmer ennå. Trykk «Ny alarm».</span>}
      {!!AL.length && <div style="display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415;flex-shrink:0">
        {AL.map((a, i) => { const fg = a.on ? '#f2f2ee' : '#6b6b67'; return (
          <div key={i} style={`display:flex;align-items:center;gap:6px;min-height:66px;padding:0 10px 0 4px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'}`}>
            <button class="flat" onClick={() => { editAlarm.value = i; }} aria-label={'Endre alarmen ' + a.time + ' ' + (a.name || '')} style="flex:1;min-width:0;min-height:66px;border:none;background:none;padding:0 0 0 14px;display:flex;align-items:center;gap:18px;text-align:left">
              <span style={`font-family:${MONO};font-size:32px;font-weight:500;color:${fg};width:104px;flex-shrink:0`}>{a.time}</span>
              <span style="display:flex;flex-direction:column;gap:3px;flex:1;min-width:0">
                <span style={`font-size:14px;font-weight:600;color:${fg};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{a.name || 'Alarm'}</span>
                <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{daysTxt(a.days)} · {a.smart ? 'Myk start' : 'Vanlig'}</span>
              </span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b6b67" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M9 5l7 7-7 7" /></svg>
            </button>
            <button onClick={() => setA(i, { on: !a.on })} aria-label="Slå alarm av eller på" style="width:64px;height:54px;border:none;background:none;padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0"><span style={`position:relative;width:52px;height:30px;border-radius:15px;background:${a.on ? '#f0c46a' : '#2a2a2c'};transition:background .2s ease`}><span style={`position:absolute;top:3px;left:${a.on ? 25 : 3}px;width:24px;height:24px;border-radius:12px;background:#f2f2ee;transition:left .2s ease`} /></span></button>
          </div>); })}
      </div>}
      <WakeEntry />
      <span style="font-size:11.5px;line-height:1.4;color:#6b6b67;padding:0 4px;flex-shrink:0">Alarmene over er de samme her, i appen og på web. De ligger på enheten og virker uten nett.</span>
    </section>
  );
}

const NAVN = ['Alarm', 'Jobb', 'Skole', 'Helg', 'Trening', 'Lur'];
/** Rediger én alarm: rullehjul for time og minutt, en knapp per dag, og hurtigvalg. Alt lagres med en gang. */
function AlarmEdit() {
  const AL = alarms.value, i = editAlarm.value, a = AL[i];
  if (!a) return null;
  const set = (p: Partial<Alarm>) => saveAlarms(AL.map((x, j) => (j === i ? { ...x, ...p } : x)));
  const [hh, mm] = a.time.split(':').map(Number) as [number, number];
  const days = a.days.length ? a.days : [0, 1, 2, 3, 4, 5, 6];
  const tgl = (d: number) => { const n = days.includes(d) ? days.filter((x) => x !== d) : [...days, d].sort(); if (n.length) set({ days: n }); };
  const er = (l: number[]) => l.length === days.length && l.every((x) => days.includes(x));
  const pill = (on: boolean) => `height:44px;padding:0 14px;border-radius:22px;border:1px solid ${on ? '#f0c46a' : '#2e2e30'};background:${on ? '#1c170d' : '#161617'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;font-weight:600;white-space:nowrap;flex-shrink:0`;
  const lbl = `font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`;
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:flex;flex-direction:column;padding:8px 18px 14px 6px;box-sizing:border-box;gap:6px">
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        <button onClick={() => { editAlarm.value = -1; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <span style="font-size:20px;font-weight:600">Endre alarm</span>
        <div style="flex:1" />
        <button onClick={() => { editAlarm.value = -1; saveAlarms(AL.filter((_, j) => j !== i)); }} style="height:44px;padding:0 16px;border-radius:22px;border:1px solid #2e2e30;background:#161617;color:#e05a4a;font-size:12.5px;font-weight:600">Slett</button>
        <button onClick={() => { editAlarm.value = -1; }} style="height:44px;padding:0 22px;border-radius:22px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13px;font-weight:600">Ferdig</button>
      </div>
      <div style="flex:1;min-height:0;display:flex;align-items:center;gap:26px;padding-left:12px">
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          <Wheel label="Time" value={hh} count={24} onChange={(v) => set({ time: hhmm(v * 60 + mm) })} />
          <span style={`font-family:${MONO};font-size:44px;color:#8b8b86;margin-top:-4px`}>:</span>
          <Wheel label="Minutt" value={mm} count={60} onChange={(v) => set({ time: hhmm(hh * 60 + v) })} />
        </div>
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:9px">
          <span style={lbl}>DAGER</span>
          <div style="display:flex;gap:6px">
            {DN.map((n, d) => { const on = days.includes(d); return <button key={n} onClick={() => tgl(d)} aria-pressed={on} aria-label={['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag'][d]} style={`width:46px;height:46px;border-radius:23px;border:1px solid ${on ? '#f0c46a' : '#2e2e30'};background:${on ? '#f0c46a' : '#161617'};color:${on ? '#0b0b0c' : '#8b8b86'};font-size:13px;font-weight:600;padding:0;flex-shrink:0`}>{n}</button>; })}
          </div>
          <div style="display:flex;gap:6px">
            <button onClick={() => set({ days: [0, 1, 2, 3, 4] })} style={pill(er([0, 1, 2, 3, 4]))}>Hverdager</button>
            <button onClick={() => set({ days: [5, 6] })} style={pill(er([5, 6]))}>Helg</button>
            <button onClick={() => set({ days: [0, 1, 2, 3, 4, 5, 6] })} style={pill(days.length === 7)}>Hver dag</button>
          </div>
          <span style={lbl + ';margin-top:4px'}>NAVN</span>
          <div style="display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;touch-action:pan-x">
            {[...new Set([a.name || 'Alarm', ...NAVN])].map((n) => <button key={n} onClick={() => set({ name: n })} style={pill((a.name || 'Alarm') === n)}>{n}</button>)}
          </div>
          <button onClick={() => set({ smart: !a.smart, fade: a.smart ? 0 : 3 })} aria-pressed={a.smart} style="min-height:48px;margin-top:2px;border:none;background:none;padding:0;display:flex;align-items:center;gap:12px;text-align:left">
            <span style={`position:relative;width:52px;height:30px;flex-shrink:0;border-radius:15px;background:${a.smart ? '#f0c46a' : '#2a2a2c'};transition:background .2s ease`}><span style={`position:absolute;top:3px;left:${a.smart ? 25 : 3}px;width:24px;height:24px;border-radius:12px;background:#f2f2ee;transition:left .2s ease`} /></span>
            <span style="display:flex;flex-direction:column;gap:1px"><span style="font-size:14px;font-weight:600">Myk start</span><span style="font-size:11.5px;color:#8b8b86">Lyden starter svakt og øker over tre minutter</span></span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- smart vekking (KI Søvn i Home Assistant) ----------
const DAG = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag'];
const plus = (t: string, min: number) => { const [h, m] = t.split(':').map(Number) as [number, number]; return hhmm((h * 60 + m + min) % 1440); };
function Bryter({ on, small }: { on: boolean; small?: boolean }) {
  const w = small ? 44 : 52, h = small ? 26 : 30, k = h - 6;
  return <span style={`position:relative;display:block;width:${w}px;height:${h}px;flex-shrink:0;border-radius:${h / 2}px;background:${on ? '#f0c46a' : '#2a2a2c'};transition:background .2s ease`}><span style={`position:absolute;top:3px;left:${on ? w - k - 3 : 3}px;width:${k}px;height:${k}px;border-radius:50%;background:#f2f2ee;transition:left .2s ease`} /></span>;
}
function wakeLine(a: WakeAlarm): string {
  if (a.running) return a.phase === 'fader' ? 'Vekker nå: lyset tones opp' : 'Vekker nå: lyset er på';
  if (!a.on) return 'Slått av';
  if (!a.next) return 'Ingen dager er valgt';
  return 'Neste: ' + a.next_day.toLowerCase() + ' ' + a.next;
}
/** Inngangen på Alarm-siden: viser neste smarte vekking, eller forklarer hva som mangler. */
function WakeEntry() {
  const W = wakeData.value, kort = 'border-radius:14px;border:1px solid #242426;background:#141415;flex-shrink:0';
  const kick = <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#f0c46a`}>SMART VEKKING</span>;
  if (!W) return null;
  if (!W.alarms.length) return (
    <div style={kort + ';padding:12px 14px;display:flex;flex-direction:column;gap:4px'}>{kick}
      <span style="font-size:12.5px;line-height:1.45;color:#c9c9c4">{W.ok ? 'Smart vekking toner opp lyset før du skal opp, og kan vente med å vekke deg til du faktisk sover. Legg til «KI Søvn» i Home Assistant og lag en vekkealarm der, så dukker den opp her.' : W.error}</span>
    </div>);
  return (
    <div style={kort + ';display:flex;flex-direction:column'}>
      {W.alarms.map((a, i) => (
        <div key={a.id} style={`display:flex;align-items:center;gap:6px;min-height:66px;padding:0 10px 0 4px;border-top:1px solid ${i ? '#1f1f21' : 'transparent'}`}>
          <button class="flat" onClick={() => { wakeSel.value = a.id; wakeOpen.value = true; }} aria-label={'Smart vekking ' + a.name} style="flex:1;min-width:0;min-height:66px;border:none;background:none;padding:0 0 0 14px;display:flex;align-items:center;gap:14px;text-align:left">
            <span style={`width:40px;height:40px;border-radius:20px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:${a.on ? 'rgba(240,196,106,.14)' : '#1c1c1e'};color:${a.on ? '#f0c46a' : '#6b6b67'}`}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3v2M4.6 6.6L6 8M19.4 6.6L18 8M3 15h2M19 15h2M7.5 15a4.5 4.5 0 0 1 9 0M3 19h18" /></svg></span>
            <span style="display:flex;flex-direction:column;gap:3px;flex:1;min-width:0">
              <span style="display:flex;align-items:center;gap:8px">{!i && kick}<span style={`font-size:14px;font-weight:600;color:${a.on ? '#f2f2ee' : '#8b8b86'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{a.name}</span></span>
              <span style={`font-size:11.5px;color:${a.running ? '#f0c46a' : '#8b8b86'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{wakeLine(a)}{a.on && !a.running && a.fade ? ' · lyset tones opp over ' + a.fade.value + ' min' : ''}{a.person ? ' · ' + (a.person.name || 'Du') + (a.person.sleeping ? ' sover' : ' er våken') : ''}</span>
            </span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b6b67" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M9 5l7 7-7 7" /></svg>
          </button>
          <button onClick={() => void setWake(a.id, { aktiv: !a.on })} aria-label={'Slå smart vekking ' + (a.on ? 'av' : 'på')} aria-pressed={a.on} style="width:64px;height:54px;border:none;background:none;padding:0;display:flex;align-items:center;justify-content:center;flex-shrink:0"><Bryter on={a.on} /></button>
        </div>))}
    </div>);
}

/** Velg tid for én dag med rullehjul, og bruk den på flere dager med ett trykk. Lagres når du trykker «Bruk». */
function WakeTime({ a, day, onClose }: { a: WakeAlarm; day: number; onClose: () => void }) {
  const d0 = a.days[day]!, [h0, m0] = d0.time.split(':').map(Number) as [number, number];
  const [h, setH] = useState(h0), [m, setM] = useState(m0), [til, setTil] = useState<number[]>([day]);
  const er = (l: number[]) => l.length === til.length && l.every((x) => til.includes(x));
  const pill = (on: boolean) => `height:44px;padding:0 14px;border-radius:22px;border:1px solid ${on ? '#f0c46a' : '#2e2e30'};background:${on ? '#1c170d' : '#161617'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;font-weight:600;white-space:nowrap`;
  const bruk = () => { const ch: Record<string, unknown> = {}; for (const i of til) { ch[a.days[i]!.key] = hhmm(h * 60 + m); ch[a.days[i]!.key + '_aktiv'] = true; } void setWake(a.id, ch); onClose(); };
  return (
    <Sheet title={'Vekketid ' + DAG[day]!.toLowerCase()} kicker={a.name.toUpperCase()} onClose={onClose} height={300}>
      <div style="display:flex;align-items:center;gap:22px;padding:0 18px 14px">
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          <Wheel label="Time" value={h} count={24} onChange={setH} />
          <span style={`font-family:${MONO};font-size:44px;color:#8b8b86;margin-top:-4px`}>:</span>
          <Wheel label="Minutt" value={m} count={60} onChange={setM} />
        </div>
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:8px">
          <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>BRUK TIDEN PÅ</span>
          <div style="display:flex;flex-wrap:wrap;gap:6px">
            <button onClick={() => setTil([day])} style={pill(er([day]))}>Bare {DAG[day]!.toLowerCase()}</button>
            <button onClick={() => setTil([0, 1, 2, 3, 4])} style={pill(er([0, 1, 2, 3, 4]))}>Hverdager</button>
            <button onClick={() => setTil([5, 6])} style={pill(er([5, 6]))}>Helg</button>
            <button onClick={() => setTil([0, 1, 2, 3, 4, 5, 6])} style={pill(til.length === 7)}>Alle dager</button>
          </div>
          <button onClick={bruk} style="height:48px;margin-top:6px;border-radius:24px;border:none;background:#f0c46a;color:#0b0b0c;font-size:14px;font-weight:600">Bruk {hhmm(h * 60 + m)}</button>
        </div>
      </div>
    </Sheet>);
}

/** Hele menyen for smart vekking: uka med tid og av/på per dag, hvordan lyset skal oppføre seg, og om du sover. */
function WakeMenu() {
  const W = wakeData.value, a = W?.alarms.find((x) => x.id === wakeSel.value) ?? W?.alarms[0];
  const [pick, setPick] = useState(-1);
  useEffect(() => { const t = setInterval(() => void loadWake(), 4000); return () => clearInterval(t); }, []);
  if (!a) { wakeOpen.value = false; return null; }
  const set = (ch: Record<string, unknown>) => void setWake(a.id, ch);
  const lbl = `font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`;
  const rad = 'min-height:48px;border:none;background:none;padding:0;display:flex;align-items:center;gap:12px;text-align:left;width:100%';
  const steg = 'width:44px;height:44px;border-radius:22px;border:1px solid #2e2e30;background:#161617;color:#f2f2ee;font-size:20px;padding:0;flex-shrink:0';
  const Tall = ({ k, n, title, sub }: { k: string; n: WakeNum; title: string; sub: string }) => { const s = Math.max(5, n.step), ned = Math.max(n.min, n.value <= s ? n.value - 1 : n.value - (n.value % s || s)), opp = Math.min(n.max, n.value + (s - (n.value % s))); return (
    <div style="display:flex;align-items:center;gap:8px;min-height:48px">
      <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0"><span style="font-size:14px;font-weight:600">{title}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</span></span>
      <button onClick={() => set({ [k]: ned })} disabled={n.value <= n.min} aria-label={title + ' ned'} style={steg + (n.value <= n.min ? ';opacity:.35' : '')}>−</button>
      <span style={`font-family:${MONO};font-size:15px;width:62px;text-align:center;flex-shrink:0`}>{n.value} min</span>
      <button onClick={() => set({ [k]: opp })} disabled={n.value >= n.max} aria-label={title + ' opp'} style={steg + (n.value >= n.max ? ';opacity:.35' : '')}>+</button>
    </div>); };
  const Valg = ({ k, on, title, sub }: { k: string; on: boolean; title: string; sub: string }) => (
    <button onClick={() => set({ [k]: !on })} aria-pressed={on} style={rad}><Bryter on={on} /><span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:14px;font-weight:600">{title}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</span></span></button>);
  const p = a.person, nextDay = a.days.find((d) => DAG[a.days.indexOf(d)] === a.next_day);
  const info = wakeErr.value || a.skip || (a.running ? (a.phase === 'fader' ? 'Vekker nå. Lyset tones opp.' : 'Vekker nå. Lyset er på.') : !a.on ? 'Smart vekking er slått av.' : !a.next ? 'Ingen dager er valgt.' : `Neste: ${a.next_day.toLowerCase()} ${a.next}.` + (a.fade && a.lights ? ` Lyset er fullt ${plus(a.next, a.fade.value)}.` : ''));
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:flex;flex-direction:column;padding:8px 18px 10px 6px;box-sizing:border-box;gap:8px">
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        <button onClick={() => { wakeOpen.value = false; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <span style="font-size:20px;font-weight:600;white-space:nowrap">Smart vekking</span>
        {(W?.alarms.length ?? 0) > 1 ? <div style="display:flex;gap:6px;margin-left:8px;overflow-x:auto;scrollbar-width:none;touch-action:pan-x;min-width:0">{W!.alarms.map((x) => <button key={x.id} onClick={() => { wakeSel.value = x.id; }} style={`height:36px;padding:0 13px;border-radius:18px;border:1px solid ${x.id === a.id ? '#f0c46a' : '#2e2e30'};background:${x.id === a.id ? '#1c170d' : '#161617'};color:${x.id === a.id ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;font-weight:600;white-space:nowrap;flex-shrink:0`}>{x.name}</button>)}</div>
          : <span style={lbl + ';margin-left:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'}>{a.name.toUpperCase()}</span>}
        <div style="flex:1" />
        <button onClick={() => set({ aktiv: !a.on })} aria-pressed={a.on} aria-label={'Slå smart vekking ' + (a.on ? 'av' : 'på')} style="height:44px;border:none;background:none;padding:0 4px;display:flex;align-items:center;gap:10px;flex-shrink:0"><span style={`font-size:12.5px;font-weight:600;color:${a.on ? '#f0c46a' : '#8b8b86'}`}>{a.on ? 'På' : 'Av'}</span><Bryter on={a.on} /></button>
      </div>
      <div style={`display:flex;gap:6px;padding-left:12px;flex-shrink:0;opacity:${a.on ? 1 : .5};transition:opacity .2s ease`}>
        {a.days.map((d, i) => { const nx = a.on && d === nextDay; return (
          <div key={d.key} style={`flex:1;min-width:0;border-radius:14px;border:1px solid ${nx ? '#d9a441' : '#242426'};background:${d.on ? '#161617' : '#101011'};display:flex;flex-direction:column;align-items:center;overflow:hidden`}>
            <button class="flat" onClick={() => setPick(i)} aria-label={'Endre tiden for ' + DAG[i]!.toLowerCase() + ', nå ' + d.time} style="width:100%;height:60px;border:none;background:none;padding:6px 0 0;display:flex;flex-direction:column;align-items:center;gap:3px">
              <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:${nx ? '#f0c46a' : '#8b8b86'}`}>{DN[i]!.toUpperCase()}</span>
              <span style={`font-family:${MONO};font-size:20px;font-weight:500;color:${d.on ? '#f2f2ee' : '#55554f'}`}>{d.time}</span>
            </button>
            <button onClick={() => set({ [d.key + '_aktiv']: !d.on })} aria-pressed={d.on} aria-label={DAG[i] + (d.on ? ' på' : ' av')} style="width:100%;height:44px;border:none;background:none;padding:0;display:flex;align-items:center;justify-content:center"><Bryter on={d.on} small /></button>
          </div>); })}
      </div>
      <span style={`font-size:12.5px;color:${wakeErr.value ? '#e05a4a' : a.running || a.skip ? '#f0c46a' : '#8b8b86'};padding-left:12px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{info}</span>
      <div style="flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:0 26px;padding-left:12px;align-content:start;overflow-y:auto;scrollbar-width:none;touch-action:pan-y">
        <div style="display:flex;flex-direction:column;gap:2px">
          <span style={lbl}>LYSET</span>
          {a.fade && Tall({ k: 'fade_opp', n: a.fade, title: 'Tones opp over', sub: 'Fra svakt til fullt lys' })}
          {a.off_after && Tall({ k: 'av_etter', n: a.off_after, title: 'Slukkes etter', sub: a.off_after.value ? 'Etter at lyset er fullt' : 'Lyset blir stående på' })}
          {a.night_light !== null && Valg({ k: 'nattlampe', on: a.night_light, title: 'Nattlampe', sub: 'Ta med nattlampen i vekkingen' })}
        </div>
        <div style="display:flex;flex-direction:column;gap:2px">
          <span style={lbl}>SØVN</span>
          {a.only_if_asleep !== null && Valg({ k: 'bare_hvis_sover', on: a.only_if_asleep, title: 'Bare hvis jeg sover', sub: 'Hopper over når du allerede er oppe' })}
          {a.wake_person !== null && Valg({ k: 'vekk_person', on: a.wake_person, title: 'Marker meg som våken', sub: 'Når lyset er tonet helt opp' })}
          {p && <div style="display:flex;align-items:center;gap:10px;min-height:48px">
            <span style={`width:10px;height:10px;border-radius:50%;margin:0 4px 0 21px;flex-shrink:0;background:${p.sleeping ? '#7c8cf0' : '#6fcf7f'}`} />
            <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0;margin-left:17px"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{(p.name || 'Du') + (p.sleeping ? ' sover' : ' er våken')}</span><span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.pct !== null ? p.pct + ' % sikker på søvn' : 'Fra KI Søvn'}</span></span>
            {p.can_set && <button onClick={() => set({ [p.sleeping ? 'sett_vaken' : 'sett_sover']: true })} style="height:40px;padding:0 14px;border-radius:20px;border:1px solid #2e2e30;background:#161617;font-size:12.5px;font-weight:600;white-space:nowrap;flex-shrink:0">{p.sleeping ? 'Jeg er våken' : 'God natt'}</button>}
          </div>}
        </div>
      </div>
      {a.can_test && <div style="display:flex;align-items:center;gap:10px;padding-left:12px;flex-shrink:0">
        <span style="flex:1;font-size:11.5px;color:#6b6b67;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{a.lights ? a.lights + ' lys er med. Hvilke lys velger du i Home Assistant.' : 'Ingen lys er valgt. Velg lys i Home Assistant.'}</span>
        <button onClick={() => set({ [a.running ? 'stopp' : 'test']: true })} style={`height:44px;padding:0 20px;border-radius:22px;border:1px solid ${a.running ? '#7a2a20' : '#2e2e30'};background:${a.running ? 'rgba(224,90,74,.12)' : '#161617'};color:${a.running ? '#e05a4a' : '#f2f2ee'};font-size:12.5px;font-weight:600;flex-shrink:0`}>{a.running ? 'Stopp vekkingen' : 'Prøv vekkingen nå'}</button>
      </div>}
      {pick >= 0 && <WakeTime a={a} day={pick} onClose={() => setPick(-1)} />}
    </div>
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

// Når ringeklokke-bildet lukkes: tilbake til skjermen, volumet og spill/pause slik det var før det ringte.
// Volumet før ringingen kommer fra enheten (doorbell.v0) – statusen kan allerede vise det dempede volumet.
let doorSnap: { vol: number; playing: boolean; scr: Scr; base: string } | null = null;
effect(() => {
  const d = door.value, v0 = dev().doorbell?.v0;
  if (d && doorSnap && typeof v0 === 'number' && !ctl.peek()) doorSnap.vol = v0;   // enheten meldte volumet før dempingen
  if (d && !doorSnap) {
    const s = status.peek();
    doorSnap = { vol: typeof v0 === 'number' && !ctl.peek() ? v0 : (s?.volume ?? -1), playing: !!s?.playing, scr: scr.peek(), base: ctl.peek() };
  } else if (!d && doorSnap) {
    const snap = doorSnap; doorSnap = null;
    setTimeout(() => {
      if (ctl.value !== snap.base) return;
      const s = status.value; if (!s) return;
      if (snap.vol >= 0 && s.volume !== snap.vol) setVolume(snap.vol, true);
      if (snap.playing !== !!s.playing) playPause();
      scr.value = snap.scr;
    }, 250);
  }
});

// ---------- ringeklokke ----------
function Door({ clock }: { clock: string }) {
  const [tick, setTick] = useState(0), [noCam, setNoCam] = useState(false);
  useEffect(() => { const iv = setInterval(() => setTick((x) => x + 1), 1000); return () => clearInterval(iv); }, []);
  // To trykk for å låse opp (så døren ikke åpnes ved et uhell): første trykk ber om bekreftelse i 4 sekunder
  const [bekreft, setBekreft] = useState(false), [lasFeil, setLasFeil] = useState('');
  useEffect(() => { if (!smart.value) void loadSmart(); }, []);
  useEffect(() => { if (!bekreft) return; const t = setTimeout(() => setBekreft(false), 4000); return () => clearTimeout(t); }, [bekreft]);
  const unlock = () => {
    if (unlocked.value) return;
    if (!bekreft) { setBekreft(true); setLasFeil(''); return; }
    setBekreft(false);
    void fetch(here() + '/api/touch/unlock', { method: 'POST' }).then(async (r) => {
      unlocked.value = r.ok;
      if (!r.ok) setLasFeil(((await r.json().catch(() => ({}))) as { error?: string }).error || 'Fikk ikke låst opp');
      else window.setTimeout(() => { unlocked.value = false; }, 8000);
    }).catch(() => setLasFeil('Fikk ikke kontakt med låsen'));
  };
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
        {!!smart.value?.lock && <button onClick={unlock} style={`height:56px;padding:0 22px;border-radius:28px;border:1px solid #f0c46a;background:${unlocked.value ? '#6fcf7f' : bekreft ? '#f0c46a' : 'rgba(22,22,23,.85)'};color:${unlocked.value || bekreft ? '#0b0b0c' : '#f0c46a'};display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600`}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 11h12v10H6zM8 11V7a4 4 0 0 1 7.5-2" /></svg>{unlocked.value ? 'Døren er låst opp' : bekreft ? 'Trykk igjen for å låse opp' : 'Lås opp døren'}</button>}
        {!!lasFeil && <span style="position:absolute;bottom:84px;left:0;right:0;text-align:center;font-size:13px;color:#ff8a7a">{lasFeil}</span>}
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
// ---------- hurtigpanel: dra ned fra toppkanten ----------
// Start i den øverste centimeteren (≈ 40 px på 7″-skjermen) og dra nedover: panelet følger fingeren og blir liggende
// åpent. Lysstyrke, volum og snarveier (skjermsparer, nattmodus, rom, søk, kameraer, Wi-Fi, lås opp).
const quick = signal(0);   // 0 = lukket (ikke montert), > 0 = montert. Posisjonen styres direkte i DOM-en (qSett).
// Fingeren flytter panelet uten å tegne Preact på nytt (jevnt også på Pi-en): transform og mørkleggingen settes rett på
// elementene. Slipp: fart og retning avgjør (et raskt drag opp lukker selv om panelet er nesten helt nede), ellers halvveis.
const qEl: { panel: HTMLDivElement | null; dim: HTMLDivElement | null } = { panel: null, dim: null };
let qP = 0, qAnim = false, qLukkT = 0;
const Q_KURVE = 'cubic-bezier(.32,.72,0,1)', Q_MS = 380;
function qStil(p: number): string {
  const over = Math.max(0, p - 1) * 36;   // gummistrikk når du drar forbi helt åpent
  return `translateY(calc(${(Math.min(1, p) - 1) * 100}% + ${over}px))`;
}
function qSett(p: number, anim: boolean): void {
  qP = p; qAnim = anim;
  const pa = qEl.panel, d = qEl.dim;
  if (pa) { pa.style.transition = anim ? `transform ${Q_MS}ms ${Q_KURVE}` : 'none'; pa.style.transform = qStil(p); }
  if (d) { d.style.transition = anim ? `opacity ${Q_MS}ms ease` : 'none'; d.style.opacity = String(Math.max(0, Math.min(1, p))); }
}
function qÅpne(): void { clearTimeout(qLukkT); if (!quick.value) quick.value = 1; requestAnimationFrame(() => qSett(1, true)); }
function qLukk(): void {
  qSett(0, true); clearTimeout(qLukkT);
  qLukkT = window.setTimeout(() => { if (qP <= 0) quick.value = 0; }, Q_MS);
}
const qDrag = { y0: -1, id: -1, aktiv: false, lukk: false, p0: 0, ly: 0, lt: 0, v: 0 };
const Q_KANT = 40;
const qHøyde = (): number => qEl.panel?.offsetHeight || 300;
addEventListener('pointerdown', (e) => {
  if (boot.value.on || door.value) return;
  const grep = (e.target as HTMLElement | null)?.closest?.('[data-qgrip]');
  if (quick.value && qP >= 0.99) {   // åpent: dra opp fra pillen (eller den mørke flaten) for å lukke
    if (!grep) return;
    Object.assign(qDrag, { y0: e.clientY, id: e.pointerId, aktiv: false, lukk: true, p0: qP, ly: e.clientY, lt: e.timeStamp, v: 0 });
    return;
  }
  if (e.clientY > Q_KANT) return;   // lukket: start i den øverste centimeteren (også i skjermspareren)
  Object.assign(qDrag, { y0: e.clientY, id: e.pointerId, aktiv: false, lukk: false, p0: 0, ly: e.clientY, lt: e.timeStamp, v: 0 });
}, { capture: true });
addEventListener('pointermove', (e) => {
  if (e.pointerId !== qDrag.id || qDrag.y0 < 0) return;
  const dy = e.clientY - qDrag.y0;
  if (!qDrag.aktiv && (qDrag.lukk ? Math.abs(dy) > 8 : dy > 8)) {
    qDrag.aktiv = true; clearTimeout(qLukkT);
    if (!quick.value) { qP = 0; quick.value = 1; }   // monter panelet; posisjonen settes under
  }
  if (!qDrag.aktiv) return;
  const dt = Math.max(1, e.timeStamp - qDrag.lt);
  qDrag.v = qDrag.v * 0.6 + ((e.clientY - qDrag.ly) / dt) * 0.4;   // px/ms, glattet
  qDrag.ly = e.clientY; qDrag.lt = e.timeStamp;
  let p = qDrag.p0 + dy / qHøyde();
  if (p > 1) p = 1 + (p - 1) * 0.35;
  qSett(Math.max(0, p), false);
  e.preventDefault();
}, { capture: true, passive: false });
const qSlipp = (e: PointerEvent) => {
  if (e.pointerId !== qDrag.id) return;
  if (qDrag.aktiv) {
    const v = qDrag.v, åpne = v > 0.45 ? true : v < -0.45 ? false : qP > 0.5;
    if (åpne) qÅpne(); else qLukk();
    sluk = Date.now() + 350;   // svelg klikket som følger
  }
  qDrag.y0 = -1; qDrag.id = -1; qDrag.aktiv = false;
};
addEventListener('pointerup', qSlipp, { capture: true });
addEventListener('pointercancel', qSlipp, { capture: true });

/** Stor glider som i kontrollsenteret på telefonen: hele pillen er trykkflate, fyllet viser nivået. */
function PilleGlid({ ikon, verdi, min = 0, sett, live, navn }: { ikon: string; verdi: number; min?: number; sett: (n: number) => void; live?: (n: number) => void; navn: string }) {
  const [v, setV] = useState<number | null>(null);
  const ref = useRef<HTMLDivElement | null>(null);
  const vis = Math.max(min, Math.min(100, v ?? verdi));
  const fra = (x: number) => { const r = ref.current!.getBoundingClientRect(); return Math.round(Math.max(min, Math.min(100, ((x - r.left) / r.width) * 100))); };
  return (
    <div ref={ref} role="slider" aria-label={navn} aria-valuenow={vis} class={'qglid' + (v !== null ? ' aktiv' : '')}
      onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); const n = fra(e.clientX); setV(n); live?.(n); }}
      onPointerMove={(e) => { if (v === null) return; const n = fra(e.clientX); if (n !== v) { setV(n); live?.(n); } }}
      onPointerUp={(e) => { if (v === null) return; sett(fra(e.clientX)); setV(null); }} onPointerCancel={() => setV(null)}>
      <div class="fyll" style={`transform:scaleX(${vis / 100})`} />
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" style="position:relative"><path d={ikon} /></svg>
      <span style="position:relative;flex:1;font-size:13px;font-weight:600">{navn}</span>
      <span style={`position:relative;font-family:${MONO};font-size:13px;font-variant-numeric:tabular-nums`}>{vis}</span>
    </div>);
}

function QuickPanel() {
  const S = settings.value, st = status.value;
  const night = (S.tNightMode ?? 0) === 3;
  const [nå, setNå] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setNå(new Date()), 15000); return () => clearInterval(t); }, []);
  const lukk = () => { qLukk(); };
  // Flis: ikon i en sirkel, navn og tilstand. På = gull. Rippel fra fingeren (se rippel() nedenfor) + fjærende trykk.
  const flis = (navn: string, d: string, gjor: () => void, på = false, under?: string, i = 0) => (
    <button class={'qflis rip' + (på ? ' på' : '') + (navn === 'Nattmodus' ? ' måne' : '')} onClick={() => { gjor(); }} style={`animation-delay:${60 + i * 28}ms`} aria-pressed={på}>
      <span class="sirkel"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg></span>
      <span class="tekst"><b>{navn}</b>{under !== undefined && <small>{under}</small>}</span>
    </button>);
  const gå = (sk: Scr, f?: () => void) => () => { lukk(); wake(); scr.value = sk; f?.(); };   // snarveier vekker skjermen
  const lys = S.tBright ?? 100, vol = st?.volume ?? 0;
  const tittel = st?.title || st?.radio_now?.name || st?.station || '';
  const MÅNE = 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z';
  return (
    <div data-ss-tip style="position:absolute;inset:0;z-index:40">
      <div data-qgrip ref={(el) => { qEl.dim = el; }} onClick={lukk} class="qdim" style={`opacity:${Math.max(0, Math.min(1, qP))};transition:${qAnim ? `opacity ${Q_MS}ms ease` : 'none'}`} />
      <div ref={(el) => { qEl.panel = el; }} class="qpanel" style={`transform:${qStil(qP)};transition:${qAnim ? `transform ${Q_MS}ms ${Q_KURVE}` : 'none'}`}>
        <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:12px;padding:2px 4px 2px">
          <span style="display:flex;flex-direction:column;line-height:1"><b style="font-size:30px;font-weight:300;letter-spacing:-.02em;font-variant-numeric:tabular-nums">{nå.toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' })}</b>
            <span style="font-size:12px;color:#8b8b86;margin-top:4px;text-transform:capitalize">{nå.toLocaleDateString('nb-NO', { weekday: 'long', day: 'numeric', month: 'long' })}</span></span>
          <span style="display:flex;gap:6px;align-items:center">
            <span class="qchip"><i style={`background:${online.value ? '#6fcf7f' : '#e05a4a'}`} />{online.value ? 'Tilkoblet' : 'Frakoblet'}</span>
            {night && <span class="qchip gull"><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d={MÅNE} /></svg>Natt</span>}
          </span>
        </div>
        {tittel && <div class="qspiller qinn" style="animation-delay:40ms">
          <span class="cover" style={`background:${artOf(st)}`} />
          <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px"><b style="font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{tittel}</b><span style="font-size:12px;color:#a9a9a3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{st?.artist || srcName(st)}</span></span>
          <button class="rip rund" onClick={playPause} style="background:#f2f2ee;width:40px;height:40px" aria-label={st?.playing ? 'Pause' : 'Spill'}><svg width="20" height="20" viewBox="0 0 24 24" fill="#0b0b0c"><path d={st?.playing ? PAUSE_D : PLAY_D} /></svg></button>
          <button class="rip rund" onClick={() => void act(() => api.transport('next'))} aria-label="Neste"><svg width="20" height="20" viewBox="0 0 24 24" fill="#f2f2ee"><path d="M5 5.5v13a.8.8 0 0 0 1.25.66L15 13.1V18a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v4.9L6.25 4.84A.8.8 0 0 0 5 5.5z" /></svg></button>
        </div>}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px" class="qinn">
          <PilleGlid navn="Lysstyrke" ikon="M12 4v2M12 18v2M4 12h2M18 12h2M6.3 6.3l1.4 1.4M16.3 16.3l1.4 1.4M6.3 17.7l1.4-1.4M16.3 7.7l1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" verdi={lys} min={20} sett={(n) => setSetting('tBright', n)} />
          <PilleGlid navn="Volum" ikon="M4 9v6h4l5 4V5L8 9H4zM16 9a4 4 0 0 1 0 6" verdi={vol} sett={(n) => setVolume(n, true)} live={(n) => setVolume(n)} />
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px">
          {flis('Nattmodus', MÅNE, () => { setSetting('tNightMode', night ? 0 : 3); setSetting('tNight', false); }, night, night ? 'På' : 'Av', 0)}
          {flis('Skjermsparer', 'M3 5h18v12H3zM8 21h8M12 17v4', () => { lukk(); goIdle(); }, false, 'Nå', 1)}
          {flis('Rom', 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', gå('rooms'), false, undefined, 2)}
          {flis('Søk', 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.5-3.5', gå('lib', () => { searchOpen.value = true; }), false, undefined, 3)}
          {flis('Kameraer', 'M3 7h12v10H3zM15 10l6-3v10l-6-3', gå('smart', () => { camOpen.value = true; }), false, undefined, 4)}
          {flis('Wi-Fi', 'M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01', gå('set', () => { wifiOpen.value = true; }), online.value, online.value ? 'Tilkoblet' : 'Av', 5)}
          {flis('Smarthus', 'M3 11l9-7 9 7v9H3zM9 20v-6h6v6', gå('smart'), false, undefined, 6)}
          {flis('Oppsett', 'M4 7h10M18 7h2M4 17h4M12 17h8M14 5v4M8 15v4', gå('set'), false, undefined, 7)}
        </div>
        <div data-qgrip style="align-self:stretch;display:flex;justify-content:center;align-items:center;height:30px;margin:-2px -18px -10px;touch-action:none" aria-label="Dra opp for å lukke">
          <div style="width:44px;height:5px;border-radius:3px;background:#4a4a4e" />
        </div>
      </div>
    </div>
  );
}

// ---------- rippel: som på Android/iOS – en myk bølge fra fingeren på knapper og fliser ----------
addEventListener('pointerdown', (e) => {
  const b = (e.target as HTMLElement | null)?.closest?.('button.rip, button.qflis, [data-rip]') as HTMLElement | null;
  if (!b || (b as HTMLButtonElement).disabled) return;
  const r = b.getBoundingClientRect(), d = Math.hypot(Math.max(e.clientX - r.left, r.right - e.clientX), Math.max(e.clientY - r.top, r.bottom - e.clientY)) * 2;
  const w = document.createElement('span');
  w.className = 'rippel';
  w.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`;
  b.appendChild(w);
  const bort = () => { w.classList.add('ut'); window.setTimeout(() => w.remove(), 420); removeEventListener('pointerup', bort); removeEventListener('pointercancel', bort); };
  addEventListener('pointerup', bort); addEventListener('pointercancel', bort);
}, { capture: true });

// ---------- Dørlås (Home Assistant) til «Lås opp» når det ringer på ----------
interface LasVal { ok: boolean; locks: { id: string; name: string }[]; valgt: string; bruker: string; error?: string }
const lasVal = signal<LasVal | null>(null);
function hentLaser(): void { getAt<LasVal>('', '/api/touch/locks').then((r) => { lasVal.value = r; }).catch(() => {}); }
effect(() => { if (scr.value === 'set') hentLaser(); });
const lasValg = (): string[] => ['', '-', ...(lasVal.value?.locks ?? []).map((l) => l.id)];   // '' = automatisk, '-' = av
function lasNavn(): string {
  const v = lasVal.value; if (!v) return '…';
  if (v.valgt === '-') return 'Av';
  if (!v.valgt) return v.bruker ? 'Auto · ' + (v.locks.find((l) => l.id === v.bruker)?.name ?? v.bruker) : 'Auto';
  return v.locks.find((l) => l.id === v.valgt)?.name ?? v.valgt.replace('lock.', '');
}
function byttLas(d: number): void {
  const o = lasValg(), i = Math.max(0, o.indexOf(lasVal.value?.valgt ?? '')), ny = o[(i + d + o.length) % o.length] ?? '';
  if (lasVal.value) lasVal.value = { ...lasVal.value, valgt: ny };
  void postAt('', '/api/touch', { lock_entity: ny }).then(() => { hentLaser(); void loadSmart(); });
}

// ---------- Wi-Fi: koble til et nytt nett ----------
const wifiOpen = signal(false), wifiNow = signal('');
function hentWifiNå(): void { getAt<{ networks: { ssid: string; active?: boolean }[] }>('', '/api/wifi').then((r) => { wifiNow.value = r.networks.find((n) => n.active)?.ssid ?? ''; }).catch(() => {}); }
effect(() => { if (scr.value === 'set') hentWifiNå(); });

function Qr({ text, size }: { text: string; size: number }) {
  let m: boolean[][];
  try { m = qrMatrix(text); } catch { return null; }
  const n = m.length, q = 2, d: string[] = [];
  m.forEach((row, y) => row.forEach((on, x) => { if (on) d.push(`M${x + q} ${y + q}h1v1h-1z`); }));
  return <svg width={size} height={size} viewBox={`0 0 ${n + q * 2} ${n + q * 2}`} shape-rendering="crispEdges" style="background:#fff;border-radius:10px;display:block;flex-shrink:0"><path d={d.join('')} fill="#0b0b0c" /></svg>;
}

type WNet = { ssid: string; security?: string; signal?: number; active?: boolean };
function WifiSetup({ innebygd, onLukk }: { innebygd?: boolean; onLukk?: () => void } = {}) {
  const [tab, setTab] = useState(0);
  const [nets, setNets] = useState<WNet[] | null>(null), [valgt, setValgt] = useState<WNet | null>(null);
  const pwt = useTekst(63), pw = pwt.v, setPw = pwt.sett;
  const [vis, setVis] = useState(false), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false), [feilet, setFeilet] = useState(false);
  const husk = useRef<Record<string, string>>({});   // sist skrevne passord per nett (til «Prøv igjen» etter Tilbake)
  const ble = dev().ble_setup;
  const skann = () => { setNets(null); getAt<{ networks: WNet[] }>('', '/api/wifi').then((r) => { const sett = new Set<string>(); setNets(r.networks.filter((n) => n.ssid && !n.ssid.startsWith('Skjold-oppsett-') && !sett.has(n.ssid) && !!sett.add(n.ssid))); }).catch(() => setNets([])); };
  useEffect(() => { skann(); }, []);
  const koble = async (n: WNet, psk: string) => {
    setBusy(true); setFeilet(false); setMsg('Kobler til «' + n.ssid + '» …'); if (psk) husk.current[n.ssid] = psk;
    try {
      const r = await fetch(here() + '/api/wifi', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ssid: n.ssid, psk }) });
      const j = await r.json().catch(() => ({})) as { error?: string; pending?: boolean };
      const jj = j as { pending?: boolean };
      if (r.ok && jj.pending) { setMsg('Kobler til «' + n.ssid + '» …'); onLukk?.(); }   // fra oppsett-nettet: Touch bytter nett nå
      else if (r.ok) { setMsg('Koblet til «' + n.ssid + '»'); wifiNow.value = n.ssid; setValgt(null); setPw(''); window.setTimeout(() => { wifiOpen.value = false; onLukk?.(); }, 1500); }
      else { setMsg(j.error || 'Fikk ikke koblet til. Sjekk passordet.'); setFeilet(true); }
    } catch { setMsg('Fikk ikke svar. Touch bytter kanskje nett – vent litt.'); setFeilet(true); }
    setBusy(false);
  };
  const åpent = (n: WNet) => (n.security ?? '') === 'open';
  const TABS = ['På skjermen', 'Med mobilen', 'Bluetooth'];
  const bar = (p: number) => <span style="display:flex;gap:2px;align-items:flex-end;height:14px">{[0, 1, 2, 3].map((i) => <i key={i} style={`width:3px;height:${4 + i * 3}px;border-radius:1px;background:${(p ?? 0) > i * 25 ? '#f2f2ee' : '#3a3a37'}`} />)}</span>;
  const steg = (i: number, t: string, b: preact.ComponentChildren) => <div style="display:flex;gap:12px;align-items:flex-start"><span style={`width:26px;height:26px;flex-shrink:0;border-radius:13px;background:#1c170d;border:1px solid #d9a441;color:#f0c46a;font-family:${MONO};font-size:12px;display:flex;align-items:center;justify-content:center`}>{i}</span><span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px;font-weight:600">{t}</span><span style="font-size:12.5px;line-height:1.4;color:#a8a8a3">{b}</span></span></div>;
  return (
    <div class="inn" style={`position:absolute;inset:${innebygd ? '0' : '52px 0 0 0'};z-index:${innebygd ? 23 : 6};background:#0b0b0c;display:flex;flex-direction:column`}>
      <div style="display:flex;align-items:center;gap:8px;padding:8px 14px 8px 6px;flex-shrink:0">
        <button onClick={() => { if (valgt) { setValgt(null); setPw(''); setMsg(''); setFeilet(false); } else if (onLukk) onLukk(); else wifiOpen.value = false; }} aria-label="Tilbake" style="width:44px;height:44px;border:none;background:none;color:#c9c9c4;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg></button>
        <span style="font-size:19px;font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{valgt ? 'Passord for «' + valgt.ssid + '»' : 'Koble til Wi-Fi'}</span>
        {!valgt && !innebygd && TABS.map((n, i) => <button key={n} onClick={() => setTab(i)} style={`height:40px;padding:0 14px;border-radius:20px;border:1px solid ${tab === i ? '#f2f2ee' : '#2e2e30'};background:${tab === i ? '#f2f2ee' : '#161617'};color:${tab === i ? '#0b0b0c' : '#c9c9c4'};font-size:12.5px;font-weight:600;white-space:nowrap`}>{n}</button>)}
      </div>
      {valgt ? <>
        <div style="flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 20px">
          <div style="display:flex;align-items:center;gap:10px;height:48px;border-radius:12px;border:1px solid #2e2e30;background:#141415;padding:0 14px">
            <TekstFelt t={pwt} skjul={!vis} tom="Passord" />
            <button onClick={() => setVis(!vis)} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:#242426;color:#c9c9c4;font-size:12px;font-weight:600">{vis ? 'Skjul' : 'Vis'}</button>
          </div>
          {msg && <span style={`font-size:13px;color:${/Koblet til/.test(msg) ? '#6fcf7f' : /Kobler/.test(msg) ? '#c9c9c4' : '#ff8a7a'}`}>{msg}</span>}
          {feilet && !busy && <div style="display:flex;gap:8px">
            <button onClick={() => void koble(valgt, pw)} disabled={pw.length < 8} style="height:40px;padding:0 18px;border-radius:20px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13px;font-weight:600">Prøv igjen med samme passord</button>
            <button onClick={() => { setPw(''); setFeilet(false); setMsg(''); }} style="height:40px;padding:0 18px;border-radius:20px;border:1px solid #2e2e30;background:#161617;color:#f2f2ee;font-size:13px;font-weight:600">Skriv nytt passord</button>
          </div>}
        </div>
        <Keyboard pw enter={busy ? 'Kobler til …' : 'Koble til'} onKey={pwt.inn} onBack={pwt.slett} onFlytt={pwt.flytt} onEnter={() => { if (!busy && pw.length >= 8) void koble(valgt, pw); else if (pw.length < 8) setMsg('Passordet må ha minst 8 tegn'); }} />
      </> : tab === 0 || innebygd ? (
        <div style="flex:1;min-height:0;overflow-y:auto;touch-action:pan-y;display:flex;flex-direction:column;gap:6px;padding:4px 14px 14px">
          {msg && <span style="font-size:13px;color:#c9c9c4;padding:2px 4px">{msg}</span>}
          {nets === null && <span style={`padding:12px 4px;font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#8b8b86`}>SØKER ETTER NETT …</span>}
          {nets?.length === 0 && <span style="padding:12px 4px;font-size:13.5px;color:#8b8b86">Fant ingen nett. Prøv igjen, eller bruk mobilen.</span>}
          {(nets ?? []).map((n) => (
            <button key={n.ssid} onClick={() => { setMsg(''); if (n.active) return; if (åpent(n)) void koble(n, ''); else { setValgt(n); setPw(husk.current[n.ssid] ?? ''); setFeilet(false); } }} style={`min-height:52px;flex-shrink:0;border-radius:12px;border:1px solid ${n.active ? '#d9a441' : '#242426'};background:${n.active ? '#1c170d' : '#141415'};display:flex;align-items:center;gap:12px;padding:0 16px;text-align:left`}>
              {bar(n.signal ?? 0)}
              <span style={`flex:1;min-width:0;font-size:15px;font-weight:600;color:${n.active ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{n.ssid}</span>
              <span style="font-size:11.5px;color:#8b8b86">{n.active ? 'Tilkoblet' : åpent(n) ? 'Åpent' : '🔒'}</span>
            </button>))}
          {nets !== null && <button onClick={skann} style="align-self:flex-start;margin-top:4px;height:40px;padding:0 16px;border-radius:20px;border:1px solid #2e2e30;background:#161617;font-size:12.5px;font-weight:600">Søk på nytt</button>}
        </div>
      ) : tab === 1 ? (
        <div style="flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:24px;align-items:center;padding:0 24px 14px">
          <div style="display:flex;flex-direction:column;gap:14px">
            {steg(1, 'Trykk «Start» her', 'Touch lager sitt eget oppsett-nett. Mens du gjør dette, er Touch ikke på hjemmenettet.')}
            {steg(2, 'Skann QR-koden med mobilen', 'Mobilen kobler seg til oppsett-nettet, og siden for å velge nett åpner seg av seg selv.')}
            {steg(3, 'Velg nett på mobilen', 'Mobilen viser nettene Touch ser. Velg ditt, skriv passordet med mobilens tastatur – ferdig.')}
          </div>
          <div style="display:flex;flex-direction:column;align-items:center;gap:12px">
            <button onClick={() => { setBusy(true); void postAt('', '/api/oppsett', { start: true }).finally(() => { setBusy(false); wifiOpen.value = false; }); }} style="height:52px;width:100%;border-radius:26px;border:none;background:#f0c46a;color:#0b0b0c;font-size:15px;font-weight:600">{busy ? 'Starter …' : 'Start'}</button>
            <span style="font-size:12px;color:#8b8b86;text-align:center;line-height:1.4">QR-koden vises på skjermen når oppsett-nettet er klart. Avbryt når som helst.</span>
          </div>
        </div>
      ) : (
        <div style="flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 200px;gap:24px;align-items:center;padding:0 24px 14px">
          <div style="display:flex;flex-direction:column;gap:12px">
            {steg(1, 'Trykk «Start Bluetooth»', 'Touch blir synlig over Bluetooth som «' + (local.value?.name || 'Skjold') + '» i 10 minutter.')}
            {steg(2, 'Åpne improv-wifi.com på mobilen', 'Skann QR-koden, trykk «Connect device to Wi-Fi» og velg Touch. Virker i Chrome på Android (ikke Safari på iPhone – bruk «Med mobilen» der).')}
            {steg(3, 'Velg nett og skriv passordet', 'Mobilen sender det til Touch over Bluetooth. Touch kobler til og viser når den er ferdig.')}
            {ble && <span style={`font-size:13.5px;font-weight:600;color:${ble.state === 'done' ? '#6fcf7f' : ble.state === 'error' ? '#ff8a7a' : '#f0c46a'}`}>
              {ble.state === 'ready' ? 'Synlig over Bluetooth – venter på mobilen …' : ble.state === 'starting' ? 'Starter Bluetooth …' : ble.state === 'connecting' ? 'Kobler til «' + ble.ssid + '» …' : ble.state === 'done' ? 'Koblet til «' + ble.ssid + '»' : ble.state === 'error' ? (ble.error || 'Noe gikk galt') : 'Bluetooth-oppsettet er stoppet'}</span>}
          </div>
          <div style="display:flex;flex-direction:column;align-items:center;gap:10px">
            <Qr text="https://www.improv-wifi.com/" size={150} />
            {ble && ['starting', 'ready', 'connecting'].includes(ble.state)
              ? <button onClick={() => void postAt('', '/api/oppsett', { ble: false })} style="height:46px;width:100%;border-radius:23px;border:1px solid #2e2e30;background:#161617;color:#f2f2ee;font-size:14px;font-weight:600">Stopp</button>
              : <button onClick={() => void postAt('', '/api/oppsett', { ble: true })} style="height:46px;width:100%;border-radius:23px;border:none;background:#f0c46a;color:#0b0b0c;font-size:14px;font-weight:600">Start Bluetooth</button>}
          </div>
        </div>
      )}
    </div>
  );
}

function SetupNet() {
  const n = dev().setup_net!;
  const [skjerm, setSkjerm] = useState(false), [busy, setBusy] = useState(false);
  const eth = n.ethernet, kabel = !!n.kabel && !n.joining;
  const steg = (i: number, a: string, b: preact.ComponentChildren) => (
    <div style="display:flex;gap:14px;align-items:flex-start">
      <span style={`width:30px;height:30px;flex-shrink:0;border-radius:15px;background:#1c170d;border:1px solid #d9a441;color:#f0c46a;font-family:${MONO};font-size:13px;display:flex;align-items:center;justify-content:center`}>{i}</span>
      <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px;font-weight:600">{a}</span><span style="font-size:13px;line-height:1.4;color:#a8a8a3">{b}</span></span>
    </div>);
  const kode = `font-family:${MONO};color:#f0c46a`;
  const send = (b: Record<string, unknown>) => { setBusy(true); void postAt('', '/api/oppsett', b).finally(() => setBusy(false)); };
  // valgene øverst til høyre: på skjermen, med mobilen (standard, QR) og kabel (bare når Touch har Ethernet-port)
  const valg = (navn: string, ikon: string, på: boolean, gjør: () => void) => (
    <button onClick={gjør} disabled={busy} style={`height:44px;padding:0 16px 0 12px;border-radius:22px;border:1px solid ${på ? '#d9a441' : '#2e2e30'};background:${på ? '#1c170d' : '#161617'};color:${på ? '#f0c46a' : '#f2f2ee'};display:flex;align-items:center;gap:9px;font-size:14px;font-weight:600;white-space:nowrap`}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d={ikon} /></svg>{navn}</button>);
  const IK_SKJERM = 'M3 5h18v11H3zM8 20h8M12 16v4', IK_MOBIL = 'M7 2h10v20H7zM11 18h2', IK_KABEL = 'M6 3v5M10 3v5M4 8h8v4a4 4 0 0 1-8 0zM8 16v5h9a3 3 0 0 0 3-3v-6';
  const ethTekst = !eth ? '' : eth.state.startsWith('connected') ? 'Tilkoblet med kabel – et øyeblikk …'
    : eth.state.startsWith('connecting') ? 'Kabel funnet – henter adresse fra ruteren …'
    : eth.state === 'unavailable' ? 'Ingen kabel ennå' : 'Kabel funnet – venter på ruteren …';
  return (
    <div style="position:absolute;inset:0;z-index:22;background:#0b0b0c;display:grid;grid-template-columns:300px minmax(0,1fr);animation:tinn .4s ease both">
      <div style="display:flex;flex-direction:column;justify-content:center;gap:14px;padding:0 30px;background:#101011;border-right:1px solid #1f1f21">
        <div style="display:flex;gap:5px;align-items:flex-start;height:52px">{BARS.map((h, i) => <div key={i} style={`width:8px;height:${h * 2}px;border-radius:4px;background:${i === 2 ? '#d9a441' : '#f2f2ee'}`} />)}</div>
        <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#f0c46a`}>{n.joining ? 'KOBLER TIL' : kabel ? 'KABEL' : n.manual ? 'NYTT WI-FI' : 'IKKE PÅ NETT'}</span>
        <span style="font-size:28px;font-weight:600;line-height:1.12;letter-spacing:-.01em">{n.joining ? 'Kobler til «' + n.joining + '»' : kabel ? 'Koble til med kabel' : 'Koble Touch til nettet'}</span>
        {!!n.error && !n.joining && <span style="font-size:13px;line-height:1.4;color:#e05a4a">{n.error}</span>}
      </div>
      <div style="display:flex;flex-direction:column;justify-content:center;gap:18px;padding:0 32px">
        {n.joining ? <>
          {steg(1, 'Touch kobler til «' + n.joining + '»', 'Det tar opptil et halvt minutt. Går det ikke, kommer denne siden tilbake med en melding.')}
        </> : <>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            {valg('På skjermen', IK_SKJERM, false, () => { if (kabel) send({ kabel: false }); setSkjerm(true); })}
            {valg('Med mobilen', IK_MOBIL, !kabel, () => { if (kabel) send({ kabel: false }); })}
            {!!eth && valg('Kabel', IK_KABEL, kabel, () => { if (!kabel) send({ kabel: true }); })}
          </div>
          {kabel ? <>
            {steg(1, 'Sett en nettverkskabel i Ethernet-porten', 'Den andre enden i ruteren eller en svitsj. Wi-Fi-oppsettet er slått av så lenge.')}
            {steg(2, 'Touch kobler til av seg selv', 'Denne siden forsvinner når Touch er på nett. Wi-Fi kan du sette opp senere under Innstillinger.')}
            <span style={`font-size:14px;font-weight:600;color:${eth?.state.startsWith('connected') ? '#6fcf7f' : eth?.state === 'unavailable' ? '#a8a8a3' : '#f0c46a'}`}>{ethTekst}</span>
            <span style="font-size:12px;color:#6b6b67">Kommer det ingen kabel innen 10 minutter, slås Wi-Fi-oppsettet på igjen.</span>
          </> : !n.active ? (
            <span style="font-size:14px;color:#a8a8a3">Starter oppsett-nettet …</span>
          ) : <>
            <div style="display:flex;gap:16px;align-items:center">
              {!!n.qr && <Qr text={n.qr} size={120} />}
              {steg(1, 'Skann QR-koden med mobilen', <>Eller koble til nettet <span style={kode}>{n.ssid}</span> med passordet <span style={kode}>{n.password}</span></>)}
            </div>
            {steg(2, 'Velg hjemmenettet ditt', <>Oppsettsiden åpner seg selv. Skjer det ikke, gå til <span style={kode}>{n.url.replace('http://', '')}</span>. Eller i Skjold-appen: <b>Legg til enhet → Enheten er ikke på nett</b> med koden <span style={kode}>{n.ssid.replace('Skjold-oppsett-', '')}</span></>)}
            {steg(3, 'Ferdig', 'Touch slår av oppsett-nettet og kobler til. Denne siden forsvinner av seg selv.')}
          </>}
          {n.manual && <button onClick={() => send({ stop: true })} style="align-self:flex-start;height:44px;padding:0 20px;border-radius:22px;border:1px solid #2e2e30;background:#161617;color:#f2f2ee;font-size:13.5px;font-weight:600">Avbryt – bruk nettet som før</button>}
        </>}
      </div>
      {skjerm && !n.joining && <WifiSetup innebygd onLukk={() => setSkjerm(false)} />}
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

// ---------- omstart: hold av/på-knappen (på skjermen nederst til venstre, eller den fysiske) i 3 s ----------
const HOLD_MS = 3000;
const pwrHold = signal(0);          // 0 = ikke holdt, ellers fremdrift 0–1 fra skjermknappen
const restarting = signal(false);   // omstart er sendt fra skjermen
let holdT = 0, holdStart = 0, holdDone = false;
function holdTick(): void {
  const p = Math.min(1, (Date.now() - holdStart) / HOLD_MS);
  pwrHold.value = p;
  if (p >= 1 && !holdDone) {
    holdDone = true; restarting.value = true; void postAt('', '/api/reboot', {}).catch(() => {});
    setTimeout(() => { restarting.value = false; }, 90000);   // startet den likevel ikke på nytt: tilbake til skjermen
    return;
  }
  if (!holdDone) holdT = requestAnimationFrame(holdTick);
}

function PowerHold() {
  const p = pwrHold.value, R = 20, C = 2 * Math.PI * R;
  // På nettbrettet starter ikke et langt trykk Skjold-enheten på nytt – knappen viser bare skjermspareren
  const start = (e: PointerEvent) => { e.preventDefault(); holdStart = Date.now(); holdDone = false; cancelAnimationFrame(holdT); if (!TABLET) holdT = requestAnimationFrame(holdTick); };
  const end = (kort: boolean) => { cancelAnimationFrame(holdT); const holdt = Date.now() - holdStart; const ferdig = holdDone; pwrHold.value = 0; holdStart = 0; if (kort && !ferdig && holdt < 600) goIdle(); };
  return (
    <button onPointerDown={start} onPointerUp={() => end(true)} onPointerCancel={() => end(false)} onPointerLeave={() => { if (holdStart) end(false); }}
      aria-label="Standby (hold for å starte på nytt)" style="position:relative;width:44px;height:44px;margin-bottom:-2px;border-radius:22px;border:1px solid #2e2e30;background:transparent;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0;touch-action:none">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0" /></svg>
      {p > 0 && <svg width="48" height="48" viewBox="0 0 48 48" style="position:absolute;left:-3px;top:-3px;transform:rotate(-90deg);pointer-events:none"><circle cx="24" cy="24" r={R} fill="none" stroke="#d9a441" stroke-width="3" stroke-linecap="round" stroke-dasharray={`${(C * p).toFixed(1)} ${C.toFixed(1)}`} /></svg>}
    </button>
  );
}

/** Fullskjerm mens knappen holdes (fyller en ring rundt logoen) og når Skjold starter på nytt (stolpene toner ut én etter én). */
function RebootLayer() {
  const D = dev(), fys = D.hold?.key === 'reboot' ? D.hold.p : 0;
  const p = Math.max(pwrHold.value, fys), gaar = restarting.value || !!D.rebooting, av = !!D.poweroff;
  const [t, setT] = useState(0);
  useEffect(() => { if (!gaar) { setT(0); return undefined; } const t0 = Date.now(); const id = setInterval(() => setT(Date.now() - t0), 50); return () => clearInterval(id); }, [gaar]);
  if (!gaar && p < 0.12) return null;
  const R = 92, C = 2 * Math.PI * R, BH = [30, 46, 58, 46, 30];
  const vis = gaar ? 1 : Math.min(1, (p - 0.12) / 0.15);
  return (
    <div style={`position:absolute;inset:0;z-index:40;background:rgba(0,0,0,${gaar ? 1 : 0.86});display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;opacity:${vis};transition:background .5s ease`}>
      <div style="position:relative;width:220px;height:220px;display:flex;align-items:center;justify-content:center">
        <svg width="220" height="220" viewBox="0 0 220 220" style="position:absolute;inset:0;transform:rotate(-90deg)">
          <circle cx="110" cy="110" r={R} fill="none" stroke="#1c1c1e" stroke-width="4" style={`opacity:${gaar ? Math.max(0, 1 - t / 1400) : 1}`} />
          <circle cx="110" cy="110" r={R} fill="none" stroke="#d9a441" stroke-width="4" stroke-linecap="round" stroke-dasharray={`${(C * (gaar ? 1 : p)).toFixed(1)} ${C.toFixed(1)}`} style={`opacity:${gaar ? Math.max(0, 1 - t / 1400) : 1};transition:opacity .3s`} />
        </svg>
        <div style="display:flex;align-items:flex-start;gap:7px;height:58px">
          {BH.map((h, i) => { const ut = gaar ? Math.min(1, Math.max(0, (t - 500 - i * 220) / 420)) : 0; return (
            <div key={i} style={`width:10px;height:${h * (1 - ut * 0.85)}px;border-radius:5px;background:${i === 2 ? '#d9a441' : '#f2f2ee'};opacity:${1 - ut};transition:height .2s linear`} />); })}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:6px">
        <span style="font-size:24px;font-weight:600;color:#f2f2ee">{gaar ? (av ? 'Slår av …' : 'Starter på nytt …') : p >= 1 ? 'Slipp' : 'Hold for å starte på nytt'}</span>
        <span style={`font-family:${MONO};font-size:11px;letter-spacing:.14em;color:#8b8b86`}>{gaar ? (av ? 'SKJOLD SLÅS AV' : 'TILBAKE OM ET MINUTT') : 'SLIPP FOR Å AVBRYTE'}</span>
      </div>
    </div>
  );
}

// ---------- Forslag på skjermspareren ----------
// «Vil du høre på P3?» (kanalen du pleier å høre på denne tiden av døgnet) og «2 nye episoder av …» (favorittpodkastene).
// Trykk på forslaget spiller uten å vekke skjermen; krysset skjuler det. Av/på under Oppsett → Skjermsparer.
interface Tip { key: string; kicker: string; text: string; art: string; go: () => void }
const tips = signal<Tip[]>([]), tipI = signal(0);
const TIP_SEEN = 'skjold-touch-tips-sett', RADIO_LOG = 'skjold-touch-radiotimer';
const lsGet = <T,>(k: string, d: T): T => { try { return (JSON.parse(localStorage.getItem(k) || 'null') as T) ?? d; } catch { return d; } };
const lsSet = (k: string, v: unknown) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* full lagring */ } };
// Husk hvilken kanal som spilles når på døgnet (teller per time), så forslaget passer tiden
let radioLogT = 0;
effect(() => {
  const st = local.value;
  if (!st?.playing || st.input !== 'radio' || !st.preset || Date.now() - radioLogT < 5 * 60000) return;
  radioLogT = Date.now();
  const log = lsGet<Record<string, Record<string, number>>>(RADIO_LOG, {}), h = String(new Date().getHours());
  log[h] = { ...(log[h] ?? {}), [String(st.preset)]: (log[h]?.[String(st.preset)] ?? 0) + 1 };
  lsSet(RADIO_LOG, log);
});
function radioTip(): Tip | null {
  const f = favs.value.filter((x) => x.url || x.n);
  if (!f.length) return null;
  const log = lsGet<Record<string, Record<string, number>>>(RADIO_LOG, {}), h = new Date().getHours(), sc: Record<string, number> = {};
  for (const d of [-1, 0, 1]) for (const [n, c] of Object.entries(log[String((h + d + 24) % 24)] ?? {})) sc[n] = (sc[n] ?? 0) + c * (d ? 1 : 2);
  const best = Object.entries(sc).sort((a, b) => b[1] - a[1])[0];
  const fav = (best && f.find((x) => String(x.n) === best[0])) || f[0]!;
  return { key: 'radio:' + fav.n, kicker: best ? 'RADIO · DU PLEIER Å HØRE PÅ DENNE NÅ' : 'RADIO', text: 'Vil du høre på ' + fav.title + '?', art: artBg(fav.title, fav.image), go: () => { playFav(fav); gestVis('Spiller ' + fav.title); } };
}
async function loadTips(): Promise<void> {
  if (settings.value.tTips === false) { tips.value = []; return; }
  const sett = new Set(lsGet<string[]>(TIP_SEEN, [])), out: Tip[] = [];
  try {
    const nye = (await api.podNew()).items.filter((e) => !e.heard && !e.pos && !sett.has('ep:' + e.id) && (!e.ts || Date.now() / 1000 - e.ts < 7 * 86400));
    const per = new Map<string, PodEpisode[]>();
    for (const e of nye) per.set(e.show, [...(per.get(e.show) ?? []), e]);
    for (const [show, eps] of per) {
      const e = eps[0]!;
      out.push({ key: 'ep:' + e.id, kicker: 'PODKAST · ' + (eps.length > 1 ? eps.length + ' NYE EPISODER' : 'NY EPISODE'),
        text: eps.length > 1 ? 'Du har ' + eps.length + ' nye episoder av «' + show + '»' : 'Ny episode av «' + show + '»: ' + e.title,
        art: artBg(show, e.image), go: () => { void playPodTouch(e); gestVis('Spiller ' + show); eps.forEach((x) => sett.add('ep:' + x.id)); lsSet(TIP_SEEN, [...sett].slice(-300)); } });
    }
  } catch { /* uten podkaster */ }
  const r = radioTip();
  if (r && !sett.has(r.key + ':' + new Date().toDateString())) out.push(r);
  tips.value = out; tipI.value = 0;
}
function skjulTip(t: Tip): void {
  const sett = lsGet<string[]>(TIP_SEEN, []);
  sett.push(t.key.startsWith('radio:') ? t.key + ':' + new Date().toDateString() : t.key);   // radioforslaget kommer igjen i morgen
  lsSet(TIP_SEEN, sett.slice(-300));
  tips.value = tips.value.filter((x) => x.key !== t.key);
}
effect(() => { if (idle.value) void loadTips(); });
setInterval(() => { if (idle.value) { if (tips.value.length > 1) tipI.value = (tipI.value + 1) % tips.value.length; } }, 20000);
setInterval(() => { if (idle.value) void loadTips(); }, 10 * 60000);

function TipCard() {
  const s = status.value, t = tips.value[tipI.value % Math.max(1, tips.value.length)];
  if (!t || (s?.playing && t.key.startsWith('radio:'))) return null;
  return (
    <div data-ss-tip style="position:absolute;top:20px;right:20px;max-width:380px;display:flex;align-items:center;gap:12px;padding:10px 10px 10px 10px;border-radius:16px;background:rgba(20,20,22,.78);border:1px solid #2e2e30;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:0 10px 30px rgba(0,0,0,.45);animation:tinn .5s ease both;z-index:3;text-align:left">
      <div role="button" tabIndex={0} onClick={() => { t.go(); skjulTip(t); }} style="display:flex;align-items:center;gap:12px;min-width:0;cursor:pointer">
        <div style={`width:52px;height:52px;border-radius:10px;background:${t.art};flex-shrink:0`} />
        <span style="display:flex;flex-direction:column;gap:3px;min-width:0">
          <span style={`font-family:${MONO};font-size:9.5px;letter-spacing:.12em;color:#f0c46a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{t.kicker}</span>
          <span style="font-size:14.5px;font-weight:600;color:#f2f2ee;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{t.text}</span>
        </span>
        <span style="height:36px;padding:0 14px;border-radius:18px;background:#f2f2ee;color:#0b0b0c;font-size:13px;font-weight:600;display:flex;align-items:center;gap:6px;flex-shrink:0"><svg width="12" height="12" viewBox="0 0 24 24" fill="#0b0b0c"><path d={PLAY_D} /></svg>Spill</span>
      </div>
      <div role="button" tabIndex={0} aria-label="Skjul forslaget" onClick={() => skjulTip(t)} style="width:32px;height:36px;display:flex;align-items:center;justify-content:center;color:#8b8b86;flex-shrink:0;cursor:pointer"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></div>
    </div>
  );
}

function Standby({ clock, dateTxt }: { clock: string; dateTxt: string }) {
  const s = status.value, m = settings.value.tIdle ?? 0, night = nightNow(), nx = nextAlarm();
  const bg = artOf(s), playing = !!s?.playing;
  return (
    <button class="flat" aria-label="Vekk skjermen" style={`position:absolute;inset:0;touch-action:none;border:none;background:#000;padding:0;overflow:hidden;opacity:${idleOp.value};transition:opacity .8s ease;z-index:20`}>
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
      {m === 4 && !night && <>
        <video autoplay muted loop playsInline style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block">
          <source src="./media/fjord.mp4" type="video/mp4" /><source src="./media/fjord.webm" type="video/webm" />
        </video>
        <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 45%,rgba(0,0,0,.72) 100%)" />
        <div style="position:absolute;left:36px;right:36px;bottom:34px;display:flex;align-items:flex-end;justify-content:space-between;gap:20px">
          <span style="display:flex;flex-direction:column;gap:4px;text-align:left">
            <span style="font-size:64px;font-weight:300;letter-spacing:-.02em;color:#f2f2ee;line-height:1;text-shadow:0 2px 18px rgba(0,0,0,.5)">{clock}</span>
            <span style="font-size:15px;color:#d8d8d2">{dateTxt}</span>
          </span>
          <span style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;min-width:0">
            {playing && <span style="font-size:13px;color:#f2f2ee;max-width:380px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[s?.artist, s?.title || s?.station].filter(Boolean).join(' – ')}</span>}
            {nx && <span style={`font-family:${MONO};font-size:11px;letter-spacing:.12em;color:#f0c46a`}>ALARM {nx.time}</span>}
          </span>
        </div>
      </>}
      {m === 5 && !night && <FotoSaver clock={clock} dateTxt={dateTxt} />}
      {m === 3 && !night && (
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;gap:22px">
          <video autoplay muted loop playsInline style="width:100%;aspect-ratio:3/1;object-fit:cover;display:block">
            <source src="./media/fjord.mp4" type="video/mp4" /><source src="./media/fjord.webm" type="video/webm" />
          </video>
          <div style="display:flex;align-items:baseline;justify-content:space-between;padding:0 40px">
            <span style="font-size:58px;font-weight:300;letter-spacing:-.02em;color:#f2f2ee;line-height:1">{clock}</span>
            <span style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;min-width:0">
              <span style="font-size:15px;color:#8b8b86;white-space:nowrap">{dateTxt}</span>
              {playing && <span style="font-size:13px;color:#c9c9c4;max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[s?.artist, s?.title || s?.station].filter(Boolean).join(' – ')}</span>}
              {nx && <span style={`font-family:${MONO};font-size:11px;letter-spacing:.12em;color:#f0c46a`}>ALARM {nx.time}</span>}
            </span>
          </div>
        </div>
      )}
      {(m === 0 || (m === 1 && night) || (m >= 3 && night)) && (
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px">
          <span style={`font-size:132px;font-weight:300;letter-spacing:-.03em;color:${night ? '#7a2a20' : '#f2f2ee'};line-height:1`}>{clock}</span>
          <span style={`font-size:17px;color:${night ? '#5a211a' : '#8b8b86'};white-space:nowrap`}>{dateTxt}</span>
          {nx && <span style={`margin-top:8px;font-family:${MONO};font-size:12px;letter-spacing:.12em;color:${night ? '#7a2a20' : '#f2f2ee'};opacity:.8`}>ALARM {nx.time}</span>}
          {playing && !night && <span style="margin-top:26px;display:flex;align-items:center;gap:10px;font-size:13px;color:#8b8b86"><div style={`width:24px;height:24px;border-radius:5px;background:${bg}`} />{(s?.title || s?.station) + (s?.artist ? ' · ' + s.artist : '')}</span>}
        </div>
      )}
      {(m === 0 || m === 3 || m === 4 || m === 5) && !night && <KalKort nede={m === 4 || m === 5} />}
      {m !== 2 && !night && <TipCard />}
      {gestVol.value !== null && (
        <div style="position:absolute;left:50%;top:22px;transform:translateX(-50%);display:flex;align-items:center;gap:14px;padding:12px 20px;border-radius:999px;background:rgba(20,20,22,.82);border:1px solid #3a2e17;animation:tinn .2s ease both">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4zM16 9a4 4 0 0 1 0 6" /></svg>
          <div style="width:260px;height:6px;border-radius:3px;background:#2a2a2c;overflow:hidden"><div style={`width:${gestVol.value}%;height:100%;background:#f0c46a;transition:width .08s linear`} /></div>
          <span style={`font-family:${MONO};font-size:16px;color:#f0c46a;width:34px;text-align:right`}>{gestVol.value}</span>
        </div>
      )}
      {!!gestTxt.value && <span style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:14px 26px;border-radius:999px;background:rgba(20,20,22,.82);border:1px solid #3a2e17;color:#f0c46a;font-size:22px;font-weight:600;white-space:nowrap;animation:tinn .2s ease both">{gestTxt.value}</span>}
      {m !== 2 && m !== 4 && m !== 5 && !night && <span style={`position:absolute;left:0;right:0;bottom:16px;text-align:center;font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#3a3a37`}>TRYKK FOR Å VEKKE</span>}
    </button>
  );
}

function Boot() {
  const b = boot.value, bs = b.step, BH = [30, 46, 58, 46, 30];   // samme forhold som logoen (22/33/42/33/22)
  const names = peers.value.map((p) => p.navn).slice(0, 3).join(', ');
  const msgs = ['', '', '', '', '', '', 'Starter lydmotoren …', 'Kobler til Skjold-nettverket …', names ? 'Finner rom: ' + names + ' …' : 'Finner rom …', 'Klar'];
  const txt = bs >= 6 ? 1 : 0;
  return (
    <div style={`position:absolute;inset:0;background:#000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;opacity:${b.op};transition:opacity .6s ease;z-index:30`}>
      <div style="display:flex;align-items:flex-start;gap:7px;height:64px">
        {BH.map((h, i) => <div key={i} style={`width:10px;height:${bs > i ? h : 4}px;border-radius:5px;background:${i === 2 ? '#d9a441' : '#f2f2ee'};opacity:${bs > i ? 1 : 0.15};transition:height .5s cubic-bezier(.2,.8,.2,1),opacity .4s ease`} />)}
      </div>
      <div style={`display:flex;flex-direction:column;align-items:center;gap:6px;opacity:${txt};transform:translateY(${txt ? 0 : 10}px);transition:opacity .6s ease,transform .6s ease`}>
        <span style="font-size:34px;font-weight:700;letter-spacing:.16em;padding-left:.16em;color:#f2f2ee">SKJOLD</span>
        <span style={`font-family:${MONO};font-size:12px;letter-spacing:.5em;color:#8b8b86;padding-left:.5em`}>TOUCH</span>
      </div>
      <div style={`width:180px;height:3px;border-radius:2px;background:#1c1c1e;overflow:hidden;opacity:${txt}`}><div style={`width:${Math.max(0, (bs - 5) / 4 * 100).toFixed(0)}%;height:100%;background:#f0c46a;transition:width .5s linear`} /></div>
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.1em;color:#6b6b67;opacity:${txt}`}>{msgs[bs] || ''}</span>
    </div>
  );
}

// Nattmodus slått på/av (Home Assistant, Homey, appen, stemme): animasjon som på S1 – måne/sol, kilden og stegene
// (lys av, dører låst …) som hakes av én etter én. Vises bare for hendelser som skjer mens skjermen er i gang.
const nightAnim = signal<{ on: boolean; src: string; steps: { name: string; done?: boolean }[]; t0: number } | null>(null);
let nightSeen = -1;
effect(() => {
  const n = dev().night; if (!n || !n.t) return;
  if (nightSeen === -1) { nightSeen = n.t; return; }   // første status etter oppstart: ikke vis gammel hendelse
  if (n.t === nightSeen) { if (nightAnim.peek() && n.steps) nightAnim.value = { ...nightAnim.peek()!, steps: n.steps }; return; }
  nightSeen = n.t;
  if (Date.now() / 1000 - n.t > 30) return;
  nightAnim.value = { on: !!n.on, src: n.src || '', steps: n.steps || [], t0: Date.now() };
  wake();
  const ms = 2600 + (n.steps?.length ?? 0) * 450;
  setTimeout(() => { if (nightAnim.peek()?.t0 && Date.now() - nightAnim.peek()!.t0 >= ms - 50) nightAnim.value = null; }, ms);
});
function NightAnim() {
  const a = nightAnim.value; if (!a) return null;
  const c = a.on ? '#e0a46a' : '#f0c46a', src = a.src && a.src !== 'Skjold Touch' ? 'Fra ' + a.src : '';
  return (
    <button class="flat" onPointerDown={(e) => { e.preventDefault(); nightAnim.value = null; }} aria-label="Lukk"
      style="position:absolute;inset:0;z-index:40;border:none;padding:0;background:radial-gradient(ellipse at 50% 38%,#1a1210 0%,#060606 70%);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;animation:tinn .35s ease both">
      <svg width="96" height="96" viewBox="0 0 24 24" fill="none" stroke={c} stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" style="animation:opp .6s cubic-bezier(.2,.8,.2,1) both">
        {a.on ? <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
          : <><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" /></>}
      </svg>
      <span style="font-size:34px;font-weight:300;letter-spacing:-.01em;color:#f2f2ee;animation:inn .5s .15s ease both">{a.on ? 'God natt' : 'God morgen'}</span>
      <span style={`font-family:${MONO};font-size:11px;letter-spacing:.16em;color:#8b8b86;animation:inn .5s .25s ease both`}>{(a.on ? 'NATTMODUS PÅ' : 'NATTMODUS AV') + (src ? ' · ' + src.toUpperCase() : '')}</span>
      {!!a.steps.length && <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px;min-width:260px">
        {a.steps.map((st, i) => (
          <div key={i} style={`display:flex;align-items:center;gap:10px;font-size:15px;color:#c9c9c4;animation:inn .4s ${0.6 + i * 0.45}s ease both`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={c} stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
            {st.name}
          </div>))}
      </div>}
    </button>
  );
}

/** Sidemenyen på Touch i fire stiler (Oppsett → Sidemeny):
 *  0 Klassisk: ikon + navn i en mørk stolpe. 1 Smal: bare ikoner, gul strek ved den valgte. 2 Flytende: avrundet
 *  «dock» som svever over bakgrunnen, valgt side som en gul pille. 3 Bunnlinje: faner nederst, som på en telefon. */
function SideMeny({ stil, NAV, cur }: { stil: number; NAV: [Scr, string][]; cur: Scr }) {
  const gå = (k: Scr) => { scr.value = k; roomsOpen.value = false; talkOpen.value = false; searchOpen.value = false; queueOpen.value = false; lyricsOpen.value = false; dimId.value = ''; editAlarm.value = -1; wakeOpen.value = false; };
  const logo = (k: number) => <div aria-label="Skjold" style={`display:flex;gap:${3.3 * k}px;align-items:flex-start;height:${28 * k}px;margin:2px 0 ${6 * k}px;flex-shrink:0`}>{[14.7, 22, 28, 22, 14.7].map((h, i) => <div key={i} style={`width:${4.5 * k}px;height:${h * k}px;border-radius:${2.25 * k}px;background:${i === 2 ? '#d9a441' : '#f2f2ee'}`} />)}</div>;
  const ikon = (k: Scr, w = 22) => <svg width={w} height={w} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={IC[k]} /></svg>;
  if (stil === 3) return (
    <nav style="grid-row:2;grid-column:1;display:flex;align-items:stretch;gap:2px;padding:0 10px 4px;background:#101011;border-top:1px solid #1f1f21">
      {NAV.map(([k, label]) => { const on = cur === k; return (
        <button key={k} onClick={() => gå(k)} aria-label={label} style={`position:relative;flex:1;min-width:0;border:none;background:none;color:${on ? '#f0c46a' : '#8b8b86'};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:0`}>
          <i style={`position:absolute;top:0;left:50%;width:${on ? 28 : 0}px;height:3px;margin-left:${on ? -14 : 0}px;border-radius:0 0 3px 3px;background:#f0c46a;transition:width .3s ease,margin .3s ease`} />
          {ikon(k)}<span style={`font-size:10px;font-weight:${on ? 600 : 400}`}>{label}</span>
        </button>); })}
      <div style="display:flex;align-items:center;padding-left:6px"><PowerHold /></div>
    </nav>);
  if (stil === 1) return (
    <nav style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:12px 0 8px;background:#0e0e0f;border-right:1px solid #1a1a1c">
      {logo(0.82)}
      {NAV.map(([k, label]) => { const on = cur === k; return (
        <button key={k} onClick={() => gå(k)} aria-label={label} style={`position:relative;width:46px;height:46px;border-radius:14px;border:none;background:${on ? '#1c1c1e' : 'transparent'};color:${on ? '#f0c46a' : '#7a7a76'};display:flex;align-items:center;justify-content:center;padding:0`}>
          <i style={`position:absolute;left:-6px;top:50%;width:3px;height:${on ? 22 : 0}px;margin-top:${on ? -11 : 0}px;border-radius:2px;background:#f0c46a;transition:height .3s ease,margin .3s ease`} />
          {ikon(k, 23)}
        </button>); })}
      <div style="flex:1" />
      <div style="transform:scale(.9)"><PowerHold /></div>
    </nav>);
  if (stil === 2) return (
    <nav style="margin:10px 0 10px 10px;display:flex;flex-direction:column;align-items:center;gap:4px;padding:12px 0 10px;border-radius:24px;background:rgba(22,22,24,.86);border:1px solid #2a2a2c;box-shadow:0 18px 40px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.04);backdrop-filter:blur(14px)">
      {logo(0.9)}
      {NAV.map(([k, label]) => { const on = cur === k; return (
        <button key={k} onClick={() => gå(k)} aria-label={label} style={`width:62px;height:${FLUID ? 54 : 48}px;border-radius:16px;border:none;background:${on ? 'linear-gradient(180deg,#f3cf7f,#d9a441)' : 'transparent'};color:${on ? '#0b0b0c' : '#8b8b86'};box-shadow:${on ? '0 6px 16px rgba(217,164,65,.35)' : 'none'};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;padding:0`}>
          {ikon(k, 20)}<span style={`font-size:9px;font-weight:${on ? 700 : 400}`}>{label}</span>
        </button>); })}
      <div style="flex:1" />
      <PowerHold />
    </nav>);
  return (
    <nav style="display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 0 8px;background:#101011;border-right:1px solid #1f1f21">
      {/* Skjold-logoen: hvite stolper som henger fra toppen, den lange gylne i midten (som appikonet og oppstartsskjermen) */}
      {logo(1)}
      {NAV.map(([k, label]) => { const on = cur === k; return (
        <button key={k} onClick={() => gå(k)} aria-label={label} style={`width:64px;height:48px;border-radius:13px;border:none;background:${on ? 'rgba(240,196,106,.14)' : 'transparent'};color:${on ? '#f0c46a' : '#8b8b86'};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:0`}>
          {ikon(k)}<span style={`font-size:9px;font-weight:${on ? 600 : 400}`}>{label}</span>
        </button>); })}
      <div style="flex:1" />
      <PowerHold />
    </nav>);
}

function App() {
  const s = status.value, d = new Date(now.value), S = settings.value, D = dev();
  const talking = !!D.touch?.voice && D.touch.voice.state !== 'idle';
  const clock = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const dateTxt = d.toLocaleDateString('nb-NO', { weekday: 'long', day: 'numeric', month: 'long' }).replace(/^./, (c) => c.toUpperCase());
  const r = role(), cur = scr.value === 'rooms' && r === 1 ? 'now' : scr.value;
  // Bare fjernkontroll: styr første andre rom så snart det finnes
  useEffect(() => { if (r === 2 && !ctl.value && peers.value[0]) control(peers.value[0].base); if (r === 1 && ctl.value) control(''); }, [r, peers.value.length]);
  const nav = S.tNav ?? 0;   // sidemenyens stil: 0 klassisk, 1 smal, 2 flytende, 3 bunnlinje
  const NAV: [Scr, string][] = ([['now', 'Spiller'], ['home', 'Hjem'], ['smart', 'Smarthus'], ['alarm', 'Alarm'], ['lib', 'Bibliotek'], ['rooms', 'Rom'], ['set', 'Oppsett']] as [Scr, string][]).filter(([k]) => !(r === 1 && k === 'rooms'));
  const rows = roomList();
  const curRoom = rows.find((x) => x.base === ctl.value);
  const roomLabel = curRoom?.name ?? s?.name ?? 'Skjold Touch', roomSub = (curRoom?.model ?? 'Skjold Touch').replace('Skjold ', '');
  return (
    <div style={`position:relative;width:${FLUID ? '100vw' : '800px'};height:${FLUID ? '100vh' : '480px'};background:${nav === 2 ? 'radial-gradient(700px 400px at 0% 100%,rgba(217,164,65,.07),transparent 60%),#0b0b0c' : '#0b0b0c'};overflow:hidden;display:grid;${nav === 3
      ? `grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr) ${FLUID ? 70 : 62}px`
      : `grid-template-columns:${[FLUID ? 88 : 76, FLUID ? 66 : 58, FLUID ? 100 : 90][nav] ?? 76}px minmax(0,1fr);grid-template-rows:${FLUID ? '100vh' : '480px'}`}`}>
      <SideMeny stil={nav} NAV={NAV} cur={cur} />
      <main style={`position:relative;display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden;${nav === 3 ? 'grid-row:1;grid-column:1' : ''}`}>
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
        {cur === 'set' && <AlleInnstillinger touch={<Setup />} oppdatering={<OppdateringSide />} />}
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
        {editAlarm.value >= 0 && cur === 'alarm' && <AlarmEdit />}
        {wakeOpen.value && cur === 'alarm' && <WakeMenu />}
        {timerOpen.value && cur === 'alarm' && <TimerSheet />}
        {searchOpen.value && cur === 'lib' && <Search />}
        {queueOpen.value && cur === 'now' && <QueueSheet />}
        {lyricsOpen.value && cur === 'now' && <LyricsSheet />}
        {!!artistSide.value && cur === 'now' && <ArtistSide />}
        {!!dimId.value && cur === 'smart' && <DimSheet />}
        {camOpen.value && cur === 'smart' && <CamView />}
        {saverOpen.value && cur === 'set' && <SaverSheet />}
        {wifiOpen.value && cur === 'set' && <WifiSetup />}
        {gruppeOpen.value && cur === 'rooms' && <GruppeSheet />}
        {talkOpen.value && <Intercom />}
        {talking && <Voice />}
        {!!toast.value && <div role="status" style="position:absolute;left:50%;bottom:78px;transform:translateX(-50%);z-index:9;max-width:620px;padding:12px 20px;border-radius:14px;background:rgba(24,24,26,.96);border:1px solid #3a2e17;color:#f2f2ee;font-size:14px;line-height:1.35;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,.5);animation:tinn .2s ease both">{toast.value.replace(/^Forsterkeren svarte: /, '')}</div>}
      </main>
      {lpOpen.value && !idle.value && <LpSpiller />}
      {idle.value && <Standby clock={clock} dateTxt={dateTxt} />}
      {quick.value > 0 && <QuickPanel />}
      {(!!D.setup_net?.active || !!D.setup_net?.joining || !!D.setup_net?.kabel) && !boot.value.on && <SetupNet />}
      {!!doorToast.value && !door.value && <DoorToast />}
      {!!door.value && <Door clock={clock} />}
      {!!D.alarm?.ringing && <AlarmRinging clock={clock} />}
      <TimerStripe />
      <TimerFerdig />
      <NightAnim />
      {boot.value.on && <Boot />}
      <RebootLayer />
    </div>
  );
}

// Til skjermbilder og test: window.__touch.screen('home') osv.
(window as unknown as { __touch: unknown }).__touch = {
  screen: (k: Scr) => { scr.value = k; }, lib: (i: number) => { lib.value = i; }, standby: goIdle, wake, boot: runBoot,
  editAlarm: (i: number) => { editAlarm.value = i; }, wake2: (o: boolean) => { wakeOpen.value = o; void loadWake(); },
  intercom: (o: boolean) => { talkOpen.value = o; }, search: (o: boolean) => { searchOpen.value = o; }, queue: (o: boolean) => { queueOpen.value = o; },
  skipBoot: () => { bootT.forEach(clearTimeout); started = true; boot.value = { on: false, step: 9, op: 0 }; }, rooms: (o: boolean) => { roomsOpen.value = o; },
  // de samme inngangene som i designet: alarm, ringeklokke, nattmodus og stemme
  alarm: () => void postAt('', '/api/alarm', { action: 'test' }), ring: () => ringNow(0, true),
  night: (on: boolean) => void postAt('', '/api/night', { on, src: 'Skjold Touch' }),
  voice: (state: string, text = '', reply = '') => void postAt('', '/api/touch/voice', { state, text, reply })
};
render(<App />, document.getElementById('touch')!);
