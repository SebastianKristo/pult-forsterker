// Romkorreksjon: Skjold spiller en logaritmisk sinus-sweep, nettleseren tar opp med mikrofonen og regner ut
// frekvensresponsen (spektralforhold opptak/sweep, 1/6-oktav glatting). Forslaget er bare kutt mellom 40 og 300 Hz,
// fordi telefonmikrofoner er unøyaktige under ~40 Hz og over ~10 kHz.
export interface Peq { f: number; q: number; g: number }
export interface Curve { f: number[]; db: number[] }

export function logSweep(f1: number, f2: number, dur: number, sr: number): Float32Array {
  const n = Math.round(dur * sr), k = Math.log(f2 / f1), out = new Float32Array(n), fade = Math.round(0.05 * sr);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let w = 1; if (i < fade) w = i / fade; else if (i > n - fade) w = (n - i) / fade;
    out[i] = Math.sin((2 * Math.PI * f1 * dur / k) * (Math.exp((t / dur) * k) - 1)) * w;
  }
  return out;
}

/** Radix-2 FFT på plass. re/im har lengde 2^m. */
export function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j]!, re[i]!]; [im[i], im[j]] = [im[j]!, im[i]!]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let j = 0; j < len / 2; j++) {
        const a = i + j, b = a + len / 2;
        const tr = re[b]! * cr - im[b]! * ci, ti = re[b]! * ci + im[b]! * cr;
        re[b] = re[a]! - tr; im[b] = im[a]! - ti; re[a] = re[a]! + tr; im[a] = im[a]! + ti;
        const ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

function power(x: Float32Array, n: number): Float64Array {
  const re = new Float64Array(n), im = new Float64Array(n);
  re.set(x.subarray(0, Math.min(x.length, n)));
  fft(re, im);
  const p = new Float64Array(n / 2);
  for (let i = 0; i < n / 2; i++) p[i] = re[i]! * re[i]! + im[i]! * im[i]!;
  return p;
}

/** Logaritmiske frekvenspunkter (24 per oktav) fra f1 til f2. */
export function logFreqs(f1 = 20, f2 = 1000, perOct = 24): number[] {
  const out: number[] = [];
  for (let f = f1; f <= f2 * 1.0001; f *= Math.pow(2, 1 / perOct)) out.push(f);
  return out;
}

/** Frekvensrespons i dB (1/6-oktav glattet) fra opptak og referansesweep, ved samme samplingsfrekvens. */
export function responseFromRecording(rec: Float32Array, sweep: Float32Array, sr: number, freqs = logFreqs()): Curve {
  let n = 1; while (n < Math.max(rec.length, sweep.length)) n <<= 1;
  const pr = power(rec, n), ps = power(sweep, n), hz = sr / n;
  const db = freqs.map((f) => {
    const lo = Math.max(1, Math.floor((f * Math.pow(2, -1 / 12)) / hz)), hi = Math.min(n / 2 - 1, Math.ceil((f * Math.pow(2, 1 / 12)) / hz));
    let a = 0, b = 0;
    for (let i = lo; i <= hi; i++) { a += pr[i]!; b += ps[i]!; }
    return 10 * Math.log10((a + 1e-20) / (b + 1e-20));
  });
  return { f: freqs, db };
}

export function averageCurves(cs: Curve[]): Curve {
  const f = cs[0]!.f;
  return { f, db: f.map((_, i) => cs.reduce((s, c) => s + c.db[i]!, 0) / cs.length) };
}

/** Peaking-filter (RBJ) i dB ved frekvens f, sr 48 kHz. */
export function peqDb(p: Peq, f: number, sr = 48000): number {
  const A = Math.pow(10, p.g / 40), w0 = (2 * Math.PI * p.f) / sr, al = Math.sin(w0) / (2 * p.q);
  const b0 = 1 + al * A, b1 = -2 * Math.cos(w0), b2 = 1 - al * A, a0 = 1 + al / A, a1 = b1, a2 = 1 - al / A;
  const w = (2 * Math.PI * f) / sr;
  const c1 = Math.cos(w), c2 = Math.cos(2 * w), s1 = Math.sin(w), s2 = Math.sin(2 * w);
  const nr = b0 + b1 * c1 + b2 * c2, ni = -(b1 * s1 + b2 * s2), dr = a0 + a1 * c1 + a2 * c2, di = -(a1 * s1 + a2 * s2);
  return 10 * Math.log10((nr * nr + ni * ni) / (dr * dr + di * di));
}

/** Referansenivå = snitt 300–1000 Hz. Inntil 8 kutt for topper over 2 dB mellom 40 og 300 Hz, maks −10 dB. */
export function suggest(c: Curve, max = 8): { filters: Peq[]; target: number; after: number[] } {
  const ref = c.f.map((f, i) => (f >= 300 && f <= 1000 ? c.db[i]! : NaN)).filter((x) => !isNaN(x));
  const target = ref.length ? ref.reduce((a, b) => a + b, 0) / ref.length : 0;
  const err = c.db.map((d) => d - target);
  const filters: Peq[] = [];
  for (let k = 0; k < max; k++) {
    let bi = -1, bv = 2;
    c.f.forEach((f, i) => { if (f >= 40 && f <= 300 && err[i]! > bv) { bv = err[i]!; bi = i; } });
    if (bi < 0) break;
    const half = bv / 2; let lo = bi, hi = bi;
    while (lo > 0 && err[lo - 1]! > half) lo--;
    while (hi < c.f.length - 1 && err[hi + 1]! > half) hi++;
    const f0 = c.f[bi]!, bw = Math.max(c.f[hi]! - c.f[lo]!, f0 / 15);
    const p: Peq = { f: Math.round(f0 * 10) / 10, q: Math.round(Math.max(1, Math.min(10, f0 / bw)) * 100) / 100, g: -Math.round(Math.min(10, bv) * 10) / 10 };
    filters.push(p);
    c.f.forEach((f, i) => { err[i] = err[i]! + peqDb(p, f); });
  }
  const after = c.db.map((d, i) => d + filters.reduce((s, p) => s + peqDb(p, c.f[i]!), 0));
  return { filters, target, after };
}

/** Tar opp mikrofonen i `secs` sekunder (uten ekkodemping/autoforsterkning). */
export async function recordMic(secs: number, onStart?: () => void): Promise<{ data: Float32Array; sr: number }> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  proc.onaudioprocess = (e) => { chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
  src.connect(proc); proc.connect(ctx.destination);
  onStart?.();
  await new Promise((r) => setTimeout(r, secs * 1000));
  proc.disconnect(); src.disconnect(); stream.getTracks().forEach((t) => t.stop());
  const sr = ctx.sampleRate; await ctx.close();
  const n = chunks.reduce((s, c) => s + c.length, 0), data = new Float32Array(n);
  let o = 0; for (const c of chunks) { data.set(c, o); o += c.length; }
  return { data, sr };
}
