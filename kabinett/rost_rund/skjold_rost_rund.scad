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
$fn = 64;

// ---------- mål ----------
W = 108; Dp = 96; R = 28;          // grunnriss: avrundet rektangel
H = 150;                           // høyde fra bunnplatens underside til toppen av lokket
bpT = 5; capT = 5;                 // bunnplate og lokk
sl = 1.8; sg = 0.3; t = 2.4;       // hylsens vegg, luft mellom hylse og kjerne, kjernens vegg
z0 = bpT; z1 = H - capT;           // kjernen og hylsen står mellom bunnplaten og lokket
rT = 4;                            // toppkanten: R4, som flater ut i 45° fas mot toppen (printes med toppen ned)
fot = 12.4; fotH = 0.6;            // forsenkninger for selvklebende gummiføtter Ø12 × 6 mm
// element (3″ fullrange, f.eks. Dayton RS75-4) bakfra mot frontblokka
drvZ = 78; drvCut = 72; drvTun = 74; drvPCD = 82; blk = 16;   // senter, utsparing, tunnel, hullsirkel, blokkas dybde fra fronten
// bassrefleks ned gjennom bunnen (føttene gir 6 mm luft)
portD = 18; portW = 2; portL = 110; portP = [-14, 26];
// stenger og innpressmuttere
rodP = [for (sx = [-1, 1], sy = [-1, 1]) [sx * 37, sy * 30]];
rodD = 3.4; bossD = 9; ins = 4.0; insL = 5.5;
// I/O bak nede (gjennom kjernen; hylsa har en spiss bue rundt)
ioX = 16; dcZ = z0 + 12; usbZ = z0 + 6; dcD = 8.2; usbW = 10; usbH = 4.4;
ioW = 32; ioH = 28;                 // utsparingen i hylsa: bredde og høyde til spissen (45° tak, printes stående)
// topp: fem knapper foran, knott bak
btnY = -24; btnX = [-28, -14, 0, 14, 28]; capD = 9.0; capHole = 9.5; flD = 12; flT = 0.9; capUp = 1.1;
encY = 14; ec11D = 7.2; knobD = 34; knobH = 13; shaftD = 6.1; shaftFlat = 4.6;
boardY = btnY; boardZ = z1 - 6.7;   // knappekortets overside: 6 × 6 × 5 mm-bryterne står 0,2 mm under hettenes nupp

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
        hull() {   // bakflaten er flat i drvZ ± 50 (elementets ramme), 45° ut mot fronten over og under
          translate([-W, -Dp/2, drvZ - 50 - blk]) cube([2 * W, 1, 100 + 2 * blk]);
          translate([-W, -Dp/2 + blk - 1, drvZ - 50]) cube([2 * W, 1, 100]);
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
    for (a = [45, 135, 225, 315]) translate([drvPCD/2 * cos(a), -Dp/2 - 1, drvZ + drvPCD/2 * sin(a)]) rotate([-90, 0, 0]) {
      cylinder(d = 3.4, h = blk + 2);                                     // M3 × 25 gjennom blokka, mutter bak elementets ramme
      cylinder(d1 = 6.6, d2 = 3.4, h = 1 - inn + 1.6);                    // senkehode i flukt med kjernens front (under hylsa)
    }
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
      for (p = rodP) translate([p[0], p[1], z1 - 8]) cylinder(d = bossD, h = 8.01);
      for (sx = [-1, 1]) translate([sx * 38, boardY, boardZ]) cylinder(d = 6, h = z1 - boardZ + 0.01);          // knappekortets tapper
    }
    for (p = rodP) translate([p[0], p[1], z1 - 8.1]) cylinder(d = ins, h = insL);
    for (x = btnX) translate([x, btnY, z1 - 1]) cylinder(d = capHole, h = capT + 2);
    for (x = btnX) translate([x, btnY, H - 0.6]) cylinder(d1 = capHole, d2 = capHole + 1.2, h = 0.61);
    translate([0, encY, z1 - 1]) cylinder(d = ec11D, h = capT + 2);
    translate([0, encY, z1 - 0.01]) cylinder(d = 12.5, h = 2.4);                      // EC11-mutteren under lokket
    for (sx = [-1, 1]) translate([sx * 38, boardY, boardZ - 0.1]) cylinder(d = 2.2, h = 5);
  }
}

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

// 3″-elementet (bare for bildene): ramme mot frontblokka bakfra, membran og støvhette
module element() {
  translate([0, -Dp/2 + blk, drvZ]) rotate([-90, 0, 0]) {
    difference() { cylinder(d = 86, h = 4); translate([0, 0, -1]) cylinder(d = 62, h = 6); }
    translate([0, 0, -0.5]) cylinder(d1 = 70, d2 = 30, h = 22);
    translate([0, 0, 4]) cylinder(d = 52, h = 26);
  }
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
else if (part == "knapp") for (i = [0:4]) translate([i * (flD + 3), 0, capUp]) rotate([180, 0, 0]) knapp_lok(i);
else if (part == "a_kjerne") kjerne(); else if (part == "a_bunn") bunn(); else if (part == "a_lokk") lokk();
else if (part == "a_knott") knott(); else if (part == "a_knapp") knapper(); else if (part == "a_stenger") stenger();
else if (part == "a_element") element();
else if (part == "a_logo") logo_form(0); else if (part == "logo_kutt") logo_form(0.01);
else if (part == "eksplodert") samlet(30);
else samlet();
