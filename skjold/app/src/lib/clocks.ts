// Standby-klokker – tegnes i 128×64 logiske piksler (OLED) og skaleres. Portert fra skjold_settings.js.
export const CLOCKS = ['Tynn', 'Stor', 'Analog', 'Ord', 'Linje', 'Dato'];
const HW = ['tolv', 'ett', 'to', 'tre', 'fire', 'fem', 'seks', 'sju', 'åtte', 'ni', 'ti', 'elleve', 'tolv'];
const DAYS = ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'];
const MON = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember'];

function wordTime(d: Date): [string, string] {
  const m = (Math.round(d.getMinutes() / 5) * 5) % 60, h0 = d.getHours() + (d.getMinutes() >= 58 ? 1 : 0), h = h0 % 12;
  const n = HW[h === 0 ? 12 : h] ?? '', n1 = HW[(h + 1) % 12 === 0 ? 12 : (h + 1) % 12] ?? '';
  const t: [string, string][] = [['klokka er', n], ['fem over', n], ['ti over', n], ['kvart over', n], ['ti på halv', n1], ['fem på halv', n1], ['halv', n1], ['fem over halv', n1], ['ti over halv', n1], ['kvart på', n1], ['ti på', n1], ['fem på', n1]];
  return t[m / 5] ?? ['klokka er', n];
}

const cap = (s: string) => s.replace(/^./, (c) => c.toUpperCase());

export function drawClock(g: CanvasRenderingContext2D, w: number, h: number, style: number, d: Date, color = '#8b8b86'): void {
  const k = w / 128, oy = (h - 64 * k) / 2, F = '"Helvetica Neue",Arial,sans-serif', mi = d.getMinutes();
  const hh = String(d.getHours()).padStart(2, '0'), mm = String(mi).padStart(2, '0');
  g.save(); g.translate(0, oy); g.scale(k, k); g.fillStyle = color; g.strokeStyle = color; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
  if (style === 0) { g.font = '300 22px ' + F; g.fillText(hh + ':' + mm, 64, 40); }
  else if (style === 1) { g.font = '700 40px ' + F; g.fillText(hh + ':' + mm, 64, 47); }
  else if (style === 2) {
    const cx = 40, cy = 32, r = 24; g.lineWidth = 1; g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.stroke();
    for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2, l = i % 3 ? 2 : 4; g.beginPath(); g.moveTo(cx + Math.sin(a) * (r - 1.5), cy - Math.cos(a) * (r - 1.5)); g.lineTo(cx + Math.sin(a) * (r - 1.5 - l), cy - Math.cos(a) * (r - 1.5 - l)); g.stroke(); }
    const ha = (((d.getHours() % 12) + mi / 60) / 12) * Math.PI * 2, ma = (mi / 60) * Math.PI * 2; g.lineCap = 'round';
    g.lineWidth = 2.4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.sin(ha) * 12, cy - Math.cos(ha) * 12); g.stroke();
    g.lineWidth = 1.4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.sin(ma) * 19, cy - Math.cos(ma) * 19); g.stroke(); g.beginPath(); g.arc(cx, cy, 1.6, 0, Math.PI * 2); g.fill();
    g.textAlign = 'left'; g.font = '600 9px ' + F; g.fillText(cap((DAYS[d.getDay()] ?? '').slice(0, 3)), 74, 30); g.font = '400 8px ' + F; g.fillText(d.getDate() + '. ' + (MON[d.getMonth()] ?? '').slice(0, 3), 74, 41);
  } else if (style === 3) { const [a, b] = wordTime(d); g.font = '300 11px ' + F; g.fillText(a, 64, 28); g.font = '600 15px ' + F; g.fillText(b, 64, 45); }
  else if (style === 4) {
    const p = (d.getHours() * 60 + mi) / 1440; g.fillRect(8, 40, 112, 0.8);
    for (let i = 0; i <= 24; i += 6) g.fillRect(8 + (112 * i) / 24 - 0.4, 37.5, 0.8, 5);
    g.beginPath(); g.arc(8 + 112 * p, 40.4, 2.4, 0, Math.PI * 2); g.fill(); g.font = '400 10px ' + F; g.textAlign = p > 0.75 ? 'right' : p < 0.25 ? 'left' : 'center'; g.fillText(hh + ':' + mm, 8 + 112 * p, 31);
  } else { g.font = '300 26px ' + F; g.fillText(hh + ':' + mm, 64, 34); g.font = '400 8px ' + F; g.fillText(cap(DAYS[d.getDay()] ?? '') + ' ' + d.getDate() + '. ' + (MON[d.getMonth()] ?? ''), 64, 48); }
  g.restore();
}
