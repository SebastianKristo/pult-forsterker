// Innstillingsmodell for Skjold S1 – portert fra skjold/design/felles/skjold_settings.js.
// Nøklene er de samme som /api/settings på forsterkeren bruker.

export type EqSource = 'air' | 'bt' | 'radio' | 'aux' | 'usb' | 'hp';
export interface EqProfile { preset: number; eq: number[]; loud: boolean }
export type EqProfiles = Record<EqSource, EqProfile>;

export interface Settings {
  bass: number; treb: number; bal: number;
  vstart: number; vmax: number; perIn: boolean; hpOwn: boolean;
  lvlAux: number; lvlUsb: number;
  name: number; nameCustom: string; nAux1: string; nAux2: string; nUsb1: string; nUsb2: string;
  hold: number;
  voice: boolean; lang: number; vv: number;
  dim: number; off: number; clock: boolean; clockStyle: number; led: number;
  auto: number; wake: boolean;
  updChannel: number; updAuto: boolean;
  setupDone: boolean;
  eq: EqProfiles;
}

export const NAMES = ['Skjold S1', 'Stue', 'Kontor', 'Soverom'];
export const LANGS = ['Norsk', 'English', 'Svenska', 'Dansk'];

export const EQ = {
  bands: ['60', '250', '1k', '4k', '12k'],
  presets: [
    ['Flat', [0, 0, 0, 0, 0]], ['Bass+', [6, 3, 0, 0, 1]], ['Vokal', [-2, 0, 3, 2, 0]],
    ['Kveld', [3, 1, -1, -2, -3]], ['Podkast', [-4, 0, 4, 3, -1]], ['Klassisk', [2, 0, -1, 1, 3]]
  ] as [string, number[]][],
  sources: [['air', 'AirPlay'], ['bt', 'Blåtann'], ['radio', 'Radio'], ['aux', 'AUX'], ['usb', 'USB'], ['hp', 'Hodetelefoner']] as [EqSource, string][],
  defaults: { air: 0, bt: 1, radio: 2, aux: 0, usb: 0, hp: 3 } as Record<EqSource, number>
};

export function defaultEq(): EqProfiles {
  const o = {} as EqProfiles;
  for (const [k] of EQ.sources) {
    const p = EQ.defaults[k];
    o[k] = { preset: p, eq: [...(EQ.presets[p]?.[1] ?? [0, 0, 0, 0, 0])], loud: k !== 'hp' };
  }
  return o;
}

export const DEF: Settings = {
  bass: 0, treb: 0, bal: 0, vstart: 0, vmax: 0, perIn: true, hpOwn: true, lvlAux: 0, lvlUsb: 0,
  name: 0, nameCustom: '', nAux1: 'AUX 1', nAux2: 'AUX 2', nUsb1: 'PC 1', nUsb2: 'PC 2',
  hold: 2, voice: true, lang: 0, vv: 1, dim: 1, off: 1, clock: true, clockStyle: 0, led: 0, auto: 1, wake: true,
  updChannel: 0, updAuto: true, setupDone: false,
  eq: defaultEq()
};

export const fmt = {
  dB: (v: number) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + ' dB',
  bal: (v: number) => (v === 0 ? 'Midt' : (v < 0 ? 'V ' : 'H ') + Math.abs(v))
} as const;

export type NumKey = 'bass' | 'treb' | 'bal' | 'lvlAux' | 'lvlUsb';
export type OptKey = 'vstart' | 'vmax' | 'name' | 'hold' | 'lang' | 'vv' | 'dim' | 'off' | 'led' | 'auto';
export type BoolKey = 'perIn' | 'hpOwn' | 'voice' | 'clock' | 'wake';
export type StrKey = 'nAux1' | 'nAux2' | 'nUsb1' | 'nUsb2' | 'nameCustom';

export type Item =
  | { kind: 'num'; k: NumKey; n: string; mn: number; mx: number; f: keyof typeof fmt; hint?: string }
  | { kind: 'opt'; k: OptKey; n: string; list: string[]; hint?: string }
  | { kind: 'bool'; k: BoolKey; n: string; hint?: string }
  | { kind: 'str'; k: StrKey; n: string; ph: string; hint?: string }
  // API-styrte rader (leses fra /api/status, skrives med egne endepunkt)
  | { kind: 'api-bool'; id: 'loudness' | 'mix' | 'autoInput' | 'hpAutomute' | 'voiceOn'; n: string; hint?: string }
  | { kind: 'api-opt'; id: 'voiceProfile' | 'usbPc' | 'loudLevel'; n: string; hint?: string }
  | { kind: 'levels'; n: string; hint?: string }
  | { kind: 'info'; n: string; key: 'btDev' | 'lyrion' | 'version' | 'ip' | 'id' | 'board' | 'headphones' | 'btPairing' | 'inputs' | 'output' }
  | { kind: 'test'; n: string; hint?: string }
  | { kind: 'act'; n: string; id: 'btPair' | 'openRadio' | 'setup' | 'testVoice' | 'forget' | 'reset' | 'reboot' | 'findDevice'; label: string; safe?: boolean; hint?: string }
  | { kind: 'eq'; n: string }
  | { kind: 'clocks'; n: string }
  | { kind: 'update'; n: string };

export interface Category { id: string; n: string; sub: string; items: Item[] }

const num = (k: NumKey, n: string, mn: number, mx: number, f: keyof typeof fmt, hint?: string): Item => ({ kind: 'num', k, n, mn, mx, f, hint });
const opt = (k: OptKey, n: string, list: string[], hint?: string): Item => ({ kind: 'opt', k, n, list, hint });
const bool = (k: BoolKey, n: string, hint?: string): Item => ({ kind: 'bool', k, n, hint });
const str = (k: StrKey, n: string, ph: string, hint?: string): Item => ({ kind: 'str', k, n, ph, hint });

export const CATS: Category[] = [
  { id: 'eq', n: 'Equalizer', sub: 'Egen profil per inngang', items: [{ kind: 'eq', n: 'Equalizer' }] },
  { id: 'lyd', n: 'Lyd', sub: 'Tone, volum og nivå', items: [
    { kind: 'info', n: 'Lydutgang', key: 'output' },
    num('bass', 'Bass', -6, 6, 'dB'), num('treb', 'Diskant', -6, 6, 'dB'), num('bal', 'Balanse', -5, 5, 'bal'),
    { kind: 'api-bool', id: 'loudness', n: 'Loudness', hint: 'Mer bass og diskant ved lavt volum' },
    { kind: 'api-opt', id: 'loudLevel', n: 'Loudness-styrke' },
    opt('vstart', 'Startvolum', ['Sist brukt', '20', '30', '40']), opt('vmax', 'Maksvolum', ['100', '90', '80', '70']),
    bool('perIn', 'Volum per inngang', 'Hver inngang husker sitt eget volum'), bool('hpOwn', 'Eget volum for hodetelefoner'),
    { kind: 'api-bool', id: 'hpAutomute', n: 'Demp høyttalerne med hodetelefoner', hint: 'Når hodetelefoner plugges i fronten' },
    { kind: 'info', n: 'Hodetelefoner', key: 'headphones' },
    { kind: 'api-bool', id: 'mix', n: 'Miks digitale kilder', hint: 'AirPlay, Blåtann, USB og radio kan spille samtidig' },
    { kind: 'levels', n: 'Nivå per kilde', hint: 'Juster så kildene er like høye' },
    num('lvlAux', 'Nivå AUX', -6, 6, 'dB', 'Juster så AUX er like høy som strømming'), num('lvlUsb', 'Nivå USB', -6, 6, 'dB'),
    { kind: 'test', n: 'Test høyttalerne', hint: 'Spill en tone i venstre eller høyre høyttaler' }] },
  { id: 'tilkobling', n: 'Tilkobling', sub: 'Navn, Blåtann og USB', items: [
    opt('name', 'Enhetsnavn', NAMES, 'Navnet som vises i AirPlay og Blåtann'),
    str('nameCustom', 'Eget navn', 'Valgfritt', 'Overstyrer listen over – AirPlay, Spotify og Blåtann'),
    str('nAux1', 'Navn på AUX 1', 'AUX 1', 'Vises på skjermen og i appen'), str('nAux2', 'Navn på AUX 2', 'AUX 2'),
    str('nUsb1', 'Navn på USB-C «PC 1»', 'PC', 'For eksempel Mac eller Jobb-PC'), str('nUsb2', 'Navn på USB-C «PC 2»', 'Switch'),
    { kind: 'api-opt', id: 'usbPc', n: 'USB-bryter', hint: 'Hvilken PC tastatur, mus og USB-lyd følger' },
    { kind: 'api-bool', id: 'autoInput', n: 'Bytt kilde automatisk', hint: 'Når AirPlay, Blåtann eller radio begynner å spille' },
    { kind: 'info', n: 'Tilkoblet Blåtann-enhet', key: 'btDev' },
    { kind: 'act', n: 'Blåtann-paring', id: 'btPair', label: 'Start paring', safe: true, hint: 'Gjør forsterkeren synlig for Blåtann i 2 minutter' },
    { kind: 'act', n: 'Glem alle Blåtann-enheter', id: 'forget', label: 'Glem alle' }] },
  { id: 'radio', n: 'Radio', sub: 'Favoritter 1–6 fra Lyrion', items: [
    opt('hold', 'Hold radioknappen', ['1', '2', '3', '4', '5', '6'], 'Favoritten som spilles når du holder radioknappen inne'),
    { kind: 'info', n: 'Lyrion', key: 'lyrion' },
    { kind: 'act', n: 'Administrer favoritter', id: 'openRadio', label: 'Åpne', safe: true }] },
  { id: 'stemme', n: 'Stemme', sub: 'Talebeskjeder', items: [
    { kind: 'api-bool', id: 'voiceOn', n: 'Talebeskjed ved bytte' },
    { kind: 'api-opt', id: 'voiceProfile', n: 'Stemme' },
    opt('lang', 'Språk', LANGS), opt('vv', 'Stemmevolum', ['Lav', 'Middels', 'Høy']),
    { kind: 'act', n: 'Test stemme', id: 'testVoice', label: 'Spill av', safe: true }] },
  { id: 'skjerm', n: 'Skjerm og lys', sub: 'Dimming, klokke, LED', items: [
    opt('dim', 'Dimme skjermen etter', ['Av', '30 s', '1 min']), opt('off', 'Slukk skjermen etter', ['Av', '2 min', '5 min'], 'Beskytter OLED-skjermen mot innbrenning'),
    bool('clock', 'Klokke i standby'), { kind: 'clocks', n: 'Klokke i standby' }, opt('led', 'LED-ringer', ['Høy', 'Middels', 'Lav', 'Av'])] },
  { id: 'strom', n: 'Strøm', sub: 'Standby og påslag', items: [
    opt('auto', 'Auto-standby uten lyd', ['Av', '20 min', '60 min']), bool('wake', 'Slå på ved signal', 'AirPlay eller Blåtann vekker forsterkeren')] },
  { id: 'rom', n: 'Rom og grupper', sub: 'Multirom – kommer', items: [] },
  { id: 'oppdatering', n: 'Oppdatering', sub: 'GitHub Releases', items: [{ kind: 'update', n: 'Oppdatering' }] },
  { id: 'system', n: 'System', sub: 'Om, oppsett og tilbakestilling', items: [
    { kind: 'info', n: 'Programvare', key: 'version' }, { kind: 'info', n: 'Adresse', key: 'ip' },
    { kind: 'info', n: 'Lyrion', key: 'lyrion' }, { kind: 'info', n: 'Enhets-ID', key: 'id' }, { kind: 'info', n: 'Type', key: 'board' },
    { kind: 'act', n: 'Kjør oppsett på nytt', id: 'setup', label: 'Start oppsett', safe: true },
    { kind: 'act', n: 'Bytt forsterker', id: 'findDevice', label: 'Finn Skjold', safe: true, hint: 'Koble appen til en annen Skjold' },
    { kind: 'act', n: 'Fabrikkinnstillinger', id: 'reset', label: 'Tilbakestill' }] }
];

export const ICONS: Record<string, string> = {
  home: 'M4 11l8-7 8 7v9H4zM10 20v-5h4v5',
  play: 'M8 5v14l11-7z',
  eq: 'M5 4v6M5 14v6M12 4v3M12 11v9M19 4v9M19 17v3M3 12h4M10 9h4M17 15h4',
  lyd: 'M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12',
  tilkobling: 'M7 7l10 10-5 5V2l5 5L7 17',
  radio: 'M4 9h16v11H4zM8 9l9-5M8 14.5h.01M14 13h4M14 16h4',
  stemme: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3',
  skjerm: 'M3 5h18v12H3zM8 21h8M12 17v4',
  strom: 'M12 3v8M6.3 6.6a8 8 0 1 0 11.4 0',
  rom: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  oppdatering: 'M12 4v11M7 10l5 5 5-5M5 20h14',
  system: 'M12 8v4M12 16h.01M12 3l9 4v6c0 5-4 8-9 9-5-1-9-4-9-9V7z',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z'
};

export const CAT_TILE: Record<string, string> = {
  eq: '#3a2e17', lyd: '#2a3340', tilkobling: '#22314a', radio: '#3d2a2a', stemme: '#2f2a40', skjerm: '#2a3a33',
  strom: '#40362a', rom: '#2a3a33', oppdatering: '#3a2e17', system: '#333335'
};

/** Bezier curve through the five EQ bands – same geometry as the design file. */
export function eqCurve(eq: number[], w: number, h: number): { line: string; area: string; mid: number } {
  const n = eq.length, xs = eq.map((_, i) => (w * (i + 0.5)) / n), mid = h / 2;
  const ys = eq.map((v) => mid - (v * (h / 2 - 6)) / 12);
  const y0 = ys[0] ?? mid, x0 = xs[0] ?? 0;
  let d = 'M0 ' + y0.toFixed(1) + ' L' + x0.toFixed(1) + ' ' + y0.toFixed(1);
  for (let i = 0; i < n - 1; i++) {
    const xa = xs[i] ?? 0, xb = xs[i + 1] ?? 0, ya = ys[i] ?? mid, yb = ys[i + 1] ?? mid, mx = (xa + xb) / 2;
    d += ' C' + mx.toFixed(1) + ' ' + ya.toFixed(1) + ' ' + mx.toFixed(1) + ' ' + yb.toFixed(1) + ' ' + xb.toFixed(1) + ' ' + yb.toFixed(1);
  }
  d += ' L' + w + ' ' + (ys[n - 1] ?? mid).toFixed(1);
  return { line: d, area: d + ' L' + w + ' ' + mid + ' L0 ' + mid + ' Z', mid };
}

/** Deterministic placeholder artwork for a title/station (used when there is no cover image). */
export function art(key: string): { bg: string; ink: string } {
  let h = 0;
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) % 360;
  return {
    bg: `linear-gradient(150deg, oklch(0.42 0.09 ${h}) 0%, oklch(0.2 0.04 ${(h + 40) % 360}) 100%)`,
    ink: `oklch(0.93 0.03 ${h})`
  };
}

export function mergeSettings(partial: unknown): Settings {
  const p = (partial && typeof partial === 'object' ? partial : {}) as Record<string, unknown>;
  const s: Settings = { ...DEF, eq: defaultEq() };
  for (const k of Object.keys(DEF) as (keyof Settings)[]) {
    if (k === 'eq') continue;
    const v = p[k];
    if (v !== undefined && typeof v === typeof DEF[k]) (s as unknown as Record<string, unknown>)[k] = v;
  }
  const eq = p['eq'];
  if (eq && typeof eq === 'object') {
    for (const [src] of EQ.sources) {
      const prof = (eq as Record<string, unknown>)[src] as Partial<EqProfile> | undefined;
      if (prof && Array.isArray(prof.eq) && prof.eq.length === 5) {
        s.eq[src] = { preset: typeof prof.preset === 'number' ? prof.preset : -1, eq: prof.eq.map((x) => Number(x) || 0), loud: !!prof.loud };
      }
    }
  }
  return s;
}

/**
 * Hva som finnes på hver enhetstype. S1 = alt. Node: skjerm og knapper, men ingen AUX/USB/hodetelefoner.
 * Core (ren Pi): ingen skjerm, knapper, AUX/USB, hodetelefoner eller radioknapp – bare lyd, utgang og Blåtann.
 */
const NO_DISPLAY = new Set(['skjerm']);
const AUX_USB = new Set(['nAux1', 'nAux2', 'nUsb1', 'nUsb2', 'usbPc', 'lvlAux', 'lvlUsb']);
const HEADPHONES = new Set(['hpAutomute', 'headphones', 'hpOwn']);
const BUTTONS = new Set(['hold']);
function itemKey(it: Item): string {
  if ('k' in it) return it.k;
  if (it.kind === 'info') return it.key;
  if ('id' in it) return it.id;
  return it.kind;
}
export function catsFor(product: 's1' | 'node' | 'core', inputs: string[] = []): Category[] {
  const hasAux = product === 's1' || inputs.some((i) => i === 'aux' || i === 'aux2');
  const hasUsb = product === 's1' || inputs.includes('usb');
  return CATS.filter((c) => !(product === 'core' && NO_DISPLAY.has(c.id))).map((c) => ({
    ...c,
    sub: product === 'core' && c.id === 'tilkobling' ? 'Navn og Blåtann' : c.sub,
    items: c.items.filter((it) => {
      const k = itemKey(it);
      if (k === 'output') return product !== 's1';
      if (AUX_USB.has(k)) return k.toLowerCase().includes('usb') ? hasUsb : hasAux;
      if (HEADPHONES.has(k)) return product === 's1';
      if (BUTTONS.has(k)) return product !== 'core';
      return true;
    })
  }));
}
