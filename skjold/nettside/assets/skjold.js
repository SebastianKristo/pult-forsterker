// Skjold nettside: scroll-reveal, hero-zoom, sticky bildesekvens, USB-demo og interesseskjema.
// Uten JS (eller med prefers-reduced-motion) står <html class="statisk"> og alt vises uten animasjon.
(function () {
  'use strict';
  var root = document.documentElement;
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!reduce) {
    root.classList.remove('statisk');
    root.classList.add('fx');

    // Reveal: 0,9 s cubic-bezier(.2,.7,.2,1), translateY 28px -> 0
    var els = document.querySelectorAll('[data-reveal]');
    els.forEach(function (el) { el.style.setProperty('--d', (+el.getAttribute('data-reveal') || 0) + 'ms'); });
    // Fliser, kort og rader i samme rutenett kommer etter hverandre (70 ms mellom), ikke alle på én gang
    document.querySelectorAll('.fliser,.kort-rutenett,.kilder,.integ,.steg,.manualer,.kjede').forEach(function (g) {
      var barn = g.children;
      for (var i = 0; i < barn.length; i++) {
        if (!barn[i].hasAttribute('data-reveal')) { barn[i].setAttribute('data-reveal', '0'); }
        barn[i].style.setProperty('--d', Math.min(i, 7) * 70 + 'ms');
      }
    });
    els = document.querySelectorAll('[data-reveal]');
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('synlig'); io.unobserve(e.target); } });
      }, { threshold: 0.12 });
      els.forEach(function (el) { io.observe(el); });
    } else {
      els.forEach(function (el) { el.classList.add('synlig'); });
    }

    // Produktbildet i toppen av produktsidene har egen inngang (CSS) og skal ikke dempes av rulling
    var zooms = Array.prototype.filter.call(document.querySelectorAll('[data-zoom]'), function (el) { return !el.closest('.p-hero'); });
    var boxes = document.querySelectorAll('[data-scrolly]');
    var tick = function () {
      var vh = innerHeight;
      zooms.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) { return; }
        // full styrke når bildet er godt inne i vinduet (toppen ca. 70 % ned), ikke først helt oppe ved menyen
        var p = Math.max(0, Math.min(1, (vh - r.top) / (vh * 0.42)));
        el.style.transform = 'scale(' + (0.94 + 0.06 * p).toFixed(4) + ')';
        el.style.opacity = String(Math.min(1, 0.55 + 0.45 * p * 1.4));
      });
      boxes.forEach(function (box) {
        var r = box.getBoundingClientRect();
        var frames = box.querySelectorAll('[data-frame]');
        var n = frames.length, span = r.height - vh;
        var p = Math.max(0, Math.min(0.9999, -r.top / Math.max(1, span)));
        var i = Math.floor(p * n);
        frames.forEach(function (f, j) { f.classList.toggle('paa', j === i); f.classList.toggle('forbi', j < i); });
        box.querySelectorAll('[data-cap]').forEach(function (c, j) {
          c.classList.toggle('paa', j === i);
          c.style.transform = j === i ? '' : 'translateY(' + (j < i ? -16 : 16) + 'px)';
          c.setAttribute('aria-hidden', j === i ? 'false' : 'true');
        });
        box.querySelectorAll('[data-dot]').forEach(function (d, j) { d.classList.toggle('paa', j === i); });
      });
    };
    var raf = 0;
    addEventListener('scroll', function () { cancelAnimationFrame(raf); raf = requestAnimationFrame(tick); }, { passive: true });
    addEventListener('resize', tick);
    tick();
  }

  // Meny på smale skjermer: en knapp åpner hele menyen som et panel. (Uten JS ruller lenkene sidelengs som før.)
  var nav = document.querySelector('header.nav');
  var lenker = nav && nav.querySelector('.nav-lenker');
  if (nav && lenker) {
    var en0 = /^en\b/i.test(root.lang || '');
    var mk = document.createElement('button');
    mk.type = 'button'; mk.className = 'meny-knapp';
    mk.setAttribute('aria-expanded', 'false'); mk.setAttribute('aria-controls', 'hovedmeny');
    mk.setAttribute('aria-label', en0 ? 'Menu' : 'Meny');
    mk.innerHTML = '<span aria-hidden="true"></span>';
    lenker.id = lenker.id || 'hovedmeny';
    Array.prototype.forEach.call(lenker.children, function (a, i) { a.style.setProperty('--i', i); });
    nav.querySelector('.nav-inn').appendChild(mk);
    root.classList.add('har-meny');
    var sett = function (aapen) {
      nav.classList.toggle('aapen', aapen);
      mk.setAttribute('aria-expanded', aapen ? 'true' : 'false');
      root.classList.toggle('meny-laast', aapen);
    };
    mk.addEventListener('click', function () { sett(!nav.classList.contains('aapen')); });
    lenker.addEventListener('click', function (e) { if (e.target.closest('a')) { sett(false); } });
    addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('aapen')) { sett(false); mk.focus(); } });
    if (window.matchMedia) {
      var mq = matchMedia('(min-width:981px)');
      var lukk = function () { if (mq.matches) { sett(false); } };
      if (mq.addEventListener) { mq.addEventListener('change', lukk); } else if (mq.addListener) { mq.addListener(lukk); }
    }
  }

  // 3D-modell: hent visningsprogrammet (ca. 1 MB) først når modellen nærmer seg skjermen
  var mv = document.querySelector('model-viewer');
  if (mv) {
    var hentMv = function () {
      var s = document.createElement('script');
      s.type = 'module'; s.src = '/assets/vendor/model-viewer-4.1.0/model-viewer.min.js';
      document.head.appendChild(s);
    };
    if ('IntersectionObserver' in window) {
      var mio = new IntersectionObserver(function (es) {
        if (es.some(function (e) { return e.isIntersecting; })) { mio.disconnect(); hentMv(); }
      }, { rootMargin: '900px 0px' });
      mio.observe(mv);
    } else { hentMv(); }
  }

  // USB-bryter-demo (S1)
  var usb = document.querySelector('[data-usb]');
  if (usb) {
    var btn = usb.querySelector('button');
    var hosts = usb.querySelectorAll('.vert');
    btn.addEventListener('click', function () {
      var pc = usb.classList.toggle('pc');
      hosts[0].classList.toggle('paa', !pc);
      hosts[1].classList.toggle('paa', pc);
      btn.setAttribute('aria-pressed', pc ? 'true' : 'false');
    });
  }

  // Interesseskjema: sender JSON med fetch. Uten JS poster skjemaet vanlig og får /takk/ (eller /en/thanks/) tilbake.
  var en = /^en\b/i.test(root.lang || '');
  var T = en
    ? { bad: 'Enter a name and a valid email.', err: 'Could not send. Try again, or send an email.', sender: 'Sending …', mange: 'Too many attempts. Wait a little and try again.' }
    : { bad: 'Skriv inn navn og en gyldig e-post.', err: 'Det gikk ikke å sende. Prøv igjen, eller send en e-post.', sender: 'Sender …', mange: 'For mange forsøk. Vent litt og prøv igjen.' };
  var form = document.querySelector('form[data-interesse]');
  if (form && window.fetch) {
    var feil = form.querySelector('.feil');
    var knapp = form.querySelector('button[type=submit]');
    var tekst = knapp.textContent;
    var re = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      if (knapp.disabled) return;
      var fd = new FormData(form);
      var body = {};
      fd.forEach(function (v, k) { body[k] = typeof v === 'string' ? v.trim() : ''; });
      if (!body.navn || !re.test(body.epost || '')) { feil.textContent = T.bad; return; }
      feil.textContent = '';
      knapp.disabled = true; knapp.textContent = T.sender;
      body.spraak = en ? 'en' : 'no'; body.lang = body.spraak; body.side = location.pathname;
      fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(body) })
        .then(function (r) { if (!r.ok) throw r.status; return r.json(); })
        .then(function () {
          var t = document.getElementById('interesse-takk');
          form.hidden = true; t.hidden = false; t.focus();
        })
        .catch(function (s) {
          feil.textContent = s === 429 ? T.mange : T.err;
          knapp.disabled = false; knapp.textContent = tekst;
        });
    });
    form.addEventListener('input', function () { if (feil.textContent && feil.textContent === T.bad) feil.textContent = ''; });
  }
})();
