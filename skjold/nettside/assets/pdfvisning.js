// Bruksanvisning: PDF-visning med pdf.js (selvhostet, Apache 2.0). Sider tegnes etter hvert som de rulles fram.
(function () {
  var rot = document.querySelector('[data-pdf]'); if (!rot || !window.pdfjsLib) return;
  var url = rot.getAttribute('data-pdf'), sider = rot.querySelector('.pdf-sider'), info = rot.querySelector('[data-pdf-info]');
  var zoom = 1, doc = null;
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/assets/pdfjs/pdf.worker.min.js';
  function tegn(side, lerret) {
    var bredde = Math.min(sider.clientWidth, 1100) * zoom, dpr = window.devicePixelRatio || 1;
    var v = side.getViewport({ scale: 1 }), skala = bredde / v.width, vp = side.getViewport({ scale: skala * dpr });
    lerret.width = vp.width; lerret.height = vp.height; lerret.style.width = (vp.width / dpr) + 'px'; lerret.style.height = (vp.height / dpr) + 'px';
    return side.render({ canvasContext: lerret.getContext('2d'), viewport: vp }).promise;
  }
  function bygg() {
    sider.innerHTML = '';
    var obs = new IntersectionObserver(function (e) {
      e.forEach(function (x) {
        if (!x.isIntersecting || x.target.dataset.ferdig) return;
        x.target.dataset.ferdig = '1';
        doc.getPage(+x.target.dataset.n).then(function (s) { return tegn(s, x.target.querySelector('canvas')); });
      });
    }, { rootMargin: '600px 0px' });
    for (var n = 1; n <= doc.numPages; n++) {
      var d = document.createElement('div'); d.className = 'pdf-side'; d.dataset.n = n;
      var c = document.createElement('canvas'); c.setAttribute('aria-label', 'Side ' + n); d.appendChild(c);
      d.style.minHeight = Math.round(Math.min(sider.clientWidth, 1100) * zoom * 1.414) + 'px';
      sider.appendChild(d); obs.observe(d);
    }
  }
  pdfjsLib.getDocument(url).promise.then(function (d) {
    doc = d; if (info) info.textContent = d.numPages + ' sider'; bygg();
  }).catch(function () { sider.innerHTML = '<p class="pdf-feil">Kunne ikke vise PDF-en her. Bruk «Last ned».</p>'; });
  rot.querySelectorAll('[data-zoom-pdf]').forEach(function (b) {
    b.addEventListener('click', function () { zoom = Math.max(0.6, Math.min(2, zoom + parseFloat(b.dataset.zoomPdf))); if (doc) bygg(); });
  });
  var t; window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(function () { if (doc) bygg(); }, 300); });
})();
