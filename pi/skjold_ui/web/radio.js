// Skjold Radio – skjermen (4,3″ DSI 800 × 480, kapasitiv touch). Velges av layout.js (?layout=radio eller ca. 5:3).
// Leser daemonen via skjold-ui sin proxy (/api/status, /api/events, /api/settings …) og tar imot hjulet og knappene
// fra skjold_radio_knapper.py via skjold-ui (/ui/stream). Kontrakten står i ../KONTRAKT.md (§ 4 Skjold Radio).
//
// Skjermer: nå spilles (omslag/logo, tittel, artist, kilde, fremdrift, klokke, volum når knotten dreies) med
// favoritt 1–6 nederst – hver brikke står rett over sin fysiske knapp. Hjulet: drei = bla i favorittene (gull ring),
// trykk = spill/pause, hold = meny. I menyen: drei = bla, trykk = velg, hold = tilbake. Av eller stille lenge: klokke.
(function () {
  'use strict';
  const Q = new URLSearchParams(location.search), DEMO = Q.get('demo') !== null;
  const now = () => performance.now();
  const $ = (s, el) => (el || document).querySelector(s);
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const set = (e, txt) => { txt = txt == null ? '' : String(txt); if (e.textContent !== txt) e.textContent = txt; };
  const tog = (e, cls, on) => { if (e.classList.contains(cls) !== !!on) e.classList.toggle(cls, !!on); };
  const pad = n => String(n).padStart(2, '0');
  const hhmm = d => pad(d.getHours()) + ':' + pad(d.getMinutes());
  const mmss = t => { t = Math.max(0, Math.floor(t)); return Math.floor(t / 60) + ':' + pad(t % 60); };

  const SRC = { radio: 'Radio', airplay: 'AirPlay', bt: 'Blåtann', spotify: 'Spotify', plex: 'Plex', roon: 'Roon', aux: 'AUX', aux2: 'AUX 2', usb: 'USB' };
  const DAYS = ['man', 'tir', 'ons', 'tor', 'fre', 'lør', 'søn'];
  const WEEK = ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'];
  const MONTH = ['januar', 'februar', 'mars', 'april', 'mai', 'juni', 'juli', 'august', 'september', 'oktober', 'november', 'desember'];
  const BRIGHT = ['Auto', 'Høy', 'Middels', 'Lav'];
  const IDLE_MS = 5 * 60 * 1000;     // ingen lyd og ingen knapp på 5 min → klokka
  const MENU_MS = 30000;             // menyen lukker seg etter 30 s uten hjul
  const SETTLE_MS = 600;             // = timing.wheel_settle i radio_pins.yaml (skjold_radio_knapper.py)

  // Favorittbrikkene står over de fysiske knappene. Fra skjold_radio.scad: knappene sitter i x = 135 + 16·i mm,
  // det aktive området (95,04 × 53,86 mm, 800 × 480) er sentrert i vinduet rundt x = 175 mm.
  const AA_W = 95.04, PX = 800 / AA_W, AA_X0 = 175 - AA_W / 2;
  const SLOT_X = [0, 1, 2, 3, 4, 5].map(i => Math.round((135 + 16 * i - AA_X0) * PX));

  const ICON = {
    radio: 'M4 8h16a2 2 0 012 2v9a2 2 0 01-2 2H4a2 2 0 01-2-2v-9a2 2 0 012-2zm3.5 4a3.5 3.5 0 100 7 3.5 3.5 0 000-7zM14 12v2h5v-2zm0 4v2h5v-2zM6 7l11-4 .7 1.9L9.5 8z',
    src: 'M3 5h18v2H3zm0 6h12v2H3zm0 6h18v2H3zm15-7l4 2-4 2z',
    lib: 'M4 4h3v16H4zm5 0h3v16H9zm5.2.6l2.9-.8 4 15.4-2.9.8z',
    moon: 'M14.5 2.5A9.5 9.5 0 1021.5 15 7.5 7.5 0 0114.5 2.5z',
    bell: 'M12 22a2.5 2.5 0 002.5-2.5h-5A2.5 2.5 0 0012 22zm7-6V11a7 7 0 00-5.5-6.8V3a1.5 1.5 0 00-3 0v1.2A7 7 0 005 11v5l-2 2v1h18v-1z',
    gear: 'M19.4 13a7.5 7.5 0 000-2l2.1-1.6-2-3.5-2.5 1a7.6 7.6 0 00-1.7-1L14.9 3h-4l-.4 2.7a7.6 7.6 0 00-1.7 1l-2.5-1-2 3.5L6.4 11a7.5 7.5 0 000 2l-2.1 1.6 2 3.5 2.5-1a7.6 7.6 0 001.7 1l.4 2.9h4l.4-2.7a7.6 7.6 0 001.7-1l2.5 1 2-3.5zM12 15.5a3.5 3.5 0 110-7 3.5 3.5 0 010 7z',
  };
  const svg = (k) => '<svg class="ic" viewBox="0 0 24 24"><path d="' + ICON[k] + '"/></svg>';

  // ---------- API (gjennom skjold-ui sin proxy) ----------
  async function api(path, body) {
    const o = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    const r = await fetch(path, o);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
    return j;
  }
  const act = (path, body) => api(path, body || {}).then(j => { if (j && (j.power !== undefined || j.input)) apply(j); return j; })
    .catch(e => toast('Feil', e.message));

  // ---------- DOM ----------
  const app = el('div'); app.id = 'app';
  app.innerHTML = `
    <div id="bg"></div><div id="scrim"></div>
    <div class="top"><span id="chips"></span><span class="grow"></span>
      <span class="stat hide" id="st-sleep"><svg viewBox="0 0 24 24"><path d="${ICON.moon}"/></svg><span></span></span>
      <span class="stat hide" id="st-alarm"><svg viewBox="0 0 24 24"><path d="${ICON.bell}"/></svg><span></span></span>
      <span id="clock"></span></div>
    <div id="art"></div><div id="paused" class="hide"><i></i><i></i></div>
    <div class="meta"><div id="kicker"></div><div id="title"></div><div id="artist"></div><div class="grow"></div>
      <div class="prog" id="prog"><div class="bar"><i></i></div><div class="times"><span id="tpos"></span><span id="tdur"></span></div></div>
      <div class="live hide" id="live"><span class="eq"><b></b><b></b><b></b><b></b></span><span id="livet">Direkte</span></div></div>
    <div id="browse" class="hide"></div>
    <div id="favs"></div>
    <div id="vol" class="hide"><span class="lbl">VOLUM</span><div class="bar"><i></i></div><span class="val"></span></div>
    <div id="toast" class="hide"></div>
    <div id="menu" class="hide"></div>
    <div id="standby" class="hide"><div class="sbw"><div class="sc"></div><div class="sd"></div><div class="sa"></div></div><div class="sn"></div></div>
    <div id="greet" class="hide"><div class="g1">GRATULERER MED DAGEN</div><div class="g2"></div><div class="g3">Trykk på en knapp for å fortsette</div></div>`;
  document.body.appendChild(app);
  const favs = $('#favs', app);
  for (let i = 0; i < 6; i++) {
    const f = el('div', 'fav'); f.dataset.n = i + 1; f.style.left = SLOT_X[i] + 'px';
    f.innerHTML = '<span class="num">' + (i + 1) + '</span><span class="lg"></span><span class="nm"></span>';
    f.addEventListener('click', () => { wakeUp(); flash(i + 1); act('/api/presets/' + (i + 1) + '/play'); });
    favs.appendChild(f);
  }
  $('#art', app).addEventListener('click', () => { wakeUp(); act('/api/transport', { action: 'playpause' }); });
  $('#clock', app).addEventListener('click', () => { wakeUp(); openMenu(); });
  $('#standby', app).addEventListener('click', () => wakeUp());

  // ---------- tilstand ----------
  let st = {}, stAt = now(), settings = { bright: 0, clock: true }, plugins = null, lib = null;
  const U = { volT: -1e9, lastVol: undefined, lastMute: undefined, lastAct: now(), browse: { acc: 0, t: -1e9 }, flash: { n: 0, t: -1e9 },
    toast: null, toastT: -1e9, greet: null };

  function apply(s) {
    const p = st; st = s || {}; stAt = now();
    if (typeof st.volume === 'number' && p.volume !== undefined && st.volume !== p.volume) U.volT = now();
    if (p.mute !== undefined && !!st.mute !== !!p.mute) U.volT = now();
    if (st.input_seq !== p.input_seq || st.title !== p.title || st.input !== p.input || st.power !== p.power) U.lastAct = now();
    if (p.preset !== st.preset || (p.radio_now || {}).n !== (st.radio_now || {}).n) U.browse.acc = 0;
    render();
  }
  function applySettings(s) { if (s) Object.assign(settings, s); render(); }

  // ---------- nå spilles ----------
  function nowInfo() {
    const inp = st.input || 'radio', rn = st.radio_now || {}, radio = inp === 'radio';
    const title = radio ? (rn.name || st.station || st.title || 'Radio') : (st.title || SRC[inp] || 'Skjold Radio');
    let artist = radio ? (rn.now || (st.title && st.title !== rn.name ? [st.artist, st.title].filter(Boolean).join(' – ') : '')) : [st.artist, st.album].filter(Boolean).join(' · ');
    if (!artist && !radio) artist = inp === 'airplay' ? 'Venter på AirPlay' : inp === 'bt' ? 'Koble til med Blåtann' : inp.startsWith('aux') ? 'Linje inn' : '';
    const n = radio ? (rn.n || 0) : 0;
    let kicker = SRC[inp] || inp;
    if (radio) kicker = [n ? 'Favoritt ' + n : '', rn.genre || '', st.source_label || 'Internettradio'].filter(Boolean).join(' · ');
    else if (inp === 'airplay' && st.airplay_device) kicker = 'AirPlay · ' + st.airplay_device;
    else if (inp === 'bt' && st.bt_device) kicker = 'Blåtann · ' + st.bt_device;
    const img = st.cover_url || (radio ? (rn.logo || '') : '');
    return { inp, radio, title, artist, kicker, img, logo: !st.cover_url && !!img, n };
  }
  // Uten omslag: farget flate med navnet (som S1 sin drawArt)
  function hue(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; }
  function phStyle(name) { const h = hue(name); return 'background:linear-gradient(135deg,hsl(' + ((h + 330) % 360) + ' 78% 58%),hsl(' + ((h + 40) % 360) + ' 70% 42%) 55%,hsl(' + ((h + 150) % 360) + ' 65% 45%))'; }
  // Kort navn til flater uten logo: «NRK P3» → P3, «P4 Norge» → P4, «Radio Norge» → RN, «NRK Klassisk» → KL
  function short(name) {
    const w = String(name || '').replace(/^NRK\s+/i, '').trim().split(/\s+/).filter(Boolean);
    if (!w.length) return '';
    if (/\d/.test(w[0]) && w[0].length <= 4) return w[0];
    if (w.length === 1) return w[0].length <= 4 ? w[0] : w[0].slice(0, 2).toUpperCase();
    return w.slice(0, 3).map(x => x[0]).join('').toUpperCase();
  }
  function artHtml(img, name, logo) {
    const ph = '<div class="ph" style="' + phStyle(name) + '">' + esc(short(name)) + '</div>';
    return img ? ph + '<img class="' + (logo ? 'logo' : '') + '" src="' + esc(img) + '" onerror="this.remove()">' : ph;
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

  let artKey = '', favKey = '', chipKey = '';
  function renderNow() {
    const n = nowInfo(), t = now();
    const ak = n.img + '|' + n.title;
    if (ak !== artKey) {
      artKey = ak; $('#art', app).innerHTML = artHtml(n.img, n.title, n.logo);
      $('#bg', app).style.cssText = n.img && !n.logo ? 'background-image:url("' + n.img.replace(/"/g, '%22') + '")' : phStyle(n.title);
    }
    const ck = n.inp + '|' + !!st.playing;
    if (ck !== chipKey) {
      chipKey = ck;
      const c = $('#chips', app); c.innerHTML = '';
      const ch = el('span', 'chip on', (SRC[n.inp] || n.inp).toUpperCase());
      if (n.radio && st.playing) ch.appendChild(el('span', 'dot'));
      c.appendChild(ch);
    }
    set($('#clock', app), hhmm(new Date()));
    set($('#kicker', app), n.kicker); set($('#title', app), n.title); set($('#artist', app), n.artist);
    const dur = +st.duration || 0, playing = !!st.playing;
    const pos = Math.min(dur, (+st.position || 0) + (playing ? (t - stAt) / 1000 : 0));
    const cur = browseCursor(), vOn = t - U.volT < 2200 || !!st.mute;   // bla-teksten og volumet tar plassen nederst
    tog($('#prog', app), 'hide', !(dur > 0) || cur || vOn);
    tog($('#live', app), 'hide', dur > 0 || !n.radio || cur || vOn);
    set($('#livet', app), playing ? 'Direkte' : 'Pause');
    if (dur > 0) { $('#prog .bar i', app).style.width = (100 * pos / dur).toFixed(2) + '%'; set($('#tpos', app), mmss(pos)); set($('#tdur', app), '−' + mmss(dur - pos)); }
    tog($('#paused', app), 'hide', playing || !(st.title || n.radio) || (n.radio && !st.radio_now));
    tog(app, 'paused', !playing);

    // favoritter
    const pr = (st.presets || []).slice(0, 6);
    const fk = JSON.stringify(pr.map(p => [p && p.title, p && p.logo]));
    if (fk !== favKey) {
      favKey = fk;
      favs.querySelectorAll('.fav').forEach((f, i) => {
        const p = pr[i] || {}, name = p.title || '';
        tog(f, 'empty', !name);
        set($('.nm', f), name || 'Hold for å lagre');
        $('.lg', f).innerHTML = name ? (p.logo ? '<img src="' + esc(p.logo) + '" onerror="this.parentNode.textContent=\'' + esc(short(name)) + '\'">' : esc(short(name))) : '';
      });
    }
    const active = n.radio ? n.n : 0;
    favs.querySelectorAll('.fav').forEach((f, i) => {
      tog(f, 'on', active === i + 1); tog(f, 'cur', cur === i + 1 && cur !== active); tog(f, 'flash', U.flash.n === i + 1 && t - U.flash.t < 220);
    });
    const b = $('#browse', app);
    if (cur) { const p = (st.presets || [])[cur - 1] || {}; set(b, 'Favoritt ' + cur + (p.title ? ' · ' + p.title : '') + ' – spilles om litt'); }
    tog(b, 'hide', !cur);

    // volum (vises 2,2 s når knotten dreies, og hele tiden når lyden er dempet)
    const v = $('#vol', app);
    tog(v, 'hide', !vOn); tog(v, 'muted', !!st.mute);
    if (vOn) { $('.bar i', v).style.width = (st.mute ? 0 : (st.volume || 0)) + '%'; set($('.val', v), st.mute ? 'DEMPET' : (st.volume || 0)); set($('.lbl', v), st.headphones ? 'HODETLF.' : 'VOLUM'); }

    // status øverst: sovetimer og neste vekking
    const sl = +st.sleep || 0, ss = $('#st-sleep', app);
    tog(ss, 'hide', !sl); if (sl) set($('span', ss), Math.max(1, Math.round(sl / 60)) + ' min');
    const na = nextAlarm(), sa = $('#st-alarm', app);
    tog(sa, 'hide', !na); if (na) set($('span', sa), na.time);
  }

  // Hjulet blar i favorittene: samme regnestykke som RadioKnapper.tick() (starter etter 0,6 s ro)
  function browseCursor() {
    if (!U.browse.acc || now() - U.browse.t > SETTLE_MS + 1500) return 0;
    const count = (st.presets || []).length || 6, base = U.browse.base || +st.preset || 1;
    return ((base - 1 + U.browse.acc) % count + count) % count + 1;
  }
  function flash(n) { U.flash = { n, t: now() }; render(); setTimeout(render, 240); }

  // ---------- vekkerklokke og sovetimer (pluginene i daemonen) ----------
  function alarmCfg() { const p = plugins && (plugins.plugins || []).find(x => x.id === 'alarm'); return p || null; }
  function nextAlarm() {
    const p = alarmCfg(); if (!p || !p.enabled) return null;
    const d = new Date(); let best = null;
    (p.cfg.alarms || []).forEach(a => {
      if (a.on === false || !/^\d\d:\d\d$/.test(a.time || '')) return;
      const [h, m] = a.time.split(':').map(Number);
      for (let k = 0; k < 8; k++) {
        const x = new Date(d.getFullYear(), d.getMonth(), d.getDate() + k, h, m);
        const wd = (x.getDay() + 6) % 7;   // daemonen: 0 = mandag
        if (x > d && (!a.days || !a.days.length || a.days.includes(wd))) { if (!best || x < best.at) best = { at: x, time: a.time, k }; break; }
      }
    });
    return best;
  }
  function daysText(days) {
    if (!days || !days.length || days.length === 7) return 'hver dag';
    const s = [...days].sort().join(',');
    if (s === '0,1,2,3,4') return 'man–fre';
    if (s === '5,6') return 'helg';
    return days.map(d => DAYS[d]).join(', ');
  }
  async function loadPlugins() { try { plugins = await api('/api/plugins'); render(); } catch (e) { /* daemonen starter */ } }
  async function loadLib() { try { lib = await api('/api/medialib'); } catch (e) { lib = {}; } }

  // ---------- melding ----------
  function toast(a, b, ms) { U.toast = [a, b]; U.toastT = now() + (ms || 2600); render(); setTimeout(render, (ms || 2600) + 50); }
  function renderToast() {
    const e = $('#toast', app), on = U.toast && now() < U.toastT;
    tog(e, 'hide', !on); if (on) e.innerHTML = esc(U.toast[0]) + (U.toast[1] ? ' <b>' + esc(U.toast[1]) + '</b>' : '');
  }

  // ---------- meny ----------
  // Et nivå: {title, items:[{label, value, info, big, art, icon, on, sub(), act(), dis}], idx, load()}
  const M = { stack: [], t: 0 };
  const back = { label: 'Tilbake', back: true };
  function openMenu() { M.stack = [rootMenu()]; M.t = now(); loadPlugins(); loadLib().then(() => { if (M.stack.length) { M.stack[0].items = rootMenu().items; render(); } }); postUi(); render(); }
  function closeMenu() { M.stack = []; postUi(); render(); }
  const menuOpen = () => M.stack.length > 0;
  function push(lv) {
    lv.idx = lv.idx || 0;
    if (lv.items && M.stack.length) lv.items = [back, ...lv.items];
    if (lv.load) {
      lv.items = M.stack.length ? [back, { label: 'Henter …', spin: true, dis: true }] : [{ label: 'Henter …', spin: true, dis: true }];
      lv.load().then(items => { lv.items = [back, ...items]; lv.idx = Math.min(Math.max(lv.idx, 1), lv.items.length - 1); render(); })
        .catch(e => { lv.items = [back, { label: 'Fikk ikke kontakt', info: e.message, dis: true }]; render(); });
    }
    M.stack.push(lv); if (lv.items && lv.items.length > 1 && lv.items[0].back && !lv.load) lv.idx = Math.max(lv.idx, 1);
    render();
  }
  function popMenu() { if (M.stack.length > 1) M.stack.pop(); else closeMenu(); render(); }
  function menuTurn(d) { const lv = M.stack[M.stack.length - 1]; if (!lv || !lv.items) return; lv.idx = Math.max(0, Math.min(lv.items.length - 1, lv.idx + d)); render(); }
  function menuPress() {
    const lv = M.stack[M.stack.length - 1]; if (!lv || !lv.items) return;
    const it = lv.items[lv.idx]; if (!it || it.dis) return;
    if (it.back) return popMenu();
    if (it.sub) return push(it.sub());
    if (it.act) { const r = it.act(); if (it.close) closeMenu(); else Promise.resolve(r).then(() => { if (lv.refresh) { lv.items = [back, ...lv.refresh()]; } render(); }); }
  }

  function rootMenu() {
    const items = [
      { label: 'Radio', icon: 'radio', info: 'Favorittene dine og stasjoner fra hele Norge, sortert etter sjanger.', sub: radioMenu },
      { label: 'Kilder', icon: 'src', value: SRC[st.input] || '', info: 'Velg hva radioen spiller: nettradio, AirPlay, Blåtann, Spotify og mer.', sub: srcMenu },
    ];
    const kinds = Object.keys(lib || {}).filter(k => lib[k] && lib[k].configured);
    if (kinds.length) items.push({ label: 'Bibliotek', icon: 'lib', info: 'Spillelister og nye album fra ' + kinds.map(k => k === 'plex' ? 'Plex' : 'Jellyfin').join(' og ') + '.', sub: () => libMenu(kinds) });
    const sl = +st.sleep || 0;
    items.push({ label: 'Sovetimer', icon: 'moon', value: sl ? Math.max(1, Math.round(sl / 60)) + ' min' : 'Av', info: 'Skrur ned lyden det siste minuttet og slår av radioen.', sub: sleepMenu });
    const al = alarmCfg();
    if (al) { const na = nextAlarm(); items.push({ label: 'Vekkerklokke', icon: 'bell', value: na ? na.time : 'Av', info: 'Vekk med en radiofavoritt. Tider og dager endres i Skjold-appen.', sub: alarmMenu }); }
    items.push({ label: 'Innstillinger', icon: 'gear', info: 'Lysstyrke, klokke i standby, nettverk og om radioen.', sub: settingsMenu });
    return { title: 'Meny', items, idx: 0 };
  }
  function presetItems() {
    return (st.presets || []).map((p, i) => p && p.title ? {
      label: (i + 1) + '  ' + p.title, art: p.logo, name: p.title, on: (st.radio_now || {}).n === i + 1,
      info: 'Favoritt ' + (i + 1) + (i < 6 ? ' – også knapp ' + (i + 1) + ' under skjermen.' : '.'), close: true,
      act: () => { flash(i + 1); return act('/api/presets/' + (i + 1) + '/play'); } } : null).filter(Boolean);
  }
  function radioMenu() {
    return { title: 'Radio', load: async () => {
      const items = [{ label: 'Favoritter', value: String(st.presets_count || presetItems().length), info: 'Hold en favorittknapp i 2 s for å lagre det som spiller.', sub: () => ({ title: 'Favoritter', items: presetItems() }) }];
      const b = await api('/api/radio/browse');
      (b.shelves || []).filter(s => (s.items || []).length).forEach(s => items.push({ label: s.title, value: String(s.items.length), info: s.items.slice(0, 4).map(x => x.name).join(', ') + ' …',
        sub: () => ({ title: s.title, items: s.items.map(x => ({ label: x.name, art: x.image, name: x.name, info: [x.genre, x.codec && x.bitrate ? x.codec + ' ' + x.bitrate + ' kbit/s' : ''].filter(Boolean).join(' · '),
          close: true, act: () => act('/api/radio/play', { url: x.url, title: x.name, image: x.image, genre: x.genre }) })) }) }));
      if (b.offline) items.push({ label: 'Stasjonslista er utilgjengelig', info: 'radio-browser.info svarer ikke. Favorittene virker likevel.', dis: true });
      return items;
    } };
  }
  function srcMenu() {
    const ins = st.inputs || Object.keys(SRC);
    const lv = { title: 'Kilder' };
    lv.refresh = () => ins.map(i => ({ label: SRC[i] || i, on: st.input === i, info: i === 'radio' ? 'Nettradio og favoritter.' : i === 'bt' ? 'Telefonen kobles til «' + (st.name || 'Skjold Radio') + '».' : i === 'airplay' ? 'Spill fra iPhone, iPad eller Mac.' : '',
      act: () => act('/api/input', { input: i }) }));
    lv.items = lv.refresh();
    return lv;
  }
  function libMenu(kinds) {
    const nm = k => k === 'plex' ? 'Plex' : 'Jellyfin';
    const one = k => [
      { label: 'Spillelister', info: nm(k), sub: () => ({ title: 'Spillelister', load: async () => (await api('/api/medialib/' + k + '/playlists')).map(p => ({ label: p.name, value: p.songCount ? p.songCount + ' låter' : '', art: p.cover, name: p.name, close: true, act: () => act('/api/medialib/' + k + '/play', { playlist: p.id }) })) }) },
      { label: 'Nye album', info: nm(k), sub: () => ({ title: 'Nye album', load: async () => (await api('/api/medialib/' + k + '/albums?type=newest')).map(a => ({ label: a.name, value: a.artist || '', art: a.cover, name: a.name, info: [a.artist, a.year].filter(Boolean).join(' · '), close: true, act: () => act('/api/medialib/' + k + '/play', { album: a.id }) })) }) },
    ];
    if (kinds.length === 1) return { title: 'Bibliotek', items: one(kinds[0]) };
    return { title: 'Bibliotek', items: kinds.map(k => ({ label: nm(k), sub: () => ({ title: nm(k), items: one(k) }) })) };
  }
  function sleepMenu() {
    const lv = { title: 'Sovetimer' }, sl = () => +st.sleep || 0;
    lv.refresh = () => [0, 15, 30, 45, 60, 90].map(m => ({ label: m ? m + ' minutter' : 'Av', on: m ? false : !sl(), big: m ? m + ' min' : 'Av', info: m ? 'Radioen slår seg av om ' + m + ' minutter. Lyden tones ned det siste minuttet.' : (sl() ? 'Slår av sovetimeren (' + Math.round(sl() / 60) + ' min igjen).' : 'Sovetimeren er av.'),
      act: () => api('/api/plugins/sleep', m ? { enabled: true, minutes: m } : { enabled: false }).then(() => { toast('Sovetimer', m ? m + ' min' : 'av'); if (!DEMO) setTimeout(poll, 300); }).catch(e => toast('Feil', e.message)) }));
    lv.items = lv.refresh(); return lv;
  }
  function alarmMenu() {
    const lv = { title: 'Vekkerklokke' };
    const save = (patch) => api('/api/plugins/alarm', patch).then(j => { plugins = j; }).catch(e => toast('Feil', e.message));
    lv.refresh = () => {
      const p = alarmCfg(); if (!p) return [];
      const al = p.cfg.alarms || [];
      return [{ label: 'Vekking', value: p.enabled ? 'På' : 'Av', on: p.enabled, info: p.enabled ? 'Neste: ' + ((nextAlarm() || {}).time || '–') : 'Ingen alarmer går.', act: () => save({ enabled: !p.enabled }) },
        ...al.map((a, i) => ({ label: a.time || '--:--', value: daysText(a.days), on: a.on !== false, big: a.time,
          info: daysText(a.days) + ' · ' + (a.url ? 'egen strøm' : 'favoritt ' + (a.preset || 1)) + ' · volum ' + (a.volume || 30) + '. Trykk for å slå av eller på.',
          act: () => save({ alarms: al.map((x, k) => k === i ? Object.assign({}, x, { on: x.on === false }) : x) }) }))];
    };
    lv.items = lv.refresh(); return lv;
  }
  function settingsMenu() {
    const lv = { title: 'Innstillinger' };
    const save = (patch) => { applySettings(patch); return api('/api/settings', patch).then(j => applySettings(j.settings)).catch(e => toast('Feil', e.message)); };
    lv.refresh = () => [
      { label: 'Lysstyrke', value: BRIGHT[settings.bright | 0] || 'Auto', info: 'Auto demper skjermen om kvelden og natta.', sub: () => {
        const l = { title: 'Lysstyrke' }; l.refresh = () => BRIGHT.map((b, i) => ({ label: b, on: (settings.bright | 0) === i, big: b, act: () => save({ bright: i }) }));
        l.items = l.refresh(); l.idx = 1 + (settings.bright | 0); return l; } },
      { label: 'Klokke i standby', value: settings.clock !== false ? 'På' : 'Av', on: settings.clock !== false, info: 'Vis klokka svakt når radioen er av. Av: skjermen blir helt svart.', act: () => save({ clock: settings.clock === false }) },
      { label: 'Nettverk', info: 'Wi-Fi, IP-adresse og navn på nettet.', sub: () => ({ title: 'Nettverk', load: async () => {
        const [w, n] = await Promise.all([api('/api/wifi').catch(() => ({ networks: [] })), api('/ui/net').catch(() => ({}))]);
        const a = (w.networks || []).find(x => x.active);
        return [{ label: 'Wi-Fi', value: a ? a.ssid : 'Kabel / ingen', dis: true, info: a ? 'Signal ' + a.signal + ' %' : '' },
          { label: 'Signal', value: a ? a.signal + ' %' : '–', dis: true }, { label: 'IP-adresse', value: n.ip || '–', dis: true },
          { label: 'Navn', value: n.host ? n.host + '.local' : '–', dis: true, info: 'Åpne http://' + (n.host || 'skjold') + '.local:8765 i nettleseren for web-oppsettet.' }];
      } }) },
      { label: 'Om radioen', info: '', sub: () => ({ title: 'Om radioen', items: [
        { label: 'Navn', value: st.name || 'Skjold Radio', dis: true }, { label: 'Versjon', value: st.version || '–', dis: true },
        { label: 'Skjerm', value: '800 × 480', dis: true }, { label: 'Lyd', value: 'Mono · 3″', dis: true }] }) },
    ];
    lv.items = lv.refresh(); return lv;
  }

  let menuKey = '';
  function renderMenu() {
    const m = $('#menu', app), open = menuOpen();
    tog(m, 'hide', !open); if (!open) { menuKey = ''; return; }
    const lv = M.stack[M.stack.length - 1], items = lv.items || [], idx = lv.idx || 0;
    const left = Math.max(0, 1 - (now() - M.t) / MENU_MS);
    const key = M.stack.length + '|' + lv.title + '|' + idx + '|' + JSON.stringify(items.map(i => [i.label, i.value, i.on, i.dis])) + '|' + hhmm(new Date());
    if (key !== menuKey) {
      menuKey = key;
      const crumbs = M.stack.map(l => l.title); crumbs[crumbs.length - 1] = '<b>' + esc(crumbs[crumbs.length - 1]) + '</b>';
      const RH = 52, VIS = 7, first = Math.max(0, Math.min(items.length - VIS, idx - 3));
      let rows = '';
      items.forEach((it, i) => {
        if (i < first || i >= first + VIS) return;
        const cls = 'row' + (i === idx ? ' sel' : '') + (it.back ? ' back' : '') + (it.dis && !it.spin ? ' dis' : '');
        rows += '<div class="' + cls + '" data-i="' + i + '" style="top:' + ((i - first) * RH) + 'px">' +
          (it.back ? '<span class="sub" style="transform:rotate(-135deg);margin:0 4px 0 2px"></span>' : '') +
          (it.icon ? svg(it.icon) : '') + (it.spin ? '<span class="spin"></span>' : '') +
          (it.on !== undefined && !it.sub ? '<span class="ck' + (it.on ? ' on' : '') + '"></span>' : '') +
          '<span class="t">' + esc(it.label) + '</span>' + (it.value ? '<span class="v">' + esc(it.value) + '</span>' : '') + (it.sub ? '<span class="sub"></span>' : '') + '</div>';
      });
      const sh = items.length > VIS ? Math.max(30, 358 * VIS / items.length) : 0;
      const it = items[idx] || {};
      let det = '';
      if (it.art !== undefined || it.name) det += '<div class="art">' + artHtml(it.art, it.name || it.label, true) + '</div>';
      det += '<div class="big">' + esc(it.big || (it.back ? 'Tilbake' : it.label.replace(/^\d+\s+/, ''))) + '</div>';
      if (it.value && !it.big) det += '<div class="kv"><b>' + esc(it.value) + '</b></div>';
      if (it.info) det += '<p>' + esc(it.info) + '</p>';
      m.innerHTML = '<div class="crumb">' + crumbs.join(' &nbsp;›&nbsp; ') + '</div><div class="mclock">' + hhmm(new Date()) + '</div>' +
        '<div class="list">' + rows + '</div>' + (sh ? '<div class="scroll" style="height:' + sh + 'px;top:' + (62 + (358 - sh) * first / Math.max(1, items.length - VIS)) + 'px"></div>' : '') +
        '<div class="det">' + det + '</div><div class="tbar"><i></i></div>' +
        '<div class="hint"><span><i></i>Drei for å bla</span><span>Trykk for å velge</span><span>Hold for å gå tilbake</span></div>';
      m.querySelectorAll('.row').forEach(r => r.addEventListener('click', () => { M.t = now(); lv.idx = +r.dataset.i; menuPress(); }));
    }
    const tb = $('.tbar i', m); if (tb) tb.style.width = (left * 100).toFixed(1) + '%';
  }

  // ---------- standby (av, eller stille lenge) ----------
  function standbyOn() {
    if (menuOpen()) return false;
    if (!st.power) return true;
    return !st.playing && now() - U.lastAct > IDLE_MS && !(+st.sleep);
  }
  let sbMin = -1;
  function renderStandby() {
    const s = $('#standby', app), on = standbyOn() && Object.keys(st).length > 0;
    tog(s, 'hide', !on); if (!on) return;
    const d = new Date(), clock = settings.clock !== false;
    s.style.opacity = clock ? '' : '0';
    if (d.getMinutes() !== sbMin) {   // flytt innholdet litt hvert minutt mot innbrenning
      sbMin = d.getMinutes(); const k = d.getMinutes() % 5; $('.sbw', s).style.transform = 'translate(' + ((k - 2) * 5) + 'px,' + (((k * 3) % 5) - 2) * 4 + 'px)';
    }
    set($('.sc', s), hhmm(d));
    set($('.sd', s), WEEK[d.getDay()][0].toUpperCase() + WEEK[d.getDay()].slice(1) + ' ' + d.getDate() + '. ' + MONTH[d.getMonth()]);
    const na = nextAlarm(), sl = +st.sleep || 0;
    let a = ''; if (na) a += '<span><svg viewBox="0 0 24 24"><path d="' + ICON.bell + '"/></svg>Vekking ' + (na.k === 0 ? 'i dag ' : na.k === 1 ? '' : DAYS[(na.at.getDay() + 6) % 7] + ' ') + na.time + '</span>';
    if (sl) a += '<span><svg viewBox="0 0 24 24"><path d="' + ICON.moon + '"/></svg>' + Math.round(sl / 60) + ' min</span>';
    const sa = $('.sa', s); if (sa.innerHTML !== a) sa.innerHTML = a;
    set($('.sn', s), st.power ? '' : 'SKJOLD');
  }

  // ---------- lysstyrke: CSS-filter + baklyset på DSI-skjermen (skjold-ui skriver /sys/class/backlight) ----------
  let lastBl = -1;
  function brightness() {
    const b = settings.bright | 0, h = new Date().getHours(), night = h >= 22 || h < 7;
    let k = [night ? 0.55 : 1, 1, 0.75, 0.5][b] || 1;
    if (standbyOn()) k = Math.min(k, night ? 0.25 : 0.45);
    app.style.filter = k < 0.99 ? 'brightness(' + (0.4 + 0.6 * k).toFixed(2) + ')' : '';
    if (k !== lastBl) { lastBl = k; if (!DEMO) fetch('/ui/backlight', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ level: k }) }).catch(() => {}); }
  }

  function renderGreet() {
    const g = $('#greet', app); tog(g, 'hide', !U.greet); if (U.greet) set($('.g2', g), U.greet + '!');
  }

  function render() {
    if (menuOpen() && now() - M.t > MENU_MS) closeMenu();
    renderNow(); renderMenu(); renderStandby(); renderToast(); renderGreet(); brightness();
  }
  setInterval(render, 250);

  function wakeUp() { U.lastAct = now(); render(); }

  // ---------- hjulet og knappene (skjold_radio_knapper.py → skjold-ui → /ui/stream) ----------
  function postUi() {
    if (DEMO) return;
    fetch('/ui/state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ menu: menuOpen(), setup: false, bday: !!U.greet }) }).catch(() => {});
  }
  function onUi(ev) {
    const t = now(); U.lastAct = t;
    switch (ev.ev) {
      case 'dismiss_greeting': U.greet = null; postUi(); break;
      case 'menu_toggle': if (menuOpen()) closeMenu(); else openMenu(); break;
      case 'turn': if (menuOpen()) { M.t = t; menuTurn(ev.d > 0 ? 1 : -1); } break;
      case 'press': if (menuOpen()) { M.t = t; menuPress(); } else if (ev.src === 'preset' && ev.n) flash(ev.n); break;
      case 'back': if (menuOpen()) { M.t = t; popMenu(); } break;
      case 'browse':   // hjulet dreies uten meny: vis hvilken favoritt som starter
        if (!U.browse.acc) U.browse.base = +st.preset || ((st.radio_now || {}).n) || 1;
        U.browse.acc += ev.d > 0 ? 1 : -1; U.browse.t = t; setTimeout(render, SETTLE_MS + 1600); break;
      case 'preset': flash(ev.n); if (menuOpen()) closeMenu(); break;
      case 'saved': flash(ev.n); toast('Lagret som favoritt', String(ev.n)); setTimeout(poll, 600); break;
    }
    render();
  }

  // ---------- data fra daemonen ----------
  async function poll() { if (DEMO) return; try { apply(await api('/api/status')); } catch (e) { /* daemonen starter */ } }
  async function loadSettings() { try { const j = await api('/api/settings'); applySettings(j.settings || j); } catch (e) {} }
  function events() {
    let es; try { es = new EventSource('/api/events'); } catch (e) { setInterval(poll, 1000); return; }
    es.onmessage = (e) => { try { const j = JSON.parse(e.data); if (j && (j.power !== undefined || j.input)) apply(j); else poll(); } catch (x) { poll(); } };
    es.onerror = () => { es.close(); setTimeout(events, 3000); };
  }
  function uiStream() {
    let es; try { es = new EventSource('/ui/stream'); } catch (e) { return; }
    es.onmessage = (e) => { try { onUi(JSON.parse(e.data)); } catch (x) {} };
    es.onerror = () => { es.close(); setTimeout(uiStream, 2000); };
  }
  async function greeting() { try { const g = await api('/greeting'); U.greet = g.state === 'armed' ? (g.name || 'Pappa') : null; postUi(); render(); } catch (e) {} }

  window.SKJOLD_RADIO = { apply, applySettings, onUi, openMenu, closeMenu, render, U, M, SLOT_X,
    setPlugins: p => { plugins = p; render(); }, setLib: l => { lib = l; }, state: () => st };
  if (DEMO) { render(); return; }
  poll(); events(); uiStream(); loadSettings(); loadPlugins(); greeting();
  setInterval(loadSettings, 30000); setInterval(loadPlugins, 10 * 60000); setInterval(poll, 15000);
})();
