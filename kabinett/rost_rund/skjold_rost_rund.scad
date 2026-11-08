// Skjold Røst Rund – alternativ Røst: avrundet kropp med grill hele veien rundt, knapper og gullknott på toppen.
// Eget design i Skjolds formspråk (sekskantgrill, gullknott, SKJOLD i gull foran nede). Lisens: CC BY-NC-SA 4.0.
//
// Oppbygging (alt holdes sammen av fire M3-gjengestenger fra lokket ned gjennom kjernen til bunnplaten, ingen synlige skruer):
//   lokk    – topp med fem knapper (av/på, favoritt 1–4) og EC11-volumknott; printes med toppen ned
//   kjerne  – mørk indre kasse: rør med frontblokk for 3″-elementet, tunnel og stangtårn; printes stående
//   hylse   – grillen rundt hele kroppen (lages av lag_hylse.py, manifold3d), med helt bånd og SKJOLD nederst foran
//   bunn    – bunnplate med bassrefleksport ned, avstandstapper for elektronikken og forsenkninger for gummiføtter
// Koordinater: x tvers, y fra front (−) til bak (+), z opp (0 = bordet, uten føtter).
// part: lokk | kjerne | bunn | knott | knapp | samlet | eksplodert | a_<del> (montert stilling)
part = "samlet";
include <../elementer/elementer.scad>
element = "rs75_4";                // se ../elementer/elementer.scad: rs75_4 | frs8_4 | grs3fr4 | faital3fe22 | egen
E = el_data(element);
if (!el_sikker(E)) echo(str("ADVARSEL: målene for ", element, " er delvis anslag – mål elementet og rett dem i elementer.scad før du printer elementplata"));
$fn = 64;

// ---------- mål ----------
W = 108; Dp = 108; R = 28;          // grunnriss: avrundet rektangel
H = 150;                           // høyde fra bunnplatens underside til toppen av lokket
bpT = 5; capT = 5;                 // bunnplate og lokk
sl = 1.8; sg = 0.3; t = 2.4;       // hylsens vegg, luft mellom hylse og kjerne, kjernens vegg
z0 = bpT; z1 = H - capT;           // kjernen og hylsen står mellom bunnplaten og lokket
rT = 4;                            // toppkanten: R4, som flater ut i 45° fas mot toppen (printes med toppen ned)
fot = 12.4; fotH = 0.6;            // forsenkninger for selvklebende gummiføtter Ø12 × 6 mm
// element (3″ fullrange, f.eks. Dayton RS75-4) bakfra mot frontblokka
drvZ = 78; drvTun = 80; blk = 16;    // elementets senter, tunnelen gjennom frontblokka (fast, Ø80), blokkas dybde fra fronten
// Elementplata (utskiftbar): 92 × 92 × 4 mm bak frontblokka, tegnet fra malen i elementer.scad. Elementet skrus i plata,
// plata skrus i fire innpressmuttere i blokka (plFeste: x ±30, z ±42 fra elementets senter – fri for stengene).
plW = 92; plT = 4; plR = 8; plFeste = [for (sx = [-1, 1], sz = [-1, 1]) [sx * 30, sz * 42]];
// bassrefleks ned gjennom bunnen (føttene gir 6 mm luft)
portD = 18; portW = 2; portL = 110; portP = [-14, 30];
// stenger og innpressmuttere
rodP = [for (sx = [-1, 1], sy = [-1, 1]) [sx * 37, sy < 0 ? -44 : 36]];   // de fremre går gjennom frontblokka (fri for elementets ramme)
rodD = 3.4; bossD = 9; ins = 4.0; insL = 5.5;
// I/O bak nede (gjennom kjernen; hylsa har en spiss bue rundt)
ioX = 16; dcZ = z0 + 12; usbZ = z0 + 6; dcD = 8.2; usbW = 10; usbH = 4.4;
ioW = 32; ioH = 28;                 // utsparingen i hylsa: bredde og høyde til spissen (45° tak, printes stående)
// topp: fem knapper foran, skjerm i midten, knott bak
btnY = -40; btnX = [-26, -13, 0, 13, 26]; capD = 9.0; capHole = 9.5; flD = 12; flT = 0.9; capUp = 1.1;
encY = 34; ec11D = 7.2; knobD = 30; knobH = 13; shaftD = 6.1; shaftFlat = 4.6;
// skjerm: 2,42″ OLED 128×64 (SSD1309, I²C, hvit), samme modul som Røst. Toppen av modulen (pinneraden) vender bakover
// mot knotten, flatkabelen foran mot knappene. Glasset ligger i en lomme i en skjermramme under lokket (lokket er bare
// 5 mm: rammen gir 7,5 mm til toppen som på Røst), kortet skrus i fire tårn med M2 × 6 selvgjengende.
dispY = -6;                              // senter av det aktive området
actW = 55.4; actH = 27.7; winW = actW + 0.6; winH = actH + 0.6;
glW = 60.0; glH = 30.5; glT = 3.25; skD = 7.5;   // glass, og glassets underside under toppen
pcbW = 70.08; pcbH = 39.0; dHoleX = 31.0; dHoleV = 16.5;
fpcW = 12.6; fpcL = 3.0;
ruteW = 64; ruteH = 36; ruteT = 1.5; ruteRec = ruteT + 0.2;   // klar rute i flukt med toppen (0,2 mm tape under)
// (ingen hevet ramme rundt ruta: lokket printes med toppen ned, så toppen må være helt flat)
boardZ = z1 - 6.7;                 // knappekortets overside: 6 × 6 × 5 mm-bryterne står 0,2 mm under hettenes nupp
// knappekortet: hullkort 64 × 20 mm, bryterne sentrert under hettene, to M2-hull bak knapperaden (fri for stangtårnene)
kortW = 64; kortH = 20; kortY = btnY + 3; kortHull = [[-29.5, btnY + 9], [29.5, btnY + 9]];
// EC11: mutteren (M7 × 0,75, Ø12 × 2 mm) ligger i en forsenkning i toppen under knotten, låsetappen i en spalte
ec11Mut = 12.6; ec11MutH = 2.2; ec11Tapp = [0, -7.8];   // tappen (ca. 1,2 × 1 mm) 7,8 mm fra akselen, mot skjermen

c_lys = [0.92, 0.91, 0.88]; c_mork = [0.14, 0.14, 0.15]; c_gull = [0.85, 0.62, 0.25];

// ---------- hjelpere ----------
module rr(w, d, r) { offset(r) offset(-r) square([w, d], center = true); }
module plan(o = 0) { offset(delta = o) rr(W, Dp, R); }

// ---------- kjerne ----------
inn = -(sl + sg);                  // kjernens yttervegg
module kjerne() {
  difference() {
    union() {
      translate([0, 0, z0]) linear_extrude(z1 - z0) difference() { plan(inn); plan(inn - t); }
      // frontblokk: element bakfra, 45° skrå under og over (printes stående uten støtte)
      intersection() {
        translate([0, 0, z0]) linear_extrude(z1 - z0) plan(inn - 0.01);
        hull() {   // bakflaten er flat i drvZ ± 46 (elementets ramme Ø86), 45° ut mot fronten over og under
          translate([-W, -Dp/2, drvZ - 46 - blk]) cube([2 * W, 1, 92 + 2 * blk]);
          translate([-W, -Dp/2 + blk - 1, drvZ - 46]) cube([2 * W, 1, 92]);
        }
      }
      for (p = rodP) translate([p[0], p[1], z0]) cylinder(d = bossD, h = z1 - 8 - z0);   // lokkets tårn tar de siste 8 mm
      // ribbe fra hvert tårn ut til hjørneveggen (stiver av og holder tårnet i veggen)
      for (p = rodP) let(c = [sign(p[0]) * (W/2 - R), sign(p[1]) * (Dp/2 - R)], v = p - c, u = v / norm(v))
        hull() { translate([p[0], p[1], z0]) cylinder(d = 3, h = z1 - 8 - z0); translate([c[0] + u[0] * (R + inn - t/2), c[1] + u[1] * (R + inn - t/2), z0]) cylinder(d = 2, h = z1 - 8 - z0); }
    }
    for (p = rodP) translate([p[0], p[1], z0 - 1]) cylinder(d = rodD, h = z1 - z0 + 2);
    // tunnel og element
    translate([0, -Dp/2 - 1, drvZ]) rotate([-90, 0, 0]) cylinder(d = drvTun, h = blk + 2);
    for (f = plFeste) translate([f[0], -Dp/2 + blk + 0.01, drvZ + f[1]]) rotate([90, 0, 0]) cylinder(d = ins, h = insL);   // innpressmuttere for elementplata
    // I/O bak
    translate([ioX - 8, Dp/2 + 1, dcZ]) rotate([90, 0, 0]) cylinder(d = dcD, h = -inn + t + 2);
    translate([ioX + 8, Dp/2 + 1, usbZ]) rotate([90, 0, 0]) linear_extrude(-inn + t + 2) offset(1.6) square([usbW - 3.2, usbH - 3.2], center = true);
  }
}

// ---------- bunnplate ----------
module bunn() {
  difference() {
    union() {
      hull() {   // 1 mm fas nederst
        linear_extrude(0.01) plan(-1);
        translate([0, 0, 1]) linear_extrude(bpT - 1) plan(0);
      }
      // sentrerer kjernen: kant langs de rette veggene (hjørnene er fri for stangtårnene)
      translate([0, 0, bpT - 0.01]) linear_extrude(2) intersection() {
        difference() { plan(inn - t - 0.3); plan(inn - t - 2.3); }
        union() { square([W - 2 * R, 2 * Dp], center = true); square([2 * W, Dp - 2 * R], center = true); }
      }
      translate([portP[0], portP[1], 0]) cylinder(d = portD + 2 * portW, h = portL);      // port opp i kammeret
      for (p = [[-30, -8], [30, -8], [-30, 14], [30, 14]]) translate([p[0], p[1], bpT]) cylinder(d = 6, h = 6);   // avstandstapper (M2,5)
    }
    for (p = rodP) translate([p[0], p[1], -1]) { cylinder(d = rodD, h = bpT + 4); cylinder(d = 6.4, h = 3.6, $fn = 6); }   // mutterlomme nedenfra
    translate([portP[0], portP[1], -1]) cylinder(d = portD, h = portL + 2);
    translate([portP[0], portP[1], -0.01]) cylinder(d1 = portD + 4, d2 = portD, h = 2);   // avrundet munning (fas)
    for (p = [[-30, -8], [30, -8], [-30, 14], [30, 14]]) translate([p[0], p[1], bpT]) cylinder(d = 2.2, h = 7);
    for (p = rodP) translate([p[0], p[1], -0.01]) cylinder(d = fot, h = fotH);   // gummiføttene rett under stengene (skjuler mutterne)
  }
}

// ---------- lokk ----------
module lokk_ytre() {   // toppkant R4 som flater ut i 45° (printes med toppen ned)
  bf = rT * (1 - cos(45));
  hull() {
    translate([0, 0, z1]) linear_extrude(capT - rT) plan(0);
    for (a = [0:9:45]) translate([0, 0, z1 + capT - rT + rT * sin(a)]) linear_extrude(0.01) plan(-rT * (1 - cos(a)));
    translate([0, 0, H - 0.01]) linear_extrude(0.01) plan(-rT * (1 - cos(45)) - (rT - rT * sin(45)));
  }
}
module lokk() {
  difference() {
    union() {
      lokk_ytre();
      translate([0, 0, z1 - 4]) linear_extrude(4.01) difference() { plan(inn - t - 0.25); plan(inn - t - 3.25); }   // krage inn i kjernen
      intersection() {   // tårnene for stengene, klippet til innsiden av kjernen
        for (p = rodP) translate([p[0], p[1], z1 - 8]) cylinder(d = bossD, h = 8.01);
        translate([0, 0, z1 - 9]) linear_extrude(10) plan(inn - t - 0.25);
      }
      for (k = kortHull) translate([k[0], k[1], boardZ]) cylinder(d = 6, h = z1 - boardZ + 0.01);          // knappekortets tapper
      // skjermramme under lokket: rundt glasset og ned til kortet, med tårn for kortets fire skruer
      translate([0, dispY, H - skD]) linear_extrude(skD - capT + 0.01) rr(glW + 0.8 + 6, glH + 0.8 + 6, 3);
      for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, dispY + sv * dHoleV, H - skD]) cylinder(d = 5.5, h = skD - capT + 0.01);
    }
    for (p = rodP) translate([p[0], p[1], z1 - 8.1]) cylinder(d = ins, h = insL);
    for (x = btnX) translate([x, btnY, z1 - 1]) cylinder(d = capHole, h = capT + 2);
    for (x = btnX) translate([x, btnY, H - 0.6]) cylinder(d1 = capHole, d2 = capHole + 1.2, h = 0.61);
    translate([0, encY, z1 - 1]) cylinder(d = ec11D, h = capT + 2);
    translate([0, encY, H - ec11MutH]) cylinder(d = ec11Mut, h = ec11MutH + 1);              // EC11-mutteren i toppen, under knotten
    translate([ec11Tapp[0], encY + ec11Tapp[1], z1 - 0.01]) translate([-0.8, -0.7, 0]) cube([1.6, 1.4, 2.0]);   // låsetappen (blind spalte)
    for (k = kortHull) translate([k[0], k[1], boardZ - 0.1]) cylinder(d = 1.8, h = 5);           // M2 × 6 selvgjengende
    // skjerm: forsenkning for ruta, vindu med 45° fas, glasslomme og flatkabel nedenfra, skruehull
    translate([0, dispY, H - ruteRec]) linear_extrude(ruteRec + 1) rr(ruteW + 0.4, ruteH + 0.4, 2.2);
    hull() {
      translate([0, dispY, H - skD + glT - 0.01]) linear_extrude(0.01) square([winW, winH], center = true);
      translate([0, dispY, H - ruteRec - 0.01]) linear_extrude(0.02) square([winW + 2 * (skD - glT - ruteRec), winH + 2 * (skD - glT - ruteRec)], center = true);
    }
    translate([0, dispY, H - skD - 0.01]) linear_extrude(glT + 0.01) square([glW + 0.8, glH + 0.8], center = true);
    translate([0, dispY - glH/2 - fpcL/2, H - skD - 0.01]) linear_extrude(glT + 0.01) square([fpcW + 1.0, fpcL + 1.0], center = true);
    for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, dispY + sv * dHoleV, H - skD - 0.01]) cylinder(d = 1.8, h = 4.5);
  }
}
module rute() { translate([0, dispY, H - ruteRec]) linear_extrude(ruteT) rr(ruteW, ruteH, 2); }
module skjerm() {   // modulen (bare for bildene og kollisjonssjekken)
  translate([0, dispY, H - skD]) linear_extrude(glT) square([glW, glH], center = true);
  translate([0, dispY, H - skD - 1.6]) difference() {
    linear_extrude(1.6) square([pcbW, pcbH], center = true);
    for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, sv * dHoleV, -1]) cylinder(d = 3, h = 4);
  }
}
module skjermflate() { translate([0, dispY, H - skD + glT + 0.02]) linear_extrude(0.02) square([actW, actH], center = true); }

// ---------- knott og knapper ----------
module knott_lok() {
  difference() {
    union() {
      cylinder(d = knobD - 2, h = knobH);
      cylinder(d = knobD, h = knobH - 1.5);
      translate([0, 0, knobH - 1.5]) cylinder(d1 = knobD, d2 = knobD - 3, h = 1.5);
    }
    for (a = [0:10:350]) rotate([0, 0, a]) translate([knobD/2 + 0.2, 0, -1]) cylinder(d = 1.4, h = knobH - 2, $fn = 12);
    translate([0, 0, knobH - 0.8]) cylinder(d = knobD - 8, h = 1);
    translate([0, 0, -0.01]) intersection() { cylinder(d = shaftD, h = 11); translate([-shaftD/2, -shaftD/2 + (shaftD - shaftFlat), 0]) cube([shaftD, shaftFlat, 11]); }
    translate([0, knobD/2 - 3.5, knobH - 0.6]) cylinder(d = 1.6, h = 1);
  }
}
module knott() { translate([0, encY, H + 0.6]) knott_lok(); }
module power_icon(r) {
  difference() { circle(r); circle(r - 0.8); translate([-1.0, 0]) square([2.0, r + 1]); }
  translate([-0.4, -0.3]) square([0.8, r + 0.8]);
}
module knapp_lok(i) {   // toppen ved z = capUp over lokket, flensen under lokket
  difference() {
    union() {
      translate([0, 0, -capT]) cylinder(d = capD, h = capT + capUp - 0.3);
      translate([0, 0, capUp - 0.3]) cylinder(d1 = capD, d2 = capD - 0.8, h = 0.3);
      translate([0, 0, -capT - flT]) cylinder(d = flD, h = flT);
      translate([0, 0, -capT - flT - 0.6]) cylinder(d = 2.6, h = 0.61);   // nupp mot bryteren
    }
    translate([0, 0, capUp - 0.4]) linear_extrude(0.41) {
      if (i == 0) power_icon(2.4); else text(str(i), size = 4.6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
    }
  }
}
module knapper() { for (i = [0:4]) translate([btnX[i], btnY, H]) knapp_lok(i); }

// elementplata i montert stilling (y fra blokkas bakside og bakover); i plataes egne koordinater: (x, z) = plan, y = tykkelse
module elementplate_lok() {   // forsiden (mot blokka) i z = 0, baksiden (mot elementet) i z = plT
  difference() {
    translate([-plW/2, -plW/2, 0]) linear_extrude(plT) offset(r = plR) offset(-plR) square(plW);
    translate([0, 0, -1]) cylinder(d = el_utsp(E), h = plT + 2, $fn = 96);
    translate([0, 0, -0.01]) cylinder(d1 = el_utsp(E) + 2 * 1.5, d2 = el_utsp(E), h = 1.5, $fn = 96);    // fas mot blokka
    for (p = el_hullpos(E)) translate([p[0], p[1], -1]) {
      cylinder(d = 3.4, h = plT + 2, $fn = 24);                                                  // M3 gjennom plata og rammen
      translate([0, 0, 1]) cylinder(d1 = 6.6, d2 = 3.4, h = 1.6, $fn = 24);                      // senkehode i flukt med forsiden
    }
    for (f = plFeste) translate([f[0], f[1], -1]) {
      cylinder(d = 3.4, h = plT + 2, $fn = 24);                                                  // M3 × 10 inn i blokka
      translate([0, 0, plT + 1 - 1.6]) cylinder(d1 = 3.4, d2 = 6.6, h = 1.61, $fn = 24);          // senkehode i flukt med baksiden
    }
  }
}
module plate_pos() { translate([0, -Dp/2 + blk, drvZ]) rotate([-90, 0, 0]) mirror([0, 1, 0]) children(); }   // lokal (x, y) → (x, z)
module elementplate() { plate_pos() elementplate_lok(); }
// elementet (bare for bildene og kollisjonssjekken): rammen mot elementplata bakfra
module element() { plate_pos() translate([0, 0, plT]) el_modell(E); }
// knappekortet og EC11 (bare for bildene og kollisjonssjekken)
module knappekort() {
  translate([0, kortY, boardZ - 1.6]) difference() {
    linear_extrude(1.6) square([kortW, kortH], center = true);
    for (k = kortHull) translate([k[0], k[1] - kortY, -1]) cylinder(d = 2.4, h = 4);
  }
  for (x = btnX) translate([x - 3, btnY - 3, boardZ]) cube([6, 6, 3.5]);                  // bryterhus
  for (x = btnX) translate([x, btnY, boardZ]) cylinder(d = 3.5, h = 5.0);                  // stempel (5 mm)
}
module ec11() {
  translate([0, encY, z1 - 6.5]) translate([-6.2, -6.7, 0]) cube([12.4, 13.4, 6.5]);       // hus under lokket
  translate([0, encY, z1 - 0.01]) cylinder(d = 7, h = capT - ec11MutH + 0.01);           // gjenget hals gjennom lokket
  translate([0, encY, H - ec11MutH]) difference() { cylinder(d = 12, h = 2, $fn = 6); translate([0, 0, -1]) cylinder(d = 7.2, h = 4); }   // mutter
}
// gjengestenger (bare for bildene)
module stenger() { for (p = rodP) translate([p[0], p[1], 1.5]) cylinder(d = 3, h = z1 - 8 + insL - 2); }

// logo: SKJOLD i gull, 0,6 mm innfelt i hylsas helt bånd foran nede (eget legeme, egen farge, samme utskrift som hylsa)
logoZ = z0 + 7; logoT = 0.6;
module logo_2d() { text("SKJOLD", size = 5.6, font = "Liberation Sans:style=Bold", spacing = 1.25, halign = "center", valign = "center"); }
module logo_form(e = 0) { translate([0, -Dp/2 - e, logoZ]) rotate([-90, 0, 0]) mirror([0, 1, 0]) linear_extrude(logoT + e) offset(e) logo_2d(); }
module hylse_stl() { import("stl_asm/hylse.stl"); }
module logo_stl() { import("stl_asm/logo.stl"); }
module samlet(ex = 0) {
  color(c_mork) kjerne();
  color(c_lys) translate([0, 0, -ex]) bunn();
  color(c_lys) translate([0, 0, 1.4 * ex]) lokk();
  color(c_gull) translate([0, 0, 2.2 * ex]) knott();
  color(c_mork) translate([0, 0, 1.8 * ex]) knapper();
  color(c_lys) translate([0, -ex, 0]) hylse_stl();
  color(c_gull) translate([0, -ex, 0]) logo_stl();
}

if (part == "kjerne") translate([0, 0, -z0]) kjerne();                        // stående
else if (part == "bunn") bunn();                                              // undersiden ned
else if (part == "lokk") translate([0, 0, H]) rotate([180, 0, 0]) lokk();     // toppen ned
else if (part == "knott") translate([0, 0, knobH]) rotate([180, 0, 0]) knott_lok();
else if (part == "rute") linear_extrude(ruteT) rr(ruteW, ruteH, 2);
else if (part == "a_rute") rute(); else if (part == "a_skjerm") skjerm(); else if (part == "a_skjermflate") skjermflate();
else if (part == "knapp") for (i = [0:4]) translate([i * (flD + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(i);
else if (part == "a_kjerne") kjerne(); else if (part == "a_bunn") bunn(); else if (part == "a_lokk") lokk();
else if (part == "a_knott") knott(); else if (part == "a_knapp") knapper(); else if (part == "a_stenger") stenger();
else if (part == "a_element") element();
else if (part == "elementplate") elementplate_lok(); else if (part == "a_elementplate") elementplate();
else if (part == "a_knappekort") knappekort(); else if (part == "a_ec11") ec11();
else if (part == "a_logo") logo_form(0); else if (part == "logo_kutt") logo_form(0.01);
else if (part == "eksplodert") samlet(30);
else samlet();
