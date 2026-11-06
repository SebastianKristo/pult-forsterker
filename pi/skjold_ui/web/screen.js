// Skjold S1 rev F – skjermen (960 × 320). Tegningen er designets egen kode (s1_draw.js, generert av extract.py);
// denne fila kobler den til daemonen (/api/status, /api/events, /api/settings) og til knappene via skjold-ui (/ui/stream).
// Kontrakten er beskrevet i ../KONTRAKT.md.
(function () {
  'use strict';
  const now = () => performance.now();
  document.body.appendChild(cvb);
  // Designets hjelpere som rører 3D-modellen: gjør dem til «tegn på nytt»
  window.animate = () => wake(4000);
  window.refresh = () => { pushSettings(); wake(1500); };

  // ---------- tegnesløyfe: 30 fps når noe beveger seg, ellers bare når klokka endres eller data kommer ----------
  let until = 0, raf = 0, lastMin = -1, lastDraw = 0;
  function wake(ms) { until = Math.max(until, now() + (ms || 1000)); if (!raf) raf = requestAnimationFrame(frame); }
  function busy() {
    const n = now();
    return n < until || booting() || S.rebootT || S.pairT || S.knobHoldT || (S.set.open && n - S.set.t < 20000)
      || ((window.bdayOn && bdayOn()) && !S.bdayHide)
      || (!S.power && S.main && S.set.clock && [6, 7].includes(S.set.clockStyle | 0));   // VU-metre og radioskala er animert
  }
  function frame(t) {
    raf = 0;
    if (t - lastDraw >= 32) { lastDraw = t; draw(); }
    if (busy()) raf = requestAnimationFrame(frame);
  }
  function draw() {
    if (S.set.open && now() - S.set.t > 20000) { S.set.open = false; postUi(); }   // menyen lukker seg etter 20 s
    // Under drawBar tegner designet 320 × 240-flaten (drawTFT0/1) for undersider og standby – samme som i prototypen
    try { drawTFT1(); } catch (e) { /* undersider uten data */ }
    drawBar();
  }
  setInterval(() => { const m = new Date().getMinutes(); if (m !== lastMin || busy()) { lastMin = m; wake(50); } }, 1000);

  // Standby-stiler med data fra Home Assistant (§4.3): bruk ekte data fra status.home; mangler det, vis «Dato» (5)
  // i stedet for designets eksempeltall (vær, kalender, bilde, alarm).
  const NEEDS = { 9: 'weather', 11: 'sun', 13: 'photo', 14: 'alarm', 15: 'cal' };
  window.drawSaver = function (g, stl) {
    const home = (st && st.home) || {}, need = NEEDS[stl];
    if (need && !home[need]) stl = 5;
    const w = WL[S.wl] || {}, data = { name: devName(), last: w.t ? w.t + ' · ' + (w.s || '') : '' };
    ['weather', 'sun', 'cal', 'photo', 'caption', 'alarm'].forEach(k => { if (home[k] != null) data[k] = home[k]; });
    SKJOLD.drawWide(g, 1920, 640, stl, new Date(), data);
  };

  // ---------- data fra daemonen ----------
  const INMAP = { airplay: 0, bt: 0, spotify: 0, upnp: 0, plex: 0, aux: 1, aux2: 1, radio: 2, usb: 3 };
  let st = {}, prev = {};
  function apply(s) {
    prev = st; st = s || {}; const n = now();
    S.power = !!st.power; S.main = true;
    if (st.name) NAMES[S.set.name | 0] = st.name;   // enhetsnavnet fra daemonen (designets devName() leser NAMES)
    const inp = st.input || 'airplay';
    S.input = INMAP[inp] ?? 0;
    if (inp === 'bt') S.wl = 'bt'; else if (S.input === 0) S.wl = 'air';
    S.aux = inp === 'aux2' ? 1 : 0;
    S.usb = (st.usb_pc || 1) - 1;
    if (typeof st.volume === 'number') { if (st.volume !== prev.volume && prev.volume !== undefined) S.volT = n; S.vol = st.volume; }
    if (!!st.mute !== !!prev.mute && prev.mute !== undefined) S.muteT = n;
    S.muted = !!st.mute; S.hp = !!st.headphones; S.paused = !st.playing;
    S.err = st.overtemp ? 3 : (S.input === 2 && st.lyrion === false ? 1 : 0); if (S.err && !prev.overtemp && st.overtemp) S.errT = n;
    // nå spilles → designets datastrukturer (INPUTS/WL/TRACKS/PRESETS)
    const t = st.title || '', a = st.artist || '';
    if (S.input === 0) {
      const w = WL[S.wl]; w.t = t || (S.wl === 'bt' ? 'Blåtann' : 'AirPlay'); w.s = a; w.st = st.airplay_device ? (S.wl === 'bt' ? 'Blåtann · ' : 'AirPlay · ') + st.airplay_device : w.st;
      const dur = +st.duration || 0, pos = +st.position || 0; TRACKS[S.wl][S.trk[S.wl] || 0] = [w.t, w.s, dur || 1];
      S.playT = n - pos * 1000; S.pausedAt = S.paused ? n : 0;
    }
    if (Array.isArray(st.presets)) st.presets.slice(0, 6).forEach((p, i) => { if (p && p.title) PRESETS[i] = [p.title, PRESETS[i] ? PRESETS[i][1] : '']; });
    if (S.input === 2) { const rn = st.radio_now || {}; if (rn.n) S.preset = rn.n - 1; INPUTS[2].t = rn.name || st.station || INPUTS[2].t; INPUTS[2].s = rn.now || t || 'Lyrion · internettradio'; }
    // knapper som holdes inne (daemonen: hold {key,p}) → designets hold-ring
    const h = st.hold;
    if (h && h.key && !h.saved) { const kind = { knob: 'knob', src: 'pair', radio: 'radio', reboot: 'power' }[h.key] || h.key, ms = kind === 'power' ? 3000 : kind === 'radio' ? 3000 : kind === 'pair' ? 2000 : 1500;
      S.holdWhat = kind; S.holdMs = ms; S.knobHoldT = n - (h.p || 0) * ms; }
    else S.knobHoldT = 0;
    if (h && h.saved) S.saveT = n;
    S.rebootT = st.rebooting ? (S.rebootT || n) : 0;
    if (st.bt_pairing) { if (!S.pairT) S.pairT = n; } else if (S.pairT) { S.pairT = 0; S.pairCancelT = n; }
    // nattmodus (daemonen/smarthus: night {on, src, steps:[{name,done}]})
    const ng = st.night;
    if (ng && typeof ng === 'object' && prev.night && (ng.on !== prev.night.on)) nightMode(ng.src || 'Home Assistant', ng.on, (ng.steps || []).map(x => x.name || x));
    else if (ng && typeof ng === 'object') S.night = !!ng.on;
    if (st.sleep && st.sleep.left) S.toastT = 0;
    if (t !== (prev.title || '') || inp !== prev.input) S.actT = n;
    S.lastAct = st.input_seq !== prev.input_seq ? n : S.lastAct;
    wake(400);
  }
  function applySettings(set) {
    if (!set) return;
    for (const k in set) if (k in S.set && typeof set[k] === typeof S.set[k]) S.set[k] = set[k];
    LEDK = [1, 0.55, 0.22, 0][S.set.led | 0];
    wake(200);
  }
  let pushT = 0, lastSent = '';
  function pushSettings() {   // endringer gjort i menyen på skjermen → daemonen (samme nøkler som skjold_settings.js)
    clearTimeout(pushT); pushT = setTimeout(() => {
      const body = {}; for (const k in SDEF) body[k] = S.set[k];
      const j = JSON.stringify(body); if (j === lastSent) return; lastSent = j;
      fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: j }).catch(() => {});
    }, 300);
  }
  async function poll() { try { const r = await fetch('/api/status'); apply(await r.json()); } catch (e) { /* daemonen starter */ } }
  async function loadSettings() { try { const r = await fetch('/api/settings'); const j = await r.json(); applySettings(j.settings || j); lastSent = ''; } catch (e) {} }
  function events() {
    let es; try { es = new EventSource('/api/events'); } catch (e) { setInterval(poll, 1000); return; }
    es.onmessage = (e) => { try { const j = JSON.parse(e.data); if (j && (j.power !== undefined || j.input)) apply(j); else poll(); } catch (x) { poll(); } };
    es.onerror = () => { es.close(); setTimeout(events, 3000); };
  }

  // ---------- knapper og hjul fra skjold-ui (/ui/stream) ----------
  function postUi() { fetch('/ui/state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ menu: !!S.set.open, setup: !!S.setup.on, bday: !!(bdayOn() && !S.bdayHide) }) }).catch(() => {}); }
  function onUi(ev) {
    const n = now(); S.lastAct = n;
    if (ev.ev === 'dismiss_greeting') { S.bdayHide = true; postUi(); wake(300); return; }
    if (ev.ev === 'menu_toggle') { S.power = true; toggleSettings(); postUi(); return; }
    if (!S.set.open) return;
    S.set.t = n;
    if (ev.ev === 'turn') {
      const d = ev.d > 0 ? 1 : -1; if (S.set.page) return;
      if (S.set.edit) { const [k, mn, mx] = curList()[S.set.idx].num; S.set[k] = Math.max(mn, Math.min(mx, S.set[k] - d)); pushSettings(); }
      else { S.set.idx = Math.max(0, Math.min(curList().length - 1, S.set.idx + d)); S.set.confirm = 0; }
    } else if (ev.ev === 'press') { setAct(); pushSettings(); }
    else if (ev.ev === 'back') { if (S.set.edit) S.set.edit = false; else if (S.set.page) S.set.page = ''; else if (S.set.cat >= 0) { S.set.cat = -1; S.set.idx = 0; } else S.set.open = false; }
    postUi(); wake(1500);
  }
  function uiStream() {
    let es; try { es = new EventSource('/ui/stream'); } catch (e) { return; }
    es.onmessage = (e) => { try { onUi(JSON.parse(e.data)); } catch (x) {} };
    es.onerror = () => { es.close(); setTimeout(uiStream, 2000); };
  }

  // ---------- bursdagshilsen: tilstanden eies av skjold-ui (/etc/skjold/greeting.json) ----------
  async function greeting() {
    try { const g = await (await fetch('/greeting')).json();
      try { localStorage.setItem('s1_bday_once', g.state === 'armed' ? 'armed' : 'shown'); localStorage.setItem('s1_bday_name', g.name || 'Pappa'); } catch (e) {}
      if (g.state === 'armed') S.bdayHide = false; postUi(); } catch (e) {}
  }

  // Forhåndsvisning/test: ?demo=<tilstand> tegner uten daemon (brukes av test_render.js)
  const demo = new URLSearchParams(location.search).get('demo');
  if (demo !== null) { window.__demo = true; window.SKJOLD_SCREEN = { apply, applySettings, onUi, S, wake }; startBoot(); wake(3000); return; }
  startBoot(); wake(3000);
  greeting(); loadSettings(); poll(); events(); uiStream();
  setInterval(loadSettings, 30000);
  window.SKJOLD_SCREEN = { apply, applySettings, onUi, S, wake };
})();
