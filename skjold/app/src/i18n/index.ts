// Språk: norsk (nb) er standard og nøkkelen, engelsk (en) slås opp i en ordbok. Mangler en oversettelse,
// vises den norske teksten – så ingenting blir tomt. Valget lagres lokalt; «auto» følger nettleseren.
import { signal } from '@preact/signals';
import { EN } from './en';

export type Lang = 'nb' | 'en';
export type LangPref = Lang | 'auto';
const KEY = 'skjold-lang';

function detect(): Lang {
  try {
    const l = (navigator.languages?.[0] || navigator.language || 'nb').toLowerCase();
    return /^(nb|nn|no|da|sv)/.test(l) ? 'nb' : l.startsWith('en') ? 'en' : 'nb';
  } catch { return 'nb'; }
}
function readPref(): LangPref {
  try { const v = localStorage.getItem(KEY); return v === 'nb' || v === 'en' || v === 'auto' ? v : 'auto'; } catch { return 'auto'; }
}

export const langPref = signal<LangPref>(readPref());
export const lang = signal<Lang>(langPref.value === 'auto' ? detect() : langPref.value);

export function setLang(p: LangPref): void {
  langPref.value = p;
  lang.value = p === 'auto' ? detect() : p;
  try { localStorage.setItem(KEY, p); } catch { /* privat modus */ }
  try { document.documentElement.lang = lang.value === 'en' ? 'en' : 'no'; } catch { /* ingen DOM */ }
}

/** t('Norsk tekst', {n: 3}) → oversatt tekst med {n} byttet ut. */
export function t(nb: string, vars?: Record<string, string | number>): string {
  let s = lang.value === 'en' ? (EN[nb] ?? nb) : nb;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split('{' + k + '}').join(String(v));
  return s;
}
