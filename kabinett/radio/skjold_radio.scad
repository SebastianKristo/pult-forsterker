// Skjold Radio – bordradio med skjerm, seks favorittknapper, navigasjonshjul og volumknott. Parametrisk OpenSCAD.
// Eget Skjold-design: en lav, liggende bordradio der alt vender mot deg. Den loddrette fronten er delt i to av en
// tynn, loddrett gullist: til venstre en mørk grill med vannrette spalter foran ett 3″-element (mono), til høyre et rolig
// betjeningspanel i tre lag – skjermen øverst, favoritt 1–6 i én rad rett under, og nederst av/på, volumknotten og
// det store gullhjulet. Myke hjørner (R14) sett forfra som Node/Røst, faset frontkant, lys (eller matt sort) kropp,
// mørk grill og knapper, gull hjul, volumknott og list, og SKJOLD preget over skjermen.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater: x = bredde (0 … W), y = dybde (0 = fronten, D = bak), z = høyde (0 = innsiden av gulvet).
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_radio.scad
// part:  kropp | bak | kammer | lokk | grill | brakett | list | knott | volum | knapp (6 favoritter + av/på) |
//        samlet | eksplodert | A_<del> (montert stilling, for sjekk_modell.py)
// STL-ene eksporteres liggende slik de skal printes (FDM) – samme filer kan bestilles i resin/MJF (se LES_MEG.md).
// Alle deler er åpne skall (ingen lukkede hulrom), så resin renner ut uten egne dreneringshull.

part = "samlet";
ex = 0;                          // eksplosjonsavstand (eksplodert visning)
farge = "lys";                   // lys | mork
$fn = 64;

// ---------- ytre mål ----------
W = 240; D = 125; H = 137;       // bredde, dybde, høyde over gulvets innside (utvendig høyde H + t = 140)
R = 14;                          // hjørnene sett forfra (alle fire)
t = 3.0;                         // vegg og gulv (≥ 2 mm for resin/MJF; 7 linjer à 0,42 mm på FDM)
c = 2.5;                         // fas rundt frontkanten
bkT = 3;                         // bakplata (ligger inne i åpningen bak, flukt med kanten)

// Profilen sett forfra (x, z), forskjøvet o innover
module prof(o = 0) { translate([o, -t + o]) rrect(W - 2*o, H + t - 2*o, max(1, R - o)); }
module ext_y(y0, y1) { translate([0, y1, 0]) rotate([90, 0, 0]) linear_extrude(y1 - y0) children(); }   // 2D (x, z) → y0 … y1
// Lokal ramme på frontflaten: u = x, v = z, w ut av fronten (w = 0 = frontflaten, w = −t = innsiden av frontveggen).
module front_ramme() { rotate([90, 0, 0]) children(); }

// ---------- høyttaler og lydkammer (mono: ett 3″-element i ett lukket kammer bak venstre halvdel) ----------
drvCut = 72;  drvF = 86;  drvFT = 4;      // 3″ fullrange (Dayton Audio RS75-4): utsparing, rammens Ø og tykkelse – mål ditt element
drvPCD = 82;                              // skruehullsirkel
kX0 = 22;  kW = 86;                       // kammer: x 22 … 108
kY0 = t + 5.6;  kD = 92;                  // baffelens forside 5,6 mm bak fronten (plass til grill, grillduk og elementrammen)
kZ0 = 0;  kH = 124;                       // står på gulvet, 124 mm høyt
kT = 2.8;  baffT = 7;                     // kammervegg og baffel
drvX = kX0 + kW/2;  drvZ = kZ0 + kH/2;    // elementet midt på baffelen
kOff = kT + 2.5;                          // innpressmutter-tårnene for lokket ligger langs sideveggene (smelter inn i veggene)
kBx = [kX0 + kOff, kX0 + kW - kOff];
kBz = [kZ0 + kOff, kZ0 + kH/2, kZ0 + kH - kOff];
kOre = 8;                                 // ører langs gulvet på utsiden (skrues fra undersiden)
kOreY = [kY0 + 12, kY0 + kD - 12];
// netto volum ≈ 80,4 × 85 × 118,4 mm − tårn og element ≈ 0,75 l (lukket, mono)

// ---------- grill (venstre halvdel av fronten) ----------
gX0 = 14;  gX1 = 114;  gZ0 = 8;  gZ1 = 126;  gR = 6;   // grillåpningen: 100 × 118 mm, samme marg oppe og nede
gT = 3.0;  gFl = 2.5;                      // grillens tykkelse = veggen, flens bak
slotW = 2.2; slotP = 4.4;                  // vannrette spalter
slotM = 8;                                 // hel kant rundt spaltene (ribbene mot baffelen sitter oppe og nede)
ribX = [drvX - 15, drvX + 15];             // ribber som holder grillen mot baffelen
// ---------- loddrett gullist mellom grill og panel ----------
lX0 = 118;  lZ0 = gZ0;  lH = 3.5;  lDyp = 1.2;   // spor i fronten (z 8 … 126), lista står 0,4 mm ut

// ---------- betjeningspanel (høyre halvdel av fronten) ----------
scrAW = 96;  scrAH = 56;                   // synlig vindu (4,3″ DSI 800×480, aktivt område ≈ 95 × 54)
scrGW = 106; scrGH = 68;                   // glass/LCD på modulen (lomme bak frontveggen) – mål din skjerm!
scrX = 175;  scrZ = 98;                    // vinduets senter: vindu x 127 … 223, z 70 … 126 (flukt med grillens overkant)
scrB = [[-57, -20], [57, -20], [-57, 20], [57, 20]];   // skruetårn på hver side av modulen (brakett)
btnZ = 60; btnP = 16; btnX0 = scrX - 2.5*btnP;   // favoritter 1–6: rad rett under skjermen (x 135 … 215)
capD = 11; capHole = 11.6; capUp = 0.8; capFl = 15; capFlT = 1.0;
kortX = [btnX0 - 12, btnX0 + 5*btnP + 12]; // tårn for knappekortet (hullkort ca. 110 × 16 mm)
botZ = 28;                                 // nederste rad: av/på, volum og hjulet
pwX = btnX0;                               // av/på under favoritt 1
pwKort = [pwX - 12, pwX + 12];             // tårn for av/på-kortet (lite hullkort ca. 30 × 16 mm)
volX = 161; volZ = botZ;                   // volumknott
volD = 22; volH = 13;
whD = 42;  whH = 15;                       // navigasjonshjul (EC11 med trykk) nede til høyre, flukt med vinduets høyre kant
whX = scrX + scrAW/2 - whD/2; whZ = botZ;
logoZ = 131.6;                             // SKJOLD preget over skjermen
ec11 = 7.2;                                // EC11 M7-gjenge
// ---------- fester ----------
ins = 4.0; insD = 6.0; boss = 8.4; m3 = 3.4; m3k = 6.4;
bakB = [[8.5, -t + 8.5], [W - 8.5, -t + 8.5], [8.5, H - 8.5], [W - 8.5, H - 8.5], [W/2, H - t - 3]];  // tårn for bakplata (x, z)
bakY0 = 20;                                // tårnene starter 20 mm bak fronten (kjegle under, printes uten støtte)
fotXY = [[30, 22], [W - 30, 22], [30, D - 22], [W - 30, D - 22]];             // selvklebende gummiføtter Ø 12
// Raspberry Pi 4 på baksiden av skjermbraketten (85 × 56, hull 58 × 49), sentrert bak skjermen
piH = [[-29, -24.5], [29, -24.5], [-29, 24.5], [29, 24.5]];
piSt = 5;                                  // avstandsstykker
// ---------- bak ----------
dcD = 8.2; jackD = 6.4; usbW = 10; usbH = 4.4;
bakKZ = 22;                                // kontaktene (DC, linje ut, USB-C) nede til høyre, bak forsterkeren
ventGulv = [130, 8, 10, 44, 52];           // luftespalter i gulvet under forsterkeren: x0, deling, antall, y0, lengde

// ---------- farger ----------
lys = farge == "lys";
c_kropp = lys ? [0.93, 0.92, 0.90] : [0.13, 0.13, 0.14];
c_grill = lys ? [0.17, 0.17, 0.18] : [0.30, 0.30, 0.31];
c_gull  = [0.85, 0.62, 0.25];
c_knapp = lys ? [0.18, 0.18, 0.19] : [0.85, 0.62, 0.25];
c_glass = [0.05, 0.07, 0.10];
c_inne  = [0.40, 0.40, 0.42];

// ---------- grunnformer ----------
module rrect(w, d, r) { translate([r, r]) offset(r) square([w - 2*r, d - 2*r]); }
module ytre() { hull() { ext_y(0, 0.01) prof(c); ext_y(c, D) prof(0); } }   // fas rundt frontkanten
module front_hull(o = 0) {   // grillåpningen sett forfra (x, z)
  offset(-o) hull() for (x = [gX0 + gR, gX1 - gR], z = [gZ0 + gR, gZ1 - gR]) translate([x, z]) circle(gR);
}
module list2d(o = 0) { translate([lX0 + o, lZ0 + o]) rrect(lH - 2*o, gZ1 - gZ0 - 2*o, lH/2 - o - 0.05); }

// ---------- kropp (ett skall: front, sider, topp og gulv; åpen bak; printes med fronten ned på platen) ----------
module kropp() {
  difference() {
    union() {
      difference() { ytre(); ext_y(t, D + 1) prof(t); }
      // tårn for bakplata (innpressmuttere bakfra), med kjegle foran så de printes uten støtte
      for (p = bakB) {
        translate([p[0], bakY0, p[1]]) rotate([-90, 0, 0]) cylinder(d = boss, h = D - bkT - bakY0);
        translate([p[0], bakY0 - 7, p[1]]) rotate([-90, 0, 0]) cylinder(d1 = 1, d2 = boss, h = 7.01);
      }
      front_ramme() {
        for (p = scrB) translate([scrX + p[0], scrZ + p[1], -t - 6]) cylinder(d = 7, h = 7);      // skjermbrakett
        for (x = concat(kortX), z = [btnZ]) translate([x, z, -t - 7]) cylinder(d = 7, h = 8);   // knappekort
        for (x = pwKort) translate([x, botZ, -t - 7]) cylinder(d = 7, h = 8);                    // av/på-kort
      }
    }
    for (p = bakB) translate([p[0], D - bkT - insD, p[1]]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD + 0.1);
    // grillåpningen og fals for grillens flens på innsiden
    ext_y(-1, t + 1) front_hull();
    ext_y(t - 0.6, t + 0.6) offset(gFl) front_hull();
    // spor for gullista
    ext_y(-1, lDyp) list2d();
    front_ramme() {
      // skjermvindu med fas, og lomme for glasset bak
      translate([scrX - scrAW/2, scrZ - scrAH/2, -t - 1]) cube([scrAW, scrAH, t + 2]);
      translate([scrX - scrAW/2 - 1, scrZ - scrAH/2 - 1, -0.8]) cube([scrAW + 2, scrAH + 2, 1]);
      translate([scrX - scrGW/2 - 0.3, scrZ - scrGH/2 - 0.3, -t - 1]) cube([scrGW + 0.6, scrGH + 0.6, t - 0.2]);
      for (p = scrB) translate([scrX + p[0], scrZ + p[1], -t - 6.1]) cylinder(d = 2.2, h = 5);   // M2,5 selvgjengende
      // favoritt 1–6 og av/på
      for (i = [0:5]) translate([btnX0 + i*btnP, btnZ, -t - 1]) cylinder(d = capHole, h = t + 2);
      translate([pwX, botZ, -t - 1]) cylinder(d = capHole, h = t + 2);
      for (x = kortX) translate([x, btnZ, -t - 7.1]) cylinder(d = 2.2, h = 6);
      for (x = pwKort) translate([x, botZ, -t - 7.1]) cylinder(d = 2.2, h = 6);
      // hjulet og volumknotten
      for (k = [[whX, whZ, whD], [volX, volZ, volD]]) {
        translate([k[0], k[1], -t - 1]) cylinder(d = ec11, h = t + 2);
        translate([k[0], k[1], -0.6]) cylinder(d = k[2] + 3, h = 1);    // grunn ring under knotten
      }
      // logo SKJOLD preget over skjermen
      translate([scrX, logoZ, -0.6]) linear_extrude(1)
        text("SKJOLD", size = 4, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.4);
    }
    // gulvet: kammerørene (senkeskruer nedenfra), gummiføtter og lufting under forsterkeren
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY)
      translate([x, y, -t - 1]) { cylinder(d = m3, h = t + 2); cylinder(d = m3k, h = 1 + 1.7); }
    for (p = fotXY) translate([p[0], p[1], -t - 1]) cylinder(d = 12.6, h = 1.8);       // 0,8 mm forsenkning
    for (i = [0:ventGulv[2] - 1]) translate([ventGulv[0] + i*ventGulv[1], ventGulv[3], -t - 1]) cube([3, ventGulv[4], t + 2]);
  }
}

// ---------- bakplate (DC, linje ut, USB-C og lufting; skrus i fem tårn) ----------
module bak() {
  difference() {
    ext_y(D - bkT, D) prof(t + 0.3);
    for (p = bakB) translate([p[0], D - bkT - 1, p[1]]) rotate([-90, 0, 0]) {
      cylinder(d = m3, h = bkT + 2); translate([0, 0, bkT + 1 - 1.7]) cylinder(d1 = m3, d2 = m3k, h = 1.71);   // senkeskrue
    }
    translate([140, D - bkT - 1, bakKZ]) rotate([-90, 0, 0]) cylinder(d = dcD, h = bkT + 2);
    translate([160, D - bkT - 1, bakKZ]) rotate([-90, 0, 0]) cylinder(d = jackD, h = bkT + 2);
    translate([180 - usbW/2, D - bkT - 1, bakKZ - usbH/2]) cube([usbW, bkT + 2, usbH]);
    for (i = [0:3]) translate([196 + i*7, D - bkT - 1, 10]) cube([4, bkT + 2, 30]);    // nede: forsterker
    for (i = [0:8]) translate([128 + i*10, D - bkT - 1, 78]) cube([4, bkT + 2, 40]);   // oppe: Pi
  }
}

// ---------- lydkammer (mono, lukket) ----------
module kammer() {
  difference() {
    union() {
      difference() {
        translate([kX0, kY0, kZ0]) cube([kW, kD, kH]);
        translate([kX0 + kT, kY0 + baffT, kZ0 + kT]) cube([kW - 2*kT, kD, kH - 2*kT]);
      }
      // tårn for lokkets innpressmuttere – går hele veien fra baffelen (printes som søyler)
      for (x = kBx, z = kBz) translate([x, kY0 + 1, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = kD - 1);
      // ører langs gulvet på utsiden, skrues fast nedenfra gjennom gulvet
      for (x = [kX0 - kOre, kX0 + kW]) translate([x, kY0, kZ0]) cube([kOre, kD, 8]);
    }
    translate([drvX, kY0 - 1, drvZ]) rotate([-90, 0, 0]) cylinder(d = drvCut, h = baffT + 2);
    for (k = [0:3]) translate([drvX + drvPCD/2*cos(45 + 90*k), kY0 - 1, drvZ + drvPCD/2*sin(45 + 90*k)])
      rotate([-90, 0, 0]) cylinder(d = 2.6, h = baffT);                     // M3 selvgjengende
    for (x = kBx, z = kBz) translate([x, kY0 + kD - insD, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD + 0.1);
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY) translate([x, y, kZ0 - 0.01]) cylinder(d = ins, h = insD);
    // kabelhull bak i gulvet (tettes med silikon etter at ledningene er trukket)
    translate([drvX, kY0 + kD - 14, kZ0 - 1]) cylinder(d = 4, h = kT + 2);
  }
}
module lokk() {   // bakveggen på kammeret (tetning: 1–2 mm skumtape rundt kanten, klemmes flat)
  difference() {
    translate([kX0, kY0 + kD, kZ0]) cube([kW, 3, kH]);
    for (x = kBx, z = kBz) translate([x, kY0 + kD - 1, z]) rotate([-90, 0, 0]) cylinder(d = m3, h = 5);
  }
}

// ---------- grill (settes inn fra innsiden; holdes av flensen og to ribber mot baffelen) ----------
module grill() {
  difference() {
    union() {
      ext_y(0, gT) front_hull(0.3);
      ext_y(t - 0.4, t + 0.6) offset(gFl - 0.3) front_hull();          // flens bak (ligger i falsen)
      for (z = [gZ0 + 2.6, gZ1 - 5]) translate([ribX[0], t, z]) cube([ribX[1] - ribX[0], kY0 - t - 0.4, 2.4]);   // ribber mot baffelen
    }
    for (z = [gZ0 + slotM : slotP : gZ1 - slotM - slotW]) translate([gX0 + slotM, -1, z]) cube([gX1 - gX0 - 2*slotM, gT + 1.7, slotW]);
  }
}
module list() { translate([0, -0.4, 0]) ext_y(0, lDyp + 0.35) list2d(0.15); }   // gullista, står 0,4 mm ut

// ---------- skjermbrakett (klemmer skjermmodulen inn i lomma; Pi 4 skrus på baksiden) ----------
module brakett() {
  front_ramme() translate([0, 0, -t - 6]) {
    difference() {
      hull() for (p = scrB) translate([scrX + p[0], scrZ + p[1], -2.4]) cylinder(d = 8, h = 2.4);
      for (p = scrB) translate([scrX + p[0], scrZ + p[1], -3]) cylinder(d = 2.9, h = 4);
      translate([scrX - 14, scrZ - 30, -3]) cube([28, 6, 4]);                                // slisse for DSI-flatkabelen
      for (s = [-1, 1]) translate([scrX + s*46 - 4, scrZ - 14, -3]) cube([8, 28, 4]);          // lufting
    }
    for (p = piH) translate([scrX + p[0], scrZ + p[1], -2.4 - piSt]) difference() {
      cylinder(d = 6, h = piSt + 0.01); translate([0, 0, -1]) cylinder(d = 2.2, h = piSt);      // M2,5 selvgjengende
    }
  }
}

// ---------- knotter og knapper ----------
module knott_form(d, h, riller) {   // hul nedenfra (mindre resin, ingen lukkede hulrom), D-aksel 6 mm
  difference() {
    union() {
      cylinder(d = d, h = h - 1.2);
      translate([0, 0, h - 1.2]) cylinder(d1 = d, d2 = d - 2.4, h = 1.2);
    }
    for (k = [0:riller - 1]) rotate([0, 0, k * 360 / riller]) translate([d/2, 0, -1]) cylinder(d = 1.6, h = h - 2, $fn = 12);
    translate([0, 0, h - 0.5]) cylinder(d = d - 8, h = 1);                       // grunn skål i toppen
    translate([0, 0, -0.01]) difference() { cylinder(d = d - 5, h = h - 3); cylinder(d = 10, h = h); }
    translate([0, 0, -0.01]) difference() { cylinder(d = 6.2, h = 11); translate([1.55, -4, -1]) cube([8, 8, 13]); }
  }
}
module knott() { knott_form(whD, whH, 48); }
module volum() { knott_form(volD, volH, 24); }
module knapp_lok(ikon) {
  difference() {
    union() {
      translate([0, 0, -t - 0.21]) cylinder(d = capD, h = t + capUp + 0.21);
      translate([0, 0, -t - 0.2 - capFlT]) cylinder(d = capFl, h = capFlT);
      translate([0, 0, -t - capFlT - 1.8]) cylinder(d = 3, h = 1.61);  // (overlapper flensen 0,01)          // nupp mot taktbryteren
    }
    translate([0, 0, capUp - 0.4]) linear_extrude(0.41)
      text(ikon, size = 4.4, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
  }
}
module knapper() {
  front_ramme() {
    for (i = [0:5]) translate([btnX0 + i*btnP, btnZ, 0]) knapp_lok(str(i + 1));
    translate([pwX, botZ, 0]) knapp_lok("O");
  }
}

// ---------- montert / eksplodert ----------
module montert(e = 0) {   // eksplodert: fronten ut mot deg, innmaten ut bakover gjennom den åpne baksiden
  color(c_kropp) kropp();
  color(c_kropp) translate([0, 8.0*e, 0]) bak();
  color(c_inne) translate([0, 4.6*e, 0]) kammer();
  color(c_inne) translate([0, 5.6*e, 0]) lokk();
  translate([0, 4.6*e, 0]) elementer();
  color(c_grill) translate([0, -1.6*e, 0]) grill();
  color([0.08, 0.08, 0.09]) translate([0, -1.3*e, 0]) ext_y(t + 0.6, t + 0.9) offset(gFl - 0.5) front_hull();   // grillduk (illustrasjon)
  color(c_gull) translate([0, -1.0*e, 0]) list();
  color(c_glass) translate([0, 4.0*e, 0]) front_ramme() translate([scrX - scrGW/2, scrZ - scrGH/2, -t - 0.7]) cube([scrGW, scrGH, 0.6]);
  color(c_inne) translate([0, 5.0*e, 0]) brakett();
  translate([0, 5.8*e, 0]) pi_kort();
  color(c_knapp) translate([0, -0.8*e, 0]) knapper();
  color(c_gull) translate([0, -1.2*e, 0]) front_ramme() translate([whX, whZ, 0.6]) knott();
  color(c_gull) translate([0, -1.2*e, 0]) front_ramme() translate([volX, volZ, 0.6]) volum();
}
module elementer() {   // høyttalerelementet (illustrasjon): ramme foran baffelen, magnet bak
  color([0.22, 0.22, 0.23]) translate([drvX, kY0 - drvFT, drvZ]) rotate([-90, 0, 0]) {
    difference() { cylinder(d = drvF, h = drvFT); translate([0, 0, 1]) cylinder(d = drvCut - 6, h = drvFT); }
    translate([0, 0, drvFT + baffT]) cylinder(d = 50, h = 30);
  }
}
module pi_kort() {   // Raspberry Pi 4 (illustrasjon) på braketten
  front_ramme() translate([scrX - 42.5, scrZ - 28, -t - 8.4 - piSt - 1.4]) {
    color([0.12, 0.42, 0.22]) cube([85, 56, 1.4]);
    color([0.75, 0.75, 0.77]) translate([85 - 21, 2, -16]) cube([21, 52, 16]);      // USB/nett
    color([0.15, 0.15, 0.16]) translate([28, 18, -2.5]) cube([15, 15, 2.5]);         // SoC med kjøleribbe
  }
}

// ---------- utskriftsretning for STL ----------
module print(p) {
  if (p == "kropp") translate([0, H, 0]) rotate([90, 0, 0]) kropp();                     // fronten ned
  else if (p == "bak") translate([0, t, D]) rotate([-90, 0, 0]) bak();                    // baksiden ned
  else if (p == "kammer") translate([0, 0, -kY0]) rotate([90, 0, 0]) kammer();            // baffelen ned
  else if (p == "lokk") translate([0, 0, -(kY0 + kD)]) rotate([90, 0, 0]) lokk();
  else if (p == "grill") translate([0, gZ1 + gFl, 0]) rotate([90, 0, 0]) grill();         // forsiden ned
  else if (p == "list") translate([0, 0, 0.4]) rotate([90, 0, 0]) list();                 // forsiden ned (118 mm lang)
  else if (p == "brakett") translate([0, H, -(t + 6)]) rotate([90, 0, 0]) brakett();      // forsiden ned, Pi-tårn opp
  else if (p == "knott") knott();
  else if (p == "volum") volum();
  else if (p == "knapp") for (i = [0:6]) translate([i * (capFl + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(i < 6 ? str(i + 1) : "O");
}

if (part == "samlet") montert(0);
else if (part == "eksplodert") montert(40);
else if (part == "A_kropp") kropp();
else if (part == "A_bak") bak();
else if (part == "A_kammer") kammer();
else if (part == "A_lokk") lokk();
else if (part == "A_grill") grill();
else if (part == "A_list") list();
else if (part == "A_brakett") brakett();
else if (part == "A_knapper") knapper();
else if (part == "A_knott") front_ramme() translate([whX, whZ, 0.6]) knott();
else if (part == "A_volum") front_ramme() translate([volX, volZ, 0.6]) volum();
else if (part == "A_element") elementer();
else if (part == "A_pi") pi_kort();
else print(part);
