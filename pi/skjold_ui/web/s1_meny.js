// Skjold S1 rev F – innstillinger som virker uten web-UI og mobil (lastes etter s1_draw.js, screen.js og system.js).
// Designets meny (s1_draw.js: SETS/CATS/curList) får ekte handlinger, og nye sider tegnes her:
//   x:saver  skjermsparer-velger med forhåndsvisning på hele baren (vri = bla, trykk = velg, kildeknapp = avbryt)
//   x:wifi   Wi-Fi: velg nett her (med tastatur på hjulet), med telefonen (QR) eller med Blåtann (Improv)
//   x:scan   nettene rundt, x:kb tastatur, x:conn kobler til
//   x:nett   Wi-Fi er borte (oppsett-nettet er oppe): QR for mobilen, «Tilbake til forsterkeren» (forhåndsvalgt) eller
//            velg nett og skriv passordet med hjulet. Lukkes også med en kildeknapp; da vises bare «Ingen Wi-Fi» på hovedskjermen.
//   x:upd    programvare: se etter og installer oppdatering
//   x:setup  oppsett ved første oppstart (velkommen → Wi-Fi → navn → høyttalertest → ferdig)
// Hjulet og knappene kommer fra screen.js (window.S1MENY.ui) før designets egen menyhåndtering.
(function () {
  'use strict';
  if (typeof S === 'undefined' || typeof SETS === 'undefined') return;
  const W = '#f6f3ee', DM = 'rgba(246,243,238,.62)', LO = 'rgba(246,243,238,.38)', RAV = '#ffb547', ROD = '#ff6b4a', GRONN = '#3fd68a';
  const MERKE = ['#ff6b4a', '#ffa23a', '#ffd23f', '#3fd68a', '#3fa9ff'];
  const SORA = 'Sora,"Helvetica Neue",Arial,sans-serif', MONO = '"IBM Plex Mono",ui-monospace,monospace';
  const now = () => performance.now();
  const status = () => (window.SKJOLD_SCREEN && SKJOLD_SCREEN.status && SKJOLD_SCREEN.status()) || {};
  const net = () => window.S1NET || status().net || {};
  const wake = (ms) => { if (window.SKJOLD_SCREEN) SKJOLD_SCREEN.wake(ms || 800); };
  const api = (path, body) => fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(r => r.json().catch(() => ({})).then(j => (r.ok ? j : Promise.reject(new Error(j.error || ('HTTP ' + r.status))))));

  // ---------- tilstand for sidene her ----------
  const M = { idx: 0, wiz: false, step: 0, nets: [], scanning: false, ssid: '', kb: null, conn: null, upd: null, ble: false, msg: '', msgT: 0, ret: '',
    nettVist: false, nettSkjult: false };
  const page = () => (S.set.open && typeof S.set.page === 'string' && S.set.page.startsWith('x:')) ? S.set.page : '';
  const active = () => M.wiz || !!page();
  function go(p, idx) { S.set.open = true; S.set.page = p; S.set.t = now(); M.idx = idx || 0; wake(1500); }
  function back() {
    const p = page();
    if (p === 'x:nett') { nettTilbake(); return; }
    if (p === 'x:kb' || p === 'x:scan' || p === 'x:conn' || p === 'x:ble') {
      const r = p === 'x:kb' ? (M.kb && M.kb.ret) : M.ret; M.kb = p === 'x:kb' ? null : M.kb;
      if (r) go(r, 0); else if (M.wiz) { S.set.page = ''; S.set.open = false; } else S.set.page = '';
      return;
    }
    if (M.wiz && !p) { if (M.step > 0) { M.step--; M.idx = 0; } return; }
    if (M.wiz) { S.set.page = ''; S.set.open = false; M.idx = 0; return; }
    S.set.page = ''; M.idx = 0;
  }
  function toast(t) { M.msg = t; M.msgT = now(); wake(2500); }

  // ---------- tegnehjelpere (1920 × 640, samme mål som system.js) ----------
  function sperret(g, s, x, y, sp) { let cx = x; for (const ch of s) { g.fillText(ch, cx, y); cx += g.measureText(ch).width + sp; } return cx; }
  function etikett(g, s, x, y, farge) { g.fillStyle = farge || RAV; g.font = '500 26px ' + MONO; g.textAlign = 'left'; sperret(g, s, x, y, 7); }
  function tekst(g, s, x, y, px, wt, farge, al, max) { g.font = (wt || 400) + ' ' + px + 'px ' + SORA; g.fillStyle = farge || W; g.textAlign = al || 'left'; g.fillText(s, x, y, max || 1800); g.textAlign = 'left'; }
  function glod(g, farge) { const r = g.createRadialGradient(320, 320, 20, 320, 320, 300); r.addColorStop(0, farge); r.addColorStop(1, 'rgba(0,0,0,0)'); g.globalAlpha = 0.16; g.fillStyle = r; g.fillRect(0, 0, 640, 640); g.globalAlpha = 1; }
  function rr(g, x, y, w, h, r) { g.beginPath(); if (g.roundRect) g.roundRect(x, y, w, h, r); else g.rect(x, y, w, h); }
  function spinner(g, farge) {
    const t = now() / 1000; g.lineWidth = 14; g.lineCap = 'round';
    g.strokeStyle = 'rgba(246,243,238,.14)'; g.beginPath(); g.arc(320, 320, 150, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = farge; g.beginPath(); g.arc(320, 320, 150, t * 4, t * 4 + Math.PI * 0.7); g.stroke();
  }
  function hake(g, farge, p) {
    p = Math.max(0, Math.min(1, p == null ? 1 : p));
    g.lineWidth = 14; g.lineCap = 'round'; g.strokeStyle = farge;
    g.beginPath(); g.arc(320, 320, 150, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, p * 1.6)); g.stroke();
    const q = Math.max(0, p * 1.6 - 0.6) / 1; g.lineWidth = 20; g.lineJoin = 'round';
    const a = [250, 325], b = [305, 380], c = [400, 262];
    g.beginPath(); g.moveTo(a[0], a[1]);
    if (q < 0.4) g.lineTo(a[0] + (b[0] - a[0]) * q / 0.4, a[1] + (b[1] - a[1]) * q / 0.4);
    else { g.lineTo(b[0], b[1]); const f = Math.min(1, (q - 0.4) / 0.6); g.lineTo(b[0] + (c[0] - b[0]) * f, b[1] + (c[1] - b[1]) * f); }
    g.stroke();
  }
  function merke(g, k) {   // Skjold-merket: fem søyler
    const hs = [110, 165, 210, 165, 110];
    hs.forEach((h, i) => { g.fillStyle = i === 2 ? '#d9a441' : W; rr(g, 320 - 2.5 * 52 + i * 52 + 6, 320 - h / 2 + (k || 0), 30, h, 15); g.fill(); });
  }
  function wifiIkon(g, farge, styrke) {
    g.save(); g.translate(320, 360); g.strokeStyle = farge; g.lineCap = 'round'; g.lineWidth = 22;
    [60, 120, 180].forEach((r, i) => { g.globalAlpha = styrke == null || styrke > i / 3 ? 1 : 0.22; g.beginPath(); g.arc(0, 0, r, -Math.PI * 0.78, -Math.PI * 0.22); g.stroke(); });
    g.globalAlpha = 1; g.fillStyle = farge; g.beginPath(); g.arc(0, 0, 18, 0, Math.PI * 2); g.fill(); g.restore();
  }
  function hode(g, lbl, tittel, under, farge, under2) {
    etikett(g, lbl, 652, 150, farge);
    tekst(g, tittel, 648, 262, tittel.length > 18 ? 76 : 92, 600, W, 'left', 1200);
    if (under) tekst(g, under, 652, 330, 36, 400, DM, 'left', 1200);
    if (under2) tekst(g, under2, 652, 378, 36, 400, DM, 'left', 1200);
  }
  // valg som piller nederst til høyre (vri = velg, trykk = utfør)
  function piller(g, valg, idx, y) {
    y = y || 470; let x = 652; g.font = '600 36px ' + SORA;
    valg.forEach((v, i) => {
      const w = Math.min(560, g.measureText(v).width + 84), on = i === idx;
      rr(g, x, y, w, 88, 44);
      if (on) { g.fillStyle = W; g.fill(); } else { g.strokeStyle = 'rgba(246,243,238,.28)'; g.lineWidth = 3; g.stroke(); }
      g.fillStyle = on ? '#000' : DM; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(v, x + w / 2, y + 46); g.textBaseline = 'alphabetic'; g.textAlign = 'left';
      x += w + 22;
    });
  }
  // liste til venstre, detalj til høyre (samme rytme som designets innstillingsmeny)
  function liste(g, lbl, rader, idx, detalj) {
    const CW = 680, vis = 5, first = Math.max(0, Math.min(rader.length - vis, idx - 2)); g.textBaseline = 'middle';
    for (let r = 0; r < vis; r++) {
      const i = first + r, o = rader[i]; if (!o) break; const y = 60 + r * 104 + 44, on = i === idx;
      const navn = typeof o === 'string' ? o : o.n;
      if (on) { rr(g, 48, y - 46, CW - 46, 92, [24, 0, 0, 24]); g.fillStyle = W; g.fill(); tekst(g, navn, 88, y + 2, 50, 600, '#000', 'left', CW - 120); }
      else tekst(g, navn, 88, y + 2, 44, 400, o.dim ? LO : DM, 'left', CW - 120);
    }
    g.fillStyle = 'rgba(255,255,255,.1)'; g.fillRect(CW, 52, 2, 536);
    if (rader.length > vis) { const h = 536 * vis / rader.length; g.fillStyle = 'rgba(255,255,255,.1)'; g.fillRect(20, 52, 4, 536); g.fillStyle = DM; g.fillRect(20, 52 + first * (536 - h) / (rader.length - vis), 4, h); }
    g.textBaseline = 'alphabetic';
    etikett(g, lbl, CW + 88, 100, DM);
    g.fillStyle = DM; g.font = '400 30px ' + MONO; g.textAlign = 'right'; g.fillText((idx + 1) + ' / ' + rader.length, 1832, 100); g.textAlign = 'left';
    if (detalj) detalj(CW + 88);
  }
  function melding(g) {
    if (!M.msg || now() - M.msgT > 2600) return;
    g.fillStyle = 'rgba(0,0,0,.78)'; rr(g, 560, 520, 800, 90, 45); g.fill();
    tekst(g, M.msg, 960, 578, 36, 600, W, 'center', 760);
  }

  // ---------- skjermsparer ----------
  const CLOCKS = (window.SKJOLD && SKJOLD.CLOCKS && SKJOLD.CLOCKS.slice()) || ['Tynn', 'Stor', 'Analog', 'Ord', 'Linje', 'Dato', 'VU-metre', 'Radioskala', 'Glasspanel', 'Klokke og vær', 'Bare tid', 'Døgnstripe', 'Klokka i ord', 'Fotoramme', 'Nattlys', 'Analog og kalender'];
  const SAVERS = [{ n: 'Av – svart skjerm', off: true }].concat(CLOCKS.map((n, i) => ({ n, st: i })));
  const saverIdx = () => S.set.clock ? 1 + (S.set.clockStyle | 0) : 0;
  const saverName = () => SAVERS[saverIdx()] ? SAVERS[saverIdx()].n : '';
  function tegnSaver(g) {
    const s = SAVERS[M.idx] || SAVERS[0];
    if (s.off) {
      tekst(g, 'Svart skjerm', 960, 270, 72, 600, LO, 'center'); tekst(g, 'Panelet slås av i standby', 960, 336, 36, 400, LO, 'center');
    } else if (s.st >= 6 && window.drawSaver) {
      try { window.drawSaver(g, s.st); } catch (e) { /* stil uten data */ }
    } else if (window.SKJOLD && SKJOLD.drawClock) {
      const l = g.createLinearGradient(0, 0, 0, 640); l.addColorStop(0, '#1b2a3a'); l.addColorStop(0.55, '#2c3d4a'); l.addColorStop(1, '#0d1418');
      g.fillStyle = l; g.fillRect(0, 0, 1920, 640);
      g.fillStyle = '#111a1f'; g.beginPath(); g.moveTo(0, 520); g.lineTo(380, 300); g.lineTo(700, 470); g.lineTo(1080, 260); g.lineTo(1500, 450); g.lineTo(1920, 330); g.lineTo(1920, 640); g.lineTo(0, 640); g.fill();
      g.save(); g.shadowColor = 'rgba(0,0,0,.55)'; g.shadowBlur = 24; g.translate(60, 40);
      SKJOLD.drawClock(g, 720, 240, s.st, new Date(), { color: 'rgba(255,255,255,.86)' }); g.restore();
    }
    // nederst: navnet og hint
    const l = g.createLinearGradient(0, 430, 0, 640); l.addColorStop(0, 'rgba(0,0,0,0)'); l.addColorStop(1, 'rgba(0,0,0,.88)');
    g.fillStyle = l; g.fillRect(0, 430, 1920, 210);
    tekst(g, '‹', 640, 572, 64, 400, DM, 'center'); tekst(g, '›', 1280, 572, 64, 400, DM, 'center');
    tekst(g, s.n, 960, 570, 52, 600, W, 'center', 560);
    g.fillStyle = LO; g.font = '500 22px ' + MONO; g.textAlign = 'center';
    g.fillText((M.idx === saverIdx() ? 'VALGT · ' : '') + (M.idx + 1) + ' / ' + SAVERS.length + ' · TRYKK FOR Å VELGE', 960, 616); g.textAlign = 'left';
  }
  function velgSaver() {
    const s = SAVERS[M.idx]; if (!s) return;
    if (s.off) S.set.clock = false; else { S.set.clock = true; S.set.clockStyle = s.st; }
    refresh(); toast('Skjermsparer: ' + s.n); setTimeout(() => { if (page() === 'x:saver') back(); }, 900);
  }

  // ---------- Wi-Fi ----------
  function wifiValg() {
    const v = [{ n: 'Velg nettverk her', a: () => skann() }, { n: 'Med telefonen (QR)', a: () => medTelefon() }, { n: 'Med Blåtann', a: () => medBlatann() }];
    if (M.wiz) v.push({ n: 'Hopp over', a: () => { M.step++; M.idx = 0; S.set.page = ''; S.set.open = false; } });
    return v;
  }
  function tegnWifi(g) {
    const n = net(), v = wifiValg();
    liste(g, 'WI-FI', v, M.idx, (x) => {
      if (n.ssid) { tekst(g, n.ssid, x, 230, 80, 600, W, 'left', 1060); tekst(g, 'Tilkoblet' + (n.ip ? ' · ' + n.ip : ''), x, 296, 36, 400, GRONN); }
      else { tekst(g, 'Ikke tilkoblet', x, 230, 80, 600, W); tekst(g, 'Velg hvordan du vil koble til', x, 296, 36, 400, DM); }
      const forklar = ['Velg nettet og skriv passordet med hjulet.', 'Skjold lager et oppsett-nett. Skann QR-koden med mobilen.', 'Bruk improv-wifi.com i Chrome på Android eller PC.', 'Du kan sette opp Wi-Fi senere i Innstillinger.'][M.idx] || '';
      tekst(g, forklar, x, 420, 36, 400, DM, 'left', 1060);
    });
  }
  function skann() {
    M.ret = page() || (M.wiz ? '' : 'x:wifi'); M.nets = []; M.scanning = true; go('x:scan');
    api('/api/wifi').then(j => { M.nets = (j.networks || []).filter(x => x.ssid); M.scanning = false; wake(600); })
      .catch(e => { M.scanning = false; toast('Fant ingen nett: ' + e.message); });
  }
  function medTelefon() {
    if (oppsettNett()) { M.wiz = false; S.setup.on = false; meld(); go('x:nett', 0); return; }
    api('/api/oppsett', { start: true }).then(() => { S.set.page = ''; S.set.open = false; M.wiz = false; wake(1500); })
      .catch(e => toast('Fikk ikke startet oppsett-nettet: ' + e.message));
  }
  function medBlatann() { M.ret = page() || (M.wiz ? '' : 'x:wifi'); api('/api/oppsett', { ble: true }).catch(() => {}); go('x:ble'); }
  function tegnBle(g) {
    const b = status().ble_setup || {}, ok = b.state === 'provisioned' || b.state === 'connected';
    glod(g, '#3fa9ff');
    if (ok) hake(g, GRONN, 1); else { g.save(); g.translate(320, 320); g.scale(9, 9); g.strokeStyle = '#3fa9ff'; g.lineWidth = 2.4; g.lineJoin = 'round'; g.lineCap = 'round';
      g.beginPath(); g.moveTo(-8, -8); g.lineTo(8, 8); g.lineTo(0, 16); g.lineTo(0, -16); g.lineTo(8, -8); g.lineTo(-8, 8); g.stroke(); g.restore(); }
    hode(g, 'WI-FI · BLÅTANN', ok ? 'Tilkoblet' : 'Klar for Blåtann', ok ? '«' + (b.ssid || '') + '»' : 'Åpne improv-wifi.com i Chrome på mobil eller PC,',
      ok ? GRONN : '#3fa9ff', ok ? '' : 'trykk «Connect device to Wi-Fi» og velg ' + (status().name || 'Skjold') + '.');
    if (b.error) tekst(g, b.error, 652, 470, 34, 400, ROD, 'left', 1200);
    piller(g, ['Ferdig'], 0, 500);
    S.set.t = now(); wake(800);
  }
  function tegnScan(g) {
    if (M.scanning) { glod(g, RAV); spinner(g, RAV); hode(g, 'WI-FI', 'Leter etter nett', 'Det tar noen sekunder'); wake(800); return; }
    if (!M.nets.length) { glod(g, RAV); wifiIkon(g, LO, 0); hode(g, 'WI-FI', 'Fant ingen nett', 'Trykk for å lete igjen'); return; }
    const rader = M.nets.map(x => ({ n: x.ssid + (x.active ? '  ✓' : '') }));
    liste(g, 'VELG NETTVERK', rader, M.idx, (x) => {
      const n = M.nets[M.idx] || {}, sig = +n.signal || 0, sec = n.security === 'open' ? 'Åpent nett' : (n.security || 'wpa2').toUpperCase();
      tekst(g, n.ssid || '', x, 230, 76, 600, W, 'left', 1060);
      tekst(g, 'Signal ' + sig + ' % · ' + sec, x, 296, 36, 400, DM);
      for (let i = 0; i < 4; i++) { g.fillStyle = sig > i * 25 ? W : 'rgba(255,255,255,.18)'; rr(g, x + i * 34, 420 - (i + 1) * 22, 24, (i + 1) * 22, 6); g.fill(); }
      tekst(g, n.security === 'open' ? 'Trykk for å koble til' : 'Trykk for å skrive passordet', x, 500, 36, 400, DM);
    });
  }
  function velgNett() {
    const n = M.nets[M.idx]; if (!n) { skann(); return; }
    M.ssid = n.ssid;
    if (n.security === 'open') { kobleTil(n.ssid, ''); return; }
    tastatur('WI-FI · PASSORD FOR «' + n.ssid + '»', '', 63, (pw) => {
      if (pw.length < 8) { toast('Passordet må ha minst 8 tegn'); return false; }
      kobleTil(n.ssid, pw); return true;
    }, 'x:scan');
  }
  function kobleTil(ssid, psk) {
    M.conn = { ssid, t: now(), state: 'kobler', err: '' }; go('x:conn');
    api('/api/wifi', psk ? { ssid, psk } : { ssid }).then(j => {
      if (j.pending) { M.conn.state = 'venter'; return; }
      M.conn.state = 'ok'; wake(1500);
    }).catch(e => { M.conn.state = 'feil'; M.conn.err = e.message; wake(800); });
  }
  function tegnConn(g) {
    const c = M.conn || {}, n = net(), sn = status().setup_net || {};
    if (c.state === 'venter') {   // oppsett-nettet var oppe: daemonen slår det av og kobler til (setup_net.joining)
      if (sn.joining === c.ssid) c.sett = true;
      else if (c.sett && !sn.joining) { if (sn.error) { c.state = 'feil'; c.err = sn.error; M.idx = 0; } else c.state = 'ok'; }
      if (n.ssid === c.ssid) c.state = 'ok';
    }
    if (c.state === 'ok') { glod(g, GRONN); hake(g, GRONN, (now() - (c.okT || (c.okT = now()))) / 700); hode(g, 'WI-FI', 'Tilkoblet', '«' + c.ssid + '»' + (n.ip ? ' · ' + n.ip : ''), GRONN); piller(g, [M.wiz ? 'Fortsett' : 'Ferdig'], 0, 470); wake(800); return; }
    if (c.state === 'feil') { glod(g, ROD); wifiIkon(g, ROD, 0); hode(g, 'WI-FI', 'Kom ikke på nett', c.err.length > 60 ? c.err.slice(0, 60) + '…' : c.err || 'Sjekk passordet', ROD); piller(g, ['Prøv igjen', 'Velg annet nett'], M.idx, 470); return; }
    glod(g, RAV); spinner(g, RAV); hode(g, 'WI-FI', 'Kobler til', '«' + c.ssid + '»', RAV, c.state === 'venter' ? 'Oppsett-nettet slås av mens Skjold kobler til.' : '');
    if (now() - c.t > 60000 && c.state !== 'ok') { c.state = 'feil'; c.err = 'Tidsavbrudd'; }
    S.set.t = now(); wake(800);
  }

  // ---------- Wi-Fi er borte: x:nett og «Ingen Wi-Fi» ----------
  // setup_net fra daemonen (skjold_setupnet.py): active = oppsett-nettet er oppe, skjult = «Tilbake til forsterkeren» er valgt
  const oppsettNett = () => { const sn = status().setup_net; return sn && sn.active && !sn.joining ? sn : null; };
  const NETTVALG = ['Tilbake til forsterkeren', 'Velg nett her', 'Blåtann'];
  function nettSperre() {   // skal x:nett åpnes av seg selv?
    const sn = oppsettNett();
    return !!(sn && !sn.skjult && !M.nettSkjult && S.power && !M.wiz && !status().rebooting);
  }
  function nettTilbake() {   // tilbake til forsterkeren: vanlig skjerm med «Ingen Wi-Fi», oppsett-nettet går videre (startet for hånd: slås av)
    const sn = oppsettNett() || {};
    M.nettSkjult = true; M.idx = 0; S.set.page = ''; S.set.open = false;
    api('/api/oppsett', sn.manual ? { stop: true } : { skjul: true }).catch(() => {});
    meld(); wake(800);
  }
  function nettValg(i) {
    if (i === 0) nettTilbake();
    else if (i === 1) skann();
    else medBlatann();
  }
  function qrFelt(g, sn) {
    rr(g, 120, 120, 400, 400, 28); g.fillStyle = W; g.fill();
    try { drawQR(g, 140, 140, 360, sn.qr); } catch (e) { /* uten QR-bibliotek: nettnavnet står til høyre */ }
  }
  function tegnNett(g) {
    const sn = oppsettNett() || status().setup_net || {};
    if (sn.qr) qrFelt(g, sn); else { glod(g, RAV); wifiIkon(g, LO, 0); }
    hode(g, sn.manual ? 'WI-FI · NYTT NETT' : 'INGEN WI-FI', sn.manual ? 'Koble til Wi-Fi' : 'Ikke på nett',
      'AUX, USB og Blåtann virker uten nett. Mobilen: skann koden.', sn.error ? ROD : RAV,
      sn.ssid ? 'Nett «' + sn.ssid + '» · passord ' + (sn.password || '') : '');
    if (sn.error) tekst(g, sn.error, 652, 432, 32, 400, ROD, 'left', 1200);
    piller(g, NETTVALG, M.idx, 470);
    g.fillStyle = LO; g.font = '500 22px ' + MONO; g.textAlign = 'right'; g.fillText('KILDEKNAPP = TILBAKE', 1832, 610); g.textAlign = 'left';
  }
  // følger setup_net: åpner x:nett når oppsett-nettet kommer (én gang per gang), lukker den når det er borte
  function nettVakt() {
    const sn = status().setup_net, p = page();
    if (!sn || (!sn.active && !sn.joining)) { M.nettVist = false; M.nettSkjult = false; }
    if (p === 'x:nett' && (!oppsettNett() || !S.power)) { S.set.page = ''; S.set.open = false; M.idx = 0; meld(); return; }
    if (!M.nettVist && nettSperre() && !p && !S.set.open && !booting()) { M.nettVist = true; go('x:nett', 0); meld(); }
  }
  // liten «Ingen Wi-Fi» øverst til venstre på hovedskjermen (over omslaget) når enheten ikke har nett
  function utenNett() {
    const s = status(), sn = s.setup_net, n = window.S1NET || s.net;
    if (!n && !sn) return false;   // vet ikke ennå (eller forhåndsvisning uten daemon)
    if (sn && (sn.active || sn.kabel) && !sn.joining) return true;
    return !!n && !n.ssid && !n.ip;
  }
  function hovedVisning() {
    const t = now(), s = status(), h = (s.ui || {}).hold;
    return S.power && !booting() && !S.rebootT && !S.set.open && !S.setup.on && !M.wiz && !S.knobHoldT && !S.pairT && !s.rebooting
      && t - S.muteT >= 1600 && t - (S.toastT || -1e9) >= 2200 && t - (S.nightT || -1e9) > 6000 && t - (S.clockPrevT || -1e9) > 4000
      && !menuOpen() && !(bdayOn() && !S.bdayHide) && !(h && h.stage >= 1) && !(s.setup_net && s.setup_net.joining);
  }
  function ingenWifi(g) {
    const a = 1 - screenDim(); if (a <= 0) return;
    g.save(); g.globalAlpha = a; g.setTransform(0.5, 0, 0, 0.5, 0, 0);
    g.font = '600 26px ' + SORA; const tw = g.measureText('Ingen Wi-Fi').width, x = 80, y = 80, w = tw + 104, h = 58;
    rr(g, x, y, w, h, 29); g.fillStyle = 'rgba(0,0,0,.66)'; g.fill(); g.strokeStyle = 'rgba(255,181,71,.55)'; g.lineWidth = 2; g.stroke();
    // Wi-Fi-buer med skråstrek
    g.translate(x + 40, y + 41); g.strokeStyle = RAV; g.lineCap = 'round'; g.lineWidth = 4;
    [8, 16, 24].forEach(r => { g.beginPath(); g.arc(0, 0, r, -Math.PI * 0.78, -Math.PI * 0.22); g.stroke(); });
    g.beginPath(); g.moveTo(-17, -28); g.lineTo(15, 2); g.stroke();
    g.translate(-(x + 40), -(y + 41));
    g.fillStyle = W; g.textBaseline = 'middle'; g.fillText('Ingen Wi-Fi', x + 74, y + h / 2 + 1); g.textBaseline = 'alphabetic';
    g.restore();
  }

  // ---------- tastatur på hjulet ----------
  const SETT = { abc: 'abcdefghijklmnopqrstuvwxyzæøå'.split(''), ABC: 'ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ'.split(''), '123': '0123456789-_.@!?#$%&*+=/:;,()\'"'.split('') };
  const SPES = [{ k: 'ok', n: '✓ Ferdig' }, { k: 'del', n: '⌫ Slett' }, { k: 'abc', n: 'abc' }, { k: 'ABC', n: 'ABC' }, { k: '123', n: '123' }, { k: ' ', n: 'Mellomrom' }];
  function tastatur(lbl, start, max, ferdig, ret) { M.kb = { lbl, txt: start || '', max: max || 63, set: 'abc', pos: 0, ferdig, ret: ret || '' }; go('x:kb', 0); kbPos(SPES.length); }
  const kbRing = () => SPES.filter(s => s.k !== M.kb.set).concat(SETT[M.kb.set].map(c => ({ k: 'c', n: c })));
  function kbPos(i) { const r = kbRing(); M.kb.pos = ((i % r.length) + r.length) % r.length; }
  function kbTrykk() {
    const kb = M.kb, it = kbRing()[kb.pos]; if (!it) return;
    if (it.k === 'ok') { if (kb.ferdig(kb.txt) !== false && page() === 'x:kb') M.kb = null; return; }
    if (it.k === 'del') { kb.txt = kb.txt.slice(0, -1); return; }
    if (SETT[it.k]) { const ch = kbRing()[kb.pos].n; kb.set = it.k; const r = kbRing(); kbPos(Math.max(0, r.findIndex(x => x.n === ch))); return; }
    if (kb.txt.length >= kb.max) { toast('Maks ' + kb.max + ' tegn'); return; }
    kb.txt += it.k === ' ' ? ' ' : it.n;
  }
  function tegnKb(g) {
    const kb = M.kb; if (!kb) return;
    etikett(g, kb.lbl, 88, 100, RAV);
    // tekstfeltet
    rr(g, 80, 140, 1760, 150, 28); g.fillStyle = 'rgba(255,255,255,.07)'; g.fill();
    g.font = '400 72px ' + MONO; let vis = kb.txt; while (g.measureText(vis).width > 1600 && vis.length) vis = vis.slice(1);
    g.fillStyle = W; g.textAlign = 'left'; g.fillText(vis, 124, 240);
    if (Math.floor(now() / 530) % 2 === 0) { const x = 124 + g.measureText(vis).width + 6; g.fillStyle = RAV; g.fillRect(x, 175, 6, 84); }
    g.fillStyle = LO; g.font = '400 26px ' + MONO; g.textAlign = 'right'; g.fillText(kb.txt.length + ' tegn', 1830, 330); g.textAlign = 'left';
    // tegnhjulet
    const r = kbRing(), cy = 450;
    for (let d = -7; d <= 7; d++) {
      const i = ((kb.pos + d) % r.length + r.length) % r.length, it = r[i], x = 960 + d * 128, on = d === 0, wide = it.k !== 'c';
      const a = Math.max(0, 1 - Math.abs(d) / 7.5);
      g.globalAlpha = on ? 1 : a * 0.75;
      if (on) { rr(g, x - (wide ? 150 : 62), cy - 66, wide ? 300 : 124, 132, 26); g.fillStyle = W; g.fill(); }
      g.fillStyle = on ? '#000' : (wide ? RAV : W); g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = (wide ? '600 ' + (on ? 40 : 30) : '500 ' + (on ? 76 : 58)) + 'px ' + (wide ? SORA : MONO);
      if (!wide || on || Math.abs(d) < 2) g.fillText(it.n, x, cy + 2);
      else g.fillText('•', x, cy + 2);
      g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    }
    g.globalAlpha = 1;
    tekst(g, 'Vri for å velge tegn · trykk for å skrive · kildeknapp = avbryt', 960, 600, 32, 400, DM, 'center');
    S.set.t = now(); wake(700);
  }

  // ---------- programvare ----------
  function hentUpd(start) {
    M.upd = M.upd || { state: 'sjekker' }; if (start) M.upd = { state: 'starter' };
    if (start) api('/api/update', {}).then(() => { M.upd.state = 'kjorer'; pollUpd(); }).catch(e => { M.upd = { state: 'feil', err: e.message }; });
    else api('/api/update?check=1').then(j => { M.upd = { state: j.running ? 'kjorer' : 'klar', ...j }; if (j.running) pollUpd(); wake(600); })
      .catch(e => { M.upd = { state: 'feil', err: e.message }; wake(600); });
  }
  function pollUpd() {
    clearTimeout(pollUpd.t);
    pollUpd.t = setTimeout(() => {
      if (page() !== 'x:upd') return;
      api('/api/update?check=0').then(j => { M.upd = { ...M.upd, ...j, state: j.running ? 'kjorer' : (j.result === 'ok' || j.result === 'success' ? 'ferdig' : (j.result ? 'resultat' : 'klar')) }; if (j.running) pollUpd(); wake(600); })
        .catch(() => { M.upd.state = 'omstart'; pollUpd(); wake(600); });   // daemonen starter på nytt under oppdateringen
    }, 2000);
  }
  function tegnUpd(g) {
    const u = M.upd || {};
    const cur = u.current || status().version || '';
    if (u.state === 'sjekker' || u.state === 'starter') { glod(g, RAV); spinner(g, RAV); hode(g, 'PROGRAMVARE', u.state === 'starter' ? 'Starter' : 'Ser etter', 'Versjon ' + cur); wake(800); return; }
    if (u.state === 'kjorer' || u.state === 'omstart') {
      glod(g, RAV); spinner(g, RAV); S.set.t = now();
      const last = (u.log || []).slice(-1)[0] || '';
      hode(g, 'PROGRAMVARE', 'Oppdaterer', u.state === 'omstart' ? 'Skjold starter på nytt …' : 'Ikke slå av forsterkeren', RAV, String(last).slice(0, 70));
      wake(800); return;
    }
    if (u.state === 'feil') { glod(g, ROD); hode(g, 'PROGRAMVARE', 'Fikk ikke sjekket', u.err || '', ROD); piller(g, ['Prøv igjen'], 0, 470); return; }
    if (u.state === 'ferdig') { glod(g, GRONN); hake(g, GRONN, 1); hode(g, 'PROGRAMVARE', 'Oppdatert', 'Versjon ' + (u.current || cur), GRONN); piller(g, ['Ferdig'], 0, 470); return; }
    glod(g, u.available ? RAV : W); merke(g);
    if (u.available) { hode(g, 'PROGRAMVARE · NY VERSJON', 'Versjon ' + (u.latest || ''), 'Du har ' + cur + '. Det tar et par minutter.'); piller(g, ['Oppdater nå', 'Ikke nå'], M.idx, 470); }
    else { hode(g, 'PROGRAMVARE', 'Versjon ' + cur, 'Du har nyeste versjon', GRONN); piller(g, ['Ferdig'], 0, 470); }
  }

  // ---------- oppsett (første oppstart) ----------
  const STEG = ['VELKOMMEN', 'WI-FI', 'NAVN', 'HØYTTALERE', 'FERDIG'];
  const meld = () => { if (window.SKJOLD_SCREEN && SKJOLD_SCREEN.postUi) SKJOLD_SCREEN.postUi(); };
  // S.setup.on holder skjermen våken (ingen dimming/skjermsparer) og får skjold-ui til å gi hjulet til oppsettet
  function startOppsett() { M.wiz = true; M.step = 0; M.idx = 0; M.okT = 0; S.set.open = false; S.set.page = ''; S.setup = Object.assign(S.setup || {}, { on: true, step: -1 }); S.lastAct = now(); meld(); wake(2000); }
  function stegValg() {
    const n = net();
    switch (M.step) {
      case 0: return ['Kom i gang', 'Hopp over'];
      case 1: return n.ssid ? ['Fortsett', 'Bytt nettverk'] : wifiValg().map(x => x.n);
      case 2: return NAMES.slice(0, 8).concat(['Eget navn …']);
      case 3: return ['Venstre', 'Høyre', 'Fortsett'];
      default: return ['Ferdig'];
    }
  }
  function stegTrykk() {
    const v = stegValg(), n = net(), i = M.idx;
    if (M.step === 0) { if (i === 1) return ferdigOppsett(); M.step = 1; M.idx = 0; return; }
    if (M.step === 1) {
      if (n.ssid) { if (i === 0) { M.step = 2; M.idx = Math.max(0, S.set.name | 0); } else skann(); return; }
      wifiValg()[i].a(); return;
    }
    if (M.step === 2) {
      if (i === v.length - 1) { tastatur('NAVN PÅ FORSTERKEREN', '', 24, (t) => { t = t.trim(); if (!t) return false; api('/api/settings', { nameCustom: t }).catch(() => {}); M.step = 3; M.idx = 0; S.set.page = ''; S.set.open = false; return true; }, ''); return; }
      S.set.name = i; refresh(); api('/api/settings', { name: i, nameCustom: '' }).catch(() => {}); M.step = 3; M.idx = 0; return;
    }
    if (M.step === 3) { if (i < 2) { api('/api/test', { channel: i ? 'R' : 'L' }).then(() => toast((i ? 'Høyre' : 'Venstre') + ' høyttaler')).catch(e => toast(e.message)); return; } M.step = 4; M.idx = 0; return; }
    ferdigOppsett();
  }
  function ferdigOppsett() { M.wiz = false; S.setup.on = false; setTimeout(meld, 0); api('/api/settings', { setupDone: true }).catch(() => {}); S.set.open = false; S.set.page = ''; toast('Hold hjulet inne for innstillinger'); }
  function tegnOppsett(g) {
    const n = net(), v = stegValg();
    // stegprikker øverst til høyre
    if (M.step !== 2) STEG.forEach((s, i) => { g.fillStyle = i === M.step ? RAV : i < M.step ? DM : 'rgba(246,243,238,.18)'; rr(g, 1700 + i * 28 - (i > M.step ? 0 : 0), 84, i === M.step ? 40 : 14, 14, 7); g.fill(); });
    const lbl = 'OPPSETT · ' + STEG[M.step] + ' · ' + (M.step + 1) + ' AV ' + STEG.length;
    if (M.step === 0) { glod(g, RAV); merke(g, Math.sin(now() / 700) * 6); hode(g, lbl, 'Velkommen', 'Vri hjulet for å velge, trykk for å fortsette.', RAV, 'Kildeknappene går tilbake.'); piller(g, v, M.idx); wake(800); return; }
    if (M.step === 1) {
      const sn = oppsettNett();
      if (sn && sn.qr && !n.ssid) qrFelt(g, sn); else { glod(g, n.ssid ? GRONN : RAV); wifiIkon(g, n.ssid ? GRONN : W); }
      if (n.ssid) hode(g, lbl, 'Koblet til', '«' + n.ssid + '»' + (n.ip ? ' · ' + n.ip : ''), RAV);
      else hode(g, lbl, 'Koble til Wi-Fi', ['Velg nettet her og skriv passordet med hjulet.', 'Skjold lager et oppsett-nett med QR-kode.', 'Bruk improv-wifi.com i Chrome.', 'Du kan gjøre det senere i Innstillinger.'][M.idx] || '', RAV);
      piller(g, v, M.idx); return;
    }
    if (M.step === 2) {
      liste(g, lbl, v.map(x => ({ n: x })), M.idx, (x) => { tekst(g, 'Hva heter rommet?', x, 230, 76, 600, W); tekst(g, 'Navnet vises i AirPlay, Blåtann, Spotify og appen.', x, 296, 36, 400, DM, 'left', 1060); });
      return;
    }
    if (M.step === 3) {
      glod(g, RAV);
      [-1, 1].forEach((s, k) => { const on = M.idx === k; g.fillStyle = on ? W : 'rgba(246,243,238,.3)'; rr(g, 320 + s * 120 - 60, 220, 120, 200, 22); g.fill(); g.fillStyle = on ? '#000' : '#111'; g.beginPath(); g.arc(320 + s * 120, 340, 40, 0, Math.PI * 2); g.fill(); });
      hode(g, lbl, 'Test høyttalerne', 'Du hører en kort tone fra venstre eller høyre.', RAV, 'Bytt kablene hvis lyden kommer fra feil side.');
      piller(g, v, M.idx); return;
    }
    glod(g, GRONN); hake(g, GRONN, (now() - (M.okT || (M.okT = now()))) / 700);
    hode(g, lbl, 'Alt er klart', 'Hold volumhjulet inne i 1,5 s for innstillinger.', GRONN, 'Hold power inne for å starte på nytt.');
    piller(g, v, 0); wake(800);
  }

  // ---------- designets meny: ekte handlinger ----------
  function bytt(navn, nytt) { const i = SETS.findIndex(x => x.n === navn); if (i >= 0) { if (nytt) SETS.splice(i, 1, nytt); else SETS.splice(i, 1); } return i; }
  function settInn(etter, ...nye) { const i = SETS.findIndex(x => x.n === etter); SETS.splice(i >= 0 ? i + 1 : SETS.length, 0, ...nye); }
  // «Hodetelefoner i» (hpDev: 0 = AUX 1, 1 = AUX 2): hvilken UCA202 hodetelefonene står i. Finnes ikke i designet,
  // så nøkkelen legges i S.set og SDEF her – da lagres den med de andre (screen.js: pushSettings sender alle SDEF-nøkler).
  if (typeof S.set.hpDev !== 'number') S.set.hpDev = 0;
  if (typeof SDEF !== 'undefined' && !('hpDev' in SDEF)) SDEF.hpDev = 0;
  if (!SETS.some(x => x.o && x.o[0] === 'hpDev')) settInn('Eget volum hodetlf.', { s: 'LYD', n: 'Hodetelefoner i', o: ['hpDev', ['AUX 1', 'AUX 2']] });
  // Høyttalerne (reléet til forsterkeren) av/på for seg – status().speakers fra daemonen, POST /api/speaker_relay
  if (!SETS.some(x => x.n === 'Høyttalere')) settInn('Hodetelefoner i', { s: 'LYD', n: 'Høyttalere',
    act: () => { const på = status().speakers === false; api('/api/speaker_relay', { on: på }).then(() => toast(på ? 'Høyttalerne er på' : 'Høyttalerne er av')).catch(e => toast(e.message)); },
    v: () => status().speakers === false ? 'Av' : 'På' });
  bytt('Demo: feilmelding');
  bytt('Klokke i standby');
  bytt('Klokkestil', { s: 'SKJERM', n: 'Skjermsparer', act: () => { go('x:saver', saverIdx()); }, v: () => saverName() });
  bytt('Parede enheter');
  const tilk = SETS.findIndex(x => x.s === 'TILKOBLING');
  SETS.splice(tilk >= 0 ? tilk : SETS.length, 0,
    { s: 'TILKOBLING', n: 'Wi-Fi', act: () => go('x:wifi'), v: () => net().ssid || 'Ikke tilkoblet' },
    { s: 'TILKOBLING', n: 'Blåtann-paring', act: () => { api('/api/bt', { pairing: true }).catch(() => {}); toggleSettings(); }, v: 'Start' });
  settInn('Enhetsnavn', { s: 'TILKOBLING', n: 'Eget navn', act: () => tastatur('NAVN PÅ FORSTERKEREN', status().name || '', 24, (t) => { t = t.trim(); if (!t) return false; api('/api/settings', { nameCustom: t }).then(() => toast('Heter nå «' + t + '»')).catch(e => toast(e.message)); go(''); S.set.page = ''; return true; }), v: () => status().name || 'Endre' });
  bytt('Glem alle enheter', { s: 'TILKOBLING', n: 'Glem alle Blåtann-enheter', act: () => { if (S.set.confirm) { api('/api/bt', { forget: true }).then(() => toast('Alle enheter er glemt')).catch(e => toast(e.message)); S.set.confirm = 0; } else S.set.confirm = 1; }, v: () => S.set.confirm ? 'Trykk igjen' : '' });
  bytt('Kjør oppsett på nytt', { s: 'SYSTEM', n: 'Kjør oppsett på nytt', act: () => startOppsett(), v: 'Start' });
  settInn('Kjør oppsett på nytt', { s: 'SYSTEM', n: 'Programvare', act: () => { M.upd = null; go('x:upd'); hentUpd(false); }, v: () => status().version || 'Sjekk' });
  bytt('Fabrikkinnstillinger', { s: 'SYSTEM', n: 'Fabrikkinnstillinger', act: () => { if (S.set.confirm) { S.set.confirm = 0; api('/api/settings/reset', {}).then(() => startOppsett()).catch(e => toast(e.message)); } else S.set.confirm = 1; }, v: () => S.set.confirm ? 'Trykk igjen' : 'Nullstill' });
  SETS.push({ s: 'SYSTEM', n: 'Start på nytt', act: () => { if (S.set.confirm) { S.set.confirm = 0; api('/api/reboot', {}).catch(() => {}); } else S.set.confirm = 1; }, v: () => S.set.confirm ? 'Trykk igjen' : 'Omstart' },
    { s: 'SYSTEM', n: 'Slå av', act: () => { if (S.set.confirm) { S.set.confirm = 0; api('/api/reboot', { poweroff: true }).catch(() => {}); } else S.set.confirm = 1; }, v: () => S.set.confirm ? 'Trykk igjen' : 'Slå av' });
  // designets egen «trykk igjen» nullstilles i setAct bare for to navn: hold bekreftelsen for våre også
  const _setAct = window.setAct;
  window.setAct = function () { const it = curList()[S.set.idx] || {}, c = S.set.confirm; _setAct(); if (/Fabrikk|Start på nytt|Slå av|Glem alle/.test(it.n || '') && c === 0 && it.act && S.set.confirm === 0) S.set.confirm = 1; };
  window.startSetup = startOppsett;

  // ---------- hjul og knapper (fra screen.js) ----------
  function ui(ev) {
    const p = page();
    if (!M.wiz && !p) return false;
    if (ev.ev === 'menu_toggle' && p === 'x:nett') { nettTilbake(); S.set.open = false; return false; }   // holdt hjul: lukk og åpne innstillingene
    if (ev.ev === 'menu_toggle') { if (M.wiz) return true; M.kb = null; S.set.page = ''; return false; }   // holdt hjul: designets meny åpnes/lukkes
    S.set.t = now(); S.lastAct = now();
    const d = ev.d > 0 ? 1 : -1;
    if (ev.ev === 'back') { back(); return true; }
    if (p === 'x:kb') { if (ev.ev === 'turn') kbPos(M.kb.pos + d); else if (ev.ev === 'press') kbTrykk(); return true; }
    if (p === 'x:saver') { if (ev.ev === 'turn') M.idx = (M.idx + d + SAVERS.length) % SAVERS.length; else if (ev.ev === 'press') velgSaver(); return true; }
    if (p === 'x:nett') { if (ev.ev === 'turn') M.idx = Math.max(0, Math.min(NETTVALG.length - 1, M.idx + d)); else if (ev.ev === 'press') nettValg(M.idx); return true; }
    if (p === 'x:wifi') { const v = wifiValg(); if (ev.ev === 'turn') M.idx = Math.max(0, Math.min(v.length - 1, M.idx + d)); else if (ev.ev === 'press') v[M.idx].a(); return true; }
    if (p === 'x:scan') { if (ev.ev === 'turn') M.idx = Math.max(0, Math.min(Math.max(0, M.nets.length - 1), M.idx + d)); else if (ev.ev === 'press' && !M.scanning) velgNett(); return true; }
    if (p === 'x:ble') { if (ev.ev === 'press') { api('/api/oppsett', { ble: false }).catch(() => {}); back(); } return true; }
    if (p === 'x:conn') {
      const c = M.conn || {};
      if (c.state === 'ok' && ev.ev === 'press') { if (M.wiz) { M.step = 2; M.idx = 0; S.set.page = ''; S.set.open = false; } else if (M.ret === 'x:nett') { S.set.page = ''; S.set.open = false; meld(); } else go('x:wifi'); }
      else if (c.state === 'feil') { if (ev.ev === 'turn') M.idx = M.idx ? 0 : 1; else if (ev.ev === 'press') { if (M.idx) skann(); else velgNett(); } }
      return true;
    }
    if (p === 'x:upd') {
      const u = M.upd || {};
      if (ev.ev === 'turn' && u.available && u.state === 'klar') M.idx = M.idx ? 0 : 1;
      else if (ev.ev === 'press') { if (u.state === 'klar' && u.available && M.idx === 0) hentUpd(true); else if (u.state === 'feil') hentUpd(false); else if (u.state !== 'kjorer' && u.state !== 'omstart') back(); }
      return true;
    }
    if (M.wiz) { const v = stegValg(); if (ev.ev === 'turn') M.idx = Math.max(0, Math.min(v.length - 1, M.idx + d)); else if (ev.ev === 'press') stegTrykk(); return true; }
    return false;
  }

  // ---------- tegning: våre sider foran designets ----------
  const tegn = window.drawBar;
  window.drawBar = function () {
    nettVakt();
    const p = page(), s = status(), sn = s.setup_net;
    // oppsettet viser selv QR-en når oppsett-nettet er oppe; system.js tar bare «Kobler til» (setup_net.joining)
    const egen = p || (M.wiz && !(sn && sn.joining)) ? (p || 'x:setup') : '';
    if (!egen || s.rebooting) { tegn(); if (!s.rebooting && utenNett() && hovedVisning()) { ingenWifi(cvb.getContext('2d')); texB.needsUpdate = true; } return; }
    const g = cvb.getContext('2d'); g.setTransform(0.5, 0, 0, 0.5, 0, 0); g.fillStyle = '#000'; g.fillRect(0, 0, 1920, 640);
    g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    try {
      ({ 'x:nett': tegnNett, 'x:saver': tegnSaver, 'x:wifi': tegnWifi, 'x:scan': tegnScan, 'x:kb': tegnKb, 'x:conn': tegnConn, 'x:ble': tegnBle, 'x:upd': tegnUpd, 'x:setup': tegnOppsett }[egen] || tegnOppsett)(g);
    } catch (e) { tekst(g, 'Feil: ' + e.message, 88, 320, 36, 400, ROD); }
    melding(g);
    texB.needsUpdate = true;
    if (egen !== 'x:nett' || now() - M.msgT < 2600) wake(600);   // x:nett står stille: ingen tegnesløyfe mens den venter
  };
  // melding også over designets meny (f.eks. «Heter nå …»)
  const tegnMeny = window.drawBarSettings;
  if (tegnMeny) window.drawBarSettings = function (g) { tegnMeny(g); melding(g); };

  // ---------- oppsett ved første oppstart ----------
  if (!window.__demo && new URLSearchParams(location.search).get('demo') === null) {
    setTimeout(() => {
      api('/api/settings').then(j => { const se = j.settings || j; if (se && se.setupDone === false && !M.wiz) startOppsett(); }).catch(() => {});
    }, 7000);
  }

  window.S1MENY = { ui, active, start: startOppsett, M, go, tastatur, utenNett };
})();
