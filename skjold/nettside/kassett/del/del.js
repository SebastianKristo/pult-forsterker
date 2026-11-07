// Delingslenke: https://skjold.smarthjemexperten.no/kassett/del#<kode> → åpne skjold://kassett/del?d=<kode> i appen.
(function () {
  var kode = decodeURIComponent((location.hash || '').replace(/^#/, '')).trim();
  var ok = /^[A-Za-z0-9_.-]{8,20000}$/.test(kode);
  var el = function (id) { return document.getElementById(id); };
  if (!ok) {
    el('tekst').textContent = 'Lenken mangler delingskoden. Be om en ny lenke fra den som delte kassetten.';
    el('apne').style.display = 'none'; el('kopier').style.display = 'none'; el('kode').style.display = 'none';
    return;
  }
  el('kode').textContent = kode;
  el('apne').href = 'skjold://kassett/del?d=' + encodeURIComponent(kode);
  el('kopier').addEventListener('click', function () {
    var b = el('kopier');
    (navigator.clipboard ? navigator.clipboard.writeText(kode) : Promise.reject()).then(function () {
      b.textContent = 'Koden er kopiert';
    }, function () {
      var r = document.createRange(); r.selectNodeContents(el('kode'));
      var s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Koden er markert – kopier den';
    });
  });
})();
