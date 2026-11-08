// Skjold – mal for høyttalerelementer (3″ fullrange). Brukes av Røst og Røst Rund.
//
// Velg element med -D 'element="rs75_4"' (eller endre standardverdien i produktfila), eller legg inn ditt eget under
// «egen» med målene fra databladet / skyvelæret. Alle mål i mm.
//
//   utsp     – hullet elementet trenger (produsentens «baffle cutout»; for montering bakfra: minst membran + oppheng)
//   ramme    – rammens ytre mål (diameter, eller sidekant for firkantet ramme)
//   form     – 0 = rund ramme, 1 = firkantet ramme
//   pcd      – hullsirkelen (senter til senter, gjennom elementets midtpunkt)
//   antall   – antall skruehull
//   hull     – skruehullenes diameter i rammen (M3: 3,2–3,5)
//   vinkel   – vinkelen til første skruehull (0 = rett til siden, 45 = på skrå)
//   dybde    – dybde bak rammen (magnet/kurv), for kontroll mot porten og elektronikken
//   fs       – resonansfrekvens (Hz), for å stemme porten (0 = ukjent)
//   sikker   – true når alle målene er bekreftet fra datablad; false = noen mål er anslag og MÅ måles før du printer
//
// Kilder: Dayton RS75-4 (daytonaudio.com, loudspeakerdatabase.com: utsparing 54, ytre 72, hullsirkel 2,52″ = 64, dybde
// 38,5, Fs 177 Hz). Visaton FRS 8 4 Ω (loudspeakerdatabase.com, Parts Express: utsparing 73, ytre 78, dybde 35).
// GRS 3FR-4 (Parts Express: utsparing 2,82″ = 71,6). FaitalPRO 3FE22-4F (Soundimports: utsparing 73,6).
//                     utsp   ramme form pcd   antall hull vinkel dybde fs   sikker
ELEMENTER = [
  ["rs75_4",       [54.0, 72.0, 0,   64.0, 4,     3.3, 45,    38.5, 177, true ]],   // Dayton Audio RS75-4
  ["frs8_4",       [73.0, 78.0, 0,   70.0, 4,     3.5, 45,    35.0, 0,   false]],   // Visaton FRS 8 4 Ω (hullsirkel: mål)
  ["grs3fr4",      [71.6, 84.0, 0,   78.0, 4,     3.5, 45,    40.0, 0,   false]],   // GRS 3FR-4 (ramme, hull, dybde: mål)
  ["faital3fe22",  [73.6, 84.0, 0,   78.0, 4,     4.0, 45,    45.0, 0,   false]],   // FaitalPRO 3FE22-4F (ramme, hull, dybde: mål)
  ["egen",         [70.0, 80.0, 0,   74.0, 4,     3.4, 45,    40.0, 0,   false]],   // ditt eget: fyll inn målene her
];
function el_data(navn) = let(i = search([navn], ELEMENTER)[0]) assert(i != [], str("ukjent element: ", navn)) ELEMENTER[i][1];
function el_utsp(e)   = e[0];
function el_ramme(e)  = e[1];
function el_form(e)   = e[2];
function el_pcd(e)    = e[3];
function el_antall(e) = e[4];
function el_hull(e)   = e[5];
function el_vinkel(e) = e[6];
function el_dybde(e)  = e[7];
function el_fs(e)     = e[8];
function el_sikker(e) = e[9];
function el_hullpos(e) = [for (i = [0:el_antall(e) - 1]) let(a = el_vinkel(e) + i * 360 / el_antall(e)) [el_pcd(e)/2 * cos(a), el_pcd(e)/2 * sin(a)]];
// rammens omriss (2D, sentrert), med klaring o
module el_ramme2d(e, o = 0) {
  if (el_form(e) == 1) offset(r = 3 + o) square(el_ramme(e) - 6, center = true);
  else circle(d = el_ramme(e) + 2 * o, $fn = 96);
}
// enkel modell av elementet til bilder og kollisjonssjekk: rammen i z = 0..3 (forsiden mot −z), kurv/magnet bakover (+z)
module el_modell(e) {
  difference() { linear_extrude(3) el_ramme2d(e); translate([0, 0, -1]) cylinder(d = el_utsp(e) - 6, h = 5, $fn = 64); }
  translate([0, 0, -0.5]) cylinder(d1 = el_utsp(e) - 2, d2 = el_utsp(e) * 0.45, h = el_dybde(e) * 0.55, $fn = 48);
  translate([0, 0, el_dybde(e) * 0.5]) cylinder(d = el_utsp(e) * 0.7, h = el_dybde(e) * 0.5, $fn = 48);
}
