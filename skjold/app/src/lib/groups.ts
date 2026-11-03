// Grupper av rom: hvem som er med, «Synkron» / «Surround», oppsett (2.1–5.1), plasser, avstand, nivå og synk-innstillinger.
// Forsterkeren har ikke API for synkronisert avspilling (Lyrion-synk) ennå, så gruppene lagres bare i appen.
import { signal } from '@preact/signals';

export interface Gset { layout: string; vol: 'rel' | 'abs'; buf: number; lead?: string; xo: number; phase: number; dist: Record<string, number>; lvl: Record<string, number>; trim: Record<string, number> }
export interface Groups { members: string[]; mode: 'sync' | 'surround'; roles: Record<string, number | null>; gset: Gset; presets: { n: string; ids: string[] }[] }
export const ROLES = ['Stereo', 'Venstre', 'Høyre', 'Bak V', 'Bak H', 'Sub', 'Senter'];
/** Surround-oppsett: [id, navn, plasser (ROLES-indekser)] */
export const LAYOUTS: [string, string, number[]][] = [['stereo', 'Stereopar', [1, 2]], ['2.1', '2.1', [1, 2, 5]], ['3.1', '3.1', [1, 6, 2, 5]], ['4.0', '4.0', [1, 2, 3, 4]], ['5.1', '5.1', [1, 6, 2, 3, 4, 5]]];
export const SLOT_POS: Record<number, [number, number]> = { 1: [16, 16], 6: [50, 12], 2: [84, 16], 5: [70, 30], 3: [12, 84], 4: [88, 84] };
export const ROLE_FULL: Record<number, string> = { 1: 'Front venstre', 2: 'Front høyre', 3: 'Bak venstre', 4: 'Bak høyre', 5: 'Sub', 6: 'Senter' };
const GSET_DEF: Gset = { layout: 'stereo', vol: 'rel', buf: 1, xo: 80, phase: 0, dist: {}, lvl: {}, trim: {} };
export const delayMs = (d: number, maxD: number): number => Math.max(0, (maxD - d) / 343 * 1000);

const KEY = 'skjold-groups';
function load(): Groups {
  try {
    const j = JSON.parse(localStorage.getItem(KEY) || 'null') as Partial<Groups> | null;
    if (j && Array.isArray(j.members)) return { members: j.members, mode: j.mode === 'surround' ? 'surround' : 'sync', roles: j.roles ?? {}, gset: { ...GSET_DEF, ...(j.gset ?? {}) }, presets: Array.isArray(j.presets) ? j.presets : [] };
  } catch { /* ignore */ }
  return { members: [], mode: 'sync', roles: {}, gset: { ...GSET_DEF }, presets: [] };
}
export const groups = signal<Groups>(load());
function save(g: Groups): void { groups.value = g; try { localStorage.setItem(KEY, JSON.stringify(g)); } catch { /* ignore */ } }

/** Er rommet med i gruppen til det aktive rommet? (Det aktive er alltid med.) */
export const inGroup = (key: string, activeKey: string): boolean => key === activeKey || (groups.value.members.includes(key) && groups.value.members.includes(activeKey));
export function members(activeKey: string): string[] { const m = groups.value.members; return m.includes(activeKey) ? m : [activeKey]; }
export function toggleMember(activeKey: string, key: string): void {
  if (key === activeKey) return;
  const g = groups.value; let m = g.members.includes(activeKey) ? g.members.slice() : [activeKey];
  m = m.includes(key) ? m.filter((x) => x !== key) : [...m, key];
  if (m.length < 2) m = [];
  save({ ...g, members: m });
}
export function setMembers(keys: string[]): void { save({ ...groups.value, members: keys.length > 1 ? keys.slice() : [] }); }
export function groupAll(keys: string[]): void { setMembers(keys); }
export function groupNone(): void { save({ ...groups.value, members: [] }); }
function layoutFor(n: number): string { return n >= 6 ? '5.1' : n >= 4 ? '3.1' : n === 3 ? '2.1' : 'stereo'; }
export function applyLayout(layout: string): void {
  const g = groups.value, L = LAYOUTS.find((l) => l[0] === layout) ?? LAYOUTS[0]!, roles: Record<string, number | null> = { ...g.roles };
  g.members.forEach((k, i) => { roles[k] = i < L[2].length ? L[2][i]! : null; });
  save({ ...g, roles, gset: { ...g.gset, layout } });
}
export function setMode(mode: 'sync' | 'surround'): void {
  save({ ...groups.value, mode });
  if (mode === 'surround') { const g = groups.value; applyLayout(g.gset.layout !== 'stereo' ? g.gset.layout : layoutFor(g.members.length)); }
}
export function placeRoom(key: string, role: number | null): void {
  const g = groups.value, roles: Record<string, number | null> = { ...g.roles };
  g.members.forEach((k) => { if (k === key) roles[k] = role; else if (role != null && roles[k] === role) roles[k] = null; });
  save({ ...g, roles });
}
export function setRole(key: string, role: number): void { save({ ...groups.value, roles: { ...groups.value.roles, [key]: role } }); }
export function setGset(p: Partial<Gset>): void { save({ ...groups.value, gset: { ...groups.value.gset, ...p } }); }
export function savePreset(n: string, ids: string[]): void { save({ ...groups.value, presets: [...groups.value.presets, { n, ids }].slice(-6) }); }
export function groupCount(activeKey: string): number { const m = groups.value.members; return m.includes(activeKey) ? m.length : 1; }
