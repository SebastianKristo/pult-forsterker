/**
 * SHA-512-crypt ($6$) etter Ulrich Drepper sin spesifikasjon – samme format som `openssl passwd -6`
 * og det Raspberry Pi OS forventer i userconf.txt / custom.toml (password_encrypted = true).
 */
import { createHash, randomBytes } from 'crypto';

const ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

function sha512(...parts: Buffer[]): Buffer {
  const h = createHash('sha512');
  for (const p of parts) h.update(p);
  return h.digest();
}

function repeatTo(src: Buffer, len: number): Buffer {
  const out = Buffer.alloc(len);
  for (let i = 0; i < len; i++) out[i] = src[i % src.length];
  return out;
}

export function randomSalt(len = 16): string {
  const b = randomBytes(len);
  let s = '';
  for (let i = 0; i < len; i++) s += ITOA64[b[i] & 63];
  return s;
}

export function sha512crypt(password: string, salt: string = randomSalt(), rounds = 5000): string {
  const P = Buffer.from(password, 'utf8');
  const S = Buffer.from(salt.slice(0, 16), 'utf8');
  const customRounds = rounds !== 5000;
  rounds = Math.min(999999999, Math.max(1000, rounds));

  const B = sha512(P, S, P);
  const a = createHash('sha512');
  a.update(P); a.update(S);
  let i = P.length;
  for (; i > 64; i -= 64) a.update(B);
  a.update(B.subarray(0, i));
  for (let n = P.length; n > 0; n >>= 1) a.update(n & 1 ? B : P);
  const A = a.digest();

  const dp = createHash('sha512');
  for (let k = 0; k < P.length; k++) dp.update(P);
  const Pseq = repeatTo(dp.digest(), P.length);
  const ds = createHash('sha512');
  for (let k = 0; k < 16 + A[0]; k++) ds.update(S);
  const Sseq = repeatTo(ds.digest(), S.length);

  let C = A;
  for (let r = 0; r < rounds; r++) {
    const c = createHash('sha512');
    c.update(r & 1 ? Pseq : C);
    if (r % 3) c.update(Sseq);
    if (r % 7) c.update(Pseq);
    c.update(r & 1 ? C : Pseq);
    C = c.digest();
  }

  const order = [
    [0, 21, 42], [22, 43, 1], [44, 2, 23], [3, 24, 45], [25, 46, 4], [47, 5, 26], [6, 27, 48],
    [28, 49, 7], [50, 8, 29], [9, 30, 51], [31, 52, 10], [53, 11, 32], [12, 33, 54], [34, 55, 13],
    [56, 14, 35], [15, 36, 57], [37, 58, 16], [59, 17, 38], [18, 39, 60], [40, 61, 19], [62, 20, 41],
  ];
  let out = '';
  const enc = (b2: number, b1: number, b0: number, n: number) => {
    let w = (b2 << 16) | (b1 << 8) | b0;
    while (n-- > 0) { out += ITOA64[w & 63]; w >>= 6; }
  };
  for (const [x, y, z] of order) enc(C[x], C[y], C[z], 4);
  enc(0, 0, C[63], 2);
  return `$6$${customRounds ? `rounds=${rounds}$` : ''}${S.toString('utf8')}$${out}`;
}
