// Innlogginger til musikktjenester – lagres på forsterkeren (/api/settings), så web og appene deler dem. Lokal kopi som reserve.
import { signal } from '@preact/signals';
import { ndConf, setNdConf } from './navidrome';
import type { LocalKey, Settings } from './settings';
import { setSetting, settings, settingsSource } from './store';
import { effect } from '@preact/signals';

const KEY = 'skjold-ytm';
const ytm = signal<{ ytmUser: string; ytmCookie: string }>((() => { try { const j = JSON.parse(localStorage.getItem(KEY) || '{}') as Record<string, string>; return { ytmUser: j['ytmUser'] ?? '', ytmCookie: j['ytmCookie'] ?? '' }; } catch { return { ytmUser: '', ytmCookie: '' }; } })());

export function getLocal(k: LocalKey): string {
  if (k === 'ndUrl') return ndConf.value.url;
  if (k === 'ndUser') return ndConf.value.user;
  if (k === 'ndPass') return ndConf.value.pass;
  return ytm.value[k];
}
export function setLocal(k: LocalKey, v: string): void {
  const val = k === 'ndPass' || k === 'ytmCookie' ? v : v.trim();
  if (settingsSource.value === 'api') setSetting(k as keyof Settings, val as never);   // del med appene
  if (k === 'ndUrl') return setNdConf({ url: val });
  if (k === 'ndUser') return setNdConf({ user: val });
  if (k === 'ndPass') return setNdConf({ pass: val });
  ytm.value = { ...ytm.value, [k]: val };
  try { localStorage.setItem(KEY, JSON.stringify(ytm.value)); } catch { /* ignore */ }
}

// Innloggingene fra forsterkeren vinner (de kan være satt i iOS-/Android-appen). Er forsterkeren tom men denne
// nettleseren har noe lagret fra før, sendes det opp én gang.
let pushed = false;
effect(() => {
  if (settingsSource.value !== 'api') return;
  const s = settings.value as unknown as Record<string, unknown>;
  const remote = { url: String(s['ndUrl'] ?? ''), user: String(s['ndUser'] ?? ''), pass: String(s['ndPass'] ?? '') };
  if (remote.url || remote.user || remote.pass) {
    const c = ndConf.peek();
    if (c.url !== remote.url || c.user !== remote.user || c.pass !== remote.pass) setNdConf(remote);
  } else if (!pushed && (ndConf.peek().url || ndConf.peek().user)) {
    pushed = true; const c = ndConf.peek();
    setSetting('ndUrl' as keyof Settings, c.url as never); setSetting('ndUser' as keyof Settings, c.user as never); setSetting('ndPass' as keyof Settings, c.pass as never);
  }
  const y = { ytmUser: String(s['ytmUser'] ?? ''), ytmCookie: String(s['ytmCookie'] ?? '') };
  if ((y.ytmUser || y.ytmCookie) && (y.ytmUser !== ytm.peek().ytmUser || y.ytmCookie !== ytm.peek().ytmCookie)) {
    ytm.value = y; try { localStorage.setItem(KEY, JSON.stringify(y)); } catch { /* ignore */ }
  }
});
