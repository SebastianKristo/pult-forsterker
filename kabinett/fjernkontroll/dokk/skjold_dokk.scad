// Skjold Dokk – ladestasjon for Skjold Fjernkontroll. Parametrisk OpenSCAD.
// Fjernkontrollen står i ca. 65° med baksiden mot ryggen og halen på en hylle. En magnetisk pogo-kontakt (2 pinner,
// handelen med fjærpinner i ryggen, hunndelen flatt i fjernkontrollens bunn) gir 5 V til laderen. USB-C bak.
// Toppen (vugga) printes i Bone White, sokkelen i mørk PETG/PLA med en gullstripe rundt. Ingen støtte.
// Lisens: CC BY-NC-SA 4.0.
//
// Koordinater: X tvers (0 = midten), Y fra fronten bakover, Z opp (0 = bordet).
// Fjernkontrollens egne koordinater (x tvers, y fra halen, z fra baksiden) legges inn med fk_plass().
// part: vugge | sokkel | gull | lokk | pogo_han | samlet | med_fjernkontroll | profil
part = "samlet";
variant = "kort";                // kort | full (bare for bildene: dokka er lik for begge)
farge = "bone";                  // bone | mork

// ---------- fjernkontrollen (samme som skjold_fjernkontroll.scad) ----------
FW = 55; FH = 13.5;
FL = variant == "kort" ? 202.5 : 245.5;
hodeD = 4.3;                     // skruehodene i bunnen (hale: x 4,9 og 50,1, y 8) – nøklene i ryggen går inn her
SKRUE_HALE = [[4.9, 8], [FW - 4.9, 8]];

// ---------- pogo (samme som i skjold_fjernkontroll.scad – mål din) ----------
POGO_L = 21; POGO_KROPP = 15; POGO_B = 6; POGO_HM = 4.5; POGO_PINNE = 0.9; POGO_ORE_T = 1.2;
POGO_HULL = 1.8; POGO_HULL_A = 18; POGO_DELING = 2.8; POGO_ORE = true;
POGO_X = 40; POGO_Y = 43.5;      // hunndelens senter i fjernkontrollen

// ---------- dokka ----------
A = 65;                          // vinkel mot bordet
kl = 0.4;                        // klaring til sidene
rygg_t = 8;                      // ryggens tykkelse under fjernkontrollen
rygg_l = 78;                     // ryggens lengde langs fjernkontrollen
hylle_t = 6;                     // hyllens tykkelse under halen
leppe_h = 4;                     // leppa foran halen (dekker ikke SKJOLD-logoen, som starter 5,3 mm opp)
leppe_t = 3;
vegg = 3;                        // sidevangene
vange_h = 9;                     // vangene står så høyt opp fra ryggen
vange_l = 40;
VB = FW + 2*kl + 2*vegg;         // vuggas bredde
// sokkel
SB = 80; SY0 = -28; SY1 = 72;    // bredde, front og bakkant
SH = 12; SR = 11; SF = 1.4;      // høyde, hjørneradius, fas
gull_inn = 3.2; gull_b = 1.2; gull_d = 0.6;   // gullstripa rundt toppen
// vekt og føtter
vekt = [48, 30, 7];              // lomme foran for stålkuler eller skiver (ca. 60–90 g), lukkes med lokket
vekt_Y = -7;                     // lommens senter (Y)
led_X = 31;                      // lysdioden foran til høyre
fot_d = 10; fot_h = 1.0;         // gummiføtter
// USB-C-brikke (vanlig 6-pinners «Type-C breakout» med 5,1 kΩ på CC), bakerst
usb_kort = [12.2, 14.5, 1.6];    // b × d × t (kontakten mot bakkanten)
usb_k = [9.0, 7.4, 3.3];         // kontakten (b × d × h), stikker 0,6 mm ut over kortet
usb_X = 0;
led_d = 3.1;                     // valgfri lysdiode foran (3 mm)

hb = SH + hylle_t*sin(A) + rygg_t*cos(A);   // hjørnet mellom hylla og ryggen (z)
// fjernkontrollens koordinater → dokka
module fk_plass() { translate([0, 0, hb]) rotate([A, 0, 0]) translate([-FW/2, 0, 0]) children(); }
function fk(p) = [p[0] - FW/2, p[1]*cos(A) - p[2]*sin(A), hb + p[1]*sin(A) + p[2]*cos(A)];

module rrect(b, d, r) { offset(r) offset(-r) square([b, d]); }
module sokkel_2d(o = 0) { translate([-SB/2 + o, SY0 + o]) rrect(SB - 2*o, SY1 - SY0 - 2*o, SR - o); }

// vugga i fjernkontrollens koordinater (før plassering)
module vugge_lokal() {
  translate([-VB/2 + FW/2, -hylle_t, -rygg_t]) cube([VB, rygg_l + hylle_t, rygg_t]);                     // ryggen
  translate([-VB/2 + FW/2, -hylle_t, -rygg_t]) cube([VB, hylle_t, rygg_t + FH + kl + leppe_t]);          // hylla
  translate([-VB/2 + FW/2, 0, FH + kl]) cube([VB, leppe_h, leppe_t]);                                  // leppa
}
module vanger_lokal() {
  for (s = [0, 1]) translate([s ? FW + kl : -kl - vegg, 0, -0.01]) hull() {
    cube([vegg, vange_l, 0.01]);
    cube([vegg, vange_l - vange_h, vange_h]);
  }
}
module fk_rom() {                // plassen fjernkontrollen tar (pluss klaring til sidene)
  translate([-kl, 0, 0]) cube([FW + 2*kl, 400, FH + kl]);
  translate([-kl, leppe_h, 0]) cube([FW + 2*kl, 400, 200]);
}
module pogo_han_lokal() {        // handelen: flaten i z = 0, pinnene stikker POGO_PINNE opp
  translate([POGO_X, POGO_Y, 0]) {
    color([0.12, 0.12, 0.13]) difference() {
      union() {
        translate([0, 0, -POGO_HM/2]) cube([POGO_B, POGO_KROPP, POGO_HM], center = true);
        if (POGO_ORE) translate([0, 0, -POGO_HM]) linear_extrude(POGO_ORE_T) pogo_2d();
      }
      if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, -10]) cylinder(d = POGO_HULL, h = 20, $fn = 16);
    }
    color([0.85, 0.7, 0.35]) for (s = [-1, 1]) translate([0, s * POGO_DELING/2, -0.5]) cylinder(d = 1.2, h = 0.5 + POGO_PINNE, $fn = 16);
  }
}
module pogo_2d(o = 0) {
  if (POGO_ORE) hull() for (s = [-1, 1]) translate([0, s * (POGO_L/2 - POGO_B/2)]) circle(d = POGO_B + 2*o, $fn = 32);
  else square([POGO_B + 2*o, POGO_KROPP + 2*o], center = true);
}
module pogo_lomme_lokal() {      // lommen i ryggen: kroppen ned, ørene nederst (skrus fra undersiden av lomma)
  translate([POGO_X, POGO_Y, 0]) {
    translate([0, 0, -POGO_HM - 0.01]) linear_extrude(POGO_HM + 1) offset(0.12) square([POGO_B, POGO_KROPP], center = true);
    if (POGO_ORE) translate([0, 0, -POGO_HM - 0.01]) linear_extrude(POGO_ORE_T + 0.02) pogo_2d(0.2);
    if (POGO_ORE) for (s = [-1, 1]) translate([0, s * POGO_HULL_A/2, -POGO_HM - 2.6]) cylinder(d = 1.3, h = 3, $fn = 12);
  }
}
module nokler_lokal() {          // to knotter som går inn i skruehodene i halen: dokka kan bare tas én vei
  for (p = SKRUE_HALE) translate([p[0], p[1], -0.01]) cylinder(d1 = hodeD - 0.8, d2 = hodeD - 1.6, h = 0.8, $fn = 32);
}
// ledningskanal fra pogo-lomma ned til sokkelen (loddes på handelens pinner bakfra)
pogo_bunn = fk([POGO_X, POGO_Y, -POGO_HM]);
kanal_X = pogo_bunn[0]; kanal_Y = pogo_bunn[1];

module vugge() {
  difference() {
    union() {
      hull() {
        fk_plass() vugge_lokal();
        linear_extrude(SH + 0.01) projection() fk_plass() vugge_lokal();
      }
      fk_plass() { vanger_lokal(); nokler_lokal(); }
    }
    fk_plass() { fk_rom(); pogo_lomme_lokal(); }
    translate([0, 0, -1]) linear_extrude(SH + 1) square([400, 400], center = true);   // står på sokkelen
    translate([kanal_X, kanal_Y, SH - 1]) cylinder(d = 4, h = pogo_bunn[2] - SH + 1.5, $fn = 20);   // ledninger
    for (x = [-20, 20]) translate([x, 8, SH - 1]) cylinder(d = 4.3, h = 5, $fn = 24);                  // tapper
  }
}
module sokkel() {
  difference() {
    union() {
      hull() { linear_extrude(SH - SF) sokkel_2d(); translate([0, 0, SH - SF]) linear_extrude(SF) sokkel_2d(SF); }
      for (x = [-20, 20]) translate([x, 8, SH - 0.01]) cylinder(d = 4, h = 3.5, $fn = 24);                 // tapper til vugga
    }
    // gullstripa rundt toppen
    translate([0, 0, SH - gull_d]) linear_extrude(1) difference() { sokkel_2d(gull_inn); sokkel_2d(gull_inn + gull_b); }
    // vektlomme (åpen ned, lukkes med lokket) og gummiføtter
    translate([-vekt[0]/2, vekt_Y - vekt[1]/2, -0.01]) cube([vekt[0], vekt[1], vekt[2]]);
    translate([-vekt[0]/2 - 1, vekt_Y - vekt[1]/2 - 1, -0.01]) cube([vekt[0] + 2, vekt[1] + 2, 1.2]);   // fals for lokket
    for (x = [-SB/2 + 9, SB/2 - 9], y = [SY0 + 9, SY1 - 9]) translate([x, y, -0.01]) cylinder(d = fot_d + 0.4, h = fot_h, $fn = 32);
    // ledningskanal: fra vugga rett ned, så bakover til USB-C (z 2–5) og fram til lysdioden
    translate([kanal_X, kanal_Y, 2]) cylinder(d = 4, h = SH, $fn = 20);
    hull() { translate([kanal_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true);
             translate([usb_X, SY1 - 2.5 - usb_kort[1] + 1, 3.5]) cube([4, 4, 3], center = true); }
    hull() { translate([kanal_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true);
             translate([led_X, kanal_Y, 3.5]) cube([4, 4, 3], center = true); }
    translate([led_X - 2, SY0 + 2, 2]) cube([4, kanal_Y - SY0 - 2, 3]);
    // USB-C-brikken: lomme med kortet flatt, kontakten i bakkanten
    translate([usb_X - usb_kort[0]/2 - 0.2, SY1 - 2.5 - usb_kort[1], 2]) cube([usb_kort[0] + 0.4, usb_kort[1] + 0.2, usb_kort[2] + usb_k[2] + 0.4]);
    translate([usb_X, SY1 + 1, 2 + usb_kort[2] + usb_k[2]/2]) rotate([90, 0, 0])
      linear_extrude(4) offset(1.2) square([usb_k[0] + 0.4 - 2.4, usb_k[2] + 0.4 - 2.4], center = true);
    translate([usb_X, SY1 + 0.01, 2 + usb_kort[2] + usb_k[2]/2]) rotate([90, 0, 0])
      linear_extrude(1.2) offset(2.5) square([13.6 - 5, 7.4 - 5], center = true);                          // forsenkning for pluggen
    // lysdioden foran (valgfri)
    translate([led_X, SY0 - 1, 3.5]) rotate([-90, 0, 0]) cylinder(d = led_d, h = 4, $fn = 20);
  }
}
module gull() { translate([0, 0, SH - gull_d]) linear_extrude(gull_d) difference() { sokkel_2d(gull_inn + 0.08); sokkel_2d(gull_inn + gull_b - 0.08); } }
module lokk() { translate([-vekt[0]/2 - 0.9, vekt_Y - vekt[1]/2 - 0.9, 0]) cube([vekt[0] + 1.8, vekt[1] + 1.8, 1.15]); }
module pogo_han() { fk_plass() pogo_han_lokal(); }

c_topp = farge == "bone" ? [0.81, 0.78, 0.71] : [0.17, 0.17, 0.18];
c_sokkel = farge == "bone" ? [0.17, 0.17, 0.18] : [0.82, 0.80, 0.75];
c_gull = [0.85, 0.62, 0.25];
module samlet() { color(c_topp) vugge(); color(c_sokkel) sokkel(); color(c_gull) gull(); pogo_han(); }

if (part == "vugge") vugge();
else if (part == "sokkel") sokkel();
else if (part == "gull") gull();
else if (part == "lokk") lokk();
else if (part == "pogo_han") pogo_han();
else if (part == "samlet") samlet();
else if (part == "med_fjernkontroll") {
  samlet();
  fk_plass() {   // fjernkontrollen (STL-ene fra lag_stl.sh, montert stilling)
    D = variant == "kort" ? "../asm/" : "../asm_full/";
    color(farge == "bone" ? [0.81, 0.78, 0.71] : [0.93, 0.92, 0.89]) import(str(D, "topp.stl"));
    color(farge == "bone" ? [0.17, 0.17, 0.18] : [0.2, 0.2, 0.2]) import(str(D, "bunn.stl"));
    color([0.18, 0.18, 0.18]) import(str(D, "hetter.stl"));
    color([0.93, 0.92, 0.89]) import(str(D, "symboler.stl"));
    color(c_gull) import(str(D, "logo.stl"));
  }
}
else if (part == "profil") projection(cut = true) rotate([0, 90, 0]) samlet();
