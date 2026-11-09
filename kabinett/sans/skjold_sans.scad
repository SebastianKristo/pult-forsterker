// Skjold Sans – multisensor for vegg (bad, gang, stue): bevegelse, temperatur, fuktighet og lys.
// Wemos D1 mini (ESP8266) + AM312 PIR + temperatur/fukt (SHT40/SHT31/BME280 anbefalt på bad, DHT11/DHT22 passer også)
// + lite lyskort (BH1750/TEMT6000 o.l.). Strøm: USB-kabel ut nederst i spissen.
//
// Formen er et skjold: flat topp med runde hjørner, rette sider og to buer som møtes i en spiss nede. Forkanten har
// en 2 mm fas, og en tynn gullkant følger omrisset 4 mm inne i fronten. PIR-kuppelen sitter øverst i midten,
// lysvinduet under.
//
// Inni:
//   - Sensorkammeret ligger i spissen, under et dobbelt tak (to vegger med luftspalte). Spissens buer vender nedover,
//     så luftspaltene der peker rett ned: luft kommer inn nedenfra, og vannsprut kan ikke falle inn.
//   - D1 mini står over taket med USB-kontakten ned og mot bakplata. Kabelen går i en lukket kanal langs bakplata,
//     gjennom kammeret og ut nederst. Kanalen er også luftinntaket for ESP-rommet, og lamellene oppe på sidene
//     slipper varmen ut. Varmen stiger altså bort fra sensoren.
//
// Koordinater (montert): x mot høyre, z opp (spissen i z = 0), y fra forsiden (y = 0) og bakover mot veggen (y = D).
// To printede deler + gullkant:
//   kropp       – forsiden ned på plata, ingen støtte
//   bakplate    – skrus i veggen (2 × senkeskrue), baksiden ned; D1 mini, kabelkanalen og sensorkortet sitter på den
//   logo        – gullkanten, felt inn i forsiden (samme utskrift som kroppen)
// Kroppen klikkes på bakplata (to rygger) og trekkes rett ut for service.

part = "samlet";

// ---------- ytre mål ----------
W = 64; H = 86; D = 28;           // bredde, høyde (spiss til topp), dybde (med bakplata)
Ra = 46;                          // buenes radius (spissen)
c = Ra - W/2;                     // buenes senter ligger c inn på motsatt side
zk = sqrt(Ra * Ra - c * c);       // der buene møter de rette sidene
Rt = 8;                           // hjørnene oppe
t = 2.0;                          // veggtykkelse
fas = 2.0;                        // 45° fas på forkanten (mot skriveplata)
plT = 2.4;                        // bakplatas tykkelse
Db = D - plT;                     // kroppens dybde (bakkanten mot bakplata)
kant = 4.0; kantB = 1.0; kantT = 0.6;   // gullkanten: avstand fra omrisset, bredde, dybde

// ---------- sensorkammeret (spissen) ----------
vW = 1.2; vG = 1.6;               // dobbelt tak: to vegger med luftspalte
rZ0 = 34;                         // takets underside
rZ1 = rZ0 + 2 * vW + vG;          // takets overside
kortX = -10;                      // sensorkortet står i et spor på bakplata, sensoren mot venstre
kortZ = [10.5, 33];                  // sporets lengde: kort inntil ca. 23 mm (SHT40, BME280, løs DHT11)

// ---------- D1 mini (ESP-modulen fram, USB-kontakten bak og ned) ----------
d1W = 25.6; d1L = 34.2; d1T = 1.6;
d1X = 13;
d1Z0 = rZ1 + 2;                   // underkant
d1Z1 = d1Z0 + d1L;
d1Hoy = 5.5;                      // avstand fra bakplata til kortets bakside (USB-kontakten og CH340 er her)
d1Bak = Db - d1Hoy;               // kortets bakside
d1For = d1Bak - d1T;              // kortets forside (ESP-modulen)
usbY = d1Bak + 1.4;               // midt i USB-kontakten / kabelen
kanB = 13; kanD = 8.5; kanV = 1.2;      // kabelkanalen: innvendig bredde og dybde fra bakplata, veggtykkelse

// ---------- forsiden ----------
pirZ = 72; pirHull = 12.4; pirRib = 12.1; pirRorL = 10;   // AM312: kuppel ca. Ø12 stikker ut; tre ribber holder den
lysZ = 56; lysB = 11.5; lysL = 18.5; lysVindu = 3.2;       // lyskortet (mål ditt eget), liggende, vindu midt på

// ---------- feste ----------
skrueX = 21; skrueZ = 79;         // to senkeskruer (Ø3–3,5) i veggen
leppe = 3; klar = 0.25;           // bakplatas leppe inn i kroppen
klikkZ = 48; klikkL = 10;         // klikk-ryggene på de rette sidene

$fn = 64;

// ---------- hjelpere ----------
module F() { multmatrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) children(); }   // 2D (x, z) → montert, ekstrudert langs y
module skjold() {
  union() {
    intersection() {   // øvre del: rette sider, runde hjørner oppe
      translate([0, (H + zk - 20) / 2]) offset(r = Rt) offset(delta = -Rt) square([W, H - zk + 20], center = true);
      translate([-W, zk]) square([2 * W, H]);
    }
    intersection() {   // spissen: to buer
      translate([c, zk]) circle(r = Ra, $fn = 240);
      translate([-c, zk]) circle(r = Ra, $fn = 240);
      translate([-W, -1]) square([2 * W, zk + 1.01]);
    }
  }
}
module ut2d(o = 0) { offset(delta = o) offset(r = 1.5) offset(delta = -1.5) skjold(); }   // spissen litt avrundet
function zInn(x) = zk - sqrt((Ra - t) * (Ra - t) - (c + abs(x)) * (c + abs(x)));        // bunnens innside ved x
module lameller(side, z) {   // spalte gjennom en rett sidevegg, 45° ned utover; lang i y (står i printen)
  sx = side < 0 ? -1 : 1;
  hull() {
    translate([sx * (W/2 - t - 0.6), 5, z]) cube([0.01, Db - 8, 1.6]);
    translate([sx * (W/2 + 1), 5, z - (t + 1.6)]) cube([0.01, Db - 8, 1.6]);
  }
}
module bunnspalte(x, y1 = Db - 4) { translate([x - 0.8, 6, -1]) cube([1.6, y1 - 6, zInn(x) + 2]); }   // peker rett ned
module kanal_omr(o = 0) { translate([d1X - kanB/2 - kanV - o, Db - kanD - kanV - o, -1]) cube([kanB + 2 * kanV + 2 * o, kanD + kanV + o + 1, d1Z0 + 1]); }

// ---------- kroppen ----------
module kropp() {
  difference() {
    union() {
      difference() {
        hull() { F() linear_extrude(0.01) ut2d(-fas); F() translate([0, 0, fas]) linear_extrude(Db - fas) ut2d(0); }
        F() translate([0, 0, t]) linear_extrude(Db) ut2d(-t);
      }
      // dobbelt tak over sensorkammeret, med utsparing der kabelkanalen går gjennom
      difference() {
        F() translate([0, 0, t - 0.01]) linear_extrude(Db - t - 0.2 + 0.01) intersection() {
          ut2d(-t + 0.01);
          for (z = [rZ0, rZ1 - vW]) translate([-W, z]) square([2 * W, vW]);
        }
        kanal_omr(0.3);
      }
      // PIR-rør med tre ribber, lysramme og pinner som holder D1 mini mot bakplata
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
    // PIR-hull med fas utover, lysvindu med fas
    translate([0, -1, pirZ]) rotate([-90, 0, 0]) cylinder(d = pirHull, h = t + 2);
    translate([0, -0.01, pirZ]) rotate([-90, 0, 0]) cylinder(d1 = pirHull + 1.6, d2 = pirHull, h = 0.81);
    translate([0, -1, lysZ]) rotate([-90, 0, 0]) cylinder(d = lysVindu, h = t + 2, $fn = 32);
    translate([0, -0.01, lysZ]) rotate([-90, 0, 0]) cylinder(d1 = lysVindu + 1.6, d2 = lysVindu, h = 0.81, $fn = 32);
    // gullkanten
    kant_form(0.01);
    // sensorkammeret: spalter i spissen som peker rett ned (foran kabelkanalen bare den fremre delen)
    for (x = [-24 : 3 : 3]) bunnspalte(x);
    for (x = [d1X - 4.5, d1X - 1.5, d1X + 1.5, d1X + 4.5]) bunnspalte(x, Db - kanD - kanV - 2);
    for (x = [24, 27]) bunnspalte(x);
    // ESP-rommet: lameller oppe på begge sider (varmen ut)
    for (s = [-1, 1], z = [62 : 4 : 74]) lameller(s, z);
    // kabelhull nederst, åpent bakover (kabelen sitter i D1 mini når kroppen settes på)
    hull() { translate([d1X, usbY, -1]) cylinder(d = 4.6, h = zInn(d1X + 3) + 2); translate([d1X - 2.3, Db, -1]) cube([4.6, 1, zInn(d1X + 3) + 2]); }
    // ledningsgjennomføring fra kammeret gjennom taket, ved bakkanten
    translate([kortX - 3, Db - 2.5, rZ0 - 1]) cube([6, 3, rZ1 - rZ0 + 2]);
    // spor for bakplatas klikk-rygger
    for (s = [-1, 1]) klikk(s, 0.25);
  }
}
// klikk-ryggen (bakplata) og sporet (kroppen): trekantprofil, 45° begge veier, langs z
module klikk(s, o = 0) {
  translate([s * (W/2 - t - klar), Db - 1.6, klikkZ - o])
    linear_extrude(klikkL + 2 * o) polygon([[0, -0.7 - o], [s * (0.7 + o), 0], [0, 0.7 + o]]);
}
function d1Pinner() = [[d1X - d1W/2 + 1.3, d1Z0 + 2], [d1X + d1W/2 - 1.3, d1Z0 + 2], [d1X + d1W/2 - 1.3, d1Z1 - 2]];
module kant_form(e = 0) { F() translate([0, 0, -e]) linear_extrude(kantT + e) difference() { ut2d(-kant + e); ut2d(-kant - kantB - e); } }

// ---------- bakplata ----------
module bakplate() {
  difference() {
    union() {
      hull() { F() translate([0, 0, D - 0.6]) linear_extrude(0.6) ut2d(-0.6); F() translate([0, 0, Db]) linear_extrude(plT - 0.6) ut2d(0); }
      // leppe inn i kroppen, med åpning for taket og kabelen
      F() translate([0, 0, Db - leppe]) linear_extrude(leppe + 0.01) difference() {
        ut2d(-t - klar); ut2d(-t - klar - 1.6);
        translate([-W, rZ0 - 0.4]) square([2 * W, rZ1 - rZ0 + 0.8]);
        translate([d1X - 3, -1]) square([6, zInn(d1X) + 4]);
      }
      for (s = [-1, 1]) klikk(s);
      // kabelkanalen: U-profil fra bakplata, fra bunnen opp til D1 mini (veggene er støtte under kortet)
      intersection() {
        difference() {
          translate([d1X - kanB/2 - kanV, Db - kanD - kanV, 0]) cube([kanB + 2 * kanV, kanD + kanV + 0.01, d1Z0 - 0.25]);
          translate([d1X - kanB/2, Db - kanD, -1]) cube([kanB, kanD + 1, d1Z0 + 1]);
        }
        F() translate([0, 0, t]) linear_extrude(Db) ut2d(-t - 0.3);
      }
      // D1 mini: fire hjørnestøtter, vinkler på sidene og stopp over
      for (sx = [-1, 1], sz = [-1, 1]) let(cx = d1X + sx * (d1W/2 - 1.3), cz = sz < 0 ? d1Z0 + 2 : d1Z1 - 2) {
        translate([cx - 1.3, d1Bak, cz - 1.3]) cube([2.6, Db - d1Bak + 0.01, 2.6]);
        translate([d1X + sx * (d1W/2 + 0.25) + (sx < 0 ? -1.2 : 0), d1For - 0.6, cz - 3]) cube([1.2, Db - d1For + 0.61, 6]);
      }
      translate([d1X + 4, d1For - 0.6, d1Z1 + 0.25]) cube([6, Db - d1For + 0.61, 1.2]);
      // sensorkortet: spor (1,8 mm) mellom to ribber
      for (dx = [-1.8/2 - 1.2, 1.8/2]) translate([kortX + dx, Db - 3, kortZ[0]]) cube([1.2, 3.01, kortZ[1] - kortZ[0]]);
    }
    // senkeskruer i veggen (hodet i flukt med innsiden)
    for (s = [-1, 1]) translate([s * skrueX, 0, skrueZ]) {
      translate([0, Db - 1, 0]) rotate([-90, 0, 0]) cylinder(d = 3.6, h = plT + 2, $fn = 24);
      translate([0, Db - 0.01, 0]) rotate([-90, 0, 0]) cylinder(d1 = 7.2, d2 = 3.6, h = 1.81, $fn = 32);
    }
    // kabelen ut under kanalen
    translate([d1X, usbY, -1]) cylinder(d = 4.6, h = 8);
  }
}

// ---------- kjøpte deler (bare for bildene og kollisjonssjekken) ----------
module d1mini() {
  color("#1d5fa8") translate([d1X - d1W/2, d1For, d1Z0]) cube([d1W, d1T, d1L]);
  color("#b8b8bc") translate([d1X - 8, d1For - 3.2, d1Z1 - 24]) cube([16, 3.2, 24]);          // ESP-modulen (fram)
  color("#b8b8bc") translate([d1X - 4, d1Bak, d1Z0 - 0.6]) cube([8, 2.8, 5.6]);               // micro-USB (bak)
  color("#333") translate([d1X - 4.5, d1Bak, d1Z0 + 12]) cube([9, 2.2, 6]);                   // CH340 (bak)
}
module usbplugg() {
  color("#222") translate([d1X - 5.5, usbY - 3.5, d1Z0 - 17]) cube([11, 7, 16.4]);
  color("#222") translate([d1X, usbY, -8]) cylinder(d = 3.6, h = d1Z0 - 17 + 8.01);
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
module sensorkort() {   // f.eks. SHT40- eller DHT-modul: kort 20 × 13, sensoren mot venstre
  color("#2d6fb5") translate([kortX - 0.8, Db - 13, kortZ[0]]) cube([1.6, 13, 20]);
  color("#7fc6e8") translate([kortX - 0.8 - 5.5, Db - 12, kortZ[0] + 2]) cube([5.5, 9, 12]);
}

module samlet(ex = 0) {
  color("#ECE9E3") kropp();
  color("#D99E40") kant_form();
  color("#E4E1DA") translate([0, ex, 0]) { bakplate(); d1mini(); usbplugg(); sensorkort(); }
  pir(); lyskort();
}

if (part == "kropp") rotate([90, 0, 0]) kropp();                                  // forsiden ned
else if (part == "logo") rotate([90, 0, 0]) kant_form();
else if (part == "bakplate") translate([0, 0, D]) rotate([-90, 0, 0]) bakplate();   // baksiden ned
else if (part == "a_kropp") kropp(); else if (part == "a_logo") kant_form(); else if (part == "a_bakplate") bakplate();
else if (part == "a_d1") d1mini(); else if (part == "a_plugg") usbplugg(); else if (part == "a_pir") pir();
else if (part == "a_lys") lyskort(); else if (part == "a_sensor") sensorkort();
else if (part == "eksplodert") samlet(30);
else samlet();
