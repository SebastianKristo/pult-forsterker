// Innlogginger til musikktjenester – lagres bare på denne telefonen (sendes ikke til forsterkeren).
import { signal } from '@preact/signals';
import { ndConf, setNdConf } from './navidrome';
import type { LocalKey } from './settings';

const KEY = 'skjold-ytm';
const ytm = signal<{ ytmUser: string; ytmCookie: string }>((() => { try { const j = JSON.parse(localStorage.getItem(KEY) || '{}') as Record<string, string>; return { ytmUser: j['ytmUser'] ?? '', ytmCookie: j['ytmCookie'] ?? '' }; } catch { return { ytmUser: '', ytmCookie: '' }; } })());

export function getLocal(k: LocalKey): string {
  if (k === 'ndUrl') return ndConf.value.url;
  if (k === 'ndUser') return ndConf.value.user;
  if (k === 'ndPass') return ndConf.value.pass;
  return ytm.value[k];
}
export function setLocal(k: LocalKey, v: string): void {
  if (k === 'ndUrl') return setNdConf({ url: v.trim() });
  if (k === 'ndUser') return setNdConf({ user: v.trim() });
  if (k === 'ndPass') return setNdConf({ pass: v });
  ytm.value = { ...ytm.value, [k]: v };
  try { localStorage.setItem(KEY, JSON.stringify(ytm.value)); } catch { /* ignore */ }
}
