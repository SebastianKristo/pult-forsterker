// Velger oppsett for skjold-ui før noe annet lastes:
//   s1    – Skjold S1 rev F, 4,58″ bar-skjerm 960 × 320 (designets egen canvas-tegning, screen.js)
//   radio – Skjold Radio, 4,3″ DSI 800 × 480 (radio.js/radio.css)
// ?layout=radio|s1 bestemmer. Uten den velges radio automatisk når vinduet er omtrent 5:3 (800 × 480), ellers S1,
// så S1 er uendret. Kiosken på radioen åpner /?layout=radio (SKJOLD_UI_LAYOUT=radio, se KONTRAKT.md).
(function () {
  var q = new URLSearchParams(location.search).get('layout');
  var w = window.innerWidth || screen.width, h = window.innerHeight || screen.height, r = h ? w / h : 3;
  var lay = q === 'radio' || q === 's1' ? q : (r > 1.45 && r < 1.9 ? 'radio' : 's1');
  window.SKJOLD_LAYOUT = lay;
  document.documentElement.dataset.layout = lay;
  var vp = document.querySelector('meta[name=viewport]');
  if (lay === 'radio') {
    if (vp) vp.content = 'width=800,height=480';
    document.title = 'Skjold Radio-skjerm';
    document.write('<link rel="stylesheet" href="radio.css"><script src="radio.js"><\/script>');
  } else {
    document.write('<style>html,body{margin:0;width:960px;height:320px;overflow:hidden;background:#000;cursor:none}canvas{display:block}</style>' +
      ['qrcode.js', 'skjold_settings.js', 'skjold_welcome.js', 's1_draw.js', 'night.js', 'screen.js']
        .map(function (s) { return '<script src="' + s + '"><\/script>'; }).join(''));
  }
})();
