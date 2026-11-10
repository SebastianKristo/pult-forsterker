// Hjemskjermens rekkefølge og synlighet (settings.homeLayout) – lagres per Skjold-enhet og synkes til alle klienter.
// Samme seksjons-id-er som pi/skjold_homelayout.py, iOS (HomeLayout.swift) og Android (HomeLayout.kt).
import { signal } from '@preact/signals';
import { settings, setSetting } from './store';

export interface HomeItem { id: string; visible: boolean }

export const HOME_SECTIONS: [string, string][] = [
  ['recent', 'Nylig spilt'],
  ['favs', 'Radiofavoritter'],
  ['sources', 'Kilder'],
  ['routines', 'Rutiner'],
  ['discover', 'Oppdag'],
  ['ask', 'Spill noe til …'],
  ['nrk', 'Fortsett på NRK'],
  ['playlists', 'Dine spillelister'],
  ['library', 'Fra bibliotekene'],
  ['wrapped', 'Skjold Wrapped']
];
export const homeLabel = (id: string) => HOME_SECTIONS.find(([k]) => k === id)?.[1] ?? id;

/** Lagret rekkefølge først (bare id-er klienten kan vise), så manglende seksjoner – synlige – på slutten. */
export function resolveHome(layout: HomeItem[] | undefined, available: string[]): HomeItem[] {
  const lay = Array.isArray(layout) ? layout : [];
  const out: HomeItem[] = [];
  for (const it of lay) if (it && available.includes(it.id) && !out.some((o) => o.id === it.id)) out.push({ id: it.id, visible: it.visible !== false });
  for (const id of available) if (!out.some((o) => o.id === id)) out.push({ id, visible: true });
  return out;
}

/** Synlige seksjoner i rekkefølge for hjemskjermen. */
export function homeOrder(available: string[]): string[] {
  return resolveHome(settings.value.homeLayout, available).filter((x) => x.visible).map((x) => x.id);
}

/** Lagrer ny rekkefølge; seksjoner andre klienter kjenner (men ikke denne) beholdes på slutten. */
export function saveHome(items: HomeItem[]): void {
  const old = Array.isArray(settings.value.homeLayout) ? settings.value.homeLayout : [];
  const rest = old.filter((o) => !items.some((i) => i.id === o.id));
  setSetting('homeLayout', [...items, ...rest]);
}
export function resetHome(): void { setSetting('homeLayout', []); }

// ---------- Kildene på Hjem: rekkefølge og synlighet (lagres i nettleseren, som på telefonene) ----------

/** Alle kildene Hjem kan vise (etikettene brukes som id-er, som i iOS- og Android-appen). */
export const HOME_SOURCES = ['Radio', 'AirPlay', 'Blåtann', 'Spotify', 'Plex', 'UPnP/DLNA', 'YT Music', 'Navidrome', 'Lyrion', 'AUX', 'USB'];
const SRC_KEY = 'skjold-home-sources';
function loadSources(): HomeItem[] {
  try { const j = JSON.parse(localStorage.getItem(SRC_KEY) || '[]') as HomeItem[]; return Array.isArray(j) ? j : []; } catch { return []; }
}
export const homeSources = signal<HomeItem[]>(loadSources());
export function saveSources(items: HomeItem[]): void {
  homeSources.value = items;
  try { if (items.length) localStorage.setItem(SRC_KEY, JSON.stringify(items)); else localStorage.removeItem(SRC_KEY); } catch { /* privat modus */ }
}
/** Sorterer og filtrerer en liste med kilder etter brukerens valg. `label` gir kildens navn (id). */
export function orderSources<T>(list: T[], label: (x: T) => string): T[] {
  const ids = [...new Set(list.map(label))];
  const order = resolveHome(homeSources.value, ids).filter((x) => x.visible).map((x) => x.id);
  return order.flatMap((id) => list.filter((x) => label(x) === id));
}
