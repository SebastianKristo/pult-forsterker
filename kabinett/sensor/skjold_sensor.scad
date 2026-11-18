// Skjold Sensor – liten romsensor for vegg, tak eller bord: temperatur og luftfuktighet, valgfritt lys (lux) og
// bevegelse (PIR). ESP32-WROOM DevKit eller Wemos D1 mini (ESP8266), ESPHome.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Bygget på målene fra en eksisterende sensorboks (HA_Sensor_V2): samme PIR-hull (Ø12,2 med fas til Ø14,6, AM312),
// samme lysvindu (2,5 × 5 mm gjennom, fas utover, kanal på 4,2 mm og skruetapper ±4,45 mm for BH1750/GY-302),
// samme USB-åpning (12 × 7–8 mm) og samme idé med et eget, luftet sensorkammer bak en skillevegg. Formen, kammeret,
// festene og stativet er nye og i Skjold-formspråket.
//
// Koordinater (montert på vegg): x mot høyre (midt = 0), y opp (underkant = 0), z ut fra veggen (bakside = 0).
//
// Deler:
//   bunn     – kassen med bakvegg (nøkkelhull), sidevegger, dobbel skillevegg og sensorkammer. Printes med baksiden ned.
//   lokk     – fronten med PIR, lysvindu, statuslys og luftespalter. Printes med forsiden ned. Skrus fast bakfra (2 × M3).
//   gull     – gullisten og SKJOLD, felt inn i fronten (samme utskrift som lokket, filament 3).
//   stativ   – bordstativ: to skruer i stativet, sensoren henges på dem med nøkkelhullene. Printes på siden.
//
// Bruk: openscad -D 'kort="d1mini"' -D 'pir=false' -D 'part="lokk"' -o lokk.stl skjold_sensor.scad
// part: bunn | lokk | gull | stativ | samlet | eksplodert | stativ_samlet | a_<del> (montert stilling, for sjekken)
use <../fonter/Inter-Bold.otf>     // SKJOLD-logoen: Inter (ligger i repoet, ren J)

part  = "samlet";
kort  = "esp32";      // "esp32" (ESP32-WROOM DevKit, 30 eller 38 pinner) | "d1mini" (Wemos D1 mini, ESP8266)
pir   = true;         // hull og holder for AM312 mini-PIR
lux   = true;         // lysvindu og feste for BH1750 (GY-302)
led   = true;         // 3 mm statuslys i fronten
farge = "lys";        // lys | mork (bare for bildene)
$fn = 64;

// ---------- ytre mål ----------
ESP = kort == "esp32";
W = ESP ? 70 : 54;    // bredde
H = 56;               // høyde
D = 28;               // dybde (bunn + lokk)
R = 8;                // hjørneradius sett forfra
t = 2.2;              // sidevegger
tb = 2.0;             // bakvegg (mot veggen)
lokkT = 3.0;          // lokkets tykkelse (som referansen: gir 45° fas i lysvinduet)
Db = D - lokkT;       // bunnens dybde (lokkets bakside ligger her)
fas = 1.5;            // 45° fas på forkanten
bakFas = 0.6;         // liten fas mot veggen (og mot elefantfot)
klar = 0.25;          // klaring lokk ↔ bunn

// ---------- sensorkammeret (nederst, hele bredden) ----------
kamH = 15;                    // innvendig høyde
vW = 1.2; vG = 1.6;           // dobbel skillevegg: to vegger med luftspalte (termisk skille)
yD0 = t + kamH;               // underkant av skilleveggen
yD1 = yD0 + 2*vW + vG;        // overkant av skilleveggen
ySpalt = yD0 + vW + vG/2;     // midt i luftspalten (gullisten ligger rett foran)
sensW = 13.6;                 // bredden på temp/fukt-kortet (SHT40/SHT31/AHT20+BMP280-moduler er ca. 10–14 mm)
sensX = -W/2 + t + 13;        // kortet står helt til venstre, lengst unna USB og ESP-varmen
sensY = t + kamH/2;           // kortet ligger vannrett i midten av kammeret og skyves inn i to spor forfra
sporB = 1.9; sporD = 1.2;     // sporene: bredde og dybde

// ---------- hovedrommet ----------
mainH = H - t - yD1;          // innvendig høyde over skilleveggen
cy = yD1 + mainH/2;           // midt i hovedrommet (PIR, lysvindu og statuslys ligger på denne linja)
// ESP-kortet ligger flatt, USB-enden inn mot høyre vegg. Lodd ledningene rett i hullene (ikke stiftlister).
bL = ESP ? 55.0 : 34.6;       // kortets lengde inkl. klaring (DevKit V1 51,5; DevKitC 54,4; D1 mini 34,2)
bW = ESP ? 28.6 : 26.0;       // bredde inkl. klaring (DevKit 28,3 / 25,5; D1 mini 25,6)
bT = 1.6;
bZ = ESP ? 5.2 : 7.0;         // kortets underside over bakveggens bakside (D1 mini: USB-kontakten sitter under kortet)
bX1 = W/2 - t - 0.5;          // høyre ende (USB)
bX0 = bX1 - bL;
usbZ = ESP ? bZ + bT + 1.5 : bZ - 1.4;   // midt i micro-USB-kontakten
usbB = 12; usbH = ESP ? 8 : 7.5;         // åpning for pluggen (referansen: 12 × 7)

// ---------- fronten ----------
pirX = 0;   pirHull = 12.2; pirFasD = 14.6; pirRorD = 10.5; pirRorL = 9;   // AM312: kuppel gjennom Ø12,2, kropp i Ø10,5-røret
luxX = 14;  luxSpaltX = 2.5; luxSpaltY = 5; luxFasX = 8.5; luxFasY = 11;   // lysvindu som referansen
luxBlokk = [14, 6.5, 4.2]; luxHull = 4.45; luxPilot = 2.2;                 // GY-302: hullene ±4,45 mm fra BH1750-brikka, M2,5 selvgjengende
ledX = -14; ledHull = 3.1; ledFlens = 4.0;                                 // 3 mm LED
ventY = [t + 3.4, t + 7.5, t + 11.6]; ventH = 1.6;                         // spalter foran sensorkammeret
gullB = 1.2; gullT = 0.6;                                                   // gullisten foran skilleveggen
tekst = "SKJOLD"; tekstY = yD1 + 3.4; tekstS = 2.6;

// ---------- feste ----------
skrue = [[-W/2 + t + 4.3, H - t - 4.3], [W/2 - t - 4.3, t + 4.3]];   // M3 × 12 senkeskrue bakfra inn i lokkets tapper
tappD = 6.2; pilot = 2.7;
kS = ESP ? 40 : 26;           // nøkkelhull: avstand mellom skruene
kY = cy + 4;                  // skruens stilling når sensoren henger (i toppen av sporet)
kSpor = 6; kHode = 7.6; kSkaft = 4.2;
kHud = 1.6; kLomme = 2.2; kTak = 1.2;   // bakvegg under lomma, lommas høyde (skruehodet), tak over lomma
kPute = kHud + kLomme + kTak;           // 5,0 – ESP-kortet ligger over putene

// ---------- farger ----------
MORK = farge == "mork";
c_kropp = MORK ? "#2E2D2C" : "#ECE9E3";
c_lokk  = MORK ? "#353433" : "#F2F0EB";
c_gull  = "#D99E40";
c_stativ = MORK ? "#ECE9E3" : "#2E2D2C";

// ---------- hjelpere ----------
module omriss(o = 0) { translate([0, H/2]) offset(r = R + o) square([W - 2*R, H - 2*R], center = true); }
module spalte2d(l, b) { hull() { for (s = [-1, 1]) translate([s*(l/2 - b/2), 0]) circle(d = b, $fn = 24); } }
module rrect(x, y, r) { offset(r = r) square([x - 2*r, y - 2*r], center = true); }

// ---------- bunnen ----------
module bunn() {
  difference() {
    union() {
      difference() {
        hull() { linear_extrude(0.01) omriss(-bakFas); translate([0, 0, bakFas]) linear_extrude(Db - bakFas) omriss(); }
        translate([0, 0, tb]) linear_extrude(Db) omriss(-t);
      }
      // dobbel skillevegg mellom sensorkammeret og ESP-rommet (luftspalte mellom), unntatt der lokkets kant går
      difference() {
        intersection() {
          translate([0, 0, tb - 0.01]) linear_extrude(Db - 0.2 - tb + 0.01) for (y = [yD0, yD1 - vW]) translate([-W, y]) square([2*W, vW]);
          translate([0, 0, tb - 0.02]) linear_extrude(Db) omriss(-t + 0.01);
        }
        translate([0, 0, Db - 2.3]) linear_extrude(3) difference() { omriss(-t + 0.5); omriss(-t - klar - 1.2 - 0.3); }
      }
      // nøkkelhullsputer
      for (s = [-1, 1]) translate([s*kS/2, 0, 0]) linear_extrude(kPute) hull() {
        translate([0, kY]) circle(d = kHode + 3.2); translate([0, kY - kSpor]) circle(d = kHode + 3.2);
      }
      // ESP-kortet: hjørnestøtter, med kanter som holder det på plass (ikke ved USB-enden, der veggen gjør jobben)
      for (sx = [0, 1], sy = [-1, 1]) let(x = sx == 0 ? bX0 : bX1, y = cy + sy*bW/2) {
        translate([x - (sx == 0 ? 0 : 3), y - (sy < 0 ? 0 : 3), tb - 0.01]) cube([3, 3, bZ - tb + 0.01]);
        if (sx == 0) translate([x - 1.2, y - (sy < 0 ? 0.3 : 4.7), tb - 0.01]) cube([1.25, 5, bZ - tb + bT + 1]);
        translate([x - (sx == 0 ? 0 : 5), y - (sy < 0 ? 1.2 : 0.05), tb - 0.01]) cube([5, 1.25, bZ - tb + bT + 1]);
      }
      // sensorkortet: to stolper med spor, kortet skyves inn forfra og ligger vannrett midt i kammeret
      for (s = [-1, 1]) translate([sensX + s*(sensW/2 + 0.3 - sporD + 1.5), sensY, tb - 0.01]) difference() {
        translate([-1.5, -2.5, 0]) cube([3, 5, Db - 1.5 - tb]);
        translate([s < 0 ? 1.5 - sporD : -1.5 - 0.01, -sporB/2, -1]) cube([sporD + 0.01, sporB, Db + 2]);
      }
    }
    // nøkkelhull: Ø7,6 for hodet, spor 4,2 opp, lomme for hodet inne i puta
    for (s = [-1, 1]) translate([s*kS/2, 0, 0]) {
      translate([0, kY - kSpor, -1]) cylinder(d = kHode, h = kHud + 1.01);
      translate([0, 0, -1]) linear_extrude(kHud + 1.01) hull() { translate([0, kY]) circle(d = kSkaft); translate([0, kY - kSpor]) circle(d = kSkaft); }
      translate([0, 0, kHud]) linear_extrude(kLomme) hull() { translate([0, kY]) circle(d = kHode + 0.4); translate([0, kY - kSpor]) circle(d = kHode + 0.4); }
    }
    // senkeskruer bakfra inn i lokket
    for (p = skrue) translate([p[0], p[1], 0]) {
      translate([0, 0, -1]) cylinder(d = 3.4, h = tb + 2, $fn = 32);
      translate([0, 0, -0.01]) cylinder(d1 = 6.8, d2 = 3.4, h = 1.71, $fn = 32);
    }
    // USB i høyre vegg
    translate([W/2 - t - 1, cy, usbZ]) rotate([0, 90, 0]) linear_extrude(t + 2) rrect(usbH, usbB, 1.5);
    // sensorkammeret: spalter i bunnen (luft inn nedenfra) og i begge ender
    for (x = [-W/2 + 7 : 3.4 : W/2 - 9]) translate([x - 0.8, -1, tb + 1.5]) cube([1.6, t + 2, Db - tb - 4.5]);
    for (s = [-1, 1], y = [t + 3.5, t + 7.5, t + 11.5]) translate([s < 0 ? -W/2 - 1 : W/2 - t - 1, y - 0.8, tb + 1.5]) cube([t + 2, 1.6, Db - tb - 4.5]);
    // ESP-rommet: spalter i toppen (varmen ut, bort fra sensoren)
    for (x = [-W/2 + 12 : 3.4 : W/2 - 12]) translate([x - 0.8, H - t - 1, tb + 3]) cube([1.6, t + 2, Db - tb - 6]);
    // ledningene fra sensoren går under skilleveggen ved sensoren
    translate([sensX - 4, yD0 - 0.5, tb - 0.01]) cube([8, yD1 - yD0 + 1, 3.5]);
  }
}

// ---------- lokket (montert stilling: baksiden på z = Db, forsiden på z = D) ----------
module lokk() {
  difference() {
    union() {
      hull() {
        translate([0, 0, Db]) linear_extrude(lokkT - fas) omriss();
        translate([0, 0, D - 0.01]) linear_extrude(0.01) omriss(-fas);
      }
      // kant inn i bunnen (sentrerer lokket)
      translate([0, 0, Db - 2]) linear_extrude(2.01) difference() { omriss(-t - klar); omriss(-t - klar - 1.2); }
      // ribbe ned i skilleveggens luftspalte (tetter kammeret)
      translate([0, ySpalt, Db - 2.5]) linear_extrude(2.51) square([W - 2*t - 2*klar - 0.4, vG - 0.5], center = true);
      // tapper for skruene bakfra
      for (p = skrue) translate([p[0], p[1], tb + 0.2]) cylinder(d = tappD, h = Db - tb - 0.2 + 0.01);
      // PIR-rør (C-form, fjærer om AM312-kroppen)
      if (pir) translate([pirX, cy, Db - pirRorL]) difference() {
        cylinder(d = pirRorD + 3, h = pirRorL + 0.01);
        translate([0, 0, -1]) cylinder(d = pirRorD, h = pirRorL + 2);
        translate([0, -0.75, -1]) cube([pirRorD, 1.5, pirRorL - 1]);
      }
      // lysblokk: kanal fra vinduet og to skruetapper for GY-302
      if (lux) translate([luxX - luxBlokk[0]/2, cy - luxBlokk[1]/2, Db - luxBlokk[2]]) cube([luxBlokk[0], luxBlokk[1], luxBlokk[2] + 0.01]);
      // LED-holder
      if (led) translate([ledX, cy, Db - 4]) cylinder(d = ledFlens + 2.4, h = 4.01);
      // pinner som holder ESP-kortet nede (bare i enden uten USB – knappene sitter ved USB)
      for (sy = [-1, 1]) translate([bX0 + 1.8 - 1.4, cy + sy*(bW/2 - 1.8) - 1.4, bZ + bT + 0.3]) cube([2.8, 2.8, Db - bZ - bT - 0.3 + 0.01]);
    }
    // PIR-hull med 45° fas utover
    if (pir) {
      translate([pirX, cy, Db - 1]) cylinder(d = pirHull, h = lokkT + 2);
      translate([pirX, cy, D - (pirFasD - pirHull)/2]) cylinder(d1 = pirHull, d2 = pirFasD + 0.02, h = (pirFasD - pirHull)/2 + 0.01);
    }
    // lysvindu: 2,5 × 5 gjennom, 45° fas ut til 8,5 × 11, kanal gjennom blokka og pilothull ±4,45 mm
    if (lux) {
      translate([luxX, cy, Db - luxBlokk[2] - 1]) linear_extrude(D) square([luxSpaltX, luxSpaltY], center = true);
      translate([luxX, cy, Db - 0.01]) hull() {
        linear_extrude(0.01) square([luxSpaltX, luxSpaltY], center = true);
        translate([0, 0, lokkT + 0.05]) linear_extrude(0.01) square([luxFasX + 0.1, luxFasY + 0.1], center = true);
      }
      for (s = [-1, 1]) translate([luxX + s*luxHull, cy, Db - luxBlokk[2] - 1]) cylinder(d = luxPilot, h = luxBlokk[2], $fn = 24);
    }
    if (led) {
      translate([ledX, cy, Db - 5]) cylinder(d = ledHull, h = lokkT + 6, $fn = 32);
      translate([ledX, cy, Db - 4.1]) cylinder(d = ledFlens, h = 4.1, $fn = 32);
      translate([ledX, cy, D - 0.5]) cylinder(d1 = ledHull, d2 = ledHull + 1, h = 0.51, $fn = 32);
    }
    // pilothull i tappene
    for (p = skrue) translate([p[0], p[1], tb]) cylinder(d = pilot, h = 14, $fn = 24);
    // luftespalter foran sensorkammeret
    for (y = ventY) translate([0, y, Db - 3]) linear_extrude(lokkT + 4) spalte2d(W - 20, ventH);
    // gullisten og SKJOLD
    gull(0.01);
  }
}
module gull2d() {
  translate([0, ySpalt]) square([W - 2*R, gullB], center = true);
  translate([0, tekstY]) text(tekst, size = tekstS, font = "Inter:style=Bold", halign = "center", valign = "bottom", spacing = 1.3);
}
module gull(e = 0) { translate([0, 0, D - gullT]) linear_extrude(gullT + e) gull2d(); }

// ---------- bordstativ (to M3 × 8 skruer skrus i stativet; sensoren henges på dem) ----------
sB = W - 12;
module stativ() {
  difference() {
    multmatrix([[0, 0, 1, -sB/2], [0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1]]) linear_extrude(sB) offset(r = 1) offset(delta = -1) union() {
      translate([-30, -8]) square([30 + D + 6, 4]);        // fot (sensoren står 4 mm over den, så bunnspaltene får luft)
      translate([-5, -8]) square([5, kY + 16]);            // rygg
      hull() { translate([-29, -6]) circle(d = 4); translate([-4, kY - 4]) circle(d = 4); }   // stag
    }
    for (s = [-1, 1]) translate([s*kS/2, kY, -6]) cylinder(d = pilot, h = 7, $fn = 24);
    // gummiføtter Ø10
    for (s = [-1, 1], z = [-22, D]) translate([s*(sB/2 - 8), -8.01, z]) rotate([-90, 0, 0]) cylinder(d = 10.4, h = 0.8);
  }
}

// ---------- kjøpte deler (for bildene og kollisjonssjekken) ----------
module esp() {
  color("#1f1f22") translate([bX0 + 0.3, cy - bW/2 + 0.3, bZ]) cube([bL - 0.6, bW - 0.6, bT]);
  if (ESP) {
    color("#b8b8bc") translate([bX0 + 6.5, cy - 8, bZ + bT]) cube([17.8, 16, 3.1]);          // WROOM-modulen
    color("#202020") translate([bX0 + 0.5, cy - 9, bZ + bT]) cube([6, 18, 0.8]);             // antennen
    color("#c8c8cc") translate([bX1 - 5, cy - 4, bZ + bT]) cube([5.6, 8, 2.9]);              // micro-USB
    for (s = [-1, 1]) color("#333") translate([bX1 - 7, cy + s*9 - 2, bZ + bT]) cube([4, 4, 2.5]);   // EN / BOOT
  } else {
    color("#b8b8bc") translate([bX0 + 1, cy - 8, bZ + bT]) cube([24, 16, 3.2]);              // ESP-12F
    color("#c8c8cc") translate([bX1 - 5, cy - 4, bZ - 2.8]) cube([5.6, 8, 2.8]);             // micro-USB (undersiden)
    color("#333") translate([bX0 + 12, cy - 4.5, bZ - 1.5]) cube([9, 9, 1.5]);               // CH340 (undersiden)
  }
}
module usbplugg() {
  color("#222") translate([bX1 + 0.6, cy - 5.25, usbZ - 3.25]) cube([16, 10.5, 6.5]);
  color("#222") translate([bX1 + 16.6, cy, usbZ]) rotate([0, 90, 0]) cylinder(d = 3.6, h = 20);
}
module am312() {
  color("#f4f4f2") translate([pirX, cy, D - 0.8]) scale([1, 1, 0.55]) sphere(d = 12);
  color("#f4f4f2") translate([pirX, cy, D - 3]) cylinder(d = 12, h = 2.2);
  color("#e8e8e6") translate([pirX, cy, Db - 9]) cylinder(d = 10, h = 9 + lokkT - 3);
  color("#555") translate([pirX - 1.5, cy - 1.5, Db - 12]) cube([3, 3, 3]);
}
module gy302() {
  color("#5b2d86") translate([luxX - 6.95, cy - 3, Db - luxBlokk[2] - 1.6]) cube([13.9, 18.5, 1.6]);
  color("#111") translate([luxX - 1.5, cy - 0.8, Db - luxBlokk[2] - 0.01]) cube([3, 1.6, 0.01]);
}
module sensorkort() {
  color("#2d6fb5") translate([sensX - sensW/2 + 0.2, sensY - 0.8, tb + 0.2]) cube([sensW - 0.4, 1.6, 12]);
  color("#ddd") translate([sensX - 1.5, sensY - 1.6, tb + 4.5]) cube([3, 0.8, 3]);
}
module led3() {
  color("#f2f2f2", 0.9) translate([ledX, cy, Db - 4]) cylinder(d = 3.8, h = 1);
  color("#f2f2f2", 0.9) translate([ledX, cy, Db - 3]) cylinder(d = 3, h = lokkT + 2.5);
}

module lokk_alt() { color(c_lokk) lokk(); color(c_gull) gull(); }
module samlet(ex = 0) {
  color(c_kropp) bunn();
  translate([0, 0, ex]) { lokk_alt(); if (pir) am312(); if (lux) gy302(); if (led) led3(); }
  translate([0, 0, ex * 0.45]) esp();
  translate([ex * 0.5, 0, ex * 0.45]) usbplugg();
  translate([0, 0, ex * 0.2]) sensorkort();
}

// ---------- utskriftsretning ----------
module lokk_print() { translate([0, 0, D]) rotate([180, 0, 0]) lokk(); }
module gull_print() { translate([0, 0, D]) rotate([180, 0, 0]) gull(); }

// vis = true: stående som på veggen (forsiden mot −y, opp = z), for bildene
vis = false;
module V() { if (vis) rotate([90, 0, 0]) children(); else children(); }

if (part == "bunn") bunn();
else if (part == "lokk") lokk_print();
else if (part == "gull") gull_print();
else if (part == "stativ") rotate([0, -90, 0]) translate([sB/2, 0, 0]) stativ();   // på siden
else if (part == "a_bunn") bunn(); else if (part == "a_lokk") lokk(); else if (part == "a_gull") gull();
else if (part == "a_esp") esp(); else if (part == "a_plugg") usbplugg(); else if (part == "a_pir") am312();
else if (part == "a_lux") gy302(); else if (part == "a_sensor") sensorkort(); else if (part == "a_led") led3();
else if (part == "a_stativ") stativ();
else if (part == "eksplodert") V() samlet(32);
else if (part == "inni") V() { color(c_kropp) bunn(); esp(); usbplugg(); sensorkort(); }
else if (part == "stativ_samlet") V() { samlet(); color(c_stativ) stativ(); }
else V() samlet();
