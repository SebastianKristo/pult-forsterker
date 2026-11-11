// Skjold S1 rev F – systemskjermer som ikke finnes i den uttrukne designkoden (s1_draw.js):
// oppsett-nett (QR), USB-bryter i standby, og de to siste trinnene når power holdes (omstart / tilbakestilling).
// Oppbygningen følger kravspesifikasjonen §4.4: stort ikon i venstre felt (senter 320,320), og i høyre felt (fra x 652)
// etikett i IBM Plex Mono 500 26 px sperret 7 px, tittel i Sora 600 92 px og undertekst i Sora 400 38 px.
// Når den nye designfila er hentet ut med extract.py, kan tegnefunksjonene her byttes mot designets egne.
(function () {
  'use strict';
  const W = '#f6f3ee', DM = 'rgba(246,243,238,.62)', RAV = '#ffb547', ROD = '#ff6b4a', GRONN = '#3fd68a';
  const MERKE = ['#ff6b4a', '#ffa23a', '#ffd23f', '#3fd68a', '#3fa9ff'];
  const SORA = 'Sora,"Helvetica Neue",Arial,sans-serif', MONO = '"IBM Plex Mono",ui-monospace,monospace';
  const st = () => (window.SKJOLD_SCREEN && window.SKJOLD_SCREEN.status && window.SKJOLD_SCREEN.status()) || {};

  function sperret(g, s, x, y, sp) { let cx = x; for (const ch of s) { g.fillText(ch, cx, y); cx += g.measureText(ch).width + sp; } return cx; }
  function hode(g, etikett, tittel, under, farge, under2) {
    g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillStyle = farge || RAV; g.font = '500 26px ' + MONO; sperret(g, etikett, 652, 214, 7);
    g.fillStyle = W; g.font = '600 92px ' + SORA; g.fillText(tittel, 648, 326, 1180);
    g.fillStyle = DM; g.font = '400 38px ' + SORA; g.fillText(under, 652, 396, 1180);
    if (under2) g.fillText(under2, 652, 448, 1180);
  }
  function glod(g, farge) { const r = g.createRadialGradient(320, 320, 20, 320, 320, 300); r.addColorStop(0, farge); r.addColorStop(1, 'rgba(0,0,0,0)'); g.globalAlpha = 0.16; g.fillStyle = r; g.fillRect(0, 0, 640, 640); g.globalAlpha = 1; }
  function ring(g, p, farge) {
    g.lineWidth = 14; g.lineCap = 'round';
    g.strokeStyle = 'rgba(246,243,238,.14)'; g.beginPath(); g.arc(320, 320, 150, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = farge; g.beginPath(); g.arc(320, 320, 150, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0, Math.min(1, p))); g.stroke();
  }
  function pil(g, farge, vinkel) {      // omstartspil: tre firedels sirkel med pilhode
    g.save(); g.translate(320, 320); g.rotate(vinkel); g.strokeStyle = farge; g.fillStyle = farge; g.lineWidth = 16; g.lineCap = 'round';
    g.beginPath(); g.arc(0, 0, 78, -Math.PI * 0.35, Math.PI * 1.2); g.stroke();
    const a = -Math.PI * 0.35, x = Math.cos(a) * 78, y = Math.sin(a) * 78;
    g.beginPath(); g.moveTo(x + 34, y - 6); g.lineTo(x - 6, y - 34); g.lineTo(x - 10, y + 16); g.closePath(); g.fill(); g.restore();
  }
  function linje(g, p) { const l = g.createLinearGradient(652, 0, 1830, 0); MERKE.forEach((c, i) => l.addColorStop(i / 4, c)); g.fillStyle = 'rgba(246,243,238,.12)'; g.fillRect(652, 566, 1178, 6); g.fillStyle = l; g.fillRect(652, 566, 1178 * Math.max(0, Math.min(1, p)), 6); }
  function teller(g, s, farge) { g.textAlign = 'right'; g.fillStyle = farge; g.font = '500 44px ' + MONO; g.fillText(String(Math.ceil(s)), 1830, 222); g.textAlign = 'left'; }

  function usbIkon(g, farge) {
    g.save(); g.translate(320, 320); g.strokeStyle = farge; g.fillStyle = farge; g.lineWidth = 14; g.lineCap = 'round'; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(0, 120); g.lineTo(0, -96); g.stroke();
    g.beginPath(); g.moveTo(0, -140); g.lineTo(-30, -92); g.lineTo(30, -92); g.closePath(); g.fill();
    g.beginPath(); g.moveTo(0, 40); g.lineTo(-64, -8); g.lineTo(-64, -44); g.stroke(); g.beginPath(); g.arc(-64, -62, 20, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.moveTo(0, 76); g.lineTo(64, 30); g.lineTo(64, -10); g.stroke(); g.fillRect(44, -50, 40, 40);
    g.beginPath(); g.arc(0, 128, 24, 0, Math.PI * 2); g.fill(); g.restore();
  }

  // ---------- skjermene ----------
  function oppsett(g, n) {
    if (n.joining) {
      glod(g, RAV); ring(g, ((performance.now() / 1400) % 1), RAV);
      hode(g, 'WI-FI · KOBLER TIL', 'Kobler til', '«' + n.joining + '»', RAV, 'Oppsett-nettet slås av mens Skjold kobler til.');
      return;
    }
    g.fillStyle = W; g.beginPath(); if (g.roundRect) g.roundRect(120, 120, 400, 400, 28); else g.rect(120, 120, 400, 400); g.fill();
    try { drawQR(g, 140, 140, 360, n.qr); } catch (e) { /* uten QR-bibliotek står nettnavnet til høyre */ }
    hode(g, 'OPPSETT · STEG 1 AV 2', 'Koble til Wi-Fi', 'Skann koden med mobilen, eller koble til nettet', n.error ? ROD : RAV);
    g.font = '500 34px ' + MONO; g.fillStyle = RAV; g.fillText(n.ssid, 652, 462, 1180);
    g.fillStyle = DM; g.font = '400 30px ' + SORA; g.fillText('Passord:', 652, 516);
    g.fillStyle = W; g.font = '500 32px ' + MONO; g.fillText(n.password, 800, 516);
    if (n.error) { g.fillStyle = ROD; g.font = '400 30px ' + SORA; g.fillText(n.error, 652, 578, 1180); }
  }
  function usb(g, pc) {
    glod(g, W); usbIkon(g, W);
    hode(g, 'USB-SWITCH', 'PC ' + pc, 'USB-utstyret er koblet til PC ' + pc);
  }
  function hold(g, h) {
    const t = performance.now() / 1000, reset = h.stage >= 2;
    const farge = reset ? ROD : W;
    glod(g, farge);
    ring(g, reset ? (h.s - 7) / 3 : 1, farge);
    pil(g, farge, (reset ? -1 : 1) * t * 2.4);
    if (reset) hode(g, 'AV/PÅ · HOLDES', 'Tilbakestill', 'Hold videre for fabrikkinnstillinger · slipp = omstart', ROD);
    else hode(g, 'AV/PÅ · HOLDES', 'Omstart', 'Slipp nå for omstart · hold videre for å tilbakestille');
    teller(g, h.left, farge); linje(g, h.s / 10);
  }

  const tegn = window.drawBar;
  window.drawBar = function () {
    const s = st(), g = cvb.getContext('2d');
    const ui = s.ui || {}, h = ui.hold, ov = ui.overlay, n = s.setup_net;
    const egen = (h && (h.kind === 'reboot' || h.kind === 'reset') && h.stage >= 1 && !s.rebooting) ? 'hold'
      : (ov && ov.type === 'usb' && !s.power) ? 'usb'
      : (n && (n.active || n.joining) && !s.rebooting && !(window.bdayOn && bdayOn() && !S.bdayHide)) ? 'oppsett' : '';
    if (!egen) { tegn(); return; }
    g.setTransform(0.5, 0, 0, 0.5, 0, 0); g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 640);
    if (egen === 'hold') hold(g, h); else if (egen === 'usb') usb(g, ov.pc || 1); else oppsett(g, n);
    texB.needsUpdate = true;
    if (egen !== 'usb' && window.SKJOLD_SCREEN) window.SKJOLD_SCREEN.wake(600);     // animert: hold skjermen i gang
  };
})();
