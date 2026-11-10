// Haptikk på glidebrytere (EQ, balanse) i web og Capacitor-appen. Bruker navigator.vibrate der det finnes
// (Android/Chrome); iOS Safari har ikke vibrate, så der skjer ingenting – uten feil.
const KEY = 'hapticSliders';

export function hapticsOn(): boolean {
  try { return localStorage.getItem(KEY) !== '0'; } catch { return true; }
}
export function setHapticsOn(on: boolean): void {
  try { localStorage.setItem(KEY, on ? '1' : '0'); } catch { /* privat modus */ }
  if (on) buzz(8);
}

function buzz(p: number | number[]): void {
  try { if (typeof navigator !== 'undefined' && 'vibrate' in navigator) navigator.vibrate(p); } catch { /* ikke støttet */ }
}

/** Lett tikk per hele steg, tydelig klikk på/over nullpunktet, kraftig «stopp» når grensen nås. */
export function sliderStep(old: number, v: number, min: number, max: number, zero: number | null = 0): void {
  if (old === v || !hapticsOn()) return;
  if (v === min || v === max) buzz([20, 40, 20]);
  else if (zero !== null && (v === zero || ((old < zero) !== (v < zero) && old !== zero))) buzz(15);
  else buzz(5);
}

/** Lett bekreftelse (slipp, valgt profil). */
export function confirmTap(): void { if (hapticsOn()) buzz(10); }

/** Lite tikk (linsen i Låt/Kø krysser midten). */
export function tick(): void { if (hapticsOn()) buzz(6); }
