// Pinne-editoren for Skjold S1 rev F: validering og bytting av GPIO-pinner i web-UI-et.
// Reglene kommer fra daemonen (GET /api/s1f/pins → regler) og er de samme som valider_pinner i pi/skjold_s1f.py.
// Daemonen validerer på nytt før den lagrer – dette er bare for å vise feil og advarsler mens man redigerer.
import type { S1fRegler, S1fTildeling } from './api';

/** Farge og navn per gruppe i tegningen og listen. */
export const GRUPPE: Record<string, { navn: string; farge: string }> = {
  knapp: { navn: 'Knapper', farge: '#e0a63a' },
  lys: { navn: 'LED-ringer', farge: '#f2dc6b' },
  hjul: { navn: 'Volumhjul', farge: '#5fb3d9' },
  rele: { navn: 'Relé', farge: '#f07f5c' },
  hp: { navn: 'Hodetelefondetekt', farge: '#b48ae0' },
  usbsw: { navn: 'USB-switch', farge: '#5fd99a' },
  dac: { navn: 'DAC XSMT', farge: '#e08ad0' },
  i2s: { navn: 'Lydkort I²S (fast)', farge: '#4f7fe0' },
  reservert: { navn: 'Reservert (HAT-EEPROM)', farge: '#77777a' },
};
/** Strømpinnene i tegningen. */
export const STROM: Record<string, string> = { '3V3': '#e8873a', '5V': '#c0392b', GND: '#1d1d1f' };
/** I²S-pinnene til PCM5102 (de reserverte utenom 0/1). */
export const I2S = new Set([18, 19, 21]);

export interface Validering { feil: string[]; advarsler: string[] }

/** BCM → fysisk pinne, fra headeren daemonen sender. */
export function fysisk(r: S1fRegler): Map<number, number> {
  const m = new Map<number, number>();
  for (const p of r.header) if (p.gpio !== null) m.set(p.gpio, p.fys);
  return m;
}

/** Kan pinnen brukes til en funksjon? null = ja, ellers hvorfor ikke. */
export function sperret(r: S1fRegler, gpio: number): string | null {
  const res = r.reservert[String(gpio)];
  if (res) return 'Reservert – ' + res;
  const fys = fysisk(r).get(gpio);
  if (fys === undefined) return `GPIO${gpio} finnes ikke`;
  const [fra = 31, til = 40] = r.lydkort_fys;
  if (fys >= fra && fys <= til) return `Pinne ${fra}–${til} holdes fri til lydkortet (og GND)`;
  return null;
}

/** GPIO-ene som kan velges, i rekkefølgen på headeren. */
export function ledigeGpio(r: S1fRegler): number[] {
  return r.header.filter((p) => p.gpio !== null && !sperret(r, p.gpio)).map((p) => p.gpio as number);
}

export function navnPaa(r: S1fRegler, fid: string): string {
  return r.funksjoner.find((f) => f.id === fid)?.navn ?? fid;
}

/** Hvilken funksjon har pinnen nå? */
export function eierAv(t: S1fTildeling, gpio: number): string | undefined {
  return Object.keys(t).find((k) => t[k] === gpio);
}

/** Samme regler som valider_pinner i skjold_s1f.py (feil = lagres ikke, advarsler = lagres). */
export function valider(r: S1fRegler, t: S1fTildeling): Validering {
  const feil: string[] = [], advarsler: string[] = [];
  const brukt = new Map<number, string[]>();
  for (const f of r.funksjoner) {
    const g = t[f.id];
    if (g === null || g === undefined) continue;
    const s = sperret(r, g);
    if (s) feil.push(`${f.navn}: GPIO${g} – ${s}`);
    brukt.set(g, [...(brukt.get(g) ?? []), f.id]);
  }
  for (const [g, fids] of [...brukt].sort((a, b) => a[0] - b[0])) {
    if (fids.length > 1) feil.push(`GPIO${g} er brukt to ganger: ` + fids.map((f) => navnPaa(r, f)).join(' og '));
  }
  // Samlet per krav (I²C/UART/SPI av), så listen ikke blir lang: «GPIO2 (Knapp USB), GPIO3 (Lys av/på) – I²C må være av …»
  const perVarsel = new Map<string, string[]>();
  for (const [g, fids] of [...brukt].sort((a, b) => a[0] - b[0])) {
    const v = r.varsel[String(g)];
    if (v && !r.reservert[String(g)]) perVarsel.set(v, [...(perVarsel.get(v) ?? []), `GPIO${g} (${navnPaa(r, fids[0] ?? '')})`]);
  }
  for (const [v, pinner] of perVarsel) advarsler.push(`${pinner.join(', ')} – ${v}`);
  for (const fid of r.viktige) if (fid in t && t[fid] === null) advarsler.push(`${navnPaa(r, fid)} har ingen pinne`);
  return { feil, advarsler };
}

/**
 * Gi funksjonen `fid` pinnen `gpio` (fid = null: gjør pinnen ledig). Har en annen funksjon pinnen fra før, får den
 * pinnen `fid` hadde (de to byttes) – eller blir uten pinne hvis `fid` ikke hadde noen. Returnerer ny tildeling og
 * en melding som sier tydelig hva som skjedde.
 */
export function tildel(r: S1fRegler, t: S1fTildeling, gpio: number, fid: string | null): { t: S1fTildeling; melding: string } {
  const ny = { ...t };
  const eier = eierAv(t, gpio);
  if (fid === null) {
    if (!eier) return { t: ny, melding: `GPIO${gpio} er allerede ledig` };
    ny[eier] = null;
    return { t: ny, melding: `GPIO${gpio} er nå ledig – ${navnPaa(r, eier)} har ingen pinne` };
  }
  if (eier === fid) return { t: ny, melding: `${navnPaa(r, fid)} er allerede på GPIO${gpio}` };
  const gammel = t[fid] ?? null;
  ny[fid] = gpio;
  if (!eier) return { t: ny, melding: `${navnPaa(r, fid)} → GPIO${gpio}` + (gammel !== null ? ` (GPIO${gammel} er nå ledig)` : '') };
  ny[eier] = gammel;
  return {
    t: ny,
    melding: gammel !== null
      ? `Byttet: ${navnPaa(r, fid)} → GPIO${gpio} og ${navnPaa(r, eier)} → GPIO${gammel}`
      : `${navnPaa(r, fid)} → GPIO${gpio}. ${navnPaa(r, eier)} var på GPIO${gpio} og har nå ingen pinne`
  };
}

/** Funksjonene som er endret fra `fra` til `til`. */
export function endringer(r: S1fRegler, fra: S1fTildeling, til: S1fTildeling): string[] {
  const p = (v: number | null | undefined) => (v === null || v === undefined ? 'ingen' : 'GPIO' + v);
  return r.funksjoner.filter((f) => (fra[f.id] ?? null) !== (til[f.id] ?? null)).map((f) => `${f.navn}: ${p(fra[f.id])} → ${p(til[f.id])}`);
}
