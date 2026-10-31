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
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('synlig'); io.unobserve(e.target); } });
      }, { threshold: 0.12 });
      els.forEach(function (el) { io.observe(el); });
    } else {
      els.forEach(function (el) { el.classList.add('synlig'); });
    }

    var zooms = document.querySelectorAll('[data-zoom]');
    var boxes = document.querySelectorAll('[data-scrolly]');
    var tick = function () {
      var vh = innerHeight;
      zooms.forEach(function (el) {
        var r = el.getBoundingClientRect();
        var p = Math.max(0, Math.min(1, 1 - (r.top + r.height * 0.3) / vh));
        el.style.transform = 'scale(' + (0.86 + 0.14 * p).toFixed(4) + ')';
        el.style.opacity = String(0.35 + 0.65 * Math.min(1, p * 1.6));
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
