// Skjold Jord – trådløs jordfuktsensor på batteri. Parametrisk OpenSCAD. Lisens: CC BY-NC-SA 4.0.
// Et lite, stående hus over bakken: XIAO ESP32C3, LiPo 603450 (1200 mAh) og toppen av en kapasitiv jordfuktsensor
// (v1.2/v2.0, 98 × 23 mm). Sensoren går ned gjennom en TPU-mansjett i bunnen, og et spyd ved siden av holder huset
// stødig i jorda. Lokket bak skrus fast med 4 × M2 og tettes med en TPU-pakning (tynn leppe som bøyer seg, ikke en
// tykk ring – TPU 95A er for hard til å presses sammen). USB-C (lading) peker ned og tettes med en TPU-plugg.
//
// Koordinater: x = bredde (venstre → høyre sett forfra), y = dybde (0 = forsiden), z = høyde (0 = undersiden).
// Bruk: openscad -D 'part="kropp"' -o stl/kropp.stl skjold_jord.scad
// part: kropp | lokk | logo | pakning | mansjett | plugg | samlet | eksplodert | A_<del> (montert, for sjekk_jord.py)
use <../fonter/Inter-Bold.otf>

part = "samlet";
$fn = 48;

// ---------- mål ----------
t = 2.0;                  // vegger
Wi = 57; Di = 15; Hi = 60;   // innvendig: bredde, dybde, høyde
W = Wi + 2*t; H = Hi + 2*t; D = t + Di;   // kroppen (åpen bak)
lokkT = 2.4;              // lokket
R = 6;                    // hjørneradius sett forfra

// skruer M2 × 10 selvgjengende (4 stk) i tårn i hjørnene
SKRUER = [[t + 3.5, t + 3.5], [t + Wi - 3.5, t + 3.5], [t + 3.5, t + Hi - 3.5], [t + Wi - 3.5, t + Hi - 3.5]];
bossD = 5.5; pilot = 1.7; klar = 2.4; hodeD = 4.2;

// jordfuktsensoren: kretskortet står i x–z-planet med komponentene fram, 30 mm inn i huset
senB = 23.0; senT = 1.6; senInn = 30;
senX0 = t + 7;                       // venstre kant
senY0 = t + 5.0;                     // forsiden av kortet (JST-kontakten står 4,5 mm fram)
senX = senX0 + senB/2;               // midten
skinneZ0 = t + 3.4;                  // skinnene starter over mansjettens krage

// XIAO ESP32C3 (21 × 17,5 mm), stående, USB-C ned
xiaoB = 17.5; xiaoH = 21; xiaoT = 1.0;
xiaoX0 = t + 32.5; xiaoZ0 = t + 1.6; xiaoY0 = t + 5.6;   // kortets forside (komponentene fram)
usbB = 9.0; usbH = 3.2; usbL = 7.3;                      // USB-C-kontakten (bredde, høyde fra kortet, lengde)
usbX = xiaoX0 + xiaoB/2;

// batteriet bak kortene
bat = [34, 6.0, 50];   // x, y, z (LiPo 603450)
batX0 = t + (Wi - bat[0])/2; batY0 = t + 8.0; batZ0 = t + 5;

// åpninger i bunnen
mOpn = [26.0, 5.0];                  // mansjetten (sensoren)
usbOpn = [13.0, 7.5];                // USB-C-pluggen (med støpt hette)
usbOpnY = xiaoY0 - usbH/2;           // midt på kontakten

// spydet (stødig i jorda)
spydX = W - 6.5; spydB = 4.5; spydD = 5; spydL = 45;

// ---------- hjelpere ----------
module rrect(w, h, r) { translate([r, r]) offset(r) square([w - 2*r, h - 2*r]); }
module omriss(o = 0) { translate([o, o]) rrect(W - 2*o, H - 2*o, max(0.5, R - o)); }
module i_y(y0, h) { translate([0, y0 + h, 0]) rotate([90, 0, 0]) linear_extrude(h) children(); }   // 2D i x–z → y0 … y0+h

module drape(s = 1) {   // dråpe-symbol (2D)
  scale(s) union() { circle(d = 4, $fn = 32); polygon([[-1.73, 1.0], [0, 4.2], [1.73, 1.0]]); }
}
module logo2d() {
  translate([W/2, H - 13]) text("SKJOLD", size = 4.2, font = "Inter:style=Bold", halign = "center", valign = "center", spacing = 1.25);
  translate([W/2, H - 24]) drape(1.6);
}

// ---------- kroppen ----------
module kropp() {
  difference() {
    union() {
      difference() {
        i_y(0, D) omriss();
        i_y(t, D) translate([t, t]) rrect(Wi, Hi, max(0.5, R - t));
      }
      // skruetårn
      for (s = SKRUER) translate([s[0], t - 0.01, s[1]]) rotate([-90, 0, 0]) cylinder(d = bossD, h = Di + 0.01);
      // skinner for sensorkortet (kanten går 1,0 mm inn i hver skinne)
      for (k = [[senX0 - 2.0, 0], [senX0 + senB - 1.0, 1]]) translate([k[0], t, skinneZ0])
        difference() {
          cube([3.0, senY0 + senT + 1.2 - t, senInn - (skinneZ0 - t) - 2]);
          translate([k[1] ? -0.01 : 1.8, senY0 - t - 0.2, -1]) cube([k[1] ? 1.21 : 2.21, senT + 0.4, 50]);
        }
      // hylle under batteriet
      translate([batX0 + 4, batY0 + 2.0, t - 0.01]) cube([bat[0] - 8, D - lepH - 0.3 - (batY0 + 2.0), batZ0 - t - 0.2]);
      // spydet
      translate([spydX - spydB/2, (D - spydD)/2, 0.01]) mirror([0, 0, 1]) spyd();
    }
    // skruehull
    for (s = SKRUER) translate([s[0], D - 10, s[1]]) rotate([-90, 0, 0]) cylinder(d = pilot, h = 11, $fn = 16);
    // mansjettåpningen og USB-C-åpningen i bunnen
    translate([senX, senY0 + senT/2, -1]) linear_extrude(t + 2) offset(1) square([mOpn[0] - 2, mOpn[1] - 2], center = true);
    translate([usbX, usbOpnY, -1]) linear_extrude(t + 2) offset(1.5) square([usbOpn[0] - 3, usbOpn[1] - 3], center = true);
    // SKJOLD og dråpen felt 0,5 mm inn i forsiden (gull)
    translate([0, 0.5, 0]) rotate([90, 0, 0]) linear_extrude(1) logo2d();
  }
}
module logo() { translate([0, 0.5, 0]) rotate([90, 0, 0]) linear_extrude(0.5) logo2d(); }

module spyd() {   // fra z = 0 og ned (her: oppover før mirror), spiss i enden
  hull() {
    cube([spydB, spydD, spydL - 8]);
    translate([spydB/2 - 0.4, spydD/2 - 0.4, spydL - 0.8]) cube([0.8, 0.8, 0.8]);
  }
}

// ---------- lokket ----------
lepT = 1.2; lepH = 2.0; lepSpill = 0.25;    // leppe som går inn i kroppen (styrer lokket, og en ekstra sperre for vann)
pakB = 1.8; pakBunn = 0.6; pakLeppe = 0.5; pakH = 1.4; pakSpor = 1.6;   // pakningen: fot i bunnen av et 1,6 mm dypt spor i lokket + én tynn leppe som står 0,4 mm ut
module lokk() {
  difference() {
    union() {
      i_y(D, lokkT) omriss();
      // leppen inn i kroppen
      difference() {
        i_y(D - lepH, lepH + 0.01) translate([t + lepSpill, t + lepSpill]) rrect(Wi - 2*lepSpill, Hi - 2*lepSpill, max(0.5, R - t - lepSpill));
        i_y(D - lepH - 1, lepH + 2) translate([t + lepSpill + lepT, t + lepSpill + lepT]) rrect(Wi - 2*(lepSpill + lepT), Hi - 2*(lepSpill + lepT), max(0.5, R - t - lepSpill - lepT));
        // hakk for skruetårnene
        for (s = SKRUER) translate([s[0], D - lepH - 1, s[1]]) rotate([-90, 0, 0]) cylinder(d = bossD + 0.8, h = lepH + 2);
      }
    }
    // sporet for pakningens fot (midt på veggen)
    i_y(D - 0.01, pakSpor + 0.01) pakning2d(pakB + 0.3);
    // skruehull med forsenkning
    for (s = SKRUER) translate([s[0], D - 1, s[1]]) rotate([-90, 0, 0]) {
      cylinder(d = klar, h = lokkT + 2, $fn = 16);
      translate([0, 0, 1 + lokkT - 1.2]) cylinder(d1 = klar, d2 = hodeD + 0.4, h = 1.21, $fn = 24);
    }
  }
}
module pakning2d(b) {   // ring midt på veggen (b bred), rundt skruetårnene
  difference() {
    translate([t/2 - b/2, t/2 - b/2]) rrect(W - t + b, H - t + b, max(0.5, R - t/2 + b/2));
    translate([t/2 + b/2, t/2 + b/2]) rrect(W - t - b, H - t - b, max(0.5, R - t/2 - b/2));
  }
}
// pakningen (TPU 95A): fot 1,8 × 0,6 mm i bunnen av sporet, og en leppe 0,5 mm tykk som står 0,4 mm ut av sporet. Kanten
// på kroppen presser leppen 0,4 mm inn; den bøyer seg til siden i sporet (lite kraft) og tetter.
module pakning() {
  i_y(D + pakSpor - pakBunn, pakBunn) pakning2d(pakB);
  i_y(D + pakSpor - pakBunn - pakH, pakH + 0.01) pakning2d(pakLeppe);
}

// ---------- TPU-mansjett rundt sensoren ----------
// Trykkes ned i åpningen i bunnen fra innsiden. Spalten er 0,2 mm smalere enn kortet, og ytterkanten 0,3 mm større
// enn åpningen, så den tetter begge veier. Kragen inne hindrer at den skyves ut.
kragH = 1.2; kragO = 1.2; mansH = t + kragH;
module mansjett() {
  translate([senX, senY0 + senT/2, 0]) difference() {
    union() {
      linear_extrude(mansH) offset(1) square([mOpn[0] + 0.3 - 2, mOpn[1] + 0.3 - 2], center = true);
      translate([0, 0, t + 0.01]) linear_extrude(kragH) offset(1) square([mOpn[0] + 2*kragO - 2, mOpn[1] + 2*kragO - 2], center = true);
    }
    translate([0, 0, -1]) linear_extrude(mansH + 5) square([senB - 0.2, senT - 0.2], center = true);
  }
}

// ---------- TPU-plugg for USB-C ----------
module plugg() {
  translate([usbX, usbOpnY, 0]) {
    translate([0, 0, 0.3]) linear_extrude(t - 0.3) offset(1.5) square([usbOpn[0] + 0.3 - 3, usbOpn[1] + 0.3 - 3], center = true);
    translate([0, 0, -0.8]) linear_extrude(1.1) offset(1.5) square([usbOpn[0] + 2 - 3, usbOpn[1] + 2 - 3], center = true);
    translate([usbOpn[0]/2 + 0.5, -2, -0.8]) cube([9, 4, 0.8]);   // fliken du drar i
  }
}

// ---------- referansedeler (for sjekken og bildene) ----------
module sensorkort() {
  translate([senX0, senY0, t + 1.4 - 68]) {
    cube([senB, senT, 98 - 0]);
  }
  translate([senX0 + 6, senY0 - 3.0, t + senInn - 18]) cube([11, 3.0, 14]);   // komponentene (555, motstander)
  translate([senX - 5, senY0 - 4.5 + 0.01, t + senInn - 6.0]) cube([10, 4.5, 6.0]);   // JST-PH 3 p, stående (forsiden)
  translate([senX - 4, senY0 - 4.0, t + senInn]) cube([8, 3.5, 8]);                      // pluggen og ledningene opp
}
module xiao() {
  translate([xiaoX0, xiaoY0, xiaoZ0]) cube([xiaoB, xiaoT, xiaoH]);
  translate([xiaoX0 + 2.5, xiaoY0 - 2.6, xiaoZ0 + 7]) cube([12.5, 2.6, 12]);             // skjerm/brikke
  translate([usbX - usbB/2, xiaoY0 - usbH, xiaoZ0 - 1.3]) cube([usbB, usbH, usbL]);       // USB-C
}
module batteri() { translate([batX0, batY0, batZ0]) cube(bat); }

// ---------- utskrift og montering ----------
module print_kropp() { rotate([90, 0, 0]) children(); }               // forsiden ned (y = 0 på plata)
module print_lokk() { translate([0, 0, D + lokkT]) rotate([90, 0, 0]) children(); }   // yttersiden ned
if (part == "kropp") print_kropp() kropp();
else if (part == "logo") print_kropp() logo();
else if (part == "lokk") translate([0, 0, D + lokkT]) rotate([-90, 0, 0]) lokk();   // yttersiden ned
else if (part == "pakning") translate([0, 0, D + pakSpor]) rotate([-90, 0, 0]) pakning();   // foten ned
else if (part == "mansjett") translate([0, 0, mansH]) mirror([0, 0, 1]) mansjett();   // kragen ned
else if (part == "plugg") translate([0, 0, 0.8]) plugg();
else if (part == "A_kropp") kropp();
else if (part == "A_logo") logo();
else if (part == "A_lokk") lokk();
else if (part == "A_pakning") pakning();
else if (part == "A_mansjett") mansjett();
else if (part == "A_plugg") plugg();
else if (part == "A_sensor") sensorkort();
else if (part == "A_xiao") xiao();
else if (part == "A_batteri") batteri();
else if (part == "samlet" || part == "eksplodert") {
  e = part == "eksplodert" ? 12 : 0;
  color([0.18, 0.18, 0.19]) kropp(); color([0.85, 0.62, 0.25]) logo();
  color([0.24, 0.24, 0.25]) translate([0, 2*e, 0]) lokk();
  color([0.29, 0.50, 0.72]) { translate([0, e, 0]) pakning(); translate([0, 0, e/2]) mansjett(); translate([0, 0, -e]) plugg(); }
  color([0.08, 0.3, 0.12]) translate([0, 0, -e]) sensorkort(); color([0.1, 0.1, 0.12]) xiao();
  color([0.65, 0.68, 0.72]) translate([0, e, 0]) batteri();
}
