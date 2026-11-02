// Skjold – visuell editor for nettsiden (/admin/).
//
// Prinsipp: kildeteksten (HTML-filen slik den ligger i GitHub) er modellen. Siden vises i en iframe (srcdoc,
// skript slått av) der hvert element har fått en midlertidig id som peker til posisjonen i kilden. Ved lagring
// skrives bare de elementene som faktisk er endret på nytt; alt annet kopieres byte for byte fra kilden.
// Angre/gjør om er en liste med hele kilder. Ingen editor-attributter havner i filen.
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];

  // ---------------------------------------------------------------- lagring av nøkkel
  const lager = {
    hent() { try { return sessionStorage.getItem('skjold-admin') || localStorage.getItem('skjold-admin') || ''; } catch { return ''; } },
    sett(v, husk) { try { sessionStorage.setItem('skjold-admin', v); if (husk) localStorage.setItem('skjold-admin', v); } catch {} },
    slett() { try { sessionStorage.removeItem('skjold-admin'); localStorage.removeItem('skjold-admin'); } catch {} },
  };
  let nokkel = '';

  async function api(sti, body) {
    const init = { method: body ? 'POST' : 'GET', headers: { Authorization: 'Bearer ' + nokkel }, cache: 'no-store' };
    if (body) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
    let r;
    try { r = await fetch('/api/admin/' + sti, init); } catch { throw new Error('Fikk ikke kontakt med serveren. Sjekk nettet.'); }
    let data = {}; try { data = await r.json(); } catch {}
    if (r.status === 401) { visInnlogging('Nøkkelen ble ikke godtatt.'); throw new Error('Feil nøkkel.'); }
    if (!r.ok) throw new Error(data.feil || ('Feil ' + r.status));
    return data;
  }

  // ---------------------------------------------------------------- meldinger
  let meldingTimer;
  function melding(tekst, type = '', ms = 5000) {
    const m = $('#melding');
    m.textContent = tekst; m.className = 'melding ' + type; m.hidden = false;
    clearTimeout(meldingTimer);
    if (ms) meldingTimer = setTimeout(() => { m.hidden = true; }, ms);
  }

  function visSkjerm(id) { $$('.skjerm').forEach(s => { s.hidden = s.id !== id; }); }

  // ================================================================ HTML-tokenisering
  const VOID = new Set('area base br col embed hr img input link meta source track wbr'.split(' '));
  const RAA = new Set(['script', 'style', 'textarea', 'title', 'noscript', 'xmp']);
  const P_LUKKES = new Set('address article aside blockquote details div dl fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr main nav ol p pre section table ul'.split(' '));

  // Returnerer { noder: [], rot } der hver node har start/startSlutt/sluttStart/slutt-posisjoner i kilden.
  function tokeniser(src) {
    const noder = [];
    const rot = { id: -1, tag: '#rot', barn: [] };
    const stabel = [rot];
    const lukk = (node, pos, slutt) => { node.sluttStart = pos; node.slutt = slutt; };
    let i = 0;
    const n = src.length;
    while (i < n) {
      const lt = src.indexOf('<', i);
      if (lt < 0) break;
      if (src.startsWith('<!--', lt)) { const e = src.indexOf('-->', lt + 4); i = e < 0 ? n : e + 3; continue; }
      if (src[lt + 1] === '!' || src[lt + 1] === '?') { const e = src.indexOf('>', lt); i = e < 0 ? n : e + 1; continue; }
      if (src[lt + 1] === '/') {
        const m = /^<\/([a-zA-Z][a-zA-Z0-9-]*)[^>]*>/.exec(src.slice(lt, lt + 200));
        if (!m) { i = lt + 1; continue; }
        const tag = m[1].toLowerCase();
        const slutt = lt + m[0].length;
        let k = stabel.length - 1;
        while (k > 0 && stabel[k].tag !== tag) k--;
        if (k > 0) {
          while (stabel.length - 1 > k) { const x = stabel.pop(); lukk(x, lt, lt); }
          lukk(stabel.pop(), lt, slutt);
        }
        i = slutt; continue;
      }
      const mn = /^<([a-zA-Z][a-zA-Z0-9-]*)/.exec(src.slice(lt, lt + 100));
      if (!mn) { i = lt + 1; continue; }
      const tag = mn[1].toLowerCase();
      // Finn slutten av starttaggen (respekter anførselstegn).
      let j = lt + mn[0].length, q = null;
      while (j < n) {
        const c = src[j];
        if (q) { if (c === q) q = null; } else if (c === '"' || c === "'") q = c; else if (c === '>') break;
        j++;
      }
      const startSlutt = j + 1;
      // Implisitte lukkinger som er vanlige i håndskrevet HTML.
      const topp = () => stabel[stabel.length - 1];
      if (P_LUKKES.has(tag) && topp().tag === 'p') lukk(stabel.pop(), lt, lt);
      if (tag === 'li' && topp().tag === 'li') lukk(stabel.pop(), lt, lt);
      if ((tag === 'dt' || tag === 'dd') && (topp().tag === 'dt' || topp().tag === 'dd')) lukk(stabel.pop(), lt, lt);
      if (tag === 'option' && topp().tag === 'option') lukk(stabel.pop(), lt, lt);
      const node = { id: noder.length, tag, start: lt, navnSlutt: lt + mn[0].length, startSlutt, sluttStart: null, slutt: null, barn: [], forelder: topp() };
      noder.push(node);
      topp().barn.push(node);
      if (VOID.has(tag) || src[j - 1] === '/' && tag !== 'a') { node.slutt = startSlutt; node.void = true; i = startSlutt; continue; }
      if (RAA.has(tag)) {
        const re = new RegExp('</' + tag + '\\s*>', 'ig'); re.lastIndex = startSlutt;
        const m = re.exec(src);
        if (m) { node.sluttStart = m.index; node.slutt = m.index + m[0].length; i = node.slutt; }
        else { node.sluttStart = node.slutt = n; i = n; }
        continue;
      }
      stabel.push(node);
      i = startSlutt;
    }
    while (stabel.length > 1) lukk(stabel.pop(), n, n);
    return { noder, rot };
  }

  // Lager iframe-kilden: data-ske-id på hvert element, skript slått av, <base> for relative stier.
  function instrumenter(src, noder, sti) {
    const innsett = [];
    for (const nd of noder) {
      let a = ' data-ske-id="' + nd.id + '"';
      if (nd.tag === 'script') a = ' type="text/x-ske-av"' + a;
      innsett.push([nd.navnSlutt, a]);
      if (nd.tag === 'head') innsett.push([nd.startSlutt, '<base data-ske-ui href="/' + sti.replace(/[^/]*$/, '') + '">']);
    }
    innsett.sort((x, y) => x[0] - y[0]);
    let ut = '', pos = 0;
    for (const [p, t] of innsett) { ut += src.slice(pos, p) + t; pos = p; }
    return ut + src.slice(pos);
  }

  // ================================================================ tilstand
  const S = {
    sider: [], sti: '', sha: '', lagret: '', historikk: [], indeks: -1,
    src: '', noder: [], dok: null, srcId: new WeakMap(), snap: new Map(), upaalitelig: new Set(),
    redigerer: null, foerRedigering: '', blokk: null, bilde: null,
    forhand: new Map(), // sti -> data:-URL for nylig opplastede bilder (vises før utrulling)
  };

  const erUi = n => n.nodeType === 1 && n.hasAttribute('data-ske-ui');
  const skjultAttr = navn => navn === 'contenteditable' || navn === 'spellcheck' || navn.startsWith('data-ske');

  function attrVerdi(el, a) {
    let v = a.value;
    if ((a.name === 'src' || a.name === 'srcset') && v.startsWith('data:')) for (const [p, d] of S.forhand) if (d === v) v = p;
    return v;
  }
  function attrListe(el) {
    const ut = [];
    for (const a of el.attributes) if (!skjultAttr(a.name)) ut.push([a.name, attrVerdi(el, a)]);
    return ut;
  }
  const attrSig = el => JSON.stringify(attrListe(el));
  const barnListe = el => [...el.childNodes].filter(c => !erUi(c));
  function barnSig(el) {
    return JSON.stringify(barnListe(el).map(c => c.nodeType === 1 ? 'e' + (S.srcId.has(c) ? S.srcId.get(c) : '?') : c.nodeType === 3 ? 't' + c.data : c.nodeType === 8 ? 'c' + c.data : 'x'));
  }

  const escTekst = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/ /g, '&nbsp;');
  const escAttr = s => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/ /g, '&nbsp;');

  function nyStartTag(el) {
    return '<' + el.localName + attrListe(el).map(([k, v]) => v === '' ? ' ' + k : ' ' + k + '="' + escAttr(v) + '"').join('') + '>';
  }

  function serNode(c, raa) {
    if (c.nodeType === 3) return raa ? c.data : escTekst(c.data);
    if (c.nodeType === 8) return '<!--' + c.data + '-->';
    if (c.nodeType === 1) return erUi(c) ? '' : ser(c);
    return '';
  }

  // Serialiserer et element: uendrede deler hentes rett fra kilden.
  function ser(el) {
    const id = S.srcId.get(el);
    const nd = id != null ? S.noder[id] : null;
    const snap = id != null ? S.snap.get(id) : null;
    const src = S.src;
    const start = nd && snap && attrSig(el) === snap.attrs ? src.slice(nd.start, nd.startSlutt) : nyStartTag(el);
    if (nd ? nd.void : VOID.has(el.localName)) return start;
    const slutt = nd ? src.slice(nd.sluttStart, nd.slutt) : '</' + el.localName + '>';
    const tag = el.localName;
    if (RAA.has(tag)) {
      const t = el.textContent;
      if (nd && snap && t === snap.tekst) return start + src.slice(nd.startSlutt, nd.sluttStart) + slutt;
      return start + (tag === 'title' || tag === 'textarea' ? escTekst(t) : t) + slutt;
    }
    if (nd && snap && !S.upaalitelig.has(id) && barnSig(el) === snap.barn) {
      let ut = start, pos = nd.startSlutt, k = 0;
      for (const c of barnListe(el)) {
        if (c.nodeType !== 1) continue;
        const b = nd.barn[k++];
        ut += src.slice(pos, b.start) + ser(c);
        pos = b.slutt;
      }
      return ut + src.slice(pos, nd.sluttStart) + slutt;
    }
    return start + barnListe(el).map(c => serNode(c)).join('') + slutt;
  }

  function serialiser() {
    const html = S.dok.documentElement;
    const id = S.srcId.get(html);
    const nd = id != null ? S.noder[id] : null;
    if (!nd) return S.src; // bør ikke skje
    return S.src.slice(0, nd.start) + ser(html) + S.src.slice(nd.slutt);
  }

  // Kloner et element og lar klonene peke til samme kildenode (så uendrede kloner skrives byte for byte).
  function klon(el) {
    const k = el.cloneNode(true);
    const a = [el, ...el.querySelectorAll('*')], b = [k, ...k.querySelectorAll('*')];
    a.forEach((x, i) => { if (S.srcId.has(x)) S.srcId.set(b[i], S.srcId.get(x)); });
    return k;
  }

  // ================================================================ last inn en kilde i iframen
  const ramme = () => $('#ramme');
  let rulling = 0;

  function lastKilde(src, behold) {
    return new Promise(res => {
      if (behold && S.dok) rulling = S.dok.scrollingElement ? S.dok.scrollingElement.scrollTop : 0; else rulling = 0;
      S.redigerer = null; S.blokk = null; S.bilde = null;
      S.src = src; S.dok = null; S.verktoy = null;
      const { noder } = tokeniser(src);
      S.noder = noder;
      const f = ramme();
      f.onload = () => { oppsett(f.contentDocument); res(); };
      f.srcdoc = instrumenter(src, noder, S.sti);
    });
  }

  function oppsett(dok) {
    S.dok = dok;
    S.srcId = new WeakMap(); S.snap = new Map(); S.upaalitelig = new Set();
    for (const el of dok.querySelectorAll('[data-ske-id]')) {
      S.srcId.set(el, +el.getAttribute('data-ske-id'));
      el.removeAttribute('data-ske-id');
    }
    // Vis nylig opplastede bilder fra minnet til siden er rullet ut.
    if (S.forhand.size) for (const el of dok.querySelectorAll('img[src],img[srcset],source[srcset]')) {
      for (const a of ['src', 'srcset']) { const v = el.getAttribute(a); if (v && S.forhand.has(v)) el.setAttribute(a, S.forhand.get(v)); }
    }
    // Kontroller at nettleserens tre stemmer med kildetreet; avvik skrives på nytt i stedet for å kopieres.
    for (const el of dok.querySelectorAll('*')) {
      if (erUi(el)) continue;
      if (!S.srcId.has(el)) { const p = el.parentElement; if (p && S.srcId.has(p)) S.upaalitelig.add(S.srcId.get(p)); continue; }
      const id = S.srcId.get(el), nd = S.noder[id];
      const p = el.parentElement;
      const forv = nd.forelder.id;
      if ((p ? S.srcId.get(p) : -1) !== forv) { S.upaalitelig.add(forv); if (p && S.srcId.has(p)) S.upaalitelig.add(S.srcId.get(p)); }
      const domBarn = barnListe(el).filter(c => c.nodeType === 1).map(c => S.srcId.get(c));
      if (domBarn.length !== nd.barn.length || domBarn.some((x, i) => x !== nd.barn[i].id)) S.upaalitelig.add(id);
      S.snap.set(id, { attrs: attrSig(el), barn: barnSig(el), tekst: RAA.has(nd.tag) ? el.textContent : null });
    }
    // Editorstil og verktøylinje inne i iframen (merket data-ske-ui, tas aldri med i lagringen).
    const stil = dok.createElement('style');
    stil.setAttribute('data-ske-ui', '');
    stil.textContent = `
      [contenteditable]{outline:2px solid #4a8cff!important;outline-offset:3px;cursor:text}
      .ske-boks{position:fixed;pointer-events:none;z-index:2147483646;border-radius:4px}
      .ske-hover{outline:1px dashed #d8cfb4}
      .ske-blokk{outline:2px dashed #e8893a}
      .ske-verktoy{position:fixed;z-index:2147483647;display:flex;gap:2px;background:#111113;border:1px solid #e8893a;border-radius:8px;padding:2px;font:600 12px Sora,system-ui,sans-serif}
      .ske-verktoy button{background:none;border:0;color:#f5f5f2;padding:6px 8px;border-radius:6px;cursor:pointer;font:inherit;min-width:30px}
      .ske-verktoy button:hover{background:#26262a}
      .ske-verktoy .ske-slett{color:#ff5d5d}
      html{cursor:default}`;
    (dok.head || dok.documentElement).appendChild(stil);
    const lag = cls => { const d = dok.createElement('div'); d.setAttribute('data-ske-ui', ''); d.className = 'ske-boks ' + cls; d.hidden = true; dok.body.appendChild(d); return d; };
    S.hoverBoks = lag('ske-hover');
    S.blokkBoks = lag('ske-blokk');
    const vl = dok.createElement('div');
    vl.setAttribute('data-ske-ui', ''); vl.className = 'ske-verktoy'; vl.hidden = true;
    vl.innerHTML = '<button data-blokk="opp" title="Flytt opp">↑</button><button data-blokk="ned" title="Flytt ned">↓</button><button data-blokk="kopier" title="Lag en kopi under">Kopier</button><button data-blokk="slett" class="ske-slett" title="Slett blokken">Slett</button><button data-blokk="ytre" title="Velg blokken utenfor">Ytre</button>';
    dok.body.appendChild(vl);
    S.verktoy = vl;

    // Hendelser fra et dokument som er byttet ut (etter angre/innlasting) ignoreres.
    const aktiv = f => (...a) => { if (S.dok === dok) f(...a); };
    dok.addEventListener('mouseover', aktiv(e => {
      const t = tekstMaal(e.target) || bildeMaal(e.target);
      plasser(S.hoverBoks, t && t !== S.redigerer ? t : null);
    }));
    dok.addEventListener('mouseleave', aktiv(() => plasser(S.hoverBoks, null)));
    dok.addEventListener('click', e => { if (S.dok === dok) klikk(e); else e.preventDefault(); }, true);
    dok.addEventListener('submit', e => e.preventDefault(), true);
    dok.addEventListener('keydown', aktiv(tast), true);
    dok.addEventListener('paste', aktiv(lim), true);
    dok.addEventListener('focusout', aktiv(e => { if (e.target === S.redigerer) setTimeout(() => { if (S.dok === dok && S.redigerer === e.target && dok.activeElement !== e.target) avsluttRedigering(); }, 0); }));
    dok.defaultView.addEventListener('scroll', aktiv(oppdaterBokser), { passive: true });
    dok.defaultView.addEventListener('resize', aktiv(oppdaterBokser));
    dok.addEventListener('keydown', aktiv(snarveier));
    if (rulling && dok.scrollingElement) dok.scrollingElement.scrollTop = rulling;
    visPanel();
  }

  // ================================================================ hva kan klikkes
  const TEKST = 'h1,h2,h3,h4,h5,h6,p,li,dt,dd,figcaption,blockquote,td,th,label,button,summary,caption,.k,.h,.p,.mer';
  const BLOKK_INNI = 'div,p,section,article,ul,ol,dl,picture,img,figure,h1,h2,h3,h4,h5,h6,table,form,header,footer,nav,svg,video,iframe,input,select,textarea';
  const BLOKKER = 'section,.seksjon,.flis,.kilde,.rad,a.produkt,figure,article';

  function tekstMaal(t) {
    if (!t || t.nodeType !== 1 || erUi(t) || t.closest('[data-ske-ui]')) return null;
    if (t.closest('svg')) t = t.closest('svg').parentElement;
    const ok = el => el && el !== S.dok.body && el !== S.dok.documentElement && !el.querySelector(BLOKK_INNI) && el.textContent.trim() !== '';
    const c = t.closest(TEKST);
    if (ok(c)) return c;
    const a = t.closest('a');
    if (ok(a)) return a;
    if (ok(t) && [...t.childNodes].every(x => x.nodeType === 3 || /^(b|i|strong|em|a|br|span|small|code|sup|sub)$/i.test(x.nodeName))) return t;
    return null;
  }
  const bildeMaal = t => (t && t.nodeType === 1 && !t.closest('[data-ske-ui]')) ? (t.localName === 'img' ? t : t.localName === 'picture' ? t.querySelector('img') : null) : null;

  function plasser(boks, el) {
    if (!boks) return;
    if (!el || !el.isConnected) { boks.hidden = true; return; }
    const r = el.getBoundingClientRect();
    Object.assign(boks.style, { left: r.left - 3 + 'px', top: r.top - 3 + 'px', width: r.width + 6 + 'px', height: r.height + 6 + 'px' });
    boks.hidden = false;
  }
  function oppdaterBokser() {
    plasser(S.blokkBoks, S.blokk);
    const v = S.verktoy;
    if (!v) return;
    if (!S.blokk || !S.blokk.isConnected) { v.hidden = true; return; }
    const r = S.blokk.getBoundingClientRect();
    v.hidden = false;
    const h = v.offsetHeight || 32, w = v.offsetWidth || 200;
    const vw = S.dok.documentElement.clientWidth;
    v.style.top = Math.max(4, r.top - h - 6) + 'px';
    v.style.left = Math.max(4, Math.min(r.right - w, vw - w - 4)) + 'px';
  }

  // ================================================================ klikk og redigering
  function klikk(e) {
    const t = e.target;
    const knapp = t.closest && t.closest('.ske-verktoy button');
    if (knapp) { e.preventDefault(); e.stopPropagation(); blokkHandling(knapp.dataset.blokk); return; }
    if (S.redigerer && S.redigerer.contains(t)) { e.preventDefault(); return; }
    e.preventDefault(); e.stopPropagation();
    const img = bildeMaal(t);
    if (img) { avsluttRedigering(); velgBilde(img); velgBlokk(img.closest(BLOKKER)); return; }
    const tm = tekstMaal(t);
    if (tm) { startRedigering(tm); velgBlokk(tm.closest(BLOKKER)); return; }
    avsluttRedigering(); S.bilde = null;
    velgBlokk(t.closest && t.closest(BLOKKER));
  }

  function startRedigering(el) {
    if (S.redigerer === el) return;
    avsluttRedigering();
    S.bilde = null;
    S.redigerer = el;
    S.foerRedigering = barnSig(el) + '\u0000' + el.innerHTML;
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('spellcheck', 'true');
    plasser(S.hoverBoks, null);
    el.focus({ preventScroll: true });
    visPanel();
  }

  function avsluttRedigering() {
    const el = S.redigerer;
    if (!el) return;
    S.redigerer = null;
    el.removeAttribute('contenteditable');
    el.removeAttribute('spellcheck');
    rensInline(el);
    const naa = barnSig(el) + '\u0000' + el.innerHTML;
    if (naa !== S.foerRedigering) registrer();
    visPanel();
  }

  // Fjerner formatering nettleseren legger inn (span/font/div/style) i nye elementer; beholder b/i/strong/em/a/br.
  function rensInline(rotEl) {
    const lov = /^(b|strong|i|em|a|br)$/;
    for (const el of [...rotEl.querySelectorAll('*')].reverse()) {
      if (S.srcId.has(el)) continue; // fantes i kilden fra før – la stå
      el.removeAttribute('style');
      for (const a of [...el.attributes]) if (!(el.localName === 'a' && a.name === 'href')) el.removeAttribute(a.name);
      if (el.localName === 'div' || el.localName === 'p') { el.before(S.dok.createElement('br')); el.replaceWith(...el.childNodes); continue; }
      if (!lov.test(el.localName)) el.replaceWith(...el.childNodes);
    }
    rotEl.normalize();
  }

  function tast(e) {
    const el = S.redigerer;
    if (!el || !el.contains(e.target)) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) S.dok.execCommand('insertLineBreak');
      else { el.blur(); avsluttRedigering(); }
    } else if (e.key === 'Escape') { e.preventDefault(); el.blur(); avsluttRedigering(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); lagLenke(); }
  }
  function lim(e) {
    if (!S.redigerer) return;
    e.preventDefault();
    const t = (e.clipboardData || window.clipboardData).getData('text/plain').replace(/\s*\n\s*/g, ' ');
    S.dok.execCommand('insertText', false, t);
  }
  function snarveier(e) {
    if (S.redigerer) return; // tekstfeltets egen angre gjelder mens man skriver
    globalSnarvei(e);
  }
  function globalSnarvei(e) {
    if (!(e.ctrlKey || e.metaKey)) return;
    const k = e.key.toLowerCase();
    if (k === 'z' && !e.shiftKey) { e.preventDefault(); angre(); }
    else if ((k === 'z' && e.shiftKey) || k === 'y') { e.preventDefault(); gjenta(); }
    else if (k === 's') { e.preventDefault(); lagre(); }
  }

  function lagLenke() {
    if (!S.redigerer) return;
    const url = prompt('Lenke til (f.eks. /s1/ eller https://…):', '/');
    if (!url) return;
    if (/^\s*javascript:/i.test(url)) { melding('Ugyldig lenke.', 'feil'); return; }
    S.redigerer.focus();
    S.dok.execCommand('createLink', false, url.trim());
  }

  // ================================================================ bilder
  function velgBilde(img) { S.bilde = img; visPanel(); }

  async function byttBilde(fil) {
    const img = S.bilde;
    if (!img || !fil) return;
    if (fil.size > 5 * 1024 * 1024) { melding('Bildet er større enn 5 MB. Gjør det mindre først.', 'feil'); return; }
    if (!/^image\/(png|jpeg|webp|gif|avif)$/.test(fil.type)) { melding('Bare PNG, JPG, WebP, GIF eller AVIF.', 'feil'); return; }
    const dataUrl = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(fil); });
    const dim = await new Promise(res => { const i = new Image(); i.onload = () => res([i.naturalWidth, i.naturalHeight]); i.onerror = () => res(null); i.src = dataUrl; });
    melding('Laster opp bildet …', '', 0);
    let svar;
    try { svar = await api('upload', { name: fil.name, base64: dataUrl.split(',')[1] }); }
    catch (e) { melding('Opplasting feilet: ' + e.message, 'feil'); return; }
    S.forhand.set(svar.path, dataUrl);
    img.setAttribute('src', dataUrl);
    if (img.hasAttribute('srcset')) img.setAttribute('srcset', dataUrl);
    if (dim && img.hasAttribute('width') && img.hasAttribute('height')) { img.setAttribute('width', dim[0]); img.setAttribute('height', dim[1]); }
    const pic = img.parentElement && img.parentElement.localName === 'picture' ? img.parentElement : null;
    if (pic) for (const s of pic.querySelectorAll('source')) { s.setAttribute('srcset', dataUrl); if (s.hasAttribute('type')) s.setAttribute('type', fil.type); }
    registrer();
    visPanel();
    melding('Bildet er lastet opp. Trykk «Lagre og publiser» for å bruke det på siden.', 'ok');
  }

  // ================================================================ blokker
  function velgBlokk(b) {
    S.blokk = b && b !== S.dok.body ? b : null;
    oppdaterBokser();
    visPanel();
  }
  const synligSosken = (el, retning) => { let s = el[retning]; while (s && erUi(s)) s = s[retning]; return s; };
  const erMellomrom = n => n && n.nodeType === 3 && !n.data.trim();

  function blokkHandling(h) {
    const b = S.blokk;
    if (!b) return;
    avsluttRedigering();
    const p = b.parentNode;
    if (h === 'ytre') { velgBlokk(p.closest && p.closest(BLOKKER)); return; }
    if (h === 'opp' || h === 'ned') {
      const annen = synligSosken(b, h === 'opp' ? 'previousElementSibling' : 'nextElementSibling');
      if (!annen) { melding(h === 'opp' ? 'Blokken er allerede øverst.' : 'Blokken er allerede nederst.'); return; }
      const merke = S.dok.createTextNode('');
      p.replaceChild(merke, annen); p.replaceChild(annen, b); p.replaceChild(b, merke);
    } else if (h === 'kopier') {
      const k = klon(b);
      const ws = erMellomrom(b.previousSibling) ? b.previousSibling.cloneNode() : null;
      b.after(k);
      if (ws) b.after(ws);
      S.blokk = k;
    } else if (h === 'slett') {
      if (erMellomrom(b.previousSibling)) b.previousSibling.remove();
      b.remove();
      S.blokk = null;
    }
    registrer();
    oppdaterBokser();
    visPanel();
    if (S.blokk) S.blokk.scrollIntoView({ block: 'nearest' });
  }

  // ================================================================ sideinfo (head)
  function metaEl(navn) {
    const d = S.dok;
    if (navn === 'title') return d.querySelector('head > title');
    return d.querySelector(navn.startsWith('og:') ? 'meta[property="' + navn + '"]' : 'meta[name="' + navn + '"]');
  }
  function fyllMeta() {
    for (const inp of $$('[data-meta]')) {
      const el = metaEl(inp.dataset.meta);
      inp.disabled = !el;
      inp.value = el ? (inp.dataset.meta === 'title' ? el.textContent : el.getAttribute('content') || '') : '';
      inp.placeholder = el ? '' : '(finnes ikke på denne siden)';
    }
  }
  function settMeta(inp) {
    const el = metaEl(inp.dataset.meta);
    if (!el) return;
    if (inp.dataset.meta === 'title') { if (el.textContent !== inp.value) el.textContent = inp.value; }
    else if (el.getAttribute('content') !== inp.value) el.setAttribute('content', inp.value);
    registrer();
  }

  // ================================================================ angre / historikk / lagring
  function registrer() {
    if (!S.dok) return;
    const s = serialiser();
    if (s === S.historikk[S.indeks]) return;
    S.historikk = S.historikk.slice(0, S.indeks + 1);
    S.historikk.push(s);
    if (S.historikk.length > 100) S.historikk.shift();
    S.indeks = S.historikk.length - 1;
    oppdaterKnapper();
  }
  const naaKilde = () => S.historikk[S.indeks];
  const ulagret = () => S.historikk.length > 0 && naaKilde() !== S.lagret;

  async function angre() {
    avsluttRedigering();
    if (S.indeks <= 0) return;
    S.indeks--; oppdaterKnapper();
    await lastKilde(naaKilde(), true);
  }
  async function gjenta() {
    avsluttRedigering();
    if (S.indeks >= S.historikk.length - 1) return;
    S.indeks++; oppdaterKnapper();
    await lastKilde(naaKilde(), true);
  }
  function oppdaterKnapper() {
    $('#angre').disabled = S.indeks <= 0;
    $('#gjenta').disabled = S.indeks >= S.historikk.length - 1;
    $('#lagre').disabled = !ulagret();
    $('#lagre').textContent = ulagret() ? 'Lagre og publiser' : 'Publisert';
  }

  let lagrer = false;
  async function lagre() {
    if (!$('#rafl').hidden) { if (!brukRaa()) return; }
    avsluttRedigering();
    if (!ulagret() || lagrer) return;
    lagrer = true;
    $('#lagre').disabled = true; $('#lagre').textContent = 'Publiserer …';
    const html = naaKilde();
    try {
      const svar = await api('page', { path: S.sti, html, sha: S.sha, message: 'Nettside: oppdater ' + S.sti + ' (redigert i admin)' });
      S.sha = svar.sha || S.sha;
      S.lagret = html;
      melding('Publisert – siden er oppdatert om ca. 1 minutt.', 'ok', 8000);
    } catch (e) {
      melding('Kunne ikke publisere: ' + e.message, 'feil', 10000);
    } finally { lagrer = false; oppdaterKnapper(); }
  }

  // ================================================================ panel
  function visPanel() {
    const red = S.redigerer, img = S.bilde, b = S.blokk;
    const meta = !$('#panel-meta').hidden && S.visMeta;
    $('#panel-tekst').hidden = !red;
    const lenkeEl = (red && (red.closest('a') || (red.querySelector('a') && red.querySelectorAll('a').length === 1 ? red.querySelector('a') : null))) || (b && b.localName === 'a' ? b : null) || (img && img.closest('a'));
    S.lenkeEl = lenkeEl || null;
    $('#panel-href').hidden = !lenkeEl;
    if (lenkeEl && document.activeElement !== $('#href')) $('#href').value = lenkeEl.getAttribute('href') || '';
    $('#panel-bilde').hidden = !img;
    if (img) { $('#bilde-vis').src = img.currentSrc || img.src; if (document.activeElement !== $('#alt')) $('#alt').value = img.getAttribute('alt') || ''; $('#bilde-fil').value = ''; }
    $('#panel-blokk').hidden = !b;
    if (b) $('#blokk-navn').textContent = '‹' + b.localName + (b.classList.length ? '.' + [...b.classList].join('.') : '') + '›';
    $('#panel-meta').hidden = !S.visMeta;
    if (S.visMeta && !meta) fyllMeta();
    $('#panel-tom').hidden = !!(red || img || b || S.visMeta);
  }

  // ================================================================ rå HTML
  function visFane(raa) {
    if (raa) { avsluttRedigering(); $('#raa').value = naaKilde(); }
    else if (!$('#rafl').hidden && $('#raa').value !== naaKilde()) { if (!brukRaa()) return; }
    $('#rafl').hidden = !raa;
    $('#fane-html').classList.toggle('aktiv', raa);
    $('#fane-visuell').classList.toggle('aktiv', !raa);
  }
  function brukRaa() {
    const v = $('#raa').value;
    if (v === naaKilde()) return true;
    if (!/<html[\s>]/i.test(v) || !/<\/html>/i.test(v)) { melding('HTML-en mangler <html> … </html>.', 'feil'); return false; }
    S.historikk = S.historikk.slice(0, S.indeks + 1);
    S.historikk.push(v); S.indeks++;
    oppdaterKnapper();
    lastKilde(v, true);
    return true;
  }

  // ================================================================ sider
  const visningsUrl = p => '/' + p.replace(/(^|\/)index\.html$/, '$1');

  async function lastSider() {
    const { pages } = await api('pages');
    S.sider = pages;
    const no = $('#liste-no'), en = $('#liste-en');
    no.textContent = ''; en.textContent = '';
    for (const p of pages) {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.type = 'button';
      const navn = document.createElement('span');
      navn.textContent = visningsUrl(p);
      const sti = document.createElement('span'); sti.className = 'sti'; sti.textContent = p;
      b.append(navn, sti);
      b.addEventListener('click', () => aapne(p));
      li.append(b);
      (p.startsWith('en/') ? en : no).append(li);
    }
    const sel = $('#ny-fra'); sel.textContent = '';
    for (const p of pages) { const o = document.createElement('option'); o.value = p; o.textContent = visningsUrl(p); sel.append(o); }
  }

  async function aapne(p) {
    melding('Henter siden …', '', 0);
    let d;
    try { d = await api('page?path=' + encodeURIComponent(p)); } catch (e) { melding(e.message, 'feil'); return; }
    S.sti = p; S.sha = d.sha; S.lagret = d.html; S.historikk = [d.html]; S.indeks = 0; S.visMeta = false;
    $('#sidenavn').textContent = visningsUrl(p);
    $('#se').href = visningsUrl(p);
    visSkjerm('editor');
    visFane(false);
    oppdaterKnapper();
    await lastKilde(d.html, false);
    $('#melding').hidden = true;
    try { history.replaceState(null, '', '#' + p); } catch {}
  }

  function tilListe() {
    avsluttRedigering();
    if (ulagret() && !confirm('Du har endringer som ikke er publisert. Vil du forkaste dem?')) return;
    S.historikk = []; S.indeks = -1;
    visSkjerm('sider');
    try { history.replaceState(null, '', '#'); } catch {}
  }

  function normaliserNySti(v) {
    let p = String(v || '').trim().toLowerCase().replace(/^https?:\/\/[^/]+/, '').replace(/^\/+/, '');
    if (!p) return '';
    if (!/\.html$/.test(p)) p = p.replace(/\/?$/, '/') + 'index.html';
    return p;
  }

  // ================================================================ innlogging
  function visInnlogging(feil) {
    nokkel = ''; lager.slett();
    visSkjerm('innlogging');
    $('#loggfeil').textContent = feil || '';
    $('#nokkel').focus();
  }

  async function startMedNokkel(k, husk) {
    nokkel = k;
    try {
      const svar = await api('ping');
      lager.sett(k, husk);
      if (!svar.github) melding('GITHUB_TOKEN er ikke satt i Cloudflare – du kan ikke publisere ennå.', 'feil', 10000);
      visSkjerm('sider');
      await lastSider();
      const hash = decodeURIComponent(location.hash.slice(1));
      if (hash && S.sider.includes(hash)) aapne(hash);
    } catch (e) {
      if (!$('#innlogging').hidden) $('#loggfeil').textContent = e.message;
      else melding(e.message, 'feil');
    }
  }

  // ================================================================ koble opp
  function init() {
    $('#logginn').addEventListener('submit', e => { e.preventDefault(); $('#loggfeil').textContent = ''; startMedNokkel($('#nokkel').value.trim(), $('#husk').checked); });
    $('#loggut').addEventListener('click', () => visInnlogging(''));
    $('#tilbake').addEventListener('click', tilListe);
    $('#angre').addEventListener('click', angre);
    $('#gjenta').addEventListener('click', gjenta);
    $('#lagre').addEventListener('click', lagre);
    $('#fane-visuell').addEventListener('click', () => visFane(false));
    $('#fane-html').addEventListener('click', () => visFane(true));
    $('#raa-bruk').addEventListener('click', () => { if (brukRaa()) visFane(false); });
    $('#sideinfo').addEventListener('click', () => { avsluttRedigering(); S.visMeta = !S.visMeta; visPanel(); });
    $('#meta-lukk').addEventListener('click', () => { S.visMeta = false; visPanel(); });
    for (const inp of $$('[data-meta]')) inp.addEventListener('change', () => settMeta(inp));
    // Tekstknapper: mousedown + preventDefault så markeringen i iframen beholdes.
    const tekstKnapp = (sel, f) => { const k = $(sel); k.addEventListener('mousedown', e => e.preventDefault()); k.addEventListener('click', f); };
    tekstKnapp('#fet', () => S.redigerer && S.dok.execCommand('bold'));
    tekstKnapp('#kursiv', () => S.redigerer && S.dok.execCommand('italic'));
    tekstKnapp('#lenke', lagLenke);
    tekstKnapp('#fjernlenke', () => S.redigerer && S.dok.execCommand('unlink'));
    tekstKnapp('#ferdig', () => { avsluttRedigering(); S.blokk = null; oppdaterBokser(); visPanel(); });
    $('#href').addEventListener('change', () => {
      const el = S.lenkeEl; const v = $('#href').value.trim();
      if (!el || /^\s*javascript:/i.test(v)) return;
      const var_ = !!S.redigerer;
      if (var_) avsluttRedigering();
      el.setAttribute('href', v); registrer();
    });
    $('#alt').addEventListener('change', () => { if (S.bilde) { S.bilde.setAttribute('alt', $('#alt').value); registrer(); } });
    $('#bilde-fil').addEventListener('change', e => byttBilde(e.target.files[0]));
    $$('#panel-blokk [data-blokk]').forEach(b => b.addEventListener('click', () => blokkHandling(b.dataset.blokk)));
    document.addEventListener('keydown', e => { if (!e.target.closest('input,textarea')) globalSnarvei(e); else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); lagre(); } });
    window.addEventListener('beforeunload', e => { if (ulagret()) { e.preventDefault(); e.returnValue = ''; } });

    // Ny side
    const dlg = $('#ny-dialog');
    $('#nyside').addEventListener('click', () => { $('#ny-feil').textContent = ''; $('#ny-til').value = ''; dlg.showModal(); });
    $('#ny-skjema').addEventListener('submit', async e => {
      if (e.submitter && e.submitter.value === 'avbryt') return;
      e.preventDefault();
      const til = normaliserNySti($('#ny-til').value);
      if (!/^[a-z0-9][a-z0-9._\-/]*\.html$/.test(til) || til.includes('..') || /^(admin|functions)\//.test(til)) { $('#ny-feil').textContent = 'Bruk bare a–z, 0–9 og bindestrek, f.eks. «kampanje» eller «en/campaign».'; return; }
      if (S.sider.includes(til)) { $('#ny-feil').textContent = 'Siden finnes allerede.'; return; }
      $('#ny-lag').disabled = true;
      try {
        await api('new', { from: $('#ny-fra').value, to: til });
        dlg.close();
        await lastSider();
        if (!S.sider.includes(til)) S.sider.push(til);
        melding('Siden er laget. Husk å endre teksten og tittelen før du publiserer.', 'ok');
        await aapne(til);
      } catch (err) { $('#ny-feil').textContent = err.message; }
      finally { $('#ny-lag').disabled = false; }
    });

    const k = lager.hent();
    if (k) startMedNokkel(k, false); else visInnlogging('');
  }

  // Til testing i nettleserkonsollen.
  window.skjoldEditor = { S, serialiser, tokeniser };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
