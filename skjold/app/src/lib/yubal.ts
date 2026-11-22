// yubal i app, web-UI og Touch: finn låter du ikke har i Navidrome, velg riktig, og følg nedlastingen inn i biblioteket.
// Daemonen (pi/skjold_yubal.py) slår opp i YouTube Music og sender lenken til yubal.
import { signal } from '@preact/signals';
import { api, type YubalKandidat } from './api';
import { settings } from './store';

export interface YbNed { q: string; id: string; tittel: string; artist: string; bilde: string; status: string; fremdrift: number; feil?: string }
/** Nedlastingen som pågår (eller sist var), per søkeord. */
export const ybNed = signal<YbNed | null>(null);
/** Øker noen ganger etter en ferdig nedlasting (Navidrome skanner) – søkene lytter og søker igjen. */
export const ybNyttSok = signal(0);
export const YB_TEKST: Record<string, string> = { starter: 'Starter …', pending: 'I kø hos yubal', fetching_info: 'Henter info', downloading: 'Laster ned', importing: 'Legger inn i biblioteket', completed: 'Ferdig – ligger i Navidrome', failed: 'Klarte ikke å laste ned', cancelled: 'Avbrutt' };

export const yubalPa = (): boolean => !!(settings.value as unknown as { yubalUrl?: string }).yubalUrl;
export const yubalAuto = (): boolean => (settings.value as unknown as { yubalAuto?: boolean }).yubalAuto !== false;

let t = 0;
export async function ybLastNed(q: string, k: YubalKandidat, ferdig?: (n: YbNed) => void): Promise<void> {
  ybNed.value = { q, id: '', tittel: k.tittel, artist: k.artist, bilde: k.bilde, status: 'starter', fremdrift: 0 };
  try {
    const r = await api.yubalHentValgt(k);
    ybNed.value = { q, id: r.id, tittel: r.tittel || k.tittel, artist: r.artist || k.artist, bilde: r.bilde || k.bilde, status: 'pending', fremdrift: 0 };
    folg(ferdig);
  } catch (e) { ybNed.value = { ...ybNed.value!, status: 'failed', feil: e instanceof Error ? e.message : String(e) }; }
}
function folg(ferdig?: (n: YbNed) => void): void {
  clearTimeout(t);
  t = window.setTimeout(async () => {
    const n = ybNed.value; if (!n || !n.id) return;
    try {
      const j = (await api.yubalJobber()).jobber.find((x) => x.id === n.id);
      if (j) ybNed.value = { ...n, status: j.status, fremdrift: j.fremdrift ?? 0, tittel: j.tittel || n.tittel, artist: j.artist || n.artist, bilde: j.bilde || n.bilde };
    } catch { /* prøv igjen */ }
    const v = ybNed.value!;
    if (v.status === 'completed') { ferdig?.(v); [2500, 8000, 20000].forEach((ms) => window.setTimeout(() => { ybNyttSok.value++; }, ms)); return; }
    if (v.status === 'failed' || v.status === 'cancelled') return;
    folg(ferdig);
  }, 2000);
}
