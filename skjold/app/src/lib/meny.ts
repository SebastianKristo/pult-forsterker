// Hvilke musikktjenester og sider som vises i sidemenyen og blant kildene. Lagres på Skjold-enheten (navSkjul),
// så nettleseren, appene og de andre i huset ser det samme.
import { setSetting, settings } from './store';

/** Det som kan skjules fra menyen: [id, navn]. */
export const MENY: [string, string][] = [['radio', 'Radio'], ['ytm', 'YouTube Music'], ['nd', 'Navidrome'], ['sw', 'SUB/WAVE'], ['ma', 'Music Assistant'], ['lms', 'Lyrion'], ['eq', 'Equalizer']];

const skjulte = (): string[] => { const v = (settings.value as unknown as { navSkjul?: unknown }).navSkjul; return Array.isArray(v) ? v.map(String) : []; };

/** Vises tjenesten i menyen? Skjult for hånd, eller slått av etter at den er satt opp (YouTube Music, Navidrome). */
export function vises(id: string): boolean {
  if (skjulte().includes(id)) return false;
  const s = settings.value;
  if (id === 'ytm' && s.ytmCookie && !s.ytmEn) return false;
  if (id === 'nd' && s.ndUrl && !s.ndEn) return false;
  return true;
}

/** Skjult for hånd (uavhengig av om tjenesten er slått av)? */
export const skjult = (id: string): boolean => skjulte().includes(id);

export function settVises(id: string, vis: boolean): void {
  const ny = skjulte().filter((x) => x !== id);
  if (!vis) ny.push(id);
  setSetting('navSkjul', ny);
}
