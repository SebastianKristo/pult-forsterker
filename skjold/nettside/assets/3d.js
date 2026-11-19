// /3d/: søk og filter i kortene (uten JS vises alle)
(function () {
  var sok = document.querySelector('[data-d3-sok]'), knapper = document.querySelectorAll('.d3-filter'), kort = document.querySelectorAll('.d3-kort'), ingen = document.querySelector('.d3-ingen');
  if (!sok) return;
  var kat = '';
  function vis() {
    var q = sok.value.trim().toLowerCase().split(/\s+/).filter(Boolean), n = 0;
    kort.forEach(function (k) {
      var ok = (!kat || k.dataset.kat === kat) && q.every(function (o) { return k.dataset.sok.indexOf(o) >= 0; });
      k.hidden = !ok; if (ok) n++;
    });
    if (ingen) ingen.hidden = n > 0;
  }
  knapper.forEach(function (b) {
    b.addEventListener('click', function () {
      kat = b.dataset.kat || '';
      knapper.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      vis();
    });
  });
  sok.addEventListener('input', vis);
})();
