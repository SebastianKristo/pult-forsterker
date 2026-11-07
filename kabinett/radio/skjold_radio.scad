// Skjold Radio – bordradio med skjerm, seks favorittknapper, navigasjonshjul og volumknott. Parametrisk OpenSCAD.
// Eget Skjold-design: en lav, bred «pult» der hele toppen heller ned mot brukeren (som et skråstilt dashbord), med
// skjermen, favorittknappene og hjulet på skråflaten. Fronten er én mørk grill som går helt ned til bordet, rammet inn
// av kroppen på sidene og oppe. Volumknotten sitter på høyre side, av/på bak til venstre på toppen. Myke vertikale
// hjørner (R14) som Node/Røst, fasede toppkanter, lys kropp, mørk grill og knapper, gull hjul og logo.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater: x = bredde (0 … W), y = dybde (0 = fronten, D = bak), z = høyde (0 = oversiden av bunnplata).
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_radio.scad
// part:  kropp | kammer | lokk | grill | bunn | brakett | knott | volum | knapp (6 favoritter + av/på) |
//        samlet | eksplodert | A_<del> (montert stilling, for sjekk_modell.py)
// STL-ene eksporteres liggende slik de skal printes (FDM) – samme filer kan bestilles i resin/MJF (se LES_MEG.md).
// Alle deler er åpne skall (ingen lukkede hulrom), så resin renner ut uten egne dreneringshull.

part = "samlet";
ex = 0;                          // eksplosjonsavstand (eksplodert visning)
farge = "lys";                   // lys | mork
$fn = 64;

// ---------- ytre mål ----------
W = 236; D = 152;                // bredde, dybde
Hf = 100; Hb = 128;              // høyde foran og bak (over bunnplata) – toppen heller 28 mm mot brukeren (≈ 10,6°)
R = 14;                          // vertikale hjørner
t = 3.0;                         // vegg (≥ 2 mm for resin/MJF; 7 linjer à 0,42 mm på FDM)
c = 2.5;                         // fas på toppkantene
bT = 4;                          // bunnplate (ligger inne i kroppens skjørt)

a = atan((Hb - Hf) / D);         // toppens helning
L = D / cos(a);                  // toppflatens lengde langs skråningen
function topz(y, o = 0) = Hf + (Hb - Hf) * y / D - o / cos(a);   // toppflaten, forskjøvet o innover (vinkelrett)
// Lokal ramme på toppflaten: u langs bredden (= x), v oppover skråningen fra forkanten, w ut av flaten (w = 0 = overflaten).
module topp_ramme() { translate([0, 0, Hf]) rotate([a, 0, 0]) children(); }

// ---------- høyttalere og lydkammer ----------
drvCut = 72;  drvF = 86;  drvFT = 4;      // 3″ fullrange (f.eks. Dayton RS75-4): utsparing, rammens Ø og tykkelse – mål ditt element
drvPCD = 82;  drvX = 52;                  // skruehullsirkel, avstand fra midten
kX0 = 22;  kW = W - 2*kX0;                // kammer: x 22 … 214
kY0 = t + 5.6;  kD = 78;                  // baffelens forside 5,6 mm bak fronten (plass til grill, grillduk og elementrammen)
kZ0 = 0;  kH = Hf - 12;                   // står på bunnplata, 88 mm høyt
kT = 2.8;  baffT = 7;                     // kammervegg og baffel
kOff = kT + 2.5;                          // innpressmutter-tårnene for lokket ligger i hjørnene (smelter inn i veggene)
kBx = [kX0 + kOff, W/2 - kT/2 - 3, W/2 + kT/2 + 3, kX0 + kW - kOff];
kBz = [kZ0 + kOff, kZ0 + kH - kOff];
kOre = 8;                                 // ører langs gulvet på utsiden (skrues fra bunnen)
kOreY = [kY0 + 12, kY0 + kD - 12];
// netto volum per side ≈ 91,8 × 71 × 82,4 mm − tårn og element ≈ 0,47 l (lukket, stereo med skillevegg)

// ---------- front og grill ----------
gM = 12;  gZ1 = Hf - 12;  gR = 6;          // grillåpningen: 12 mm marg på sidene, opp til 88 mm, helt ned til bordet
gT = 3.0;  gFl = 2.5;                      // grillens tykkelse = veggen, flens bak
slotW = 2.2; slotP = 4.4;                  // vannrette spalter

// ---------- skjerm, knapper, hjul ----------
scrAW = 96;  scrAH = 56;                   // synlig vindu (4,3″ DSI 800×480, aktivt område ≈ 95 × 54)
scrGW = 106; scrGH = 68;                   // glass/LCD på modulen (lomme under toppen) – mål din skjerm!
scrU = 92;   scrV = 72;                    // vinduets senter (u, v) på toppflaten
scrB = [[-56.5, -34], [56.5, -34], [-56.5, 34], [56.5, 34]];   // skruetårn rundt modulen (brakett)
btnV = 22;  btnU0 = 34; btnP = 23;         // favoritter 1–6: rad langs forkanten av toppen
capD = 11; capHole = 11.6; capUp = 0.8; capFl = 15; capFlT = 1.0;
whU = W - 46; whV = 70;                    // navigasjonshjul (EC11 med trykk) – knott Ø 46
whD = 46;  whH = 15;
pwU = 22;  pwV = L - 20;                   // av/på bak til venstre på toppen
volZ = 52; volY = 72;                      // volumknott på høyre side
volD = 22; volH = 13;
ec11 = 7.2;                                // EC11 M7-gjenge
// ---------- fester ----------
ins = 4.0; insD = 6.0; boss = 8.4; m3 = 3.4; m3k = 6.4;
bossXY = [[8.5, 8.5], [W - 8.5, 8.5], [8.5, D - 8.5], [W - 8.5, D - 8.5]];   // kroppens skruetårn (i hjørnene)
fotXY = [[30, 22], [W - 30, 22], [30, D - 22], [W - 30, D - 22]];             // selvklebende gummiføtter Ø 12
// Raspberry Pi 4 bak kammeret (85 × 56, hull 58 × 49), USB-C/HDMI mot bakveggen
piX0 = 20; piY0 = D - t - 2.5 - 56;
piH = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];
// ---------- bak ----------
dcD = 8.2; jackD = 6.4; usbW = 10; usbH = 4.4;

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
module ytre(o = 0) {   // ytre form forskjøvet innover med o (o > 0: innerformen, går litt under kanten)
  z0 = o > 0 ? -bT - 1 : -bT;
  intersection() {
    translate([o, o, z0]) linear_extrude(Hb + bT + 2) rrect(W - 2*o, D - 2*o, max(1, R - o));
    hull() for (yy = [[o, o + c], [D - o, D - o - c]]) {   // skrå topp, fas langs alle fire toppkanter
      translate([o, yy[0] - 0.005, z0]) cube([W - 2*o, 0.01, topz(yy[0], o) - c - z0]);
      translate([o, yy[1] - 0.005, z0]) cube([W - 2*o, 0.01, topz(yy[1], o) - c - z0]);
      translate([o + c, yy[1] - 0.005, z0]) cube([W - 2*o - 2*c, 0.01, topz(yy[1], o) - z0]);
    }
  }
}
module front_hull(o = 0) {   // grillåpningen sett forfra (x, z): rette sider, runde hjørner oppe, åpen nedover
  offset(-o) hull() {
    translate([gM, -bT - 2]) square([W - 2*gM, 1]);
    for (x = [gM + gR, W - gM - gR]) translate([x, gZ1 - gR]) circle(gR);
  }
}

// ---------- kropp (ett skall; printes med toppflaten ned på platen) ----------
module kropp() {
  difference() {
    union() {
      difference() { ytre(0); ytre(t); }
      // skruetårn i hjørnene (innpressmuttere nedenfra), med kjegle over så de printes uten støtte
      for (p = bossXY) translate([p[0], p[1], 0]) { cylinder(d = boss, h = 22); translate([0, 0, 22]) cylinder(d1 = boss, d2 = 1, h = 7); }
      topp_ramme() {
        for (p = scrB) translate([scrU + p[0], scrV + p[1], -t - 6]) cylinder(d = 7, h = 7);      // skjermbrakett
        for (du = [btnU0 - 12, btnU0 + 5*btnP + 12]) translate([du, btnV, -t - 7]) cylinder(d = 7, h = 8);   // knappekort
        for (du = [pwU - 12, pwU + 12]) translate([du, pwV, -t - 7]) cylinder(d = 7, h = 8);      // av/på-kort
      }
    }
    for (p = bossXY) translate([p[0], p[1], -0.01]) cylinder(d = ins, h = insD);
    // grillåpningen og fals for grillens flens (åpen nedover – ingen lang bro å printe)
    translate([0, t + 1, 0]) rotate([90, 0, 0]) linear_extrude(t + 2) front_hull();
    translate([gM - gFl, t - 0.6, -bT - 1]) cube([W - 2*gM + 2*gFl, 1.2, gZ1 + gFl + bT + 1]);
    topp_ramme() {
      // skjermvindu med fas, og lomme for glasset under
      translate([scrU - scrAW/2, scrV - scrAH/2, -t - 1]) cube([scrAW, scrAH, t + 2]);
      translate([scrU - scrAW/2 - 1, scrV - scrAH/2 - 1, -0.8]) cube([scrAW + 2, scrAH + 2, 1]);
      translate([scrU - scrGW/2 - 0.3, scrV - scrGH/2 - 0.3, -t - 1]) cube([scrGW + 0.6, scrGH + 0.6, t - 0.2]);
      for (p = scrB) translate([scrU + p[0], scrV + p[1], -t - 6.1]) cylinder(d = 2.2, h = 5);   // M2,5 selvgjengende
      // favoritt 1–6 og av/på
      for (i = [0:5]) translate([btnU0 + i*btnP, btnV, -t - 1]) cylinder(d = capHole, h = t + 2);
      translate([pwU, pwV, -t - 1]) cylinder(d = capHole, h = t + 2);
      for (du = [btnU0 - 12, btnU0 + 5*btnP + 12]) translate([du, btnV, -t - 7.1]) cylinder(d = 2.2, h = 6);
      for (du = [pwU - 12, pwU + 12]) translate([du, pwV, -t - 7.1]) cylinder(d = 2.2, h = 6);
      // hjulet
      translate([whU, whV, -t - 1]) cylinder(d = ec11, h = t + 2);
      translate([whU, whV, -0.6]) cylinder(d = whD + 3, h = 1);    // grunn ring under knotten
      // logo SKJOLD preget bak hjulet
      translate([whU, L - 15, -0.6]) linear_extrude(1)
        text("SKJOLD", size = 5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.4);
    }
    // volumknotten på høyre side
    translate([W - t - 1, volY, volZ]) rotate([0, 90, 0]) cylinder(d = ec11, h = t + 2);
    // bak: DC 19–24 V, hodetelefon, USB-C (service) og lufting
    translate([40, D - t - 1, 26]) rotate([-90, 0, 0]) cylinder(d = dcD, h = t + 2);
    translate([62, D - t - 1, 26]) rotate([-90, 0, 0]) cylinder(d = jackD, h = t + 2);
    translate([82 - usbW/2, D - t - 1, 26 - usbH/2]) cube([usbW, t + 2, usbH]);
    for (i = [0:7]) translate([126 + i*10, D - t - 1, 12]) cube([4, t + 2, 34]);
  }
}

// ---------- lydkammer (stereo, lukket, med skillevegg) ----------
module kammer() {
  difference() {
    union() {
      difference() {
        translate([kX0, kY0, kZ0]) cube([kW, kD, kH]);
        translate([kX0 + kT, kY0 + baffT, kZ0 + kT]) cube([kW - 2*kT, kD, kH - 2*kT]);
      }
      translate([W/2 - kT/2, kY0, kZ0]) cube([kT, kD, kH]);                    // skillevegg (venstre/høyre)
      // tårn for lokkets innpressmuttere – går hele veien fra baffelen (printes som søyler)
      for (x = kBx, z = kBz) translate([x, kY0 + 1, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = kD - 1);
      // ører langs gulvet på utsiden, skrues fast nedenfra gjennom bunnplata
      for (x = [kX0 - kOre, kX0 + kW]) translate([x, kY0, kZ0]) cube([kOre, kD, 8]);
    }
    for (s = [-1, 1]) let (x = W/2 + s*drvX, z = kZ0 + kH/2) {
      translate([x, kY0 - 1, z]) rotate([-90, 0, 0]) cylinder(d = drvCut, h = baffT + 2);
      for (k = [0:3]) translate([x + drvPCD/2*cos(45 + 90*k), kY0 - 1, z + drvPCD/2*sin(45 + 90*k)])
        rotate([-90, 0, 0]) cylinder(d = 2.6, h = baffT);                     // M3 selvgjengende
    }
    for (x = kBx, z = kBz) translate([x, kY0 + kD - insD, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD + 0.1);
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY) translate([x, y, kZ0 - 0.01]) cylinder(d = ins, h = insD);
    // kabelhull bak i gulvet (tettes med silikon etter at ledningene er trukket)
    for (s = [-1, 1]) translate([W/2 + s*30, kY0 + kD - 14, kZ0 - 1]) cylinder(d = 4, h = kT + 2);
  }
}
module lokk() {   // bakveggen på kammeret (tetning: 1–2 mm skumtape rundt kanten, klemmes flat)
  difference() {
    translate([kX0, kY0 + kD, kZ0]) cube([kW, 3, kH]);
    for (x = kBx, z = kBz) translate([x, kY0 + kD - 1, z]) rotate([-90, 0, 0]) cylinder(d = m3, h = 5);
  }
}

// ---------- grill ----------
module grill() {
  difference() {
    union() {
      translate([0, gT, 0]) rotate([90, 0, 0]) linear_extrude(gT)
        intersection() { front_hull(0.3); translate([0, -bT]) square([W, Hb]); }
      // flens bak (ligger i falsen på sidene og oppe)
      translate([gM - gFl + 0.3, t - 0.4, 0.5]) cube([W - 2*gM + 2*gFl - 0.6, 1.0, gZ1 + gFl - 0.8]);
      // midtribbe mot kammerets skillevegg – holder grillen rett
      translate([W/2 - 1.2, t, 2]) cube([2.4, kY0 - t - 0.4, gZ1 - 8]);
    }
    for (z = [2 : slotP : gZ1 - 7]) translate([gM + 8, -1, z]) cube([W - 2*gM - 16, gT + 1.7, slotW]);
  }
}

// ---------- bunnplate ----------
module bunn() {
  difference() {
    union() {
      translate([0, 0, -bT]) linear_extrude(bT) offset(-t - 0.3) rrect(W, D, R);
      for (p = piH) translate([piX0 + p[0], piY0 + p[1], 0]) cylinder(d = 6, h = 5);        // Pi 4
    }
    for (p = bossXY) translate([p[0], p[1], -bT - 1]) { cylinder(d = m3, h = bT + 2); cylinder(d = m3k, h = 1 + 1.7); }
    for (x = [kX0 - kOre/2, kX0 + kW + kOre/2], y = kOreY)
      translate([x, y, -bT - 1]) { cylinder(d = m3, h = bT + 2); cylinder(d = m3k, h = 1 + 1.7); }
    for (p = piH) translate([piX0 + p[0], piY0 + p[1], -1]) cylinder(d = 2.2, h = 7);       // M2,5 selvgjengende
    for (p = fotXY) translate([p[0], p[1], -bT - 1]) cylinder(d = 12.6, h = 1.6);           // forsenkning for gummiføtter
    // lufting under forsterker og spenningsregulator
    for (i = [0:9]) translate([124 + i*8, kY0 + kD + 10, -bT - 1]) cube([3, 40, bT + 2]);
  }
}

// ---------- skjermbrakett (klemmer skjermmodulen opp i lomma, med skumtape mellom) ----------
module brakett() {
  topp_ramme() translate([0, 0, -t - 6]) difference() {
    hull() for (p = scrB) translate([scrU + p[0], scrV + p[1], -2.4]) cylinder(d = 10, h = 2.4);
    translate([scrU - 50, scrV - 25, -3]) cube([100, 50, 4]);
    for (p = scrB) translate([scrU + p[0], scrV + p[1], -3]) cylinder(d = 2.9, h = 4);
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
  topp_ramme() {
    for (i = [0:5]) translate([btnU0 + i*btnP, btnV, 0]) knapp_lok(str(i + 1));
    translate([pwU, pwV, 0]) knapp_lok("O");
  }
}

// ---------- montert / eksplodert ----------
module montert(e = 0) {
  n = [0, -sin(a), cos(a)];        // toppflatens normal – knapper, glass og hjul eksploderes ut av flaten
  color(c_kropp) translate([0, 0, 2.2*e]) kropp();
  color(c_inne) translate([0, 0.6*e, 0]) kammer();
  color(c_inne) translate([0, 1.6*e, 0]) lokk();
  color(c_grill) translate([0, -1.6*e, 0]) grill();
  color(c_kropp) translate([0, 0, -e]) bunn();
  color(c_inne) translate([0, 0, 2.2*e] - 0.6*e*n) brakett();
  color(c_glass) translate([0, 0, 2.2*e] - 0.3*e*n) topp_ramme() translate([scrU - scrGW/2, scrV - scrGH/2, -t - 0.7]) cube([scrGW, scrGH, 0.6]);
  color(c_knapp) translate([0, 0, 2.2*e] + 0.7*e*n) knapper();
  color(c_gull) translate([0, 0, 2.2*e] + 1.1*e*n) topp_ramme() translate([whU, whV, 0.6]) knott();
  color(c_gull) translate([W + 1 + 1.2*e, volY, volZ + 2.2*e]) rotate([0, 90, 0]) volum();
  translate([0, 0.6*e, 0]) elementer();
}
module elementer() {   // høyttalerelementene (illustrasjon): ramme foran baffelen, magnet bak
  color([0.22, 0.22, 0.23]) for (s = [-1, 1]) translate([W/2 + s*drvX, kY0 - drvFT, kZ0 + kH/2]) rotate([-90, 0, 0]) {
    difference() { cylinder(d = drvF, h = drvFT); translate([0, 0, 1]) cylinder(d = drvCut - 6, h = drvFT); }
    translate([0, 0, drvFT + baffT]) cylinder(d = 50, h = 30);
  }
}

// ---------- utskriftsretning for STL ----------
module print(p) {
  if (p == "kropp") translate([W, 0, Hf * cos(a)]) rotate([0, 180, 0]) rotate([-a, 0, 0]) kropp();   // toppflaten ned
  else if (p == "kammer") translate([0, 0, -kY0]) rotate([90, 0, 0]) kammer();                       // baffelen ned
  else if (p == "lokk") translate([0, 0, -(kY0 + kD)]) rotate([90, 0, 0]) lokk();
  else if (p == "grill") translate([0, gZ1, 0]) rotate([90, 0, 0]) grill();                           // forsiden ned
  else if (p == "bunn") translate([0, 0, bT]) bunn();                                                 // undersiden ned
  else if (p == "brakett") translate([0, 0, t + 8.4]) rotate([-a, 0, 0]) translate([0, 0, -Hf]) brakett();
  else if (p == "knott") knott();
  else if (p == "volum") volum();
  else if (p == "knapp") for (i = [0:6]) translate([i * (capFl + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(i < 6 ? str(i + 1) : "O");
}

if (part == "samlet") montert(0);
else if (part == "eksplodert") montert(40);
else if (part == "A_kropp") kropp();
else if (part == "A_kammer") kammer();
else if (part == "A_lokk") lokk();
else if (part == "A_grill") grill();
else if (part == "A_bunn") bunn();
else if (part == "A_brakett") brakett();
else if (part == "A_knapper") knapper();
else if (part == "A_knott") topp_ramme() translate([whU, whV, 0.6]) knott();
else if (part == "A_element") elementer();
else if (part == "A_volum") translate([W + 1, volY, volZ]) rotate([0, 90, 0]) volum();
else print(part);
