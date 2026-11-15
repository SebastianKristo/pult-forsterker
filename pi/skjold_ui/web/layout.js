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
    // Panel på høykant (SKJOLD_UI_PANEL/SKJOLD_UI_ROTATE, se __main__.py): S1-bildet 960 × 320 dreies og sentreres på panelet.
    var P = new URLSearchParams(location.search), rot = parseInt(P.get('rot') || '0', 10) || 0;
    var pw = parseInt(P.get('pw') || '0', 10), ph = parseInt(P.get('ph') || '0', 10);
    // fit=stretch: bildet strekkes på tvers så det fyller panelets korte side (320 → f.eks. 400)
    var side = (rot % 180) ? pw : ph, sy = (P.get('fit') === 'stretch' && side > 320) ? side / 320 : 1;
    // h = ønsket bildehøyde (overstyrer fit), shift = flytt bildet opp (+) / ned (−) i piksler
    var hh = parseInt(P.get('h') || '0', 10), shift = parseInt(P.get('shift') || '0', 10) || 0;
    if (hh > 0) sy = hh / 320;
    var fit = (pw && ph) ? '<style>html{width:' + pw + 'px!important;height:' + ph + 'px!important;overflow:hidden;background:#000}' +
      'body{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) rotate(' + rot + 'deg) translateY(' + (-shift) + 'px) scale(1,' + sy + ');transform-origin:50% 50%}</style>' : '';
    document.write('<style>@font-face{font-family:Sora;font-weight:400;src:url(fonts/sora-latin-400-normal.woff2) format("woff2")}@font-face{font-family:Sora;font-weight:600;src:url(fonts/sora-latin-600-normal.woff2) format("woff2")}@font-face{font-family:"IBM Plex Mono";font-weight:400;src:url(fonts/ibm-plex-mono-latin-400-normal.woff2) format("woff2")}@font-face{font-family:"IBM Plex Mono";font-weight:500;src:url(fonts/ibm-plex-mono-latin-500-normal.woff2) format("woff2")}html,body{margin:0;width:960px;height:320px;overflow:hidden;background:#000;cursor:none}canvas{display:block}</style>' + fit +
      ['qrcode.js', 'skjold_settings.js', 'skjold_welcome.js', 's1_draw.js', 'night.js', 'screen.js', 'system.js']
        .map(function (s) { return '<script src="' + s + '"><\/script>'; }).join(''));
  }
})();
