// Skjold nettside: scroll-reveal, hero-zoom, sticky bildesekvens, forsidens stolpeteppe og produktvelger,
// lys som følger pekeren, USB-demo og interesseskjema.
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
    var navEl = document.querySelector('header.nav');
    var scene = document.querySelector('[data-scene] .f-scene-ramme');
    var tick = function () {
      var vh = innerHeight;
      // Leselinja i menyen
      if (navEl) {
        var maks = root.scrollHeight - vh;
        navEl.style.setProperty('--les', maks > 0 ? Math.min(1, scrollY / maks).toFixed(4) : '0');
      }
      // Familiebildet vokser fra 88 % til full bredde mens det kommer inn
      if (scene) {
        var sr = scene.getBoundingClientRect();
        var sp = Math.max(0, Math.min(1, (vh - sr.top) / (vh * 0.75)));
        scene.style.setProperty('--s', (0.88 + 0.12 * sp).toFixed(4));
      }
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

    // Pekeren: kort lyser der pekeren er, knapper trekkes svakt mot den, og produktbildet i toppen vipper litt
    if (matchMedia('(hover:hover) and (pointer:fine)').matches) {
      var LYS = '.kort,.flis,.integ>div,.ledd,.manualer a,.steg>div,.f-b';
      document.addEventListener('pointermove', function (e) {
        var k = e.target.closest && e.target.closest(LYS);
        if (k) {
          var r = k.getBoundingClientRect();
          k.style.setProperty('--mx', (e.clientX - r.left) + 'px');
          k.style.setProperty('--my', (e.clientY - r.top) + 'px');
        }
      }, { passive: true });
      document.querySelectorAll('.knapp').forEach(function (b) {
        b.addEventListener('pointermove', function (e) {
          var r = b.getBoundingClientRect();
          b.style.setProperty('--tx', ((e.clientX - r.left - r.width / 2) * 0.18).toFixed(1) + 'px');
          b.style.setProperty('--ty', ((e.clientY - r.top - r.height / 2) * 0.3).toFixed(1) + 'px');
        });
        b.addEventListener('pointerleave', function () { b.style.setProperty('--tx', '0px'); b.style.setProperty('--ty', '0px'); });
      });
      var helt = document.querySelector('.p-hero'), heltBilde = helt && helt.querySelector('picture');
      if (heltBilde) {
        helt.addEventListener('pointermove', function (e) {
          var r = helt.getBoundingClientRect();
          heltBilde.style.setProperty('--rx', (((e.clientX - r.left) / r.width - 0.5) * 7).toFixed(2) + 'deg');
          heltBilde.style.setProperty('--ry', (-((e.clientY - r.top) / r.height - 0.5) * 5).toFixed(2) + 'deg');
        });
        helt.addEventListener('pointerleave', function () { heltBilde.style.setProperty('--rx', '0deg'); heltBilde.style.setProperty('--ry', '0deg'); });
      }
      var sceneBilde = scene && scene.querySelector('img');
      if (sceneBilde) {
        scene.addEventListener('pointermove', function (e) {
          var r = scene.getBoundingClientRect();
          sceneBilde.style.setProperty('--px', (-((e.clientX - r.left) / r.width - 0.5) * 18).toFixed(1) + 'px');
          sceneBilde.style.setProperty('--py', (-((e.clientY - r.top) / r.height - 0.5) * 12).toFixed(1) + 'px');
        });
        scene.addEventListener('pointerleave', function () { sceneBilde.style.setProperty('--px', '0px'); sceneBilde.style.setProperty('--py', '0px'); });
      }
    }
  }

  // Forsiden: stolpeteppet i toppen. Stolpene fra logoen henger ned fra menyen, beveger seg rolig som et
  // lydnivå og strekker seg mot pekeren. Den midterste er gull. Med redusert bevegelse tegnes ett stille bilde.
  var felt = document.querySelector('canvas[data-felt]');
  if (felt && felt.getContext) {
    var cx = felt.getContext('2d'), fw = 0, fh = 0, n = 0, mus = { x: -1, y: 0, k: 0 }, synlig = true, fraf = 0;
    var maal = function () {
      var dpr = Math.min(2, window.devicePixelRatio || 1), r = felt.getBoundingClientRect();
      fw = r.width; fh = r.height;
      felt.width = Math.round(fw * dpr); felt.height = Math.round(fh * dpr);
      cx.setTransform(dpr, 0, 0, dpr, 0, 0);
      n = Math.max(15, Math.floor(fw / 22)); if (n % 2 === 0) { n++; }
    };
    var tegn = function (t) {
      cx.clearRect(0, 0, fw, fh);
      var steg = fw / n, b = Math.max(3, Math.min(7, steg * 0.3)), midt = (n - 1) / 2;
      mus.k += ((mus.x >= 0 ? 1 : 0) - mus.k) * 0.06;
      for (var i = 0; i < n; i++) {
        var x = steg * (i + 0.5), u = (i - midt) / midt;
        // Skjoldform: lengst på midten, kortere ut mot sidene
        var form = 0.2 + 0.8 * Math.pow(Math.cos(u * Math.PI / 2), 1.6);
        var liv = 0.62 + 0.2 * Math.sin(t * 0.0011 + i * 0.9) + 0.18 * Math.sin(t * 0.0019 - i * 0.37);
        var dx = (x - mus.x) / 190, naer = mus.k * Math.exp(-dx * dx);
        var h = fh * 0.62 * form * liv + naer * fh * 0.2;
        var gull = i === midt;
        cx.fillStyle = gull ? 'rgba(217,164,65,' + (0.85 + 0.15 * naer) + ')' : 'rgba(242,242,238,' + (0.07 + 0.3 * naer).toFixed(3) + ')';
        cx.beginPath();
        if (cx.roundRect) { cx.roundRect(x - b / 2, -b, b, h + b, b / 2); } else { cx.rect(x - b / 2, 0, b, h); }
        cx.fill();
      }
    };
    var loop = function (t) { tegn(t); if (synlig) { fraf = requestAnimationFrame(loop); } };
    maal();
    if (reduce) { tegn(0); addEventListener('resize', function () { maal(); tegn(0); }); }
    else {
      addEventListener('resize', maal);
      var fhero = felt.parentNode;
      fhero.addEventListener('pointermove', function (e) { var r = felt.getBoundingClientRect(); mus.x = e.clientX - r.left; mus.y = e.clientY - r.top; });
      fhero.addEventListener('pointerleave', function () { mus.x = -1; });
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (es) {
          synlig = es[0].isIntersecting; cancelAnimationFrame(fraf);
          if (synlig) { fraf = requestAnimationFrame(loop); }
        }).observe(felt);
      } else { fraf = requestAnimationFrame(loop); }
    }
  }

  // Forsiden: produktvelgeren. Faner med piltaster; bytter selv hvert 6. sekund til noen tar over.
  var vis = document.querySelector('[data-vis]');
  if (vis) {
    var faner = Array.prototype.slice.call(vis.querySelectorAll('[role=tab]'));
    var paneler = Array.prototype.slice.call(vis.querySelectorAll('[role=tabpanel]'));
    var naa = 0, tid = 0, TID = 6000;
    root.classList.add('har-vis');
    var velg = function (i, fokus) {
      naa = (i + faner.length) % faner.length;
      faner.forEach(function (f, j) {
        f.setAttribute('aria-selected', j === naa ? 'true' : 'false');
        if (j === naa) { f.removeAttribute('tabindex'); } else { f.setAttribute('tabindex', '-1'); }
      });
      paneler.forEach(function (p, j) { p.classList.toggle('paa', j === naa); });
      if (fokus) { faner[naa].focus(); }
      // På smale skjermer ligger fanene på rad: hold den valgte synlig uten å flytte siden
      var l = faner[naa].parentNode;
      if (l.scrollWidth > l.clientWidth) { l.scrollTo({ left: faner[naa].offsetLeft - 20, behavior: reduce ? 'auto' : 'smooth' }); }
    };
    var stopp = function () { clearInterval(tid); tid = 0; vis.classList.remove('auto', 'pause'); };
    faner.forEach(function (f, i) {
      f.addEventListener('click', function () { stopp(); velg(i); });
      f.addEventListener('keydown', function (e) {
        var d = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
        if (d) { e.preventDefault(); stopp(); velg(naa + d, true); }
        else if (e.key === 'Home') { e.preventDefault(); stopp(); velg(0, true); }
        else if (e.key === 'End') { e.preventDefault(); stopp(); velg(faner.length - 1, true); }
      });
    });
    if (!reduce && 'IntersectionObserver' in window) {
      var kjorer = false, stanset = false;
      var start = function () { if (stanset || tid) { return; } vis.classList.add('auto'); tid = setInterval(function () { velg(naa + 1); }, TID); };
      var pause = function () { clearInterval(tid); tid = 0; };
      vis.style.setProperty('--tid', TID + 'ms');
      new IntersectionObserver(function (es) { kjorer = es[0].isIntersecting; if (kjorer) { start(); } else { pause(); } }, { threshold: 0.35 }).observe(vis);
      // Stopp for godt når noen velger selv; hvil mens pekeren er over
      faner.forEach(function (f) { f.addEventListener('click', function () { stanset = true; }); f.addEventListener('keydown', function () { stanset = true; }); });
      vis.addEventListener('pointerenter', function () { if (!stanset) { pause(); vis.classList.add('pause'); } });
      vis.addEventListener('pointerleave', function () { if (!stanset && kjorer) { vis.classList.remove('pause', 'auto'); void vis.offsetWidth; start(); } });
      vis.addEventListener('focusin', function () { stanset = true; stopp(); });
    }
  }

  // Forsiden: grupper rommene
  var romKnapp = document.querySelector('[data-rom-knapp]'), rom = document.querySelector('[data-rom]');
  if (romKnapp && rom) {
    romKnapp.addEventListener('click', function () {
      var paa = rom.classList.toggle('gruppe');
      romKnapp.setAttribute('aria-pressed', paa ? 'true' : 'false');
      romKnapp.textContent = romKnapp.getAttribute(paa ? 'data-paa' : 'data-av');
    });
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
    Array.prototype.forEach.call(lenker.querySelectorAll('a'), function (a, i) { a.style.setProperty('--i', i); });
    // Produkter: nedtrekksmeny på brede skjermer. Åpnes med hover og fokus (CSS), og med trykk her (berøring og tastatur).
    var gr = lenker.querySelector('.nav-gruppe'), gk = gr && gr.querySelector('.nav-gruppe-knapp');
    if (gk) {
      var grSett = function (a) { gr.classList.toggle('aapen', a); gr.classList.toggle('lukket', !a); gk.setAttribute('aria-expanded', a ? 'true' : 'false'); };
      gk.addEventListener('click', function () { grSett(!gr.classList.contains('aapen')); });
      gr.addEventListener('mouseenter', function () { gr.classList.remove('lukket'); });
      gr.addEventListener('mouseleave', function () { gr.classList.remove('aapen', 'lukket'); gk.setAttribute('aria-expanded', 'false'); });
      document.addEventListener('click', function (e) { if (!gr.contains(e.target)) { gr.classList.remove('aapen'); gk.setAttribute('aria-expanded', 'false'); } });
      addEventListener('keydown', function (e) { if (e.key === 'Escape' && gr.contains(document.activeElement)) { grSett(false); gk.focus(); } });
      gr.addEventListener('focusout', function (e) { if (!gr.contains(e.relatedTarget)) { gr.classList.remove('aapen', 'lukket'); gk.setAttribute('aria-expanded', 'false'); } });
    }
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
