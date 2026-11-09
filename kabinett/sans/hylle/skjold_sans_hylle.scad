// Skjold Sans Hylle – multisensor som henger under en hylle (f.eks. ved forkanten av en hylle i et hjørneskap).
// Samme innmat som Skjold Sans: Wemos D1 mini + AM312 PIR + temperatur/fukt (SHT40 anbefalt) + lite lyskort.
//
// Formen: en lav «list» (84 × 64 × 26 mm) med flat topp mot hylla, runde hjørner sett ovenfra og en front som
// følger hyllas bue (hylleR) og skrår 20° innover nedover, så PIR-en ser ut i rommet og litt ned. En tynn gullstripe går rundt nede.
//
// Inni (sett ovenfra):
//   - venstre: sensorkammeret, skilt fra resten med dobbel vegg; spalter i bunnen (peker rett ned) og i venstre side
//   - midten foran: PIR-en; høyre foran: lysvinduet
//   - høyre: D1 mini liggende under topplata (ESP-modulen opp, USB-kontakten bak). Pluggen stikker ut bak gjennom et
//     spor, og kabelen går langs hylla inn mot hjørnet. Varmen går ut gjennom spalter bak og på høyre side, oppe.
//
// Koordinater (montert): x mot høyre, y bakover (forsiden mot −y), z opp; hyllas underside i z = 0, kroppen under.
// Delene:
//   kropp     – bunnen ned på skriveplata, ingen støtte
//   plate     – topplata som skrus under hylla (2 × treskrue 3 × 12, eller monteringstape); siden mot hylla ned
//   gull      – gullstripa rundt kroppen (samme utskrift som kroppen)
// Kroppen klikkes opp på topplata (to rygger) og trekkes rett ned for service.

part = "samlet";

// ---------- ytre mål ----------
W = 84; Dd = 64; Hh = 26;         // bredde, dybde, høyde
R = 8;                            // hjørneradius sett ovenfra
tilt = 20;                        // frontens helning fra loddrett (innover nedover)
t = 2.0;                          // veggtykkelse
plT = 3.0;                        // topplatas tykkelse
yF0 = -Dd/2;                      // frontens overkant
yF1 = yF0 + Hh * tan(tilt);       // frontens underkant (midt på)
hylleR = 350;                     // radius på hyllas forkant sett ovenfra (mål din: se LES_MEG); fronten følger buen
hylleC = [0, yF0 + hylleR];       // buens sentrum (bak enheten)
gullZ = -20; gullH = 1.0; gullT = 0.6;   // gullstripa

// ---------- innmat ----------
skX0 = -14; vW = 1.2; vG = 1.6;   // skilleveggens venstre side (kammeret er til venstre for den)
skX1 = skX0 + 2 * vW + vG;
kortX = -27;                      // sensorkortet står i et spor i bunnen, sensoren mot venstre
kortY = [-12, 14];
d1W = 25.6; d1L = 34.2; d1T = 1.6;
d1X = 22.5; d1Y0 = -16; d1Y1 = d1Y0 + d1L;   // D1 mini ligger med USB-kanten bak (y = d1Y1)
d1Hoy = 5.5;                      // fra topplata ned til kortets overside (ESP-modulen er her)
d1Z1 = -d1Hoy; d1Z0 = d1Z1 - d1T; // kortets overside og underside
usbZ = d1Z0 - 1.4;                // midt i USB-kontakten (under kortet)
pirZ = -11; lysZ = -11; lysX = 16;
lysB = 11.5; lysL = 18.5; lysVindu = 3.2;    // lyskortet (mål ditt eget): liggende, vindu midt på
skrueP = [[-27, 0], [24, -24]];   // skruene opp i hylla
leppe = 3; klar = 0.25;

$fn = 64;

// ---------- form ----------
module plan2d(o = 0) {   // sett ovenfra: runde hjørner, fronten følger hyllebuen
  offset(r = R + o) offset(delta = -R) intersection() {
    square([W, Dd], center = true);
    translate(hylleC) circle(r = hylleR, $fn = 1440);
  }
}
function sag(x) = hylleR - sqrt(hylleR * hylleR - x * x);   // hvor mye fronten ligger bak midten ved x
module side2d(o = 0) {   // sett fra siden (y, z): front som skrår, fas nede foran og bak, toppen åpen over z = 0
  offset(delta = o) polygon([
    [yF0 - 20, 5], [Dd/2, 5], [Dd/2, -Hh + 2.5], [Dd/2 - 2.5, -Hh], [yF0 - 20, -Hh]]);   // fronten lages av konen under
}
module X() { multmatrix([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) children(); }   // 2D (y, z), ekstrudert langs x
// fronten: en kon rundt hyllebuens sentrum, så skråningen (20°) og fasen nede følger buen
module front_kon(o = 0) {
  A = asin((W/2 + 12) / hylleR);
  translate([hylleC[0], hylleC[1], 0]) rotate([0, 0, -90 - A]) rotate_extrude(angle = 2 * A, $fn = 4000)
    offset(delta = o) polygon([[hylleR - 120, 5], [hylleR + 5 * tan(tilt), 5], [hylleR - (Hh - 3.5) * tan(tilt), -Hh + 3.5],
                               [hylleR - Hh * tan(tilt) - 2, -Hh], [hylleR - 120, -Hh]]);
}
module form(o = 0, z0 = -Hh - 1, z1 = 0) {
  intersection() {
    translate([0, 0, z0]) linear_extrude(z1 - z0) plan2d(o);
    X() translate([0, 0, -W]) linear_extrude(2 * W) side2d(o);
    front_kon(o);
  }
}
module innside(o = 0) { form(-t + o, -Hh + t - o, 1); }
// lokal ramme på fronten: X langs x, Y opp langs fronten, Z innover (vinkelrett på fronten)
module paa_front(x, z) {
  n = [0, cos(tilt), sin(tilt)];   // innover
  translate([x, yF0 + sag(x), 0]) rotate([0, 0, asin(x / hylleR)]) translate([0, (-z) * tan(tilt), z]) multmatrix([[1, 0, 0, 0], [0, -sin(tilt), cos(tilt), 0], [0, cos(tilt), sin(tilt), 0], [0, 0, 0, 1]]) children();
}
module draape2d(d) { hull() { circle(d = d); translate([0, d/2 * sqrt(2)]) square(0.01, center = true); } }   // spiss opp: hull uten støtte

// ---------- kroppen ----------
module kropp() {
  difference() {
    union() {
      difference() { form(0); innside(0); }
      intersection() {
        innside(0.01);
        union() {
          // dobbel skillevegg, fra bunnen opp til platen
          for (x = [skX0, skX1 - vW]) translate([x, -Dd, -Hh]) cube([vW, 2 * Dd, Hh - 0.2]);
          // blokker bak PIR og lyskortet (står på bunnen, baksiden parallell med fronten)
          for (b = [[0, 8, 12], [lysX, lysL/2 + 2.2, 6.5]]) translate([b[0] - b[1], 0, 0])
            X() translate([0, 0, 0]) linear_extrude(2 * b[1]) polygon([[-Dd, -Hh], [-Dd, -3.5], [yF0 + b[2] / cos(tilt) + 3.5 * tan(tilt), -3.5], [yF0 + b[2] / cos(tilt) + Hh * tan(tilt), -Hh]]);
          // pinner fra bunnen som holder D1 mini opp mot topplata
          for (p = d1Pinner()) translate([p[0] - 1.25, p[1] - 1.25, -Hh]) cube([2.5, 2.5, Hh + d1Z0 - 0.3]);
          // spor for sensorkortet (1,8 mm) i bunnen
          for (dx = [-1.8/2 - 1.2, 1.8/2]) translate([kortX + dx, kortY[0], -Hh]) cube([1.2, kortY[1] - kortY[0], t + 3]);
        }
      }
    }
    // PIR: hull med spiss tak, gjennom fronten og blokka
    paa_front(0, pirZ) {   // rundt hull i fronten, spisst tak bare inne i blokka (synes ikke utenfra)
      translate([0, 0, -3]) cylinder(d = 12.4, h = t + 3.5);
      translate([0, 0, t + 0.4]) linear_extrude(14) draape2d(12.4);
    }
    // lysvindu og spor for lyskortet (skyves ned ovenfra, parallelt med fronten)
    paa_front(lysX, lysZ) {
      translate([0, 0, -1]) cylinder(d = lysVindu, h = t + 2, $fn = 24);
      translate([-(lysL + 0.6)/2, -(lysB + 0.6)/2, t + 0.9]) cube([lysL + 0.6, 40, 2.0]);
    }
    // gullstripa
    gull_form(0.01);
    // sensorkammeret: spalter i bunnen (rett ned) og i venstre side
    for (x = [-37, -34, -31, -22, -19]) translate([x - 0.8, -17, -Hh - 1]) cube([1.6, 41, t + 2]);
    for (y = [-14 : 4 : 22]) translate([-W/2 - 1, y - 0.8, -Hh + 6]) cube([t + 2, 1.6, 11]);
    // ESP-rommet: spalter bak og på høyre side, oppe
    for (x = [-8 : 3 : 34]) if (abs(x - d1X) > 8.5) translate([x - 0.8, Dd/2 - t - 1, -14]) cube([1.6, t + 2, 10]);
    for (y = [-12 : 4 : 24]) translate([W/2 - t - 1, y - 0.8, -14]) cube([t + 2, 1.6, 10]);
    // spor bak for USB-pluggen og kabelen, åpent opp mot platen
    translate([d1X - 6.25, Dd/2 - t - 1, usbZ - 4]) cube([12.5, t + 2, -usbZ + 5]);
    // ledningsgjennomføring øverst bak i skilleveggen
    translate([skX0 - 1, Dd/2 - t - 5, -4]) cube([skX1 - skX0 + 2, 4, 5]);
    // spor for klikk-ryggene
    for (s = [-1, 1]) klikk(s, 0.25);
  }
}
function d1Pinner() = [for (sx = [-1, 1], y = [d1Y0 + 2, d1Y1 - 2]) [d1X + sx * (d1W/2 - 1.3), y]];
module klikk(s, o = 0) {   // trekantprofil (45°) langs y på leppas yttersider
  translate([s * (W/2 - t - klar), -8 - o, -1.6]) rotate([-90, 0, 0])
    linear_extrude(16 + 2 * o) polygon([[0, -0.7 - o], [s * (0.7 + o), 0], [0, 0.7 + o]]);
}
module gull_form(e = 0) {
  difference() { form(e, gullZ - e, gullZ + gullH + e); form(-gullT - e, gullZ - 1, gullZ + gullH + 1); }
}

// ---------- topplata ----------
module plate() {
  difference() {
    union() {
      linear_extrude(plT) plan2d(0);
      // leppe inn i kroppen (følger innsiden, også der fronten skrår), med åpning for skilleveggen og pluggen
      difference() {
        intersection() { innside(-klar); translate([-W, -Dd, -leppe]) cube([2 * W, 2 * Dd, leppe + 0.01]); }
        innside(-klar - 1.6);
        translate([skX0 - 0.4, -Dd, -leppe - 1]) cube([skX1 - skX0 + 0.8, 2 * Dd, leppe + 2]);
        translate([d1X - 7, 0, -leppe - 1]) cube([14, Dd, leppe + 2]);
      }
      for (s = [-1, 1]) klikk(s);
      // D1 mini: fire støtter (fri for ESP-modulen), vinkler på sidene og stopp foran
      for (sx = [-1, 1], y = [d1Y0 + 2, d1Y1 - 2]) {
        translate([d1X + sx * (d1W/2 - 1.3) - 1.3, y - 1.3, d1Z1]) cube([2.6, 2.6, -d1Z1 + 0.01]);
        translate([d1X + sx * (d1W/2 + 0.25) + (sx < 0 ? -1.2 : 0), y - 3, d1Z0 - 0.6]) cube([1.2, 6, -d1Z0 + 0.61]);
      }
      translate([d1X - 4, d1Y0 - 1.45, d1Z0 - 0.6]) cube([8, 1.2, -d1Z0 + 0.61]);
    }
    for (p = skrueP) translate([p[0], p[1], -1]) {
      cylinder(d = 3.4, h = plT + 2, $fn = 24);
      cylinder(d1 = 7.4, d2 = 3.4, h = 1 + 2, $fn = 32);    // senkehode i flukt med undersiden
    }
  }
}

// ---------- kjøpte deler (bilder og kollisjonssjekk) ----------
module d1mini() {
  color("#1d5fa8") translate([d1X - d1W/2, d1Y0, d1Z0]) cube([d1W, d1L, d1T]);
  color("#b8b8bc") translate([d1X - 8, d1Y0, d1Z1]) cube([16, 24, 3.2]);                  // ESP-modulen (opp)
  color("#b8b8bc") translate([d1X - 4, d1Y1 - 5, d1Z0 - 2.8]) cube([8, 5.6, 2.8]);        // micro-USB (under, bak)
  color("#333") translate([d1X - 4.5, d1Y0 + 14, d1Z0 - 2.2]) cube([9, 6, 2.2]);          // CH340 (under)
}
module usbplugg() {
  color("#222") translate([d1X - 5.5, d1Y1 + 0.6, usbZ - 3.5]) cube([11, 16.4, 7]);
  color("#222") translate([d1X, d1Y1 + 17, usbZ]) rotate([-90, 0, 0]) cylinder(d = 3.6, h = 20);
}
module pir() {
  paa_front(0, pirZ) {
    color("#f4f4f2") translate([0, 0, 0.4]) scale([1, 1, 0.55]) sphere(d = 12);
    color("#f4f4f2") translate([0, 0, 0.4]) cylinder(d = 12, h = 7);
    color("#2a2a2a") translate([-5, -4, 7.4]) cube([10, 8, 1.2]);
  }
}
module lyskort() {
  paa_front(lysX, lysZ) {
    color("#7b3fa0") translate([-lysL/2, -lysB/2, t + 1.1]) cube([lysL, lysB, 1.6]);
    color("#ddd") translate([-1.5, -1.5, t + 0.25]) cube([3, 3, 0.8]);
  }
}
module sensorkort() {   // SHT40-modul o.l.: kort 20 × 14 stående i sporet, sensoren mot venstre
  color("#2d6fb5") translate([kortX - 0.8, kortY[0] + 3, -Hh + t + 0.2]) cube([1.6, 20, 14]);
  color("#7fc6e8") translate([kortX - 0.8 - 2.5, kortY[0] + 8, -Hh + t + 5]) cube([2.5, 8, 6]);
}

module samlet(ex = 0) {
  color("#ECE9E3") translate([0, 0, -ex]) { kropp(); color("#D99E40") gull_form(); pir(); lyskort(); }
  color("#E4E1DA") { plate(); d1mini(); usbplugg(); }
  translate([0, 0, -ex]) sensorkort();
}

if (part == "kropp") translate([0, 0, Hh]) kropp();                                   // bunnen ned
else if (part == "gull") translate([0, 0, Hh]) gull_form();
else if (part == "plate") translate([0, 0, plT]) rotate([180, 0, 0]) plate();         // siden mot hylla ned
else if (part == "a_kropp") kropp(); else if (part == "a_gull") gull_form(); else if (part == "a_plate") plate();
else if (part == "a_d1") d1mini(); else if (part == "a_plugg") usbplugg(); else if (part == "a_pir") pir();
else if (part == "a_lys") lyskort(); else if (part == "a_sensor") sensorkort();
else if (part == "eksplodert") samlet(30);
else samlet();
