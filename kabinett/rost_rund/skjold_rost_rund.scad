// Skjold Røst Rund – alternativ Røst: avrundet kropp med grill hele veien rundt, knapper og gullknott på toppen.
// Eget design i Skjolds formspråk (sekskantgrill, gullknott, SKJOLD i gull foran nede). Lisens: CC BY-NC-SA 4.0.
//
// Oppbygging (alt holdes sammen av fire M3-gjengestenger fra lokket ned gjennom kjernen til bunnplaten, ingen synlige skruer):
//   lokk    – topp med fem knapper (av/på, favoritt 1–4), 2,42″ OLED og EC11-volumknott; printes med toppen ned
//   knappeholder – under lokket: lommer for de fem bryterne og to skinner som klemmer skjermkortet; bunnen ned
//   kjerne  – mørk indre kasse: rør med frontblokk for 3″-elementet, tunnel og stangtårn; printes stående
//   hylse   – grillen rundt hele kroppen (lages av lag_hylse.py, manifold3d), med helt bånd og SKJOLD nederst foran
//   bunn    – bunnplate med bassrefleksport ned, avstandstapper for elektronikken og forsenkninger for gummiføtter
// Koordinater: x tvers, y fra front (−) til bak (+), z opp (0 = bordet, uten føtter).
// part: lokk | kjerne | bunn | knott | knapp | knappeholder | rute | elementplate | samlet | eksplodert | under |
//       a_<del> (montert stilling)
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
drvZ = 78; drvTun = 80; blk = 16;    // elementets senter, tunnelen gjennom frontblokka (fast, Ø80, fylles av elementplatas krage), blokkas dybde
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
// skjerm: 2,42″ OLED 128×64 (SSD1309, I²C, hvit), samme modul og samme mål som Røst (se ../rost/LES_MEG.md, «Skjermen»):
//   kort 70,08 × 48,04 × 1,00 mm, 5,25 mm tykk med glass, glass 62,64 × 39,18, synlig område 57,80 × 29,70,
//   aktivt område 55,40 × 27,78 (128 × 64), 4 hull Ø3 (62,64 × 41,60), pinnerad (GND VDD SCL SDA) langs øvre kant,
//   flatkabel (12,64 mm) ut over nedre kant. Tolket (ikke målsatt): glassets og det aktive områdets plassering i høyden,
//   hullavstanden i høyden og hvor langt flatkabelen stikker ut. Mål din modul og juster.
// Pinneraden vender bakover mot knotten, flatkabelen foran mot knappene. Lokket er bare 5 mm, så glasset ligger i en
// lomme i en skjermramme under lokket (7,5 mm fra toppen til kortet, som på Røst). Kortet ligger flatt mot rammen og
// klemmes opp av knappeholderens to skinner – ingen skruer i skjermen.
dispY = -4;                              // senter av det aktive området = vinduets senter
pcbW = 70.08; pcbH = 48.04; pcbT = 1.0;  // kretskort
modT = 5.25; glT = modT - pcbT;          // kort + glass; glass (med tape/ramme) over kortet: 4,25
glW = 62.64; glH = 39.18;                // glass
vaW = 57.80; vaH = 29.70;                // synlig område
actW = 55.40; actH = 27.78;              // aktivt område (128 × 64)
hullD = 3.0; dHoleX = 62.64 / 2; hullKant = 3.22; dHoleV = pcbH / 2 - hullKant;   // hullene (brukes ikke til skruer)
glOffV = 0;                              // glassets senter i forhold til kortets senter (+ = bakover, mot pinneraden)
aaOffV = ((glH - vaH) - (glW - vaW)) / 2;   // det aktive området 2,32 mm bakover i glasset (smal kant mot pinneraden)
fpcW = 12.64; fpcL = 2.0;                // flatkabelen: bredde, og hvor langt den stikker ut forbi kortets nedre kant
hdrN = 4; hdrFraKant = 2.3;              // pinneraden: 4 × 2,54 mm, ca. 2,3 mm fra kortets øvre kant
skD = 7.5;                               // fra toppen til oversiden av kortet (= skjermrammens underkant)
pcbY = dispY - glOffV - aaOffV;          // kortets senter
glY = pcbY + glOffV;                     // glassets senter
pcbBot = pcbY - pcbH / 2; pcbTopp = pcbY + pcbH / 2;   // nedre kant (flatkabelen, foran) og øvre kant (pinneraden, bak)
pcbZ = H - skD;                          // kortets overside
glKl = 0.4; glTak = pcbZ + glT + 0.15;   // klaring rundt glasset i lomma, og taket i lomma (0,15 mm over glasset)
rammeV = 2.5;                            // skjermrammens vegg rundt glasslomma
winW = actW + 1.2; winH = actH + 1.2;    // vindu: 0,6 mm utenfor det aktive området (innenfor VA), 45° fas opp mot ruta
ruteW = 64; ruteH = 36; ruteT = 1.5; ruteRec = ruteT + 0.2;   // klar rute i flukt med toppen (0,2 mm tape under)
// (ingen hevet ramme rundt ruta: lokket printes med toppen ned, så toppen må være helt flat)
// knappene: 6 × 6 × 5 mm-bryterne står med stempelet 0,2 mm under hettenes nupp
knappefeste = "holder";            // holder: printet knappeholder med lommer for bryterne (ingen hullkort)
                                   // hullkort: bryterne loddet på et hullkort 64 × 20 mm, som skrus på holderens dekk
boardZ = z1 - 6.7;                 // bryternes underkant (= hullkortets overside)
tactB = 6.0; tactH = 5.0; tactHus = 3.5; stempD = 3.5;   // taktbryter: hus 6 × 6 × 3,5, stempel Ø3,5, 5 mm totalt
kortW = 64; kortH = 20; kortT = 1.6; kortY = btnY + 3; kortHull = [[-29.5, btnY + 9], [29.5, btnY + 9]];
// knappeholder (PETG/ASA, printes med bunnen ned, uten støtte): ligger under lokket, skrudd i fire tapper med
// M2 × 6 selvgjengende (ørene nederst). Foran: fem lommer med klemribber for bryterne, spor for beina og en kam for
// ledningene. To skinner går bakover under kantene av skjermkortet og trykker det opp mot skjermrammen.
lommeB = 6.4; lommeRib = 0.25;     // lomme for bryterhuset, klemribber (5,9 mm mellom ribbene: presspasning)
khVegg = 1.2; khVeggH = 3.0;       // lommeveggene (bryterhuset er 3,5 mm høyt)
benV = 2.25; benSpor = 1.3;        // beina: ±2,25 mm fra senter, bøyd ut mot sidene (±x), spor i lommeveggen
dekkT = 2.0;                       // hullkort: dekket kortet skrus på (over spissen av elementplatas krage)
khB0 = knappefeste == "holder" ? boardZ - 2.0 : boardZ - kortT - dekkT;   // holderens underside
khXi = dHoleX + hullD / 2 + 0.2;   // skinnene: innenfor kortets kant, utenfor hullene (33,0) …
khXo = khXi + 3.6;                 // … til 36,6
khTop = pcbZ - pcbT - 0.1;         // skinnenes overside, 0,1 mm under kortet, med en klemribbe som står 0,1 mm opp i det
klemH = 0.2;
khY0 = -38;                        // skinnene: fra like bak de fremre stangtårnene …
khY1 = pcbTopp + 1.5;              // … til bak kortet
kamY = btnY + lommeB / 2 + khVegg + 0.3; ribT = 1.4;   // kammen bak lommene
barX = btnX[4] + lommeB / 2 + khVegg + 0.6;            // lommelista: ±31 (fri for de fremre stangtårnene)
barY0 = btnY - lommeB / 2 - khVegg - 0.8;
khOre = [for (sx = [-1, 1], y = [-31, pcbTopp - 4]) [sx * 40, y]];   // ører og lokkets tapper for M2 × 6
oreD = 8; tappD = 6;
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
    // tunnelen som dråpe: rund nede, 45° tak oppe (spiss), så toppen bygger seg opp uten bro eller støtte (stående print)
    translate([0, -Dp/2 - 1, drvZ]) rotate([-90, 0, 0]) mirror([0, 1, 0]) linear_extrude(blk + 2) tunnel2d();
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
      for (k = khOre) translate([k[0], k[1], khB0 + 2]) cylinder(d = tappD, h = z1 - khB0 - 2 + 0.01);    // knappeholderens tapper
      // skjermramme under lokket: rundt glasslomma og ned til kortet (kortet ligger flatt mot undersiden av rammen)
      translate([0, glY, pcbZ]) linear_extrude(z1 - pcbZ + 0.01) rr(glW + 2 * glKl + 2 * rammeV, glH + 2 * glKl + 2 * rammeV, 3);
    }
    for (p = rodP) translate([p[0], p[1], z1 - 8.1]) cylinder(d = ins, h = insL);
    for (x = btnX) translate([x, btnY, z1 - 1]) cylinder(d = capHole, h = capT + 2);
    for (x = btnX) translate([x, btnY, H - 0.6]) cylinder(d1 = capHole, d2 = capHole + 1.2, h = 0.61);
    translate([0, encY, z1 - 1]) cylinder(d = ec11D, h = capT + 2);
    translate([0, encY, H - ec11MutH]) cylinder(d = ec11Mut, h = ec11MutH + 1);              // EC11-mutteren i toppen, under knotten
    translate([ec11Tapp[0], encY + ec11Tapp[1], z1 - 0.01]) translate([-0.8, -0.7, 0]) cube([1.6, 1.4, 2.0]);   // låsetappen (blind spalte)
    for (k = khOre) translate([k[0], k[1], khB0 + 2 - 0.1]) cylinder(d = 1.8, h = 5.5);       // M2 × 6 selvgjengende
    // skjerm: forsenkning for ruta, vindu med 45° fas, lomme nedenfra for glasset, flatkabelen og pinneraden
    translate([0, dispY, H - ruteRec]) linear_extrude(ruteRec + 1) rr(ruteW + 0.4, ruteH + 0.4, 2.2);
    hull() {
      translate([0, dispY, glTak - 0.01]) linear_extrude(0.01) square([winW, winH], center = true);
      translate([0, dispY, H - ruteRec - 0.01]) linear_extrude(0.02) square([winW + 2 * (H - ruteRec - glTak), winH + 2 * (H - ruteRec - glTak)], center = true);
    }
    translate([0, glY, pcbZ - 0.01]) linear_extrude(glTak - pcbZ + 0.01) square([glW + 2 * glKl, glH + 2 * glKl], center = true);
    translate([-fpcW/2 - 0.6, pcbBot - fpcL - 0.6, pcbZ - 0.01]) cube([fpcW + 1.2, glY - glH/2 - pcbBot + fpcL + 0.6 + 0.1, glTak - pcbZ + 0.01]);   // flatkabelen
    translate([0, pcbTopp - hdrFraKant, pcbZ - 0.01]) linear_extrude(1.5) square([hdrN * 2.54 + 2.4, 3.6], center = true);   // pinnestumpene i pinneraden
  }
}
module rute() { translate([0, dispY, H - ruteRec]) linear_extrude(ruteT) rr(ruteW, ruteH, 2); }
module skjerm() {   // modulen (bare for bildene og kollisjonssjekken): glass, kort, flatkabel og ledninger i pinneraden
  translate([0, glY, pcbZ]) linear_extrude(glT) square([glW, glH], center = true);
  translate([0, pcbY, pcbZ - pcbT]) difference() {
    linear_extrude(pcbT) square([pcbW, pcbH], center = true);
    for (sx = [-1, 1], sv = [-1, 1]) translate([sx * dHoleX, sv * dHoleV, -1]) cylinder(d = hullD, h = 4);
  }
  translate([-fpcW/2, pcbBot - fpcL, pcbZ - pcbT - 0.4]) cube([fpcW, fpcL + 3, pcbT + 0.4 + 2.0]);   // flatkabelen rundt nedre kant
  for (i = [0:hdrN - 1]) translate([(i - (hdrN - 1) / 2) * 2.54, pcbTopp - hdrFraKant, pcbZ - pcbT - 1.5]) cylinder(d = 1.6, h = 1.5 + pcbT + 0.5, $fn = 16);
}
module skjermflate() { translate([0, dispY, pcbZ + glT + 0.02]) linear_extrude(0.02) square([actW, actH], center = true); }

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

// tunnelens tverrsnitt (dråpe: rund nede, 45° spiss oppe), i plataes egne koordinater (x, y = opp); o = klaring
module tunnel2d(o = 0) { offset(delta = -o) hull() { circle(d = drvTun, $fn = 96); translate([0, drvTun/2 * sqrt(2)]) square(0.01, center = true); } }
// elementplata i montert stilling (y fra blokkas bakside og bakover); i plataes egne koordinater: (x, y) = plan, z = tykkelse.
// Krage foran fyller hele tunnelen, så åpningen ved elementet er nøyaktig elementets utsparing og vider seg ut i 45° mot
// fronten (en kort bølgeleder; ingen kant eller hulrom foran membranen). Elementet skrus bakfra i innpressmuttere i plata.
krageL = blk - sl - sg; krageKl = 0.3; krageLepp = 1.2;
module elementplate_lok() {   // forsiden (mot blokka) i z = 0, kragen fram til z = -krageL, baksiden (mot elementet) i z = plT
  rU = drvTun/2 - krageKl - krageLepp;                                                           // åpningen i fronten
  difference() {
    union() {
      translate([-plW/2, -plW/2, 0]) linear_extrude(plT) offset(r = plR) offset(-plR) square(plW);
      intersection() {   // kragen slutter i flukt med kjernens front, også der den buer rundt hjørnene
        translate([0, 0, -krageL]) linear_extrude(krageL + 0.01) tunnel2d(krageKl);
        mirror([0, 1, 0]) rotate([90, 0, 0]) translate([0, Dp/2 - blk, -60]) linear_extrude(120) plan(inn);
      }
    }
    translate([0, 0, -1]) cylinder(d = el_utsp(E), h = plT + 2, $fn = 96);
    translate([0, 0, -krageL - 0.01]) hull() {                                                   // 45° utvidelse mot fronten
      cylinder(r = rU, h = 0.01, $fn = 96);
      translate([0, 0, max(0.01, rU - el_utsp(E)/2)]) cylinder(d = el_utsp(E), h = krageL - max(0.01, rU - el_utsp(E)/2) + 0.02, $fn = 96);
    }
    for (p = el_hullpos(E)) translate([p[0], p[1], plT - insL]) cylinder(d = ins, h = insL + 1, $fn = 24);   // M3-innpressmuttere bakfra
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
// taktbryterne, hullkortet og EC11 (kjøpte deler, bare for bildene og kollisjonssjekken)
module brytere() {
  for (x = btnX) translate([x, btnY, boardZ]) {
    translate([-tactB/2, -tactB/2, 0]) cube([tactB, tactB, tactHus]);                     // bryterhus
    cylinder(d = stempD, h = tactH, $fn = 24);                                               // stempel (5 mm)
    if (knappefeste == "holder")                                                             // beina bøyd ut mot sidene
      for (sx = [-1, 1], sv = [-1, 1]) translate([sx * (tactB/2 + 1.5) - 1.5, sv * benV - 0.35, 0]) cube([3.0, 0.7, 0.3]);
  }
}
module knappekort() {   // bare med knappefeste = "hullkort"
  translate([0, kortY, boardZ - kortT]) difference() {
    linear_extrude(kortT) square([kortW, kortH], center = true);
    for (k = kortHull) translate([k[0], k[1] - kortY, -1]) cylinder(d = 2.4, h = 4);
  }
}
// ---------- knappeholder (printes, PETG/ASA, bunnen ned) ----------
module knappeholder() {
  holder = knappefeste == "holder";
  difference() {
    union() {
      if (holder) {
        translate([-barX, barY0, khB0]) cube([2 * barX, kamY + ribT - barY0, boardZ - khB0]);              // lommelista
        for (x = btnX) translate([x, btnY, boardZ - 0.01]) linear_extrude(khVeggH + 0.01) difference() {
          square(lommeB + 2 * khVegg, center = true); square(lommeB, center = true); }                        // lommer
        for (x = btnX) translate([x, btnY, boardZ - 0.01]) linear_extrude(khVeggH + 0.01)                   // klemribber
          for (a = [0:90:270]) rotate(a) translate([lommeB/2 - lommeRib, -0.5]) square([lommeRib + 0.01, 1.0]);
        translate([-barX, kamY, khB0]) cube([2 * barX, ribT, boardZ + khVeggH - khB0]);                     // kam bak lommene
      } else
        translate([-kortW/2, kortY - kortH/2, khB0]) cube([kortW, kortH, dekkT]);                           // dekk for hullkortet
      translate([-khXo, khY0, khB0]) cube([2 * khXo, (holder ? kamY + ribT : kortY + kortH/2) - khY0, 2.0]); // tverrstykke til skinnene
      for (sx = [-1, 1]) {
        translate([sx > 0 ? khXi : -khXo, khY0, khB0]) cube([khXo - khXi, khY1 - khY0, khTop - khB0]);      // skinner
        translate([sx * (khXi + 0.6), 0, 0]) hull() {                                                         // klemribbe med skrå ender
          translate([-0.4, pcbBot + 3, khTop - 0.01]) cube([0.8, pcbH - 6, 0.01]);
          translate([-0.15, pcbBot + 4.5, khTop - 0.01]) cube([0.3, pcbH - 9, klemH + 0.01]);
        }
      }
      for (k = khOre) hull() {                                                                              // ører
        translate([k[0], k[1], khB0]) cylinder(d = oreD, h = 2.0);
        translate([sign(k[0]) * khXo - (k[0] > 0 ? 1 : 0), k[1] - oreD/2, khB0]) cube([1, oreD, 2.0]);
      }
    }
    for (k = khOre) translate([k[0], k[1], khB0 - 1]) cylinder(d = 2.4, h = 4);                            // M2 × 6
    if (holder) {
      for (x = btnX, sx = [-1, 1], sv = [-1, 1])                                                            // spor for beina
        translate([x + sx * (lommeB/2 + khVegg/2) - khVegg/2 - 0.1, btnY + sv * benV - benSpor/2, boardZ]) cube([khVegg + 0.2, benSpor, khVeggH + 1]);
      for (x = concat([btnX[0] - 4.0], [for (i = [0:4]) btnX[i] + 4.0]))                  // kam: én ledning per spor (GND lengst til venstre)
        translate([x - 0.7, kamY - 0.1, boardZ]) cube([1.4, ribT + 0.2, 10]);
    } else
      for (k = kortHull) translate([k[0], k[1], khB0 - 1]) cylinder(d = 1.8, h = dekkT + 2);                // M2 × 6 for hullkortet
  }
}
module ec11() {
  translate([0, encY, z1 - 6.5]) translate([-6.2, -6.7, 0]) cube([12.4, 13.4, 6.5]);       // hus under lokket
  translate([0, encY, z1 - 0.01]) cylinder(d = 7, h = capT - ec11MutH + 0.01);           // gjenget hals gjennom lokket
  translate([0, encY, H - ec11MutH]) difference() { cylinder(d = 12, h = 2, $fn = 6); translate([0, 0, -1]) cylinder(d = 7.2, h = 4); }   // mutter
}
// gjengestenger (bare for bildene)
module stenger() { for (p = rodP) translate([p[0], p[1], 1.5]) cylinder(d = 3, h = z1 - 8 + insL - 2); }

// logo: SKJOLD i gull, 1 mm innfelt i hylsas helt bånd foran nede (eget legeme, egen farge, samme utskrift som hylsa)
logoZ = z0 + 7; logoT = 1.0;          // 1 mm dypt i den 1,8 mm tykke veggen
use <../fonter/Inter-Bold.otf>   // Inter Bold ligger i repoet (ren J uten nebb, samme logo på alle maskiner)
module logo_2d() { text("SKJOLD", size = 7, font = "Inter:style=Bold", spacing = 1.15, halign = "center", valign = "center"); }
module logo_form(e = 0) { translate([0, -Dp/2 - e, logoZ]) rotate([-90, 0, 0]) mirror([0, 1, 0]) linear_extrude(logoT + e) offset(e) logo_2d(); }
module hylse_stl() { import("stl_asm/hylse.stl"); }
module logo_stl() { import("stl_asm/logo.stl"); }
module samlet(ex = 0) {
  color(c_mork) kjerne();
  color(c_lys) translate([0, 0, -ex]) bunn();
  color(c_lys) translate([0, 0, 1.4 * ex]) lokk();
  color(c_gull) translate([0, 0, 2.2 * ex]) knott();
  color(c_mork) translate([0, 0, 1.8 * ex]) knapper();
  translate([0, 0, 0.9 * ex]) { color([0.05, 0.05, 0.06]) skjerm(); color(c_mork) brytere(); color([0.55, 0.62, 0.70]) knappeholder(); if (knappefeste == "hullkort") color([0.18, 0.42, 0.24]) knappekort(); }
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
else if (part == "elementplate") translate([0, 0, plT]) mirror([0, 0, 1]) elementplate_lok();   // baksiden ned, kragen opp
else if (part == "a_elementplate") elementplate();
else if (part == "a_knappekort") knappekort(); else if (part == "a_ec11") ec11();
else if (part == "knappeholder") translate([0, 0, -khB0]) knappeholder();   // bunnen ned
else if (part == "a_knappeholder") knappeholder(); else if (part == "a_bryter") brytere();
else if (part == "under") { color(c_lys) lokk(); color(c_mork) knapper(); color([0.05, 0.05, 0.06]) skjerm(); color(c_mork) brytere();
  color([0.55, 0.62, 0.70]) knappeholder(); if (knappefeste == "hullkort") color([0.18, 0.42, 0.24]) knappekort(); ec11(); }
else if (part == "a_logo") logo_form(0); else if (part == "logo_kutt") logo_form(0.01);
else if (part == "eksplodert") samlet(30);
else samlet();
