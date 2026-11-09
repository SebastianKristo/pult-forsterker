// Skjold Sans – multisensor for vegg (bad, gang, stue): bevegelse, temperatur, fuktighet og lys.
// Wemos D1 mini (ESP8266) + AM312 PIR + temperatur/fukt (SHT40/SHT31/BME280 anbefalt på bad, DHT11/DHT22 passer også)
// + lite lyskort (BH1750/TEMT6000 o.l.). Strøm: USB-kabel inn nedenfra.
//
// Koordinater (montert): x mot høyre, z opp, y fra forsiden (y = 0) og bakover mot veggen (y = D).
// To printede deler + gullskjold:
//   kropp       – forsiden ned på plata, ingen støtte
//   bakplate    – skrus i veggen (2 × senkeskrue), baksiden ned; D1 mini og sensorkortet sitter på den
//   logo        – lite skjold i gull, felt inn i forsiden (samme utskrift som kroppen)
// Kroppen klikkes på bakplata (to rygger) og trekkes rett ut for service.
//
// Det viktigste: temperatur- og fuktsensoren sitter i et eget kammer nede til venstre, skilt fra ESP-en med dobbel
// vegg og luftspalte, og har egne lameller i siden og spalter i bunnen. Varmen fra ESP-en stiger opp og ut på
// høyre side, så sensoren måler romluft – ikke elektronikk. Lamellene heller 45° nedover utover, så vannsprut ikke
// går rett inn (bad: heng den utenfor sone 1 og 2, f.eks. høyt på veggen ved døra).

part = "samlet";

// ---------- ytre mål ----------
W = 56; H = 80; D = 26;           // bredde, høyde, dybde (med bakplata)
R = 10;                           // hjørneradius sett forfra
t = 2.0;                          // veggtykkelse
fas = 1.2;                        // 45° fas på forkanten (mot skriveplata)
plT = 2.4;                        // bakplatas tykkelse
Db = D - plT;                     // kroppens dybde (bakkanten mot bakplata)

// ---------- sensorkammeret (nede til venstre) ----------
chW = 17;                         // innvendig bredde
chH = 32;                         // innvendig høyde (gulv i z = t)
vW = 1.2; vG = 1.6;               // dobbel vegg: to vegger med luftspalte
dX0 = -W/2 + t + chW;             // skilleveggens venstre side
dX1 = dX0 + 2 * vW + vG;          // skilleveggens høyre side
rZ0 = t + chH;                    // kammerets tak (underside)
rZ1 = rZ0 + 2 * vW + vG;          // kammerets tak (overside)
kortX = -W/2 + t + chW/2 + 2;     // sensorkortet står i et spor på bakplata (kortet vender mot lamellene til venstre)
kortZ = [7, 29];                  // sporets lengde (z)

// ---------- D1 mini ----------
d1W = 25.6; d1L = 34.2; d1T = 1.6;
d1X = (dX1 + W/2 - t) / 2;        // midt i hovedrommet
d1Z0 = 22;                        // underkant (plass til USB-pluggen under)
d1Z1 = d1Z0 + d1L;
d1Bak = Db - 4.5;                 // kortets bakside (ESP-modulen vender mot bakplata)
d1For = d1Bak - d1T;              // kortets forside (USB-kontakten)
usbY = d1For - 1.5;               // midt i USB-kontakten

// ---------- forsiden ----------
pirZ = H - 15; pirHull = 12.4; pirRib = 12.1; pirRorL = 10;   // AM312: kuppel ca. Ø12 stikker ut; tre ribber holder den
lysZ = 47; lysB = 11.5; lysL = 18.5; lysVindu = 3.2;          // lyskortet (mål ditt eget), liggende, vindu midt på
logoZ = 13; logoT = 0.6; logoS = 2.1;

// ---------- feste ----------
skrueX = 16; skrueZ = pirZ;       // to senkeskruer (Ø3–3,5) i veggen
leppe = 3; klar = 0.25;           // bakplatas leppe inn i kroppen

$fn = 64;

// ---------- hjelpere ----------
module F() { multmatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) children(); }   // 2D (x, z) → montert, ekstrudert langs y
module ut2d(o = 0) { translate([0, H/2]) offset(r = R + o) offset(delta = -R) square([W, H], center = true); }
module skjold2d(s = logoS) { scale(s) polygon([[-1.9, 1.9], [1.9, 1.9], [1.9, 0.2], [0, -2.3], [-1.9, 0.2]]); }
module lameller(side, z) {   // en spalte gjennom sideveggen, 45° ned utover; lang i y (står i printen)
  sx = side < 0 ? -1 : 1;
  hull() {
    translate([sx * (W/2 - t - 0.6), 5, z]) cube([0.01, Db - 8, 1.6]);
    translate([sx * (W/2 + 1), 5, z - (t + 1.6)]) cube([0.01, Db - 8, 1.6]);
  }
}
module bunnspalte(x) { translate([x - 0.8, 5, -1]) cube([1.6, Db - 8, t + 2]); }

// skilleveggen og taket (dobbel vegg med luftspalte), innenfor kroppens innside
module skillevegg2d() {
  intersection() {
    ut2d(-t + 0.01);
    union() {
      for (x = [dX0, dX1 - vW]) translate([x, -1]) square([vW, rZ1 + 1]);
      for (z = [rZ0, rZ1 - vW]) translate([-W, z]) square([W + dX1, vW]);
    }
  }
}
module skilleomr2d(o = 0) { offset(delta = o) union() { translate([dX0, -1]) square([dX1 - dX0, rZ1 + 1]); translate([-W, rZ0]) square([W + dX1, rZ1 - rZ0]); } }

// ---------- kroppen ----------
module kropp() {
  difference() {
    union() {
      difference() {
        union() {
          hull() { F() linear_extrude(0.01) ut2d(-fas); F() translate([0, 0, fas]) linear_extrude(0.01) ut2d(0); }
          F() translate([0, 0, fas]) linear_extrude(Db - fas) ut2d(0);
        }
        F() translate([0, 0, t]) linear_extrude(Db) ut2d(-t);
      }
      F() translate([0, 0, t - 0.01]) linear_extrude(Db - t - 0.2 + 0.01) skillevegg2d();
      // PIR-rør, lysramme og pinner som holder D1 mini mot bakplata
      translate([0, t - 0.01, pirZ]) rotate([-90, 0, 0]) difference() {
        cylinder(d = pirHull + 2.4, h = pirRorL);
        translate([0, 0, -1]) cylinder(d = pirHull, h = pirRorL + 2);
      }
      for (a = [90, 210, 330]) translate([0, t - 0.01, pirZ]) rotate([-90, 0, 0]) rotate([0, 0, a])
        translate([pirRib/2, -0.6, 0]) cube([(pirHull - pirRib)/2 + 0.3, 1.2, pirRorL]);
      translate([0, t - 0.01, lysZ]) rotate([-90, 0, 0]) linear_extrude(2.6) difference() {
        square([lysL + 0.4 + 2.4, lysB + 0.4 + 2.4], center = true); square([lysL + 0.4, lysB + 0.4], center = true);
        translate([0, (lysB + 3)/2]) square([lysL - 4, 3], center = true);    // åpning nede for ledningene
      }
      for (p = d1Pinner()) translate([p[0] - 1.25, t - 0.01, p[1] - 1.25]) cube([2.5, d1For - 0.3 - t + 0.01, 2.5]);
    }
    // PIR: hull med 45° utvidelse utover, rør innvendig
    translate([0, -1, pirZ]) rotate([-90, 0, 0]) cylinder(d = pirHull, h = t + 2);
    translate([0, -0.01, pirZ]) rotate([-90, 0, 0]) cylinder(d1 = pirHull + 1.6, d2 = pirHull, h = 0.81);
    // lysvindu
    translate([0, -1, lysZ]) rotate([-90, 0, 0]) cylinder(d = lysVindu, h = t + 2, $fn = 32);
    translate([0, -0.01, lysZ]) rotate([-90, 0, 0]) cylinder(d1 = lysVindu + 1.6, d2 = lysVindu, h = 0.81, $fn = 32);
    // gullskjoldet
    logo_form(0.01);
    // sensorkammeret: lameller til venstre og spalter i bunnen
    for (z = [12 : 4 : rZ0 - 2]) lameller(-1, z);
    for (x = [-W/2 + 6 : 3 : dX0 - 2]) bunnspalte(x);
    // hovedrommet: lameller oppe til høyre (varmen ut), spalter i bunnen (luft inn)
    for (z = [42 : 4 : H - 12]) lameller(1, z);
    for (dx = [-7, -4.5, 4.5, 7]) bunnspalte(d1X + dx);
    // kabelspor nedenfra, åpent bakover (kabelen sitter i D1 mini når kroppen settes på)
    hull() { translate([d1X, usbY, -1]) cylinder(d = 4.2, h = t + 2); translate([d1X - 2.1, Db, -1]) cube([4.2, 1, t + 2]); }
    // ledningsgjennomføring fra kammeret, ved bakkanten
    translate([dX0 - 1, Db - 2.5, rZ0 - 5]) cube([dX1 - dX0 + 2, 3, 4]);
    // spor for bakplatas klikk-rygger
    for (s = [-1, 1]) klikk(s, 0.25, true);
  }
}
// klikk-ryggen (bakplata) og sporet (kroppen): trekantprofil, 45° begge veier, langs z
module klikk(s, o = 0, spor = false) {
  z0 = s < 0 ? 42 : 18; L = 12;
  x = s * (W/2 - t - klar);
  translate([x, Db - 1.6, z0 - o]) rotate([0, 0, 0])
    linear_extrude(L + 2 * o) polygon(s < 0 ? [[0, -0.7 - o], [-0.7 - o + (spor ? 0 : 0), 0], [0, 0.7 + o]] : [[0, -0.7 - o], [0.7 + o, 0], [0, 0.7 + o]]);
}
function d1Pinner() = [[d1X - d1W/2 + 1.3, d1Z0 + 2], [d1X + d1W/2 - 1.3, d1Z0 + 2], [d1X + d1W/2 - 1.3, d1Z1 - 2]];
module logo_form(e = 0) { F() translate([0, 0, -e]) linear_extrude(logoT + e) translate([0, logoZ]) offset(delta = e) skjold2d(); }

// ---------- bakplata ----------
module bakplate() {
  difference() {
    union() {
      hull() { F() translate([0, 0, D - 0.6]) linear_extrude(0.6) ut2d(-0.6); F() translate([0, 0, Db]) linear_extrude(plT - 0.6) ut2d(0); }
      // leppe inn i kroppen, med åpning for skilleveggen og kabelen
      F() translate([0, 0, Db - leppe]) linear_extrude(leppe + 0.01) difference() {
        ut2d(-t - klar); ut2d(-t - klar - 1.6);
        skilleomr2d(0.4);
        translate([d1X - 3, -1]) square([6, t + 3]);
      }
      for (s = [-1, 1]) klikk(s);
      // D1 mini: fire hjørnestøtter (4,5 mm, fri for ESP-modulen) med vinkler som holder kortet på plass
      for (sx = [-1, 1], sz = [-1, 1]) let(cx = d1X + sx * (d1W/2 - 1.3), cz = sz < 0 ? d1Z0 + 2 : d1Z1 - 2) {
        translate([cx - 1.3, d1Bak, cz - 1.3]) cube([2.6, Db - d1Bak + 0.01, 2.6]);
        translate([d1X + sx * (d1W/2 + 0.25) + (sx < 0 ? -1.2 : 0), d1For - 0.6, cz - 3]) cube([1.2, Db - d1For + 0.61, 6]);
      }
      for (sx = [-1, 1]) translate([d1X + sx * 8 - 3, d1For - 0.6, (sx < 0 ? d1Z0 : d1Z1) + (sx < 0 ? -1.45 : 0.25)]) cube([6, Db - d1For + 0.61, 1.2]);   // stopp under og over, fri for USB-kontakten
      // sensorkortet: spor (1,8 mm) mellom to ribber
      for (dx = [-1.8/2 - 1.2, 1.8/2]) translate([kortX + dx, Db - 3, kortZ[0]]) cube([1.2, 3.01, kortZ[1] - kortZ[0]]);
    }
    // senkeskruer i veggen (hodet i flukt med innsiden)
    for (s = [-1, 1]) translate([s * skrueX, 0, skrueZ]) {
      translate([0, Db - 1, 0]) rotate([-90, 0, 0]) cylinder(d = 3.6, h = plT + 2, $fn = 24);
      translate([0, Db - 0.01, 0]) rotate([-90, 0, 0]) cylinder(d1 = 7.2, d2 = 3.6, h = 1.81, $fn = 32);
    }
  }
}

// ---------- kjøpte deler (bare for bildene og kollisjonssjekken) ----------
module d1mini() {
  color("#1d5fa8") translate([d1X - d1W/2, d1For, d1Z0]) cube([d1W, d1T, d1L]);
  color("#b8b8bc") translate([d1X - 8, d1Bak, d1Z1 - 24]) cube([16, 3.2, 24]);                 // ESP-modulen (mot bakplata)
  color("#b8b8bc") translate([d1X - 4, d1For - 2.8, d1Z0 - 0.6]) cube([8, 2.8, 5.6]);          // micro-USB
  color("#333") translate([d1X - 4.5, d1For - 2.2, d1Z0 + 12]) cube([9, 2.2, 6]);              // CH340
}
module usbplugg() {
  color("#222") translate([d1X - 5.5, usbY - 3.5, d1Z0 - 17]) cube([11, 7, 12]);
  color("#222") translate([d1X, usbY, -6]) cylinder(d = 3.6, h = d1Z0 - 17 + 6.01);
}
module pir() {
  color("#f4f4f2") translate([0, 0.6, pirZ]) scale([1, 0.55, 1]) sphere(d = 12);
  color("#f4f4f2") translate([0, 0.6, pirZ]) rotate([-90, 0, 0]) cylinder(d = 12, h = 7);
  color("#2a2a2a") translate([-5, 7.6, pirZ - 4]) cube([10, 1.2, 8]);
}
module lyskort() {
  color("#7b3fa0") translate([-lysL/2, t + 1, lysZ - lysB/2]) cube([lysL, 1.6, lysB]);
  color("#ddd") translate([-1.5, t + 0.2, lysZ - 1.5]) cube([3, 0.8, 3]);
}
module sensorkort() {   // DHT11-modul: kort 28 × 14, sensoren 15,5 × 12 × 5,5 mot venstre
  color("#2d6fb5") translate([kortX - 0.8, Db - 3 - 11, kortZ[0] - 2]) cube([1.6, 14, 26]);
  color("#7fc6e8") translate([kortX - 0.8 - 5.5, Db - 13.5, kortZ[0] + 1]) cube([5.5, 10, 15.5]);
}

module samlet(ex = 0) {
  color("#ECE9E3") kropp();
  color("#D99E40") logo_form();
  color("#E4E1DA") translate([0, ex, 0]) { bakplate(); d1mini(); usbplugg(); sensorkort(); }
  pir(); lyskort();
}

if (part == "kropp") rotate([90, 0, 0]) kropp();                                  // forsiden ned
else if (part == "logo") rotate([90, 0, 0]) logo_form();
else if (part == "bakplate") translate([0, 0, D]) rotate([-90, 0, 0]) bakplate();   // baksiden ned
else if (part == "a_kropp") kropp(); else if (part == "a_logo") logo_form(); else if (part == "a_bakplate") bakplate();
else if (part == "a_d1") d1mini(); else if (part == "a_plugg") usbplugg(); else if (part == "a_pir") pir();
else if (part == "a_lys") lyskort(); else if (part == "a_sensor") sensorkort();
else if (part == "eksplodert") samlet(30);
else samlet();
