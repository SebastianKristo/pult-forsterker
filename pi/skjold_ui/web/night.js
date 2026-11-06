// Nattmodus-skjermen (PROMPT_S1_PROGRAMVARE.md §6.1). Designfilen kaller drawNight(g,k,nt), men definerer den ikke,
// så den er tegnet her etter beskrivelsen, i samme koordinater (1920 × 640) og stil som resten av skjermen.
// På = mørkeblå med måne, «Nattmodus på». Av = varm oransje med sol, «Nattmodus av». Kilde under, og opptil 4
// automasjonssteg som hukes av ett etter ett: 450 ms mellom, ringen fylles på 300 ms, så hake.
function drawNight(g, k, nt) {
  const F = '"Helvetica Neue",Arial,sans-serif', W = '#f6f3ee', Dm = 'rgba(246,243,238,.62)', on = !!S.night;
  g.save(); g.globalAlpha = Math.max(0, Math.min(1, k));
  const bg = g.createLinearGradient(0, 0, 1920, 640);
  if (on) { bg.addColorStop(0, '#060b1f'); bg.addColorStop(0.6, '#0d1838'); bg.addColorStop(1, '#151033'); }
  else { bg.addColorStop(0, '#3a1606'); bg.addColorStop(0.6, '#7a3410'); bg.addColorStop(1, '#a3561a'); }
  g.fillStyle = bg; g.fillRect(0, 0, 1920, 640);
  const cx = 300, cy = 320, glow = g.createRadialGradient(cx, cy, 0, cx, cy, 300);
  glow.addColorStop(0, on ? 'rgba(160,185,255,.28)' : 'rgba(255,190,90,.42)'); glow.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = glow; g.fillRect(0, 0, 700, 640);
  const p = Math.min(1, nt / 600), e = 1 - Math.pow(1 - p, 3);
  if (on) {   // måne: sirkel med utskåret sirkel (på egen flate, så utskjæringen ikke tar bakgrunnen)
    const m = drawNight.m || (drawNight.m = document.createElement('canvas')); m.width = m.height = 300; const mg = m.getContext('2d');
    mg.clearRect(0, 0, 300, 300); mg.fillStyle = '#dfe6ff'; mg.beginPath(); mg.arc(150, 150, 120, 0, 7); mg.fill();
    mg.globalCompositeOperation = 'destination-out'; mg.beginPath(); mg.arc(150 + 64 - 40 * (1 - e), 150 - 44, 112, 0, 7); mg.fill(); mg.globalCompositeOperation = 'source-over';
    g.drawImage(m, cx - 150, cy - 150);
    g.fillStyle = 'rgba(223,230,255,.7)'; [[560, 140, 5], [610, 230, 3], [520, 470, 4], [140, 120, 3], [180, 520, 4]].forEach(([x, y, r], i) => { g.globalAlpha = k * Math.max(0, Math.min(1, (nt - 200 - i * 120) / 300)); g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); });
    g.globalAlpha = k;
  } else {    // sol: skive med stråler
    g.fillStyle = '#ffd27a'; g.beginPath(); g.arc(cx, cy, 96, 0, 7); g.fill();
    g.strokeStyle = '#ffd27a'; g.lineWidth = 14; g.lineCap = 'round';
    for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6 + e * 0.4, r0 = 132, r1 = 132 + 46 * e; g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); g.stroke(); }
  }
  g.textBaseline = 'alphabetic'; g.textAlign = 'left';
  g.fillStyle = W; g.font = '600 92px ' + F; g.fillText(on ? 'Nattmodus på' : 'Nattmodus av', 652, 190);
  const src = S.nightSrc === 'S1' || !S.nightSrc ? 'Startet fra ' + devName() + ' · automasjon kjører' : 'Satt fra ' + S.nightSrc;
  g.fillStyle = Dm; g.font = '32px ' + F; g.fillText(src, 652, 250);
  const steps = (S.nightSteps || []).slice(0, 4);
  steps.forEach((s, i) => {
    const y = 330 + i * 72, t0 = 900 + i * 450, q = Math.max(0, Math.min(1, (nt - t0) / 300)), done = nt - t0 > 300;
    g.globalAlpha = k * Math.max(0.35, Math.min(1, (nt - t0 + 450) / 300));
    g.strokeStyle = 'rgba(246,243,238,.28)'; g.lineWidth = 5; g.beginPath(); g.arc(676, y - 12, 22, 0, 7); g.stroke();
    if (q > 0) { g.strokeStyle = on ? '#9fb6ff' : '#ffd27a'; g.beginPath(); g.arc(676, y - 12, 22, -Math.PI / 2, -Math.PI / 2 + q * Math.PI * 2); g.stroke(); }
    if (done) { g.strokeStyle = W; g.lineWidth = 5; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath(); g.moveTo(665, y - 12); g.lineTo(673, y - 3); g.lineTo(689, y - 22); g.stroke(); }
    g.fillStyle = done ? W : Dm; g.font = '36px ' + F; g.fillText(typeof s === 'string' ? s : (s.name || ''), 724, y);
  });
  g.restore();
}
