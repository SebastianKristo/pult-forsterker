// Skjold Mini – liten aktiv høyttaler (3″ fullrange, bassrefleks) i Skjolds formspråk. Parametrisk OpenSCAD.
// Lisens: CC BY-NC-SA 4.0 (se LISENS-MASKINVARE.md).
//
// Koordinater (montert): x = bredde (−50…50), y = dybde (0 = front, 100 = bak), z = høyde (0 = underkant kropp).
// Bruk:  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_mini.scad
// part:  kropp | front | grill | bunn | knott | samlet | eksplodert
// STL-ene eksporteres liggende slik de skal printes (se print_*-transformene nederst).

part = "samlet";
$fn = 72;

// ---------- ytre mål ----------
W = 100; D = 100; H = 140;      // kropp
R = 12;                         // hjørneradius (som Node)
t = 2.6;                        // vegg (6 × 0,42 mm linjer ≈ 2,5)
zf = 26;  ft = 2.4;             // gulv mellom elektronikkrom (under) og lydkammer (over)
fT = 6;                         // frontplate (baffel)
gT = 2.4; gGap = 0.6;           // grill og luft til frontplaten
bT = 4;                         // bunnplate

// ---------- element og port ----------
drvCut = 72;                    // utsparing for 3″-element (sjekk ditt element, typisk 70–74 mm)
drvRec = 86; drvRecD = 2.5;     // forsenkning for elementets ramme
drvPCD = 82; drvScrew = 2.6;    // skruehull (M3 selvgjengende)
drvZ = 95;                      // elementets senter
portD = 16; portW = 2.0;        // port innv. Ø og vegg
portL = 79;                     // total portlengde inkl. baffel → fb ≈ 90 Hz i ≈ 0,82 l netto (se LES_MEG.md)
portZ = 41; portFlare = 3;

// ---------- fester ----------
ins = 4.0;  insD = 6.5;         // M3 innpressmutter (Ø4,0 hull, 6,5 dyp)
boss = 8.4;
m3 = 3.4; m3k = 6.4;            // M3 senkeskrue: hull og senkehode
bx = W/2 - t - boss/2 + 0.6;    // skruetårn-plassering i x (tårnet berører sideveggen)
fz = [34, 128];                 // frontplatens skruer (skjult bak grillen)
by = [8, D - t - boss/2 + 0.6]; // bunnens skruer

// ---------- betjening ----------
ec11Y = 70; ec11D = 7.2;        // EC11-aksel gjennom toppen
ledZ = 13; ledD = 3.2;          // status-LED i fronten (elektronikkrommet)
micZ = 13; micD = 1.6;          // valgfri INMP441-mikrofon
dcD = 8.2;  usbW = 10; usbH = 4.4;
knobD = 34; knobH = 14; shaftD = 6.1; shaftFlat = 4.6;

c_lys = [0.93,0.92,0.90]; c_mork = [0.13,0.13,0.14]; c_gull = [0.85,0.62,0.25]; c_grill = [0.18,0.18,0.19];

// ---------- hjelpere ----------
module rrect(w, h, r) { offset(r) offset(-r) square([w, h], center = true); }
// avrundet boks i x/y, høyde i z; top-fas c
module rbox(w, d, h, r, c = 0) {
  hull() {
    translate([0, 0, 0]) linear_extrude(h - c) translate([0, d/2]) rrect(w, d, r);
    if (c > 0) translate([0, 0, h - c]) linear_extrude(c) translate([0, d/2]) rrect(w - 2*c, d - 2*c, r - c);
  }
}
module teardrop_x(d, l) { // hull langs x som printer uten støtte når x er vannrett og z opp
  rotate([0, 90, 0]) hull() { cylinder(d = d, h = l, center = true); rotate([0, 0, 45]) cube([d/2, d/2, l], center = true); }
}

// ---------- kropp ----------
module kropp() {
  difference() {
    union() {
      difference() {
        rbox(W, D, H, R, 2);
        // hulrom: åpent foran (y < t) og under (z < 0)
        translate([0, -1, -1]) linear_extrude(H - t + 1) translate([0, (D - t + 1)/2]) rrect(W - 2*t, D - t + 1, R - t);
        translate([-W/2 + t, -1, -1]) cube([W - 2*t, t + 1, H - t + 1]);
      }
      // gulv
      intersection() {
        translate([-W/2, 0, zf]) cube([W, D, ft]);
        rbox(W, D, H, R);
      }
      // skruetårn, klippet til ytterformen så de ikke stikker ut ved de avrundede hjørnene
      intersection() { rbox(W, D, H, R); union() {
      // frontplatens skruetårn (langs y; står på bakveggen når kroppen printes liggende)
      for (sx = [-1, 1], z = fz) translate([sx * bx, 0, z]) rotate([-90, 0, 0]) cylinder(d = boss, h = D - t + 0.01);
      // bunnplatens skruetårn (langs z)
      for (sx = [-1, 1], y = by) translate([sx * bx, y, 0]) {
        cylinder(d = boss, h = zf);
        // 45°-kile mot bakveggen for de fremre tårnene (printes uten støtte)
        if (y < D/2) hull() { cylinder(d = boss, h = zf); translate([sx * (boss/2 - 0.5), boss/2 + 3, 0]) cube([1, 1, zf]); }
      }
      } }
    }
    // innpressmutter-hull
    for (sx = [-1, 1], z = fz) translate([sx * bx, -0.01, z]) rotate([-90, 0, 0]) cylinder(d = ins, h = insD);
    for (sx = [-1, 1], y = by) translate([sx * bx, y, -0.01]) cylinder(d = ins, h = insD);
    // EC11 gjennom toppen
    translate([0, ec11Y, H - t - 1]) cylinder(d = ec11D, h = t + 2);
    // gjennomføring for høyttalerkabel i gulvet (tettes med lim)
    translate([0, 85, zf - 1]) cylinder(d = 6, h = ft + 2);
    // bak: DC-kontakt og USB-C (ESP32) i elektronikkrommet
    translate([-25, D - t - 1, 13]) rotate([-90, 0, 0]) cylinder(d = dcD, h = t + 2);
    translate([15, D - t - 1, 13]) rotate([-90, 0, 0]) linear_extrude(t + 2) rrect(usbW, usbH, 1.6);
    // gravert navn bak
    translate([0, D - 0.59, 100]) rotate([90, 0, 180]) linear_extrude(0.6) text("SKJOLD MINI", size = 5, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
  }
}

// ---------- frontplate (baffel) ----------
module front() {
  difference() {
    union() {
      // plate i x/z, y = −fT … 0
      translate([0, 0, 0]) rotate([90, 0, 0]) linear_extrude(fT) translate([0, H/2]) rrect(W, H, R);
      // bassrefleksport inn i kammeret
      translate([0, -0.01, portZ]) rotate([-90, 0, 0]) cylinder(d = portD + 2*portW, h = portL - fT);
    }
    // element
    translate([0, 1, drvZ]) rotate([90, 0, 0]) cylinder(d = drvCut, h = fT + 2);
    translate([0, -fT - 0.01, drvZ]) rotate([-90, 0, 0]) cylinder(d = drvRec, h = drvRecD);
    for (a = [45, 135, 225, 315]) translate([drvPCD/2 * cos(a), 1, drvZ + drvPCD/2 * sin(a)]) rotate([90, 0, 0]) cylinder(d = drvScrew, h = fT + 2);
    // port med avrundet munning foran
    translate([0, -fT - 1, portZ]) rotate([-90, 0, 0]) cylinder(d = portD, h = portL + 2);
    translate([0, -fT - 0.01, portZ]) rotate([-90, 0, 0]) cylinder(d1 = portD + 2*portFlare, d2 = portD, h = portFlare);
    // skruer (senkehode foran, skjult bak grillen)
    for (sx = [-1, 1], z = fz) translate([sx * bx, 1, z]) rotate([90, 0, 0]) { cylinder(d = m3, h = fT + 2); translate([0, 0, fT + 1 - 1.8]) cylinder(d1 = m3, d2 = m3k, h = 1.81); }
    // grill-pinner
    for (sx = [-1, 1], z = [36, 126]) translate([sx * 38, -fT - 0.01, z]) rotate([-90, 0, 0]) cylinder(d = 3.3, h = 4.6);
    // LED og mikrofon i den synlige stripen under grillen
    translate([-30, 1, ledZ]) rotate([90, 0, 0]) cylinder(d = ledD, h = fT + 2);
    translate([30, 1, micZ]) rotate([90, 0, 0]) cylinder(d = micD, h = fT + 2);
    // gravert logo
    translate([0, -fT - 0.01, 13]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(0.6) text("SKJOLD", size = 6, font = "Liberation Sans:style=Bold", spacing = 1.4, halign = "center", valign = "center");
  }
}

// ---------- grill ----------
gW = W - 6; gZ0 = 30; gZ1 = 138;
module grill() {
  translate([0, -fT - gGap, 0]) difference() {
    union() {
      rotate([90, 0, 0]) linear_extrude(gT) translate([0, (gZ0 + gZ1)/2]) rrect(gW, gZ1 - gZ0, 9);
      for (sx = [-1, 1], z = [36, 126]) translate([sx * 38, -0.5, z]) rotate([-90, 0, 0]) cylinder(d = 3.0, h = gGap + 4.5);
    }
    // sekskantmønster
    for (i = [-8:8], j = [0:20]) {
      x = i * 5.2 + (j % 2) * 2.6; z = gZ0 + 6 + j * 4.5;
      if (abs(x) < gW/2 - 6 && z < gZ1 - 5) translate([x, 1, z]) rotate([90, 0, 0]) rotate([0, 0, 30]) cylinder(d = 4.2, h = gT + 2, $fn = 6);
    }
  }
}

// ---------- bunn ----------
module bunn() {
  difference() {
    translate([0, 0, -bT]) linear_extrude(bT) translate([0, D/2]) rrect(W, D, R);
    for (sx = [-1, 1], y = by) translate([sx * bx, y, -bT - 1]) { cylinder(d = m3, h = bT + 2); cylinder(d1 = m3k + 2, d2 = m3, h = 1 + (m3k + 2 - m3)/2); }
    for (sx = [-1, 1], sy = [-1, 1]) translate([sx * 32, D/2 + sy * 32, -bT - 0.01]) cylinder(d = 10.2, h = 1.2);
    // lufting for forsterkeren
    for (i = [-3:3]) translate([i * 7, 50, -bT - 1]) linear_extrude(bT + 2) rrect(3, 30, 1.4);
  }
}

// ---------- knott ----------
module knott() {
  translate([0, ec11Y, H + 0.6]) difference() {
    union() {
      cylinder(d = knobD - 2, h = knobH);
      cylinder(d = knobD, h = knobH - 1.5);
      translate([0, 0, knobH - 1.5]) cylinder(d1 = knobD, d2 = knobD - 3, h = 1.5);
    }
    for (a = [0:10:350]) rotate([0, 0, a]) translate([knobD/2 + 0.2, 0, -1]) cylinder(d = 1.4, h = knobH - 2, $fn = 12);
    translate([0, 0, knobH - 0.8]) cylinder(d = knobD - 8, h = 1);   // fordypning på toppen
    translate([0, 0, -0.01]) intersection() { cylinder(d = shaftD, h = 12); translate([-shaftD/2, -shaftD/2 + (shaftD - shaftFlat), 0]) cube([shaftD, shaftFlat, 12]); }
    translate([0, knobD/2 - 3.5, knobH - 0.6]) cylinder(d = 1.6, h = 1);   // posisjonsmerke
  }
}

module samlet(ex = 0) {
  color(c_lys) kropp();
  color(c_mork) translate([0, -ex, 0]) front();
  color(c_grill) translate([0, -2.2 * ex, 0]) grill();
  color(c_mork) translate([0, 0, -ex]) bunn();
  color(c_gull) translate([0, 0, 0.8 * ex]) knott();
}

// ---------- utskriftsretning ----------
if (part == "kropp") translate([0, 0, D]) rotate([-90, 0, 0]) kropp();                   // bakveggen ned
else if (part == "front") translate([0, 0, fT]) rotate([90, 0, 0]) front();              // forsiden ned
else if (part == "grill") translate([0, 0, fT + gGap + gT]) rotate([90, 0, 0]) grill();  // forsiden ned
else if (part == "bunn") translate([0, -D/2, bT]) bunn();
else if (part == "knott") translate([0, 0, H + 0.6 + knobH]) rotate([180, 0, 0]) translate([0, -ec11Y, 0]) knott(); // toppen ned
else if (part == "eksplodert") samlet(25);
else if (part == "a_kropp") kropp(); else if (part == "a_front") front(); else if (part == "a_grill") grill();
else if (part == "a_bunn") bunn(); else if (part == "a_knott") knott();
else samlet();
