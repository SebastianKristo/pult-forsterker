// Skjold Røst Myk – liggende Røst med myk, avrundet kropp, finmasket grill foran og messingknott på toppen.
// Eget design i Skjolds formspråk. UTKAST: formen er tegnet, men delingen for utskrift, festene og lydkammeret
// er ikke regnet ferdig (se LES_MEG.md). Lisens: CC BY-NC-SA 4.0.
//
// Koordinater: x tvers, y fra front (−) til bak (+), z opp (0 = bordet).
// part: kropp | front | grill_plate | knott | element | samlet | snitt
part = "samlet";
$fn = 72;

// ---------- mål ----------
W = 128; Hh = 122; R = 40;         // tverrsnittet: avrundet rektangel (bredde × høyde, hjørneradius)
D = 150;                            // dybde fra front til bakerste punkt
t = 3.2;                            // veggtykkelse
fotH = 9;                           // føttene løfter kroppen fra bordet
zc = fotH + Hh / 2;                 // kroppens senter
bakL = 52;                          // lengden på den avrundede bakenden
frontR = 7;                         // avrundingen på forkanten
yF = -D / 2; yB = D / 2;
leppe = 7.5;                        // synlig kant rundt grillen
grDyp = 3.0;                        // grillen ligger så langt inn fra forkanten
grT = 1.4;                          // grillplatens tykkelse
bafY = yF + grDyp + grT + 6;        // frontplata (baffelen) bak grillen, 6 mm luft
bafT = 5;
drvD = 72; drvRamme = 80;           // 3″ fullrange (Dayton RS75-4): hull og ramme
knottD = 44; knottH = 11; knottY = yF + 50; halsD = 22; halsH = 2.5;
portD = 18; portL = 95;             // bassrefleks ut bak
c_lys = [0.93, 0.92, 0.89]; c_grill = [0.80, 0.79, 0.76]; c_mork = [0.13, 0.13, 0.14]; c_messing = [0.80, 0.64, 0.36];

module rr(w, h, r) { offset(r) offset(-r) square([w, h], center = true); }
module snittform(o = 0) { offset(delta = o) rr(W, Hh, R); }
// en tynn skive av tverrsnittet ved y, skalert s (om senter), krympet o
module skive(y, s, o = 0) { translate([0, y, zc]) rotate([90, 0, 0]) linear_extrude(0.02, center = true) scale([s, s]) snittform(o); }

// hele kroppen som massivt legeme (o < 0 gir innsiden)
module legeme(o = 0) {
  n = 18; m = 8; fr = max(1, frontR + o);
  // forkant: avrundet (kvart sirkel)
  for (i = [0 : m - 1]) hull() {
    a0 = 90 * i / m; a1 = 90 * (i + 1) / m;
    skive(yF - o + fr * (1 - sin(a0)), 1, o - fr * (1 - cos(a0)));
    skive(yF - o + fr * (1 - sin(a1)), 1, o - fr * (1 - cos(a1)));
  }
  // rett midtparti
  hull() { skive(yF - o + fr, 1, o); skive(yB - bakL, 1, o); }
  // bakende: kvart ellipse
  for (i = [0 : n - 1]) hull() {
    a0 = 86 * i / n; a1 = 86 * (i + 1) / n;
    skive(yB - bakL + (bakL + o) * sin(a0), cos(a0), o);
    skive(yB - bakL + (bakL + o) * sin(a1), cos(a1), o);
  }
}

module fot(x, y, r0, r1) {
  hull() {
    translate([x, y, 0]) cylinder(r = r0, h = 1.2);
    translate([x * 0.86, y, fotH + 14]) scale([1, 1.25, 1]) cylinder(r = r1, h = 1);
  }
}

module kropp() {
  color(c_lys) difference() {
    union() {
      legeme(0);
      // føtter: to små foran, én bred bak
      difference() {
        union() { fot(-36, yF + 24, 5, 10); fot(36, yF + 24, 5, 10); hull() { fot(-14, 34, 5, 9); fot(14, 34, 5, 9); } }
        translate([0, 0, -1]) cube([400, 400, 2], center = true);
      }
    }
    // hulrom, åpent foran
    legeme(-t);
    translate([0, yF - 1, zc]) rotate([-90, 0, 0]) linear_extrude(bafY - yF + bafT + 1) snittform(-leppe);
    // volumknott (EC11) gjennom toppen
    translate([0, knottY, zc]) cylinder(d = 7.4, h = Hh);
    // bak: bassrefleks, strøm og USB-C
    translate([-22, yB - 30, zc + 14]) rotate([-90, 0, 0]) cylinder(d = portD, h = 60);
    translate([24, yB - 30, zc - 26]) rotate([-90, 0, 0]) cylinder(d = 8.2, h = 60);
    translate([24, yB - 30, zc - 40]) rotate([-90, 0, 0]) hull() { translate([-3, 0, 0]) cylinder(d = 4.4, h = 60); translate([3, 0, 0]) cylinder(d = 4.4, h = 60); }
  }
}

// frontplata: baffel med hull for elementet, skrus i kroppen fra forsiden (skjules av grillen)
module front() {
  color(c_mork) translate([0, bafY, zc]) rotate([-90, 0, 0]) difference() {
    linear_extrude(bafT) snittform(-leppe - 0.3);
    translate([0, 0, -1]) cylinder(d = drvD, h = bafT + 2);
    for (a = [45 : 90 : 315]) rotate(a) translate([32, 0, -1]) cylinder(d = 3.3, h = bafT + 2);
    for (sx = [-1, 1], sz = [-1, 1]) translate([sx * 46, sz * 43, -1]) cylinder(d = 3.4, h = bafT + 2);
  }
}

// grillplata uten hull (hullene lages i lag_myk.py med manifold3d: rundt 3000 hull er for tungt for OpenSCAD)
module grill_plate() {
  color(c_grill) translate([0, yF + grDyp, zc]) rotate([-90, 0, 0]) linear_extrude(grT) snittform(-leppe - 0.25);
}

module knott() {
  color(c_messing) translate([0, knottY, zc + Hh / 2]) {
    cylinder(d = halsD, h = halsH + 0.5);
    translate([0, 0, halsH]) hull() {
      cylinder(d = knottD - 2, h = 0.6);
      translate([0, 0, 1.4]) cylinder(d = knottD, h = knottH - 3.4);
      translate([0, 0, knottH - 0.6]) cylinder(d = knottD - 2.4, h = 0.6);
    }
  }
}

// elementet (bare til bilder og snitt)
module element() {
  translate([0, bafY + bafT, zc]) rotate([-90, 0, 0]) {
    color(c_mork) cylinder(d = drvRamme, h = 3);
    color([0.2, 0.2, 0.21]) translate([0, 0, 3]) cylinder(d1 = 70, d2 = 46, h = 22);
    color([0.3, 0.3, 0.32]) translate([0, 0, 25]) cylinder(d = 52, h = 14);
  }
}

module samlet() { kropp(); front(); grill_plate(); knott(); element(); }

if (part == "kropp") kropp();
else if (part == "front") front();
else if (part == "grill_plate") grill_plate();
else if (part == "knott") knott();
else if (part == "element") element();
else if (part == "snitt") difference() { samlet(); translate([0, -200, -10]) cube([200, 400, 300]); }
else samlet();
