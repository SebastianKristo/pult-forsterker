// Grupper av rom (Rom-fanen): hvem som er med, «Samme musikk» / «Surround» og roller.
// Forsterkeren har ikke API for synkronisert avspilling (Lyrion-synk) ennå, så gruppene lagres bare i appen.
import { signal } from '@preact/signals';

export interface Groups { members: string[]; mode: 'sync' | 'surround'; roles: Record<string, number> }
export const ROLES = ['Stereo', 'Venstre', 'Høyre', 'Bak V', 'Bak H', 'Sub'];
const KEY = 'skjold-groups';
function load(): Groups { try { const j = JSON.parse(localStorage.getItem(KEY) || 'null') as Groups | null; if (j && Array.isArray(j.members)) return { members: j.members, mode: j.mode === 'surround' ? 'surround' : 'sync', roles: j.roles ?? {} }; } catch { /* ignore */ } return { members: [], mode: 'sync', roles: {} }; }
export const groups = signal<Groups>(load());
function save(g: Groups): void { groups.value = g; try { localStorage.setItem(KEY, JSON.stringify(g)); } catch { /* ignore */ } }

/** Er rommet med i gruppen til det aktive rommet? (Det aktive er alltid med.) */
export const inGroup = (key: string, activeKey: string): boolean => key === activeKey || (groups.value.members.includes(key) && groups.value.members.includes(activeKey));
export function toggleMember(activeKey: string, key: string): void {
  if (key === activeKey) return;
  const g = groups.value; let m = g.members.includes(activeKey) ? g.members.slice() : [activeKey];
  m = m.includes(key) ? m.filter((x) => x !== key) : [...m, key];
  if (m.length < 2) m = [];
  save({ ...g, members: m });
}
export function groupAll(keys: string[]): void { save({ ...groups.value, members: keys.length > 1 ? keys.slice() : [] }); }
export function groupNone(): void { save({ ...groups.value, members: [] }); }
export function setMode(mode: 'sync' | 'surround'): void {
  const g = groups.value, roles = { ...g.roles };
  if (mode === 'surround') g.members.forEach((k, i) => { if (roles[k] == null) roles[k] = [0, 3, 4, 5][Math.min(3, i)] ?? 0; });
  save({ ...g, mode, roles });
}
export function setRole(key: string, role: number): void { save({ ...groups.value, roles: { ...groups.value.roles, [key]: role } }); }
export function groupCount(activeKey: string): number { const m = groups.value.members; return m.includes(activeKey) ? m.length : 1; }
