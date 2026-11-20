// «Denne enheten»: spill det Skjold spiller på telefonen/PC-en i stedet for i rommet.
// Skjold fortsetter å spille, men dempet, så kø, neste/forrige, pause og spoling virker som før – denne enheten speiler
// strømmen (status.listen, via Skjolds /api/stream-proxy) og holder seg i takt med posisjonen. Tilbake til rommet:
// lyden slås på igjen i Skjold og spilles der fra samme sted.
import { effect, signal } from '@preact/signals';
import { api, getBase } from './api';
import { keepAlive, refreshNow, showToast, status } from './store';

export const localOn = signal(false);
const VOL_KEY = 'skjold-local-vol';
export const localVol = signal<number>((() => { try { const v = Number(localStorage.getItem(VOL_KEY)); return v > 0 ? v : 80; } catch { return 80; } })());

let el: HTMLAudioElement | null = null;
let cur = '';
let wasMuted = false;
// Siste posisjon Skjold meldte, og når (til å skille ekte spoling fra vanlig glidning, se sync()).
let skjoldPos: { p: number; at: number } | null = null;

/** Kan det som spilles nå spilles på denne enheten? (Radio og bibliotekene – ikke AirPlay, Blåtann, Spotify eller AUX.) */
export function canListen(): boolean { return !!status.value?.listen; }

/** Navn på denne enheten, til knappene. */
export function thisDevice(): string {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  return /iPhone|Android.+Mobile/.test(ua) ? 'Denne telefonen' : /iPad|Android/.test(ua) ? 'Dette nettbrettet' : 'Denne PC-en';
}

const abs = (path: string) => (getBase() || location.origin).replace(/\/+$/, '') + path;

/** Start avspilling her. Kall fra et klikk (nettleseren krever det for lyd). */
export function startLocal(): void {
  const s = status.value;
  if (!s?.listen) { showToast('Dette kan ikke spilles på denne enheten'); return; }
  el ??= new Audio();
  el.preload = 'auto';
  el.onended = () => { void refreshNow(); };   // Skjold går videre selv: hent status med en gang, så neste strøm plukkes opp
  el.onerror = () => { if (localOn.value) { showToast('Fikk ikke spilt strømmen her'); stopLocal(); } };
  localOn.value = true;
  wasMuted = !!s.mute;
  sync();
  if (!wasMuted) { void api.mute(true).catch(() => {}); flagg(true); }
}

/** Tilbake til rommet: stopp her, og slå på lyden i Skjold igjen (fra samme sted i låten). */
export function stopLocal(): void {
  if (!localOn.value) return;
  localOn.value = false;
  const pos = el && !el.paused && isFinite(el.currentTime) ? el.currentTime : null;
  if (el) { el.pause(); el.removeAttribute('src'); el.load(); }
  cur = ''; skjoldPos = null;
  const s = status.value;
  if (pos !== null && s && (s.duration ?? 0) > 0 && Math.abs((s.position ?? 0) - pos) > 3) void api.seek(pos).catch(() => {});
  if (!wasMuted) void api.mute(false).catch(() => {});
  flagg(false);
}

export function setLocalVol(v: number): void {
  localVol.value = Math.max(0, Math.min(100, Math.round(v)));
  if (el) el.volume = localVol.value / 100;
  try { localStorage.setItem(VOL_KEY, String(localVol.value)); } catch { /* privat modus */ }
}

/** Kan strømmen spoles hit? (Omkodede strømmer uten Range-støtte kan ikke det – da startet nettleseren fra begynnelsen.) */
function kanSpole(a: HTMLAudioElement, p: number): boolean {
  const r = a.seekable;
  for (let i = 0; i < r.length; i++) if (p >= r.start(i) && p <= r.end(i)) return true;
  return false;
}

/** Følg Skjold: ny strøm, pause/spill og posisjon. */
function sync(): void {
  const s = status.value;
  if (!localOn.value || !el) return;
  if (!s?.listen) { showToast('Kilden kan ikke spilles på denne enheten – tilbake til rommet'); stopLocal(); return; }
  const track = (s.duration ?? 0) > 0;
  const nå = performance.now(), pos = s.position ?? 0;
  if (s.listen !== cur) {
    cur = s.listen;
    skjoldPos = { p: pos, at: nå };
    el.src = abs(cur);
    if (track && pos > 1) {
      el.addEventListener('loadedmetadata', () => { try { if (kanSpole(el!, pos)) el!.currentTime = pos; } catch { /* ignore */ } }, { once: true });
    }
  } else if (track && skjoldPos && pos !== skjoldPos.p) {
    // Følg bare ekte hopp i Skjold (noen spolte, eller neste/forrige i samme strøm): avviket fra der Skjold burde vært
    // nå er stort. Vanlig glidning mellom rommet (dempet) og denne enheten rettes IKKE: før ble avspillingen her satt
    // tilbake hver gang den lå mer enn 4 s foran, så biter av låten ble spilt flere ganger – særlig med fanen i bakgrunnen,
    // der statusen kommer sjeldnere.
    const ventet = skjoldPos.p + (s.playing ? (nå - skjoldPos.at) / 1000 : 0);
    const hopp = Math.abs(pos - ventet) > 6;
    skjoldPos = { p: pos, at: nå };
    if (hopp && !el.seeking && el.readyState > 0 && Math.abs(el.currentTime - pos) > 4 && kanSpole(el, pos)) {
      try { el.currentTime = pos; } catch { /* ignore */ }
    }
  }
  el.volume = localVol.value / 100;
  // Ferdig her, men Skjold har ikke gått videre ennå: vent på neste strøm (play() på en ferdig strøm starter låten på nytt)
  if (el.ended) return;
  if (s.playing && el.paused) void el.play().catch((e: unknown) => {
    // nettleseren nektet å starte lyd uten et trykk (ny låt i bakgrunnen): ikke la rommet stå dempet i stillhet
    if (e instanceof DOMException && e.name === 'NotAllowedError' && localOn.value) { showToast('Nettleseren stoppet lyden – tilbake til rommet'); stopLocal(); }
  });
  else if (!s.playing && !el.paused) el.pause();
}

effect(() => { void status.value; if (localOn.value) sync(); });
effect(() => { keepAlive.value = localOn.value; });

// Rommet er dempet mens denne enheten spiller. Lukkes eller lastes fanen på nytt, må lyden slås på igjen – ellers
// spiller forsterkeren videre uten lyd, og ingen vet hvorfor.
const DEMPET_KEY = 'skjold-local-dempet';
function flagg(on: boolean): void {
  try { if (on) localStorage.setItem(DEMPET_KEY, getBase() || location.origin); else localStorage.removeItem(DEMPET_KEY); } catch { /* privat modus */ }
}
function opphevDemping(base: string): void {
  try { void fetch(base.replace(/\/+$/, '') + '/api/mute', { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json' }, body: '{"mute":false}' }).catch(() => {}); } catch { /* ignore */ }
}
if (typeof window !== 'undefined') {
  window.addEventListener('pagehide', () => { if (localOn.value && !wasMuted) { opphevDemping(getBase() || location.origin); flagg(false); } });
  // forrige økt ble avbrutt (krasj, strøm) før pagehide rakk å kjøre
  try { const b = localStorage.getItem(DEMPET_KEY); if (b) { opphevDemping(b); localStorage.removeItem(DEMPET_KEY); } } catch { /* privat modus */ }
}
