// yubal i app, web-UI og Touch: finn låter og album du ikke har i Navidrome, velg riktig, og følg nedlastingen inn i biblioteket.
// Daemonen (pi/skjold_yubal.py) slår opp i YouTube Music og sender lenken til yubal.
import { computed, signal } from '@preact/signals';
import { api, type YubalJobb, type YubalKandidat } from './api';
import { settings } from './store';

export interface YbNed { q: string; id: string; tittel: string; artist: string; bilde: string; status: string; fremdrift: number; feil?: string }
/** Alle nedlastinger denne økten, per nøkkel (søkeordet, «album:…» eller «sang:…»). */
export const ybAlle = signal<Record<string, YbNed>>({});
const sist = signal('');
/** Den siste nedlastingen (Touch viser den i søket). */
export const ybNed = computed<YbNed | null>(() => ybAlle.value[sist.value] ?? null);
/** Øker noen ganger etter en ferdig nedlasting (Navidrome skanner) – søk og lister lytter og henter på nytt. */
export const ybNyttSok = signal(0);
export const YB_TEKST: Record<string, string> = { starter: 'Starter …', pending: 'I kø hos yubal', fetching_info: 'Henter info', downloading: 'Laster ned', importing: 'Legger inn i biblioteket', completed: 'Ferdig – ligger i Navidrome', failed: 'Klarte ikke å laste ned', cancelled: 'Avbrutt' };
export const ybTekst = (n: YbNed): string => n.feil || ((YB_TEKST[n.status] ?? n.status) + (n.status === 'downloading' || n.status === 'importing' ? ' · ' + n.fremdrift + ' %' : ''));
export const ybAktiv = (n: YbNed | undefined): boolean => !!n && !['failed', 'cancelled', 'completed'].includes(n.status);

export const yubalPa = (): boolean => !!(settings.value as unknown as { yubalUrl?: string }).yubalUrl;
export const yubalAuto = (): boolean => (settings.value as unknown as { yubalAuto?: boolean }).yubalAuto !== false;

const ferdigFn: Record<string, (n: YbNed) => void> = {};
const sett = (k: string, n: YbNed) => { ybAlle.value = { ...ybAlle.value, [k]: n }; };

async function start(key: string, foreløpig: Omit<YbNed, 'q' | 'id' | 'status' | 'fremdrift'>, kall: () => Promise<YubalJobb>, ferdig?: (n: YbNed) => void): Promise<void> {
  sist.value = key;
  sett(key, { q: key, id: '', status: 'starter', fremdrift: 0, ...foreløpig });
  if (ferdig) ferdigFn[key] = ferdig;
  try {
    const r = await kall();
    sett(key, { q: key, id: r.id, tittel: r.tittel || foreløpig.tittel, artist: r.artist || foreløpig.artist, bilde: r.bilde || foreløpig.bilde, status: 'pending', fremdrift: 0 });
    folg();
  } catch (e) { sett(key, { ...ybAlle.value[key]!, status: 'failed', feil: e instanceof Error ? e.message : String(e) }); }
}
/** Last ned en låt du har valgt fra kandidatene. */
export const ybLastNed = (q: string, k: YubalKandidat, ferdig?: (n: YbNed) => void) =>
  start(q, { tittel: k.tittel, artist: k.artist, bilde: k.bilde }, () => api.yubalHentValgt(k), ferdig);
/** Last ned et helt album (album-id fra YouTube Music, eller navn + artist). */
export const ybLastNedAlbum = (key: string, a: { album_id?: string; album: string; artist: string; bilde?: string }, ferdig?: (n: YbNed) => void) =>
  start(key, { tittel: a.album, artist: a.artist, bilde: a.bilde ?? '' }, () => api.yubalAlbum(a), ferdig);
/** Finn og last ned en låt fra tittel og artist (fra «Populært»): sikkert treff, ellers det beste. */
export async function ybLastNedSang(key: string, tittel: string, artist: string, bilde = '', ferdig?: (n: YbNed) => void): Promise<void> {
  sist.value = key;
  sett(key, { q: key, id: '', tittel, artist, bilde, status: 'starter', fremdrift: 0 });
  try {
    const r = await api.yubalKandidater(artist + ' ' + tittel);
    const k = r.sikker ?? r.kandidater[0];
    if (!k) throw new Error('Fant ikke «' + tittel + '» på YouTube Music');
    await ybLastNed(key, { ...k, bilde: k.bilde || bilde }, ferdig);
  } catch (e) { sett(key, { ...ybAlle.value[key]!, status: 'failed', feil: e instanceof Error ? e.message : String(e) }); }
}

let t = 0;
function folg(): void {
  clearTimeout(t);
  t = window.setTimeout(async () => {
    const aktive = Object.entries(ybAlle.value).filter(([, n]) => n.id && ybAktiv(n));
    if (!aktive.length) return;
    try {
      const jobber = (await api.yubalJobber()).jobber;
      for (const [k, n] of aktive) {
        const j = jobber.find((x) => x.id === n.id); if (!j) continue;
        const ny = { ...n, status: j.status, fremdrift: j.fremdrift ?? 0, tittel: j.tittel || n.tittel, artist: j.artist || n.artist, bilde: j.bilde || n.bilde };
        sett(k, ny);
        if (ny.status === 'completed') { ferdigFn[k]?.(ny); delete ferdigFn[k]; [2500, 8000, 20000].forEach((ms) => window.setTimeout(() => { ybNyttSok.value++; }, ms)); }
      }
    } catch { /* prøv igjen */ }
    folg();
  }, 2000);
}
