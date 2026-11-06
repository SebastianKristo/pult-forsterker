// Liten QR-generator (byte-modus, feilretting L, versjon 1–4, ett blokk per versjon) – nok for HomeKit-adressen
// X-HM://… (20 tegn). Ingen ekstern avhengighet. Returnerer en matrise med true = mørk modul.

const CAP = [0, 17, 32, 53, 78];          // byte-kapasitet for versjon 1–4, nivå L
const DATA = [0, 19, 34, 55, 80];         // datakodeord
const ECC = [0, 7, 10, 15, 20];           // feilrettingskodeord (ett blokk)
const ALIGN = [0, 0, 18, 22, 26];         // senter for justeringsmønster (versjon 2–4)

function gfMul(a: number, b: number): number {
  let r = 0;
  for (let i = 7; i >= 0; i--) { r = (r << 1) ^ ((r >>> 7) * 0x11d); r ^= ((b >>> i) & 1) * a; }
  return r & 0xff;
}
function rsDivisor(deg: number): number[] {
  const res = new Array<number>(deg).fill(0); res[deg - 1] = 1; let root = 1;
  for (let i = 0; i < deg; i++) {
    for (let j = 0; j < deg; j++) { res[j] = gfMul(res[j]!, root); if (j + 1 < deg) res[j] = res[j]! ^ res[j + 1]!; }
    root = gfMul(root, 2);
  }
  return res;
}
function rsRemainder(data: number[], div: number[]): number[] {
  const res = new Array<number>(div.length).fill(0);
  for (const b of data) {
    const f = b ^ res.shift()!; res.push(0);
    div.forEach((c, i) => { res[i] = res[i]! ^ gfMul(c, f); });
  }
  return res;
}

export function qrMatrix(text: string): boolean[][] {
  const bytes = Array.from(new TextEncoder().encode(text));
  const ver = CAP.findIndex((c, i) => i > 0 && bytes.length <= c);
  if (ver < 1) throw new Error('For lang tekst for QR');
  const n = 17 + 4 * ver;
  // data: modus 0100, lengde 8 bit, bytes, terminator, fyll
  const bits: number[] = [];
  const put = (v: number, len: number) => { for (let i = len - 1; i >= 0; i--) bits.push((v >>> i) & 1); };
  put(4, 4); put(bytes.length, 8); bytes.forEach((b) => put(b, 8));
  const cap = DATA[ver]! * 8;
  put(0, Math.min(4, cap - bits.length));
  while (bits.length % 8) bits.push(0);
  const cw: number[] = [];
  for (let i = 0; i < bits.length; i += 8) cw.push(parseInt(bits.slice(i, i + 8).join(''), 2));
  for (let p = 0; cw.length < DATA[ver]!; p++) cw.push(p % 2 ? 0x11 : 0xec);
  const all = cw.concat(rsRemainder(cw, rsDivisor(ECC[ver]!)));

  const m: boolean[][] = Array.from({ length: n }, () => new Array<boolean>(n).fill(false));
  const fn: boolean[][] = Array.from({ length: n }, () => new Array<boolean>(n).fill(false));
  const set = (x: number, y: number, d: boolean) => { m[y]![x] = d; fn[y]![x] = true; };
  const finder = (cx: number, cy: number) => {
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
      const x = cx + dx, y = cy + dy; if (x < 0 || y < 0 || x >= n || y >= n) continue;
      const d = Math.max(Math.abs(dx), Math.abs(dy)); set(x, y, d !== 2 && d !== 4);
    }
  };
  finder(3, 3); finder(n - 4, 3); finder(3, n - 4);
  for (let i = 8; i < n - 8; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
  if (ALIGN[ver]) { const c = ALIGN[ver]!; for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(c + dx, c + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1); }
  // formatinfo: nivå L (01), maske 0
  const fmtData = (1 << 3) | 0; let rem = fmtData;
  for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  const fmt = ((fmtData << 10) | rem) ^ 0x5412;
  const fb = (i: number) => ((fmt >>> i) & 1) === 1;
  for (let i = 0; i <= 5; i++) set(8, i, fb(i));
  set(8, 7, fb(6)); set(8, 8, fb(7)); set(7, 8, fb(8));
  for (let i = 9; i < 15; i++) set(14 - i, 8, fb(i));
  for (let i = 0; i < 8; i++) set(n - 1 - i, 8, fb(i));
  for (let i = 8; i < 15; i++) set(8, n - 15 + i, fb(i));
  set(8, n - 8, true);   // mørk modul
  // data i sikk-sakk, maske 0: (x+y)%2==0
  let k = 0;
  for (let right = n - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < n; vert++) for (let j = 0; j < 2; j++) {
      const x = right - j, up = ((right + 1) & 2) === 0, y = up ? n - 1 - vert : vert;
      if (fn[y]![x]) continue;
      let d = false;
      if (k < all.length * 8) { d = ((all[k >>> 3]! >>> (7 - (k & 7))) & 1) === 1; k++; }
      if ((x + y) % 2 === 0) d = !d;
      m[y]![x] = d;
    }
  }
  return m;
}
