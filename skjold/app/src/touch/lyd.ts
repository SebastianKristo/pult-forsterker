// Trykkelyder for Skjold Touch: korte, myke klikk som kjennes som haptisk tilbakemelding. Lagd i Web Audio (ingen
// lydfiler), så de er klare med en gang. Lyden går ut på høyttalerne Touch spiller på (ALSA default → dmix → CamillaDSP),
// altså gjennom hovedvolumet. Nivået ligger langt under musikken, og de følger volumknappen.
//
// Lydene er bevisst diskré:
// - et kort «tikk» (båndpassfiltrert støy, ca. 6 ms) pluss en svak, lav «tokk» (sinus som faller fra ca. 190 til 120 Hz),
//   så det høres ut som et mykt trykk og ikke som et pip
// - litt tilfeldig tonehøyde og nivå (±4 %), så samme lyd mange ganger på rad ikke blir masete
// - tastene på tastaturet er lysere og svakere, sletting litt lavere, og raske trykk etter hverandre dempes litt
export type LydType = 'trykk' | 'tast' | 'slett' | 'på' | 'av';

const NIVÅ = [0, 0.035, 0.07];          // Av / Lav / Middels (lineær forsterkning før hovedvolumet)
let ctx: AudioContext | null = null, støy: AudioBuffer | null = null, sist = 0;

function lydCtx(): AudioContext | null {
  if (ctx) return ctx;
  try {
    ctx = new AudioContext({ latencyHint: 'interactive' });
    const n = Math.round(ctx.sampleRate * 0.03);
    støy = ctx.createBuffer(1, n, ctx.sampleRate);
    const d = støy.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  } catch { ctx = null; }
  return ctx;
}

const ARTER: Record<LydType, { f: number; q: number; tikk: number; tokk: number; lav: number; ms: number }> = {
  trykk: { f: 2600, q: 1.1, tikk: 1.0, tokk: 0.55, lav: 170, ms: 6 },
  tast: { f: 3400, q: 1.4, tikk: 0.75, tokk: 0.25, lav: 210, ms: 4 },
  slett: { f: 1900, q: 1.0, tikk: 0.8, tokk: 0.45, lav: 140, ms: 6 },
  på: { f: 3000, q: 1.2, tikk: 0.9, tokk: 0.5, lav: 200, ms: 6 },
  av: { f: 2200, q: 1.2, tikk: 0.9, tokk: 0.5, lav: 150, ms: 6 }
};

export function spillLyd(type: LydType, nivå: number): void {
  const g0 = NIVÅ[nivå] ?? 0;
  if (!g0) return;
  const c = lydCtx();
  if (!c || !støy) return;
  if (c.state === 'suspended') void c.resume();
  const nå = c.currentTime, a = ARTER[type];
  const tett = performance.now() - sist < 90 ? 0.6 : 1;   // fort etter hverandre: litt svakere
  sist = performance.now();
  const r = 1 + (Math.random() - 0.5) * 0.08;
  const g = g0 * tett * (1 + (Math.random() - 0.5) * 0.08);
  const ut = c.createGain(); ut.gain.value = g; ut.connect(c.destination);
  // tikk: støyburst gjennom båndpass, rask myk avklinging
  const src = c.createBufferSource(); src.buffer = støy;
  const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = a.f * r; bp.Q.value = a.q;
  const ev = c.createGain();
  ev.gain.setValueAtTime(0, nå); ev.gain.linearRampToValueAtTime(a.tikk, nå + 0.0008);
  ev.gain.exponentialRampToValueAtTime(0.0001, nå + a.ms / 1000 + 0.012);
  src.connect(bp); bp.connect(ev); ev.connect(ut);
  src.start(nå); src.stop(nå + 0.03);
  // tokk: lav sinus med fallende tone (gir «tyngde» uten å høres som en tone)
  const o = c.createOscillator(); o.type = 'sine';
  const start = a.lav * r * (type === 'på' ? 1.15 : 1), slutt = start * (type === 'på' ? 1.25 : 0.65);
  o.frequency.setValueAtTime(start, nå); o.frequency.exponentialRampToValueAtTime(slutt, nå + 0.03);
  const og = c.createGain();
  og.gain.setValueAtTime(0, nå); og.gain.linearRampToValueAtTime(a.tokk, nå + 0.002);
  og.gain.exponentialRampToValueAtTime(0.0001, nå + 0.035);
  o.connect(og); og.connect(ut);
  o.start(nå); o.stop(nå + 0.04);
}

/** Lytt på hele skjermen: knapper gir «trykk» når trykket blir et klikk (ikke når du ruller), elementer med
 *  data-lyd (tastaturet) gir lyden sin straks fingeren treffer. nivå() leser innstillingen (0 av, 1 lav, 2 middels). */
export function startTrykkelyder(nivå: () => number): void {
  const finn = (e: Event) => (e.target as Element | null)?.closest?.('[data-lyd],button,[role="button"]') as HTMLElement | null;
  document.addEventListener('pointerdown', (e) => {
    const el = finn(e);
    if (el?.dataset['lyd'] && !(el as HTMLButtonElement).disabled) spillLyd(el.dataset['lyd'] as LydType, nivå());
    else lydCtx();   // lag lydmotoren ved første trykk, så første klikk ikke kommer sent
  }, { capture: true, passive: true });
  document.addEventListener('click', (e) => {
    const el = finn(e);
    if (!el || el.dataset['lyd'] !== undefined || (el as HTMLButtonElement).disabled) return;
    const trykket = el.getAttribute('aria-pressed');
    spillLyd(trykket === 'true' ? 'av' : trykket === 'false' ? 'på' : 'trykk', nivå());
  }, { capture: true, passive: true });
}
